# Defines the browser actions and risk levels used by the automation system.

from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"


class RiskLevel(str, Enum):
    SAFE = "safe"
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"


class Target(BaseModel):
    description: str
    role: str | None = None
    name: str | None = None
    text: str | None = None
    css: str | None = None


class BrowserAction(BaseModel):
    action: ActionType
    target: Target | None = None
    value: str | float | None = None
    output_key: str | None = None
    risk: RiskLevel = RiskLevel.SAFE
    reason: str = ""
    timeout_ms: int = Field(default=5000, ge=500, le=30000)