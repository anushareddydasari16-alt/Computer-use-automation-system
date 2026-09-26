# Manages pause, human control, and resume on the same live browser session.

from src.evidence.logger import EvidenceLogger
from src.handoff.types import (
    ControlOwner,
    HandoffState,
    InterventionRequest,
)
from src.surface.base import Surface


class HandoffController:

    def __init__(
        self,
        surface: Surface,
        logger: EvidenceLogger
    ):
        self.surface = surface
        self.logger = logger
        self.state = HandoffState()

    async def request_intervention(
        self,
        capability_name: str,
        goal: str,
        current_step: int,
        reason: str
    ) -> InterventionRequest:

        page_state = await self.surface.observe()

        screenshot_path = self.logger.file_path(
            f"handoff_step_{current_step}.png"
        )

        await self.surface.screenshot(screenshot_path)

        request = InterventionRequest(
            capability_name=capability_name,
            goal=goal,
            current_step=current_step,
            reason=reason,
            current_url=page_state["url"],
            screenshot_path=screenshot_path
        )

        self.state = HandoffState(
            owner=ControlOwner.AUTOMATION,
            paused=True,
            intervention=request
        )

        self.logger.log(
            "handoff_requested",
            request.model_dump()
        )

        return request

    def take_control(self):
        self.state.owner = ControlOwner.HUMAN

        self.logger.log(
            "control_changed",
            {"owner": ControlOwner.HUMAN.value}
        )

    def record_human_action(self, description: str):
        self.logger.log(
            "human_action",
            {"description": description}
        )

    def resume(self):
        self.state.owner = ControlOwner.AUTOMATION
        self.state.paused = False
        self.state.intervention = None

        self.logger.log(
            "control_changed",
            {"owner": ControlOwner.AUTOMATION.value}
        )