import json
import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, MutableMapping, Optional, Tuple, Type, Union

from .boto3_proxy import SessionProxy, _get_boto_session
from .exceptions import InternalFailure, InvalidRequest, _HandlerError
from .interface import (
    BaseHookHandlerRequest,
    HandlerErrorCode,
    HookInvocationPoint,
    HookProgressEvent,
    HookStatus,
    OperationStatus,
    ProgressEvent,
)
from .log_delivery import HookProviderLogHandler
from .metrics import MetricsPublisherProxy
from .utils import (
    BaseModel,
    Credentials,
    HookInvocationRequest,
    HookTestEvent,
    KitchenSinkEncoder,
    LambdaContext,
    UnmodelledHookRequest,
)

LOG = logging.getLogger(__name__)

HandlerSignature = Callable[
    [Optional[SessionProxy], Any, MutableMapping[str, Any], Any], ProgressEvent
]


def _ensure_serialize(
    entrypoint: Callable[
        [Any, MutableMapping[str, Any], Any],
        Union[ProgressEvent, MutableMapping[str, Any]],
    ]
) -> Callable[[Any, MutableMapping[str, Any], Any], Any]:
    @wraps(entrypoint)
    def wrapper(self: Any, event: MutableMapping[str, Any], context: Any) -> Any:
        try:
            response = entrypoint(self, event, context)
            serialized = json.dumps(response, cls=KitchenSinkEncoder)
        except Exception:  # pylint: disable=broad-except
            return Hook._create_progress_response(  # pylint: disable=protected-access
                ProgressEvent.failed(HandlerErrorCode.InternalFailure),
                None,
            )._serialize()
        return json.loads(serialized)

    return wrapper


class Hook:
    def __init__(
        self,
        type_name: str,
        type_configuration_model_cls: Type[BaseModel],
        log_format: Optional[logging.Formatter] = None,
    ) -> None:
        self.type_name = type_name
        self._type_configuration_model_cls: Type[
            BaseModel
        ] = type_configuration_model_cls
        self._handlers: MutableMapping[HookInvocationPoint, HandlerSignature] = {}
        self.log_format = log_format

    def handler(
        self, invocation_point: HookInvocationPoint
    ) -> Callable[[HandlerSignature], HandlerSignature]:
        def _add_handler(f: HandlerSignature) -> HandlerSignature:
            self._handlers[invocation_point] = f
            return f

        return _add_handler

    def _invoke_handler(  # pylint: disable=too-many-arguments
        self,
        session: Optional[SessionProxy],
        request: BaseHookHandlerRequest,
        invocation_point: HookInvocationPoint,
        callback_context: MutableMapping[str, Any],
        type_configuration: Optional[BaseModel],
    ) -> ProgressEvent:
        try:
            handler = self._handlers[invocation_point]
        except KeyError:
            return ProgressEvent.failed(
                HandlerErrorCode.InternalFailure,
                f"No handler for {invocation_point.name}",
            )

        return handler(session, request, callback_context, type_configuration)

    def _parse_test_request(
        self, event_data: MutableMapping[str, Any]
    ) -> Tuple[
        Optional[SessionProxy],
        BaseHookHandlerRequest,
        HookInvocationPoint,
        MutableMapping[str, Any],
        Optional[BaseModel],
    ]:
        try:
            event = HookTestEvent(**event_data)
            creds = Credentials(**event.credentials)
            request: BaseHookHandlerRequest = UnmodelledHookRequest(
                **event.request
            ).to_modelled()

            session = _get_boto_session(creds, event.region)
            invocation_point = HookInvocationPoint[event.actionInvocationPoint]
        except Exception as e:  # pylint: disable=broad-except
            LOG.exception("Invalid request")
            raise InternalFailure(f"{e} ({type(e).__name__})") from e
        return (
            session,
            request,
            invocation_point,
            event.callbackContext or {},
            # pylint: disable=protected-access
            None
            if not self._type_configuration_model_cls
            else self._type_configuration_model_cls._deserialize(
                event.typeConfiguration or {}
            ),
        )

    @_ensure_serialize
    def test_entrypoint(
        self, event: MutableMapping[str, Any], _context: Any
    ) -> ProgressEvent:
        msg = "Uninitialized"
        try:
            (
                session,
                request,
                invocation_point,
                callback_context,
                type_configuration,
            ) = self._parse_test_request(event)
            return self._invoke_handler(
                session, request, invocation_point, callback_context, type_configuration
            )
        except _HandlerError as e:
            LOG.exception("Handler error")
            return e.to_progress_event()
        except Exception:  # pylint: disable=broad-except
            LOG.exception("Exception caught")
        except BaseException:  # pylint: disable=broad-except # noqa: B036
            LOG.critical("Base exception caught (this is usually bad)", exc_info=True)
        return ProgressEvent.failed(HandlerErrorCode.InternalFailure, msg)

    @staticmethod
    def _parse_request(
        event_data: MutableMapping[str, Any]
    ) -> Tuple[
        Tuple[Optional[SessionProxy], Optional[SessionProxy]],
        HookInvocationPoint,
        MutableMapping[str, Any],
        HookInvocationRequest,
    ]:
        try:
            event = HookInvocationRequest.deserialize(event_data)
            caller_sess = _get_boto_session(event.requestData.callerCredentials)
            provider_sess = _get_boto_session(event.requestData.providerCredentials)
            # credentials are used when rescheduling, so can't zero them out (for now)
            invocation_point = HookInvocationPoint[event.actionInvocationPoint]
            callback_context = event.requestContext.callbackContext or {}
        except Exception as e:
            LOG.exception("Invalid request")
            raise InvalidRequest(f"{e} ({type(e).__name__})") from e

        return (caller_sess, provider_sess), invocation_point, callback_context, event

    def _cast_hook_request(
        self, request: HookInvocationRequest
    ) -> Tuple[BaseHookHandlerRequest, Optional[BaseModel]]:
        try:
            handler_request = UnmodelledHookRequest(
                clientRequestToken=request.clientRequestToken,
                awsAccountId=request.awsAccountId,
                stackId=request.stackId,
                changeSetId=request.changeSetId,
                hookTypeName=request.hookTypeName,
                hookTypeVersion=request.hookTypeVersion,
                invocationPoint=HookInvocationPoint[request.actionInvocationPoint],
                targetName=request.requestData.targetName,
                targetType=request.requestData.targetType,
                targetLogicalId=request.requestData.targetLogicalId,
                targetModel=request.requestData.targetModel,
            ).to_modelled()
            # pylint: disable=protected-access
            type_configuration = self._type_configuration_model_cls._deserialize(
                request.hookModel or {}
            )

            return handler_request, type_configuration

        except Exception as e:  # pylint: disable=broad-except
            LOG.exception("Invalid request")
            raise InvalidRequest(f"{e} ({type(e).__name__})") from e

    # TODO: refactor to reduce branching and locals
    @_ensure_serialize  # noqa: C901
    def __call__(  # pylint: disable=too-many-locals  # noqa: C901
        self, event_data: MutableMapping[str, Any], context: LambdaContext
    ) -> MutableMapping[str, Any]:
        logs_setup = False

        def print_or_log(message: str) -> None:
            if logs_setup:
                LOG.exception(message, exc_info=True)
            else:
                print(message)
                traceback.print_exc()

        try:
            sessions, invocation_point, callback, event = self._parse_request(
                event_data
            )
            caller_sess, provider_sess = sessions

            request, type_configuration = self._cast_hook_request(event)

            metrics = MetricsPublisherProxy()
            if event.requestData.providerLogGroupName and provider_sess:
                HookProviderLogHandler.setup(event, provider_sess, self.log_format)
                logs_setup = True
                metrics.add_hook_metrics_publisher(
                    provider_sess, event.hookTypeName, event.awsAccountId
                )

            metrics.publish_invocation_metric(datetime.utcnow(), invocation_point)
            start_time = datetime.utcnow()
            error = None

            try:
                progress = self._invoke_handler(
                    caller_sess, request, invocation_point, callback, type_configuration
                )
            except Exception as e:  # pylint: disable=broad-except
                error = e

            m_secs = (datetime.utcnow() - start_time).total_seconds() * 1000.0
            metrics.publish_duration_metric(datetime.utcnow(), invocation_point, m_secs)
            if error:
                metrics.publish_exception_metric(
                    datetime.utcnow(), invocation_point, error
                )
                raise error
        except _HandlerError as e:
            print_or_log("Handler error")
            progress = e.to_progress_event()
        except Exception as e:  # pylint: disable=broad-except
            print_or_log(f"Exception caught {e}")
            progress = ProgressEvent.failed(HandlerErrorCode.InternalFailure)
        except BaseException as e:  # pylint: disable=broad-except # noqa: B036
            print_or_log(f"Base exception caught (this is usually bad) {e}")
            progress = ProgressEvent.failed(HandlerErrorCode.InternalFailure)

        # use the raw event_data as a last-ditch attempt to call back if the
        # request is invalid
        return self._create_progress_response(
            progress, event_data
        )._serialize()  # pylint: disable=protected-access

    @staticmethod
    def _create_progress_response(
        progress_event: ProgressEvent, request: Optional[MutableMapping[str, Any]]
    ) -> HookProgressEvent:
        response = HookProgressEvent(Hook._get_hook_status(progress_event.status))
        response.result = progress_event.result
        response.message = progress_event.message
        response.errorCode = progress_event.errorCode
        response.callbackContext = progress_event.callbackContext
        response.callbackDelaySeconds = progress_event.callbackDelaySeconds
        response.errorCode = progress_event.errorCode
        if request:
            response.clientRequestToken = request.get("clientRequestToken")
        return response

    @staticmethod
    def _get_hook_status(operation_status: OperationStatus) -> HookStatus:
        if operation_status == OperationStatus.PENDING:
            hook_status = HookStatus.PENDING
        elif operation_status == OperationStatus.IN_PROGRESS:
            hook_status = HookStatus.IN_PROGRESS
        elif operation_status == OperationStatus.SUCCESS:
            hook_status = HookStatus.SUCCESS
        elif operation_status == OperationStatus.CHANGE_SET_SUCCESS_SKIP_STACK_HOOK:
            hook_status = HookStatus.CHANGE_SET_SUCCESS_SKIP_STACK_HOOK
        else:
            hook_status = HookStatus.FAILED
        return hook_status
