# Replays a saved capability deterministically without using an LLM.

import asyncio

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.evidence.logger import EvidenceLogger
from src.models.action import (
    ActionType,
    BrowserAction,
    Target,
)
from src.models.artifact import (
    CapabilityArtifact,
    Checkpoint,
)
from src.models.result import (
    FailureDetail,
    RunResult,
    RunStatus,
)
from src.safety.policy import PolicyEngine
from src.surface.base import Surface


class ReplayEngine:

    def __init__(
        self,
        surface: Surface,
        policy: PolicyEngine,
        logger: EvidenceLogger
    ):
        self.surface = surface
        self.policy = policy
        self.logger = logger
        self.recoveries = []

    async def replay(
        self,
        artifact: CapabilityArtifact,
        inputs: dict
    ) -> RunResult:

        outputs = {}

        input_error = self._validate_inputs(
            artifact,
            inputs
        )

        if input_error:
            return self._failure(
                step_number=0,
                expected="Valid replay inputs",
                observed=input_error
            )

        for step_number, saved_action in enumerate(
            artifact.steps,
            start=1
        ):
            action = self._apply_inputs(
                saved_action,
                inputs
            )

            allowed, reason = self.policy.check(
                action
            )

            self.logger.log(
                "replay_policy_check",
                {
                    "step": step_number,
                    "action": action.model_dump(
                        mode="json"
                    ),
                    "allowed": allowed,
                    "reason": reason
                }
            )

            if not allowed:
                return await self._failure_with_evidence(
                    step_number=step_number,
                    expected="Action allowed by policy",
                    observed=reason
                )

            try:
                value = await self._run_action(
                    action,
                    step_number
                )

            except Exception as error:
                return await self._failure_with_evidence(
                    step_number=step_number,
                    expected="Action completed successfully",
                    observed=str(error)
                )

            if (
                action.output_key
                and value is not None
            ):
                outputs[action.output_key] = (
                    value.strip()
                    if isinstance(value, str)
                    else value
                )

            self.logger.log(
                "replay_action_completed",
                {
                    "step": step_number,
                    "action": action.action.value,
                    "output_key": action.output_key
                }
            )

            checkpoint = self._checkpoint_for_step(
                artifact.checkpoints,
                step_number
            )

            if checkpoint:
                checkpoint_result = (
                    await self._verify_checkpoint(
                        checkpoint,
                        step_number
                    )
                )

                if checkpoint_result is not None:
                    return checkpoint_result

        output_error = self._validate_outputs(
            artifact,
            outputs
        )

        if output_error:
            return await self._failure_with_evidence(
                step_number=len(artifact.steps),
                expected=artifact.success_condition,
                observed=output_error
            )

        final_state = await self.surface.observe()

        self.logger.log(
            "replay_completed",
            {
                "status": "success",
                "outputs": outputs,
                "recoveries": self.recoveries,
                "final_url": final_state["url"]
            }
        )

        return RunResult(
            status=RunStatus.SUCCESS,
            outputs=outputs
        )

    async def _run_action(
        self,
        action: BrowserAction,
        step_number: int
    ):
        try:
            return await self.surface.act(
                action
            )

        except PlaywrightTimeoutError:
            self.logger.log(
                "recoverable_condition",
                {
                    "step": step_number,
                    "condition": "timeout",
                    "response": "retry_once"
                }
            )

            self.recoveries.append(
                {
                    "step": step_number,
                    "condition": "timeout",
                    "action": "retry_once"
                }
            )

            await asyncio.sleep(1)

            return await self.surface.act(
                action
            )

    async def _verify_checkpoint(
        self,
        checkpoint: Checkpoint,
        step_number: int
    ):
        state = await self.surface.observe()
        page_text = state["text"]

        self.logger.log(
            "replay_checkpoint",
            {
                "step": step_number,
                "description": checkpoint.description,
                "url": state["url"]
            }
        )

        # Known temporary state: recover automatically.
        if "Processing Request" in page_text:
            recovery_result = (
                await self._recover_processing_screen(
                    step_number
                )
            )

            if recovery_result is not None:
                return recovery_result

            # Read the page again after recovery.
            state = await self.surface.observe()
            page_text = state["text"]

        if "Member Not Found" in page_text:
            self.logger.log(
                "business_outcome",
                {
                    "step": step_number,
                    "outcome": "member_not_found"
                }
            )

            return RunResult(
                status=RunStatus.BUSINESS_OUTCOME,
                business_outcome="member_not_found"
            )

        if "Account Already Exists" in page_text:
            self.logger.log(
                "business_outcome",
                {
                    "step": step_number,
                    "outcome": "account_already_exists"
                }
            )

            return RunResult(
                status=RunStatus.BUSINESS_OUTCOME,
                business_outcome="account_already_exists"
            )

        if "Permission Denied" in page_text:
            return await self._failure_with_evidence(
                step_number=step_number,
                expected=checkpoint.description,
                observed="Permission Denied"
            )

        if (
            checkpoint.expected_text
            and checkpoint.expected_text not in page_text
        ):
            return await self._failure_with_evidence(
                step_number=step_number,
                expected=checkpoint.expected_text,
                observed=page_text[:300]
            )

        if (
            checkpoint.expected_url_contains
            and checkpoint.expected_url_contains
            not in state["url"]
        ):
            return await self._failure_with_evidence(
                step_number=step_number,
                expected=checkpoint.expected_url_contains,
                observed=state["url"]
            )

        return None

    async def _recover_processing_screen(
        self,
        step_number: int
    ):
        recovery_action = BrowserAction(
            action=ActionType.CLICK,
            target=Target(
                description="Continue",
                role="button",
                name="Continue"
            ),
            reason=(
                "Dismiss known temporary "
                "processing screen."
            )
        )

        allowed, reason = self.policy.check(
            recovery_action
        )

        if not allowed:
            return await self._failure_with_evidence(
                step_number=step_number,
                expected="Known recovery action allowed",
                observed=reason
            )

        self.logger.log(
            "recoverable_condition",
            {
                "step": step_number,
                "condition": "processing_interstitial",
                "response": "click_continue"
            }
        )

        try:
            await self.surface.act(
                recovery_action
            )

        except Exception as error:
            return await self._failure_with_evidence(
                step_number=step_number,
                expected=(
                    "Temporary processing "
                    "screen dismissed"
                ),
                observed=str(error)
            )

        self.recoveries.append(
            {
                "step": step_number,
                "condition": "processing_interstitial",
                "action": "click_continue"
            }
        )

        self.logger.log(
            "recovery_completed",
            {
                "step": step_number,
                "condition": "processing_interstitial"
            }
        )

        return None

    def _checkpoint_for_step(
        self,
        checkpoints: list[Checkpoint],
        step_number: int
    ):
        for checkpoint in checkpoints:
            if checkpoint.after_step == step_number:
                return checkpoint

        return None

    def _apply_inputs(
        self,
        action: BrowserAction,
        inputs: dict
    ) -> BrowserAction:

        value = action.value

        if not isinstance(value, str):
            return action

        for input_name, input_value in inputs.items():
            placeholder = (
                "{{" + input_name + "}}"
            )

            value = value.replace(
                placeholder,
                str(input_value)
            )

        return action.model_copy(
            update={"value": value}
        )

    def _validate_inputs(
        self,
        artifact: CapabilityArtifact,
        inputs: dict
    ):
        for parameter in artifact.inputs:
            if (
                parameter.required
                and parameter.name not in inputs
            ):
                return (
                    f"Missing required input: "
                    f"{parameter.name}"
                )

        return None

    def _validate_outputs(
        self,
        artifact: CapabilityArtifact,
        outputs: dict
    ):
        for output in artifact.outputs:
            if output.name not in outputs:
                return (
                    f"Declared output '{output.name}' "
                    "was not returned."
                )

            value = outputs[output.name]

            if value is None or value == "":
                return (
                    f"Declared output '{output.name}' "
                    "was empty."
                )

        return None

    async def _failure_with_evidence(
        self,
        step_number: int,
        expected: str,
        observed: str
    ):
        screenshot_path = self.logger.file_path(
            f"replay_failure_step_{step_number}.png"
        )

        try:
            await self.surface.screenshot(
                screenshot_path
            )
        except Exception:
            screenshot_path = None

        self.logger.log(
            "replay_failure",
            {
                "step": step_number,
                "expected": expected,
                "observed": observed,
                "screenshot": screenshot_path
            }
        )

        return self._failure(
            step_number,
            expected,
            observed
        )

    def _failure(
        self,
        step_number: int,
        expected: str,
        observed: str
    ):
        return RunResult(
            status=RunStatus.FAILURE,
            failure=FailureDetail(
                failed_step=step_number,
                expected=expected,
                observed=observed,
                message=(
                    "Replay could not continue safely."
                )
            )
        )