# Defines the reusable capability artifact created after a successful discovery run.

from enum import Enum

from pydantic import BaseModel, Field

from src.models.action import BrowserAction


class ValueType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


class InputParameter(BaseModel):
    name: str
    type: ValueType
    description: str
    required: bool = True


class OutputDefinition(BaseModel):
    name: str
    type: ValueType
    description: str


class Checkpoint(BaseModel):
    after_step: int
    description: str
    expected_text: str | None = None
    expected_url_contains: str | None = None


class CapabilityArtifact(BaseModel):
    schema_version: str = "1.0"
    capability_version: int = 1

    name: str
    description: str

    surface_type: str = "web"
    target_origin: str

    inputs: list[InputParameter] = Field(default_factory=list)
    outputs: list[OutputDefinition] = Field(default_factory=list)

    steps: list[BrowserAction] = Field(default_factory=list)
    checkpoints: list[Checkpoint] = Field(default_factory=list)

    success_condition: str