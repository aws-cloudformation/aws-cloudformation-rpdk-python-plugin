# pylint: disable=redefined-outer-name,protected-access,line-too-long
from dataclasses import dataclass

import pytest
from cloudformation_cli_python_lib import Hook
from cloudformation_cli_python_lib.exceptions import InternalFailure, InvalidRequest
from cloudformation_cli_python_lib.hook import _ensure_serialize
from cloudformation_cli_python_lib.interface import (
    BaseModel,
    HandlerErrorCode,
    HookInvocationPoint,
    HookProgressEvent,
    HookStatus,
    OperationStatus,
    ProgressEvent,
)
from cloudformation_cli_python_lib.utils import (
    Credentials,
    HookInvocationRequest,
    HookRequestData,
)

import json
from datetime import datetime
from typing import Any, Mapping
from unittest.mock import Mock, call, patch, sentinel

ENTRYPOINT_PAYLOAD = {
    "awsAccountId": "123456789012",
    "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe",
    "region": "us-east-1",
    "actionInvocationPoint": "CREATE_PRE_PROVISION",
    "hookTypeName": "AWS::Test::TestHook",
    "hookTypeVersion": "1.0",
    "requestContext": {
        "invocation": 1,
        "callbackContext": {},
    },
    "requestData": {
        "callerCredentials": '{"accessKeyId": "IASAYK835GAIFHAHEI23", "secretAccessKey": "66iOGPN5LnpZorcLr8Kh25u8AbjHVllv5poh2O0", "sessionToken": "lameHS2vQOknSHWhdFYTxm2eJc1JMn9YBNI4nV4mXue945KPL6DHfW8EsUQT5zwssYEC1NvYP9yD6Y5s5lKR3chflOHPFsIe6eqg"}',  # noqa: B950
        "providerCredentials": '{"accessKeyId": "HDI0745692Y45IUTYR78", "secretAccessKey": "4976TUYVI2345GW87ERYG823RF87GY9EIUH452I3", "sessionToken": "842HYOFIQAEUDF78R8T7IU43HSADYGIFHBJSDHFA87SDF9PYvN1CEYASDUYFT5TQ97YASIHUDFAIUEYRISDKJHFAYSUDTFSDFADS"}',  # noqa: B950
        "providerLogGroupName": "providerLoggingGroupName",
        "targetName": "AWS::Test::Resource",
        "targetType": "RESOURCE",
        "targetLogicalId": "myResource",
        "hookEncryptionKeyArn": None,
        "hookEncryptionKeyRole": None,
        "targetModel": {
            "resourceProperties": sentinel.resource_properties,
            "previousResourceProperties": sentinel.previous_resource_properties,
        },
    },
    "stackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/SampleStack/e"
    "722ae60-fe62-11e8-9a0e-0ae8cc519968",
    "hookModel": sentinel.type_configuration,
}

STACK_LEVEL_HOOK_ENTRYPOINT_PAYLOAD = {
    "awsAccountId": "123456789012",
    "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe",
    "region": "us-east-1",
    "actionInvocationPoint": "CREATE_PRE_PROVISION",
    "hookTypeName": "AWS::Test::TestHook",
    "hookTypeVersion": "1.0",
    "requestContext": {
        "invocation": 1,
        "callbackContext": {},
    },
    "requestData": {
        "callerCredentials": '{"accessKeyId": "IASAYK835GAIFHAHEI23", "secretAccessKey": "66iOGPN5LnpZorcLr8Kh25u8AbjHVllv5poh2O0", "sessionToken": "lameHS2vQOknSHWhdFYTxm2eJc1JMn9YBNI4nV4mXue945KPL6DHfW8EsUQT5zwssYEC1NvYP9yD6Y5s5lKR3chflOHPFsIe6eqg"}',  # noqa: B950
        "providerCredentials": '{"accessKeyId": "HDI0745692Y45IUTYR78", "secretAccessKey": "4976TUYVI2345GW87ERYG823RF87GY9EIUH452I3", "sessionToken": "842HYOFIQAEUDF78R8T7IU43HSADYGIFHBJSDHFA87SDF9PYvN1CEYASDUYFT5TQ97YASIHUDFAIUEYRISDKJHFAYSUDTFSDFADS"}',  # noqa: B950
        "providerLogGroupName": "providerLoggingGroupName",
        "targetName": "STACK",
        "targetType": "STACK",
        "targetLogicalId": "myStack",
        "hookEncryptionKeyArn": None,
        "hookEncryptionKeyRole": None,
        "payload": "https://someS3PresignedURL",
        "targetModel": {},
    },
    "stackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/SampleStack/e"
    "722ae60-fe62-11e8-9a0e-0ae8cc519968",
    "hookModel": sentinel.type_configuration,
}


TYPE_NAME = "Test::Foo::Bar"


@pytest.fixture
def hook():
    return Hook(TYPE_NAME, Mock)


def patch_and_raise(hook, str_to_patch, exc_cls, entrypoint):
    with patch.object(hook, str_to_patch) as mock_parse:
        mock_parse.side_effect = exc_cls("hahaha")
        # "un-apply" decorator
        event = entrypoint.__wrapped__(hook, {}, None)  # pylint: disable=no-member
    return event


def test_entrypoint_handler_error(hook):
    with patch("cloudformation_cli_python_lib.hook.HookProviderLogHandler.setup"):
        event = hook.__call__.__wrapped__(hook, {}, None)  # pylint: disable=no-member
    assert event["hookStatus"] == HookStatus.FAILED.value
    assert event["errorCode"] == HandlerErrorCode.InvalidRequest


def test_entrypoint_success():
    hook = Hook(TYPE_NAME, Mock())
    event = ProgressEvent(status=OperationStatus.SUCCESS, message="")
    mock_handler = hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)(
        Mock(return_value=event)
    )

    with patch(
        "cloudformation_cli_python_lib.hook.HookProviderLogHandler.setup"
    ) as mock_log_delivery, patch(
        "cloudformation_cli_python_lib.hook._get_boto_session", autospec=True
    ):
        event = hook.__call__.__wrapped__(  # pylint: disable=no-member
            hook, ENTRYPOINT_PAYLOAD, None
        )
    mock_log_delivery.assert_called_once()

    assert event == {
        "hookStatus": HookStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": "",
        "callbackDelaySeconds": 0,
        "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe",
    }

    mock_handler.assert_called_once()


def test_entrypoint_handler_raises():
    @dataclass
    class TypeConfigurationModel(BaseModel):
        a_string: str

        @classmethod
        def _deserialize(cls, json_data):
            return cls("test")

    hook = Hook(Mock(), TypeConfigurationModel)

    with patch(
        "cloudformation_cli_python_lib.hook.HookProviderLogHandler.setup"
    ), patch(
        "cloudformation_cli_python_lib.hook.MetricsPublisherProxy"
    ) as mock_metrics, patch(
        "cloudformation_cli_python_lib.hook.Hook._invoke_handler"
    ) as mock__invoke_handler:
        mock__invoke_handler.side_effect = InvalidRequest("handler failed")
        event = hook.__call__.__wrapped__(  # pylint: disable=no-member
            hook, ENTRYPOINT_PAYLOAD, None
        )

    mock_metrics.return_value.publish_exception_metric.assert_called_once()

    assert event == {
        "errorCode": "InvalidRequest",
        "hookStatus": "FAILED",
        "message": "handler failed",
        "callbackDelaySeconds": 0,
        "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe",
    }


def test_entrypoint_with_context():
    payload = ENTRYPOINT_PAYLOAD.copy()
    payload["callbackContext"] = {"a": "b"}
    hook = Hook(TYPE_NAME, Mock())
    event = ProgressEvent(
        status=OperationStatus.SUCCESS, message="", callbackContext={"c": "d"}
    )
    mock_handler = hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)(
        Mock(return_value=event)
    )

    with patch(
        "cloudformation_cli_python_lib.hook.HookProviderLogHandler.setup"
    ), patch("cloudformation_cli_python_lib.hook._get_boto_session", autospec=True):
        hook.__call__.__wrapped__(hook, payload, None)  # pylint: disable=no-member

    mock_handler.assert_called_once()


def test_entrypoint_success_without_caller_provider_creds():
    hook = Hook(TYPE_NAME, Mock())
    event = ProgressEvent(status=OperationStatus.SUCCESS, message="")
    hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)(Mock(return_value=event))

    payload = ENTRYPOINT_PAYLOAD.copy()
    payload["requestData"] = payload["requestData"].copy()

    expected = {
        "hookStatus": HookStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": "",
        "callbackDelaySeconds": 0,
        "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe",
    }

    with patch("cloudformation_cli_python_lib.hook.HookProviderLogHandler.setup"):
        # Credentials are defined in payload, but null
        payload["requestData"]["providerCredentials"] = None
        payload["requestData"]["callerCredentials"] = None
        event = hook.__call__.__wrapped__(  # pylint: disable=no-member
            hook, payload, None
        )
        assert event == expected

        # Credentials are undefined in payload
        del payload["requestData"]["providerCredentials"]
        del payload["requestData"]["callerCredentials"]

        event = hook.__call__.__wrapped__(  # pylint: disable=no-member
            hook, payload, None
        )
        assert event == expected


def test_cast_hook_request_invalid_request(hook):
    request = HookInvocationRequest.deserialize(ENTRYPOINT_PAYLOAD)
    request.requestData = None
    with pytest.raises(InvalidRequest) as excinfo:
        hook._cast_hook_request(request)

    assert "AttributeError" in str(excinfo.value)


def test__parse_request_valid_request_and__cast_hook_request():
    mock_type_configuration_model = Mock(spec_set=["_deserialize"])
    mock_type_configuration_model._deserialize.side_effect = [
        sentinel.type_configuration
    ]

    hook = Hook(TYPE_NAME, mock_type_configuration_model)

    with patch("cloudformation_cli_python_lib.hook._get_boto_session") as mock_session:
        ret = hook._parse_request(ENTRYPOINT_PAYLOAD)
    sessions, invocation_point, callback_context, request = ret

    mock_session.assert_has_calls(
        [
            call(
                Credentials(
                    **json.loads(ENTRYPOINT_PAYLOAD["requestData"]["callerCredentials"])
                )
            ),
            call(
                Credentials(
                    **json.loads(
                        ENTRYPOINT_PAYLOAD["requestData"]["providerCredentials"]
                    )
                )
            ),
        ],
        any_order=True,
    )

    # credentials are used when rescheduling, so can't zero them out (for now)
    assert request.requestData.callerCredentials is not None
    assert request.requestData.providerCredentials is not None
    assert request.hookModel is sentinel.type_configuration

    caller_sess, provider_sess = sessions
    assert caller_sess is mock_session.return_value
    assert provider_sess is mock_session.return_value

    assert invocation_point == HookInvocationPoint.CREATE_PRE_PROVISION
    assert callback_context == {}

    modeled_request, modeled_type_configuration = hook._cast_hook_request(request)

    mock_type_configuration_model._deserialize.assert_has_calls(
        [call(sentinel.type_configuration)]
    )
    assert modeled_request.clientRequestToken == request.clientRequestToken
    assert modeled_request.hookContext.targetName == "AWS::Test::Resource"
    assert (
        modeled_request.hookContext.targetModel.get("resourceProperties")
        is sentinel.resource_properties
    )
    assert (
        modeled_request.hookContext.targetModel.get("previousResourceProperties")
        is sentinel.previous_resource_properties
    )
    assert modeled_request.hookContext.targetLogicalId == "myResource"
    assert modeled_type_configuration is sentinel.type_configuration


@pytest.mark.parametrize("exc_cls", [Exception, BaseException])
def test_entrypoint_uncaught_exception(hook, exc_cls):
    with patch("cloudformation_cli_python_lib.hook.HookProviderLogHandler.setup"):
        event = patch_and_raise(hook, "_parse_request", exc_cls, hook.__call__)
    assert event["hookStatus"] == HookStatus.FAILED
    assert event["errorCode"] == HandlerErrorCode.InternalFailure


def test__ensure_serialize_uses_custom_encoder():
    now = datetime.now()

    @_ensure_serialize
    def wrapped(_self, _event, _context):
        return {"foo": now}

    json = wrapped(None, None, None)
    assert json == {"foo": now.isoformat()}


def test__ensure_serialize_invalid_returns_progress_event():
    @_ensure_serialize
    def wrapped(_self, _event, _context):
        class Unserializable:
            pass

        return {"foo": Unserializable()}

    serialized = wrapped(None, None, None)
    event = HookProgressEvent.failed(HandlerErrorCode.InternalFailure)
    try:
        # Python 3.7/3.8
        assert serialized == event._serialize()
    except AssertionError:
        # Python 3.6
        assert serialized == event._serialize()


def test_handler_decorator(hook):
    deco = hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)
    assert deco(sentinel.mock_handler) is sentinel.mock_handler
    assert hook._handlers == {
        HookInvocationPoint.CREATE_PRE_PROVISION: sentinel.mock_handler
    }


def test__invoke_handler_not_found(hook):
    actual = hook._invoke_handler(
        None, None, HookInvocationPoint.CREATE_PRE_PROVISION, {}, None
    )
    expected = ProgressEvent.failed(
        HandlerErrorCode.InternalFailure, "No handler for CREATE_PRE_PROVISION"
    )
    assert actual == expected


def test__invoke_handler_was_found(hook):
    progress_event = ProgressEvent(status=OperationStatus.IN_PROGRESS)
    mock_handler = hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)(
        Mock(return_value=progress_event)
    )

    resp = hook._invoke_handler(
        sentinel.session,
        sentinel.request,
        HookInvocationPoint.CREATE_PRE_PROVISION,
        sentinel.context,
        sentinel.type_configuration,
    )
    assert resp is progress_event
    mock_handler.assert_called_once_with(
        sentinel.session,
        sentinel.request,
        sentinel.context,
        sentinel.type_configuration,
    )


@pytest.mark.parametrize("event,messages", [({}, ("missing", "credentials"))])
def test__parse_test_request_invalid_request(hook, event, messages):
    with pytest.raises(InternalFailure) as excinfo:
        hook._parse_test_request(event)

    for msg in messages:
        assert msg in str(excinfo.value), msg


def test__parse_test_request_valid_request():
    mock_type_configuration_model = Mock(spec_set=["_deserialize"])
    mock_type_configuration_model._deserialize.side_effect = [
        sentinel.type_configuration
    ]

    payload = {
        "credentials": {"accessKeyId": "", "secretAccessKey": "", "sessionToken": ""},
        "actionInvocationPoint": "CREATE_PRE_PROVISION",
        "request": {
            "clientRequestToken": "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2b",
            "hookContext": {
                "awsAccountId": "123456789012",
                "targetName": "AWS::Test::Resource",
                "targetModel": {
                    "resourceProperties": sentinel.resource_properties,
                    "previousResourceProperties": sentinel.previous_resource_properties,
                },
            },
        },
        "callbackContext": None,
        "typeConfiguration": sentinel.type_configuration,
    }

    hook = Hook(TYPE_NAME, mock_type_configuration_model)

    with patch("cloudformation_cli_python_lib.hook._get_boto_session") as mock_session:
        ret = hook._parse_test_request(payload)
    session, request, invocation_point, callback_context, type_configuration = ret

    mock_session.assert_called_once()
    assert session is mock_session.return_value

    assert request.clientRequestToken == "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2b"
    mock_type_configuration_model._deserialize.assert_has_calls(
        [call(sentinel.type_configuration)]
    )
    assert request.hookContext.targetName == "AWS::Test::Resource"
    assert (
        request.hookContext.targetModel.get("resourceProperties")
        is sentinel.resource_properties
    )
    assert (
        request.hookContext.targetModel.get("previousResourceProperties")
        is sentinel.previous_resource_properties
    )
    assert request.hookContext.targetLogicalId is None
    assert type_configuration is sentinel.type_configuration

    assert invocation_point == HookInvocationPoint.CREATE_PRE_PROVISION
    assert callback_context == {}


def test_test_entrypoint_handler_error(hook):
    # "un-apply" decorator
    event = hook.test_entrypoint.__wrapped__(  # pylint: disable=no-member
        hook, {}, None
    )
    assert event.status == OperationStatus.FAILED
    assert event.errorCode == HandlerErrorCode.InternalFailure


@pytest.mark.parametrize("exc_cls", [Exception, BaseException])
def test_test_entrypoint_uncaught_exception(hook, exc_cls):
    event = patch_and_raise(hook, "_parse_test_request", exc_cls, hook.test_entrypoint)
    assert event.status == HookStatus.FAILED
    assert event.errorCode == HandlerErrorCode.InternalFailure


def test_test_entrypoint_success():
    mock_type_configuration_model = Mock(spec_set=["_deserialize"])
    mock_type_configuration_model._deserialize.side_effect = [
        sentinel.type_configuration
    ]

    hook = Hook(TYPE_NAME, mock_type_configuration_model)
    progress_event = ProgressEvent(status=OperationStatus.SUCCESS)
    mock_handler = hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)(
        Mock(return_value=progress_event)
    )

    payload = {
        "credentials": {"accessKeyId": "", "secretAccessKey": "", "sessionToken": ""},
        "actionInvocationPoint": "CREATE_PRE_PROVISION",
        "request": {
            "clientRequestToken": "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2b",
        },
        "typeConfiguration": sentinel.type_configuration,
    }

    event = hook.test_entrypoint.__wrapped__(  # pylint: disable=no-member
        hook, payload, None
    )
    assert event is progress_event

    mock_type_configuration_model._deserialize.assert_has_calls(
        [call(sentinel.type_configuration)]
    )
    mock_handler.assert_called_once()


@pytest.mark.parametrize(
    "operation_status,hook_status",
    [
        (OperationStatus.PENDING, HookStatus.PENDING),
        (OperationStatus.IN_PROGRESS, HookStatus.IN_PROGRESS),
        (OperationStatus.SUCCESS, HookStatus.SUCCESS),
        (OperationStatus.FAILED, HookStatus.FAILED),
        (
            OperationStatus.CHANGE_SET_SUCCESS_SKIP_STACK_HOOK,
            HookStatus.CHANGE_SET_SUCCESS_SKIP_STACK_HOOK,
        ),
    ],
)
def test_get_hook_status(operation_status, hook_status):
    assert hook_status == Hook._get_hook_status(operation_status)


def test__hook_request_data_remote_payload():
    non_remote_input = HookRequestData(
        targetName="someTargetName",
        targetType="someTargetModel",
        targetLogicalId="someTargetLogicalId",
        targetModel={"resourceProperties": {"propKeyA": "propValueA"}},
    )
    assert non_remote_input.is_hook_invocation_payload_remote() is False

    non_remote_input_1 = HookRequestData(
        targetName="someTargetName",
        targetType="someTargetModel",
        targetLogicalId="someTargetLogicalId",
        targetModel={"resourceProperties": {"propKeyA": "propValueA"}},
        payload="https://someUrl",
    )
    assert non_remote_input_1.is_hook_invocation_payload_remote() is False

    remote_input = HookRequestData(
        targetName="someTargetName",
        targetType="someTargetModel",
        targetLogicalId="someTargetLogicalId",
        targetModel={},
        payload="https://someUrl",
    )
    assert remote_input.is_hook_invocation_payload_remote() is True


def test__test_stack_level_hook_input(hook):
    hook = Hook(TYPE_NAME, Mock())

    with patch(
        "cloudformation_cli_python_lib.utils.requests.Session.get"
    ) as mock_requests_lib:
        mock_requests_lib.return_value = MockResponse(200, {"foo": "bar"})
        _, _, _, req = hook._parse_request(STACK_LEVEL_HOOK_ENTRYPOINT_PAYLOAD)

    assert req.requestData.targetName == "STACK"
    assert req.requestData.targetType == "STACK"
    assert req.requestData.targetLogicalId == "myStack"
    assert req.requestData.targetModel == {"foo": "bar"}


def test__test_stack_level_hook_input_failed_s3_download(hook):
    hook = Hook(TYPE_NAME, Mock())

    with patch(
        "cloudformation_cli_python_lib.utils.requests.Session.get"
    ) as mock_requests_lib:
        mock_requests_lib.return_value = MockResponse(404, {"foo": "bar"})
        _, _, _, req = hook._parse_request(STACK_LEVEL_HOOK_ENTRYPOINT_PAYLOAD)

    assert req.requestData.targetName == "STACK"
    assert req.requestData.targetType == "STACK"
    assert req.requestData.targetLogicalId == "myStack"
    assert req.requestData.targetModel == {}


@dataclass
class MockResponse:
    status_code: int
    _json: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self._json
