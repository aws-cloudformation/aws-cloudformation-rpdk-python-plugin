# pylint: disable=invalid-name
from dataclasses import dataclass

import logging
from enum import Enum, auto
from typing import Any, List, Mapping, MutableMapping, Optional, Type

LOG = logging.getLogger(__name__)


class _AutoName(Enum):
    @staticmethod
    # pylint: disable=arguments-differ
    def _generate_next_value_(
        name: str, _start: int, _count: int, _last_values: List[str]
    ) -> str:
        return name


class Action(str, _AutoName):
    CREATE = auto()
    READ = auto()
    UPDATE = auto()
    DELETE = auto()
    LIST = auto()


class HookInvocationPoint(str, _AutoName):
    CREATE_PRE_PROVISION = auto()
    UPDATE_PRE_PROVISION = auto()
    DELETE_PRE_PROVISION = auto()


class StandardUnit(str, _AutoName):
    Count = auto()
    Milliseconds = auto()


class MetricTypes(str, _AutoName):
    HandlerException = auto()
    HandlerInvocationCount = auto()
    HandlerInvocationDuration = auto()


class OperationStatus(str, _AutoName):
    PENDING = auto()
    IN_PROGRESS = auto()
    SUCCESS = auto()
    CHANGE_SET_SUCCESS_SKIP_STACK_HOOK = auto()
    FAILED = auto()


class HookStatus(str, _AutoName):
    PENDING = auto()
    IN_PROGRESS = auto()
    SUCCESS = auto()
    CHANGE_SET_SUCCESS_SKIP_STACK_HOOK = auto()
    FAILED = auto()


class HandlerErrorCode(str, _AutoName):
    NotUpdatable = auto()
    InvalidRequest = auto()
    AccessDenied = auto()
    InvalidCredentials = auto()
    AlreadyExists = auto()
    NotFound = auto()
    ResourceConflict = auto()
    Throttling = auto()
    ServiceLimitExceeded = auto()
    NotStabilized = auto()
    GeneralServiceException = auto()
    ServiceInternalError = auto()
    NetworkFailure = auto()
    InternalFailure = auto()
    InvalidTypeConfiguration = auto()
    HandlerInternalFailure = auto()
    NonCompliant = auto()
    UnsupportedTarget = auto()
    Unknown = auto()


class BaseModel:
    def _serialize(self) -> Mapping[str, Any]:
        return {
            k: self._serialize_item(v)
            for k, v in self.__dict__.items()
            if v is not None
        }

    def _serialize_item(self, v: Any) -> Any:
        if isinstance(v, list):
            return self._serialize_list(v)
        if isinstance(v, BaseModel):
            return v._serialize()  # pylint: disable=protected-access
        return v

    def _serialize_list(self, src_list: List[Any]) -> List[Any]:
        return [self._serialize_item(i) for i in src_list]

    @classmethod
    def _deserialize(
        cls: Type["BaseModel"], json_data: Optional[Mapping[str, Any]]
    ) -> Optional["BaseModel"]:
        raise NotImplementedError()


# pylint: disable=too-many-instance-attributes
@dataclass
class ProgressEvent:
    # pylint: disable=invalid-name
    status: OperationStatus
    errorCode: Optional[HandlerErrorCode] = None
    message: str = ""
    result: Optional[str] = None
    callbackContext: Optional[MutableMapping[str, Any]] = None
    callbackDelaySeconds: int = 0
    resourceModel: Optional[BaseModel] = None
    resourceModels: Optional[List[BaseModel]] = None
    nextToken: Optional[str] = None

    def _serialize(self) -> MutableMapping[str, Any]:
        # to match Java serialization, which drops `null` values, and the
        # contract tests currently expect this also
        ser = {k: v for k, v in self.__dict__.items() if v is not None}

        # mutate to what's expected in the response

        ser["status"] = ser.pop("status").name

        if self.resourceModel:
            # pylint: disable=protected-access
            ser["resourceModel"] = self.resourceModel._serialize()
        if self.resourceModels:
            ser["resourceModels"] = [
                # pylint: disable=protected-access
                model._serialize()
                for model in self.resourceModels
            ]
        if self.errorCode:
            ser["errorCode"] = self.errorCode.name
        return ser

    @classmethod
    def failed(
        cls: Type["ProgressEvent"],
        error_code: HandlerErrorCode,
        message: str = "",
        result: Optional[str] = None,
    ) -> "ProgressEvent":
        return cls(
            status=OperationStatus.FAILED,
            errorCode=error_code,
            message=message,
            result=result,
        )


@dataclass
class BaseResourceHandlerRequest:
    # pylint: disable=invalid-name
    clientRequestToken: str
    desiredResourceState: Optional[BaseModel]
    previousResourceState: Optional[BaseModel]
    desiredResourceTags: Optional[Mapping[str, Any]]
    previousResourceTags: Optional[Mapping[str, Any]]
    systemTags: Optional[Mapping[str, Any]]
    previousSystemTags: Optional[Mapping[str, Any]]
    awsAccountId: Optional[str]
    logicalResourceIdentifier: Optional[str]
    typeConfiguration: Optional[BaseModel]
    nextToken: Optional[str]
    region: Optional[str]
    awsPartition: Optional[str]
    stackId: Optional[str]


@dataclass
class HookProgressEvent:
    hookStatus: HookStatus
    errorCode: Optional[HandlerErrorCode] = None
    message: str = ""
    callbackContext: Optional[MutableMapping[str, Any]] = None
    callbackDelaySeconds: int = 0
    result: Optional[str] = None
    clientRequestToken: Optional[str] = None

    def _serialize(self) -> MutableMapping[str, Any]:
        # to match Java serialization, which drops `null` values, and the
        # contract tests currently expect this also
        ser = {k: v for k, v in self.__dict__.items() if v is not None}

        # mutate to what's expected in the response

        ser["hookStatus"] = ser.pop("hookStatus").name

        if self.errorCode:
            ser["errorCode"] = self.errorCode.name
        return ser

    @classmethod
    def failed(
        cls: Type["HookProgressEvent"], error_code: HandlerErrorCode, message: str = ""
    ) -> "HookProgressEvent":
        return cls(hookStatus=HookStatus.FAILED, errorCode=error_code, message=message)


@dataclass
class HookContext:
    awsAccountId: Optional[str]
    stackId: Optional[str]
    hookTypeName: Optional[str]
    hookTypeVersion: Optional[str]
    invocationPoint: Optional[HookInvocationPoint]
    targetName: Optional[str]
    targetType: Optional[str]
    targetLogicalId: Optional[str]
    targetModel: Optional[Mapping[str, Any]]
    changeSetId: Optional[str] = None


@dataclass
class BaseHookHandlerRequest:
    clientRequestToken: str
    hookContext: HookContext
