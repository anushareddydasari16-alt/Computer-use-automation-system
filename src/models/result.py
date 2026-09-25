# Defines the structured result returned after an automation run.

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    FAILURE = "failure"


class FailureDetail(BaseModel):
    failed_step: int | None = None
    expected: str | None = None
    observed: str | None = None
    message: str


class RunResult(BaseModel):
    status: RunStatus
    outputs: dict[str, Any] = Field(default_factory=dict)
    business_outcome: str | None = None
    failure: FailureDetail | None = None