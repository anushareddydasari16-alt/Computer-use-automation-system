# Defines the information needed when automation pauses for a human.

from enum import Enum

from pydantic import BaseModel


class ControlOwner(str, Enum):
    AUTOMATION = "automation"
    HUMAN = "human"


class InterventionRequest(BaseModel):
    capability_name: str
    goal: str
    current_step: int
    reason: str
    current_url: str
    screenshot_path: str | None = None


class HandoffState(BaseModel):
    owner: ControlOwner = ControlOwner.AUTOMATION
    paused: bool = False
    intervention: InterventionRequest | None = None