# Tests deterministic replay using saved steps without any LLM calls.

import pytest

from src.models.action import (
    ActionType,
    BrowserAction,
    Target,
)
from src.models.artifact import (
    CapabilityArtifact,
    InputParameter,
    OutputDefinition,
    ValueType,
)
from src.models.result import RunStatus
from src.replay.engine import ReplayEngine
from src.safety.policy import PolicyEngine


class FakeSurface:
    def __init__(self):
        self.actions = []

    async def observe(self):
        return {
            "url": "http://127.0.0.1:8000/",
            "text": "Member Details",
            "controls": []
        }

    async def act(self, action):
        self.actions.append(action)

        if action.action == ActionType.EXTRACT:
            return "$5520.75"

        return None

    async def screenshot(self, file_path):
        return None


class FakeLogger:
    def __init__(self):
        self.events = []

    def log(self, event, details):
        self.events.append(
            {
                "event": event,
                "details": details
            }
        )

    def file_path(self, name):
        return name


@pytest.mark.asyncio
async def test_replay_uses_saved_steps():
    surface = FakeSurface()
    logger = FakeLogger()

    policy = PolicyEngine(
        allowed_origins=[
            "http://127.0.0.1:8000"
        ],
        allowed_routes=[
            "/"
        ],
        allowed_actions=[
            "navigate",
            "click",
            "type",
            "select",
            "extract",
            "wait"
        ],
        risk_policy={
            "safe": "allow",
            "reversible": "allow",
            "irreversible": "require_human"
        }
    )

    artifact = CapabilityArtifact(
        name="test_lookup",
        description="Test member balance lookup.",
        target_origin="http://127.0.0.1:8000",
        inputs=[
            InputParameter(
                name="member_id",
                type=ValueType.STRING,
                description="Member number."
            )
        ],
        outputs=[
            OutputDefinition(
                name="savings_balance",
                type=ValueType.STRING,
                description="Savings balance."
            )
        ],
        steps=[
            BrowserAction(
                action=ActionType.NAVIGATE,
                value="http://127.0.0.1:8000"
            ),
            BrowserAction(
                action=ActionType.TYPE,
                target=Target(
                    description="Member Number",
                    name="member_id"
                ),
                value="{{member_id}}"
            ),
            BrowserAction(
                action=ActionType.EXTRACT,
                target=Target(
                    description="Savings balance"
                ),
                output_key="savings_balance"
            )
        ],
        checkpoints=[],
        success_condition=(
            "Savings balance is returned."
        )
    )

    engine = ReplayEngine(
        surface=surface,
        policy=policy,
        logger=logger
    )

    result = await engine.replay(
        artifact=artifact,
        inputs={
            "member_id": "30003"
        }
    )

    assert result.status == RunStatus.SUCCESS
    assert result.outputs["savings_balance"] == "$5520.75"

    # Confirm the saved placeholder was replaced.
    assert surface.actions[1].value == "30003"

    # Confirm replay followed the saved action order.
    assert [
        action.action
        for action in surface.actions
    ] == [
        ActionType.NAVIGATE,
        ActionType.TYPE,
        ActionType.EXTRACT
    ]