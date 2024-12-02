# pylint: disable=protected-access,redefined-outer-name,abstract-method
from dataclasses import dataclass

import boto3
import pytest
from cloudformation_cli_python_lib.interface import (
    BaseModel,
    HandlerErrorCode,
    HookProgressEvent,
    HookStatus,
    OperationStatus,
    ProgressEvent,
)

import hypothesis.strategies as s  # pylint: disable=C0411
import json
from hypothesis import given  # pylint: disable=C0411
from string import ascii_letters


@pytest.fixture(scope="module")
def client():
    return boto3.client(
        "cloudformation",
        aws_access_key_id="",
        aws_secret_access_key="",
        aws_session_token="",
        region_name="us-east-1",
    )


# don't call this TestModel, or pytest will try and execute it
@dataclass
class ResourceModel(BaseModel):
    somekey: str
    someotherkey: str


def test_base_resource_model__deserialize():
    with pytest.raises(NotImplementedError):
        BaseModel()._deserialize({})


def test_base_resource_model__serialize():
    brm = BaseModel()
    assert brm._serialize() == brm.__dict__


@given(s.sampled_from(HandlerErrorCode), s.text(ascii_letters))
def test_progress_event_failed_is_json_serializable(error_code, message):
    event = ProgressEvent.failed(error_code, message)
    assert event.status == OperationStatus.FAILED
    assert event.errorCode == error_code
    assert event.message == message

    assert json.loads(json.dumps(event._serialize())) == {
        "status": OperationStatus.FAILED.value,
        "errorCode": error_code.value,
        "message": message,
        "callbackDelaySeconds": 0,
    }


@given(s.text(ascii_letters))
def test_progress_event_serialize_to_response_with_context(message):
    event = ProgressEvent(
        status=OperationStatus.SUCCESS, message=message, callbackContext={"a": "b"}
    )

    print(event._serialize())
    assert event._serialize() == {
        "status": OperationStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "callbackContext": {"a": "b"},
        "callbackDelaySeconds": 0,
    }


@given(s.text(ascii_letters))
def test_progress_event_serialize_to_response_with_model(message):
    model = ResourceModel("a", "b")
    event = ProgressEvent(
        status=OperationStatus.SUCCESS, message=message, resourceModel=model
    )

    assert event._serialize() == {
        "status": OperationStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "resourceModel": {"somekey": "a", "someotherkey": "b"},
        "callbackDelaySeconds": 0,
    }


@given(s.text(ascii_letters))
def test_progress_event_serialize_to_response_with_models(message):
    models = [ResourceModel("a", "b"), ResourceModel("c", "d")]
    event = ProgressEvent(
        status=OperationStatus.SUCCESS, message=message, resourceModels=models
    )

    assert event._serialize() == {
        "status": OperationStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "resourceModels": [
            {"somekey": "a", "someotherkey": "b"},
            {"somekey": "c", "someotherkey": "d"},
        ],
        "callbackDelaySeconds": 0,
    }


@given(s.text(ascii_letters))
def test_progress_event_serialize_to_response_with_error_code(message):
    event = ProgressEvent(
        status=OperationStatus.SUCCESS,
        message=message,
        errorCode=HandlerErrorCode.InvalidRequest,
    )

    assert event._serialize() == {
        "status": OperationStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "errorCode": HandlerErrorCode.InvalidRequest.name,  # pylint: disable=no-member
        "callbackDelaySeconds": 0,
    }


@given(s.sampled_from(HandlerErrorCode), s.text(ascii_letters))
def test_hook_progress_event_failed_is_json_serializable(error_code, message):
    event = HookProgressEvent.failed(error_code, message)
    assert event.hookStatus == HookStatus.FAILED
    assert event.errorCode == error_code
    assert event.message == message

    assert json.loads(json.dumps(event._serialize())) == {
        "hookStatus": HookStatus.FAILED.value,
        "errorCode": error_code.value,
        "message": message,
        "callbackDelaySeconds": 0,
    }


@given(s.text(ascii_letters))
def test_hook_progress_event_serialize_to_response_with_context(message):
    event = HookProgressEvent(
        hookStatus=HookStatus.SUCCESS, message=message, callbackContext={"a": "b"}
    )

    assert event._serialize() == {
        "hookStatus": HookStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "callbackContext": {"a": "b"},
        "callbackDelaySeconds": 0,
    }


@given(s.text(ascii_letters))
def test_hook_progress_event_serialize_to_response_with_data(message):
    result = "My hook data"
    event = HookProgressEvent(
        hookStatus=HookStatus.SUCCESS, message=message, result=result
    )

    assert event._serialize() == {
        "hookStatus": HookStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "callbackDelaySeconds": 0,
        "result": result,
    }


@given(s.text(ascii_letters))
def test_hook_progress_event_serialize_to_response_with_error_code(message):
    event = HookProgressEvent(
        hookStatus=HookStatus.SUCCESS,
        message=message,
        errorCode=HandlerErrorCode.InvalidRequest,
    )

    assert event._serialize() == {
        "hookStatus": HookStatus.SUCCESS.name,  # pylint: disable=no-member
        "message": message,
        "errorCode": HandlerErrorCode.InvalidRequest.name,  # pylint: disable=no-member
        "callbackDelaySeconds": 0,
    }


def test_operation_status_enum_matches_sdk(client):
    sdk = set(client.meta.service_model.shape_for("OperationStatus").enum)
    enum = set(OperationStatus.__members__)
    # CHANGE_SET_SUCCESS_SKIP_STACK_HOOK is a status specific to Hooks
    enum.remove("CHANGE_SET_SUCCESS_SKIP_STACK_HOOK")
    assert enum == sdk
