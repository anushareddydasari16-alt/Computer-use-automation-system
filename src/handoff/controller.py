# Pauses automation and transfers control of the same browser session to a human.

import asyncio

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
            f"handoff_before_step_{current_step}.png"
        )

        await self.surface.screenshot(
            screenshot_path
        )

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
            {
                "owner": ControlOwner.HUMAN.value
            }
        )

    def record_human_action(
        self,
        description: str
    ):
        self.logger.log(
            "human_action",
            {
                "description": description
            }
        )

    def resume(self):
        self.state.owner = ControlOwner.AUTOMATION
        self.state.paused = False
        self.state.intervention = None

        self.logger.log(
            "control_changed",
            {
                "owner": ControlOwner.AUTOMATION.value
            }
        )

    async def run_handoff(
        self,
        capability_name: str,
        goal: str,
        current_step: int,
        reason: str
    ):
        request = await self.request_intervention(
            capability_name=capability_name,
            goal=goal,
            current_step=current_step,
            reason=reason
        )

        self.take_control()

        print("\nHuman Intervention Required")
        print("---------------------------")
        print(f"Capability: {request.capability_name}")
        print(f"Step: {request.current_step}")
        print(f"Reason: {request.reason}")
        print(f"Current URL: {request.current_url}")

        print(
            "\nThe same Chromium session is still open."
        )

        await asyncio.to_thread(
            input,
            "Complete the required action in the browser, "
            "then press Enter here to continue..."
        )

        description = await asyncio.to_thread(
            input,
            "Briefly describe the action you completed: "
        )

        if not description.strip():
            description = (
                "Human completed the blocked action "
                "in the live browser."
            )

        self.record_human_action(
            description
        )

        after_path = self.logger.file_path(
            f"handoff_after_step_{current_step}.png"
        )

        await self.surface.screenshot(
            after_path
        )

        self.logger.log(
            "handoff_completed",
            {
                "step": current_step,
                "after_screenshot": after_path
            }
        )

        self.resume()