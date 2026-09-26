# Defines the structured result returned by deterministic replay.

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    FAILURE = "failure"


class RecoveryDetail(BaseModel):
    step: int
    condition: str
    action: str


class FailureDetail(BaseModel):
    failed_step: int | None = None
    expected: str | None = None
    observed: str | None = None
    message: str


class RunResult(BaseModel):
    status: RunStatus
    outputs: dict[str, Any] = Field(
        default_factory=dict
    )
    recoveries: list[RecoveryDetail] = Field(
        default_factory=list
    )
    business_outcome: str | None = None
    failure: FailureDetail | None = None