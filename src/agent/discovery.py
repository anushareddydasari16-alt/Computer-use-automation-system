# Runs the Groq-driven discovery loop against the live browser.

import json
import time

from groq import AsyncGroq
from pydantic import BaseModel, Field

from src.agent.prompts import DISCOVERY_SYSTEM_PROMPT
from src.config import GROQ_API_KEY
from src.evidence.logger import EvidenceLogger
from src.models.action import ActionType, BrowserAction
from src.safety.policy import PolicyEngine
from src.surface.base import Surface


class DiscoveryResult(BaseModel):
    success: bool
    steps: list[BrowserAction] = Field(
        default_factory=list
    )
    outputs: dict[str, str] = Field(
        default_factory=dict
    )
    stop_reason: str


class DiscoveryAgent:

    def __init__(
        self,
        surface: Surface,
        policy: PolicyEngine,
        logger: EvidenceLogger,
        model: str,
        max_steps: int = 15,
        timeout_seconds: int = 120
    ):
        self.surface = surface
        self.policy = policy
        self.logger = logger
        self.model = model
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds

        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is missing from the .env file."
            )

        self.client = AsyncGroq(
            api_key=GROQ_API_KEY
        )

    async def run(
        self,
        goal: str,
        target_url: str
    ) -> DiscoveryResult:

        started_at = time.monotonic()

        completed_steps = []
        outputs = {}

        navigate = BrowserAction(
            action=ActionType.NAVIGATE,
            value=target_url,
            reason="Open the target application."
        )

        allowed, reason = self.policy.check(
            navigate
        )

        if not allowed:
            return DiscoveryResult(
                success=False,
                stop_reason=reason
            )

        try:
            await self.surface.act(
                navigate
            )

        except Exception as error:
            return DiscoveryResult(
                success=False,
                stop_reason=(
                    f"Could not open target: {error}"
                )
            )

        completed_steps.append(
            navigate
        )

        self.logger.log(
            "discovery_started",
            {
                "goal": goal,
                "target": target_url
            }
        )

        previous_state = None
        repeated_state_count = 0

        for step_number in range(
            1,
            self.max_steps + 1
        ):

            elapsed = (
                time.monotonic()
                - started_at
            )

            if elapsed > self.timeout_seconds:
                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason="Discovery timed out."
                )

            state = await self.surface.observe()

            self.logger.log(
                "observation",
                {
                    "step": step_number,
                    "url": state["url"],
                    "title": state["title"],
                    "controls": state.get(
                        "controls",
                        []
                    )
                }
            )

            if "Permission Denied" in state["text"]:
                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=(
                        "Permission denied by "
                        "the target application."
                    )
                )

            if "Member Not Found" in state["text"]:
                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=(
                        "Business outcome: "
                        "member not found."
                    )
                )

            if "Account Already Exists" in state["text"]:
                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=(
                        "Business outcome: "
                        "account already exists."
                    )
                )

            # Include form values so typing counts as a state change.
            state_signature = json.dumps(
                {
                    "url": state["url"],
                    "text": state["text"][:1000],
                    "controls": state.get(
                        "controls",
                        []
                    )
                },
                sort_keys=True
            )

            if state_signature == previous_state:
                repeated_state_count += 1
            else:
                repeated_state_count = 0

            previous_state = state_signature

            if repeated_state_count >= 2:
                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=(
                        "Dead-end detected. "
                        "Page state did not change."
                    )
                )

            try:
                action = await self._choose_action(
                    goal=goal,
                    state=state
                )

            except Exception as error:
                self.logger.log(
                    "model_error",
                    {
                        "step": step_number,
                        "error": str(error)
                    }
                )

                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=(
                        f"Groq decision failed: {error}"
                    )
                )

            allowed, reason = self.policy.check(
                action
            )

            self.logger.log(
                "agent_decision",
                {
                    "step": step_number,
                    "action": action.model_dump(
                        mode="json"
                    ),
                    "allowed": allowed,
                    "policy_reason": reason
                }
            )

            if not allowed:
                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=reason
                )

            try:
                value = await self.surface.act(
                    action
                )

            except Exception as error:
                screenshot_path = (
                    self.logger.file_path(
                        f"discovery_failure_step_"
                        f"{step_number}.png"
                    )
                )

                await self.surface.screenshot(
                    screenshot_path
                )

                self.logger.log(
                    "discovery_failure",
                    {
                        "step": step_number,
                        "error": str(error),
                        "screenshot": screenshot_path
                    }
                )

                return DiscoveryResult(
                    success=False,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason=str(error)
                )

            completed_steps.append(
                action
            )

            self.logger.log(
                "action_completed",
                {
                    "step": step_number,
                    "action": action.action.value,
                    "target": (
                        action.target.model_dump()
                        if action.target
                        else None
                    )
                }
            )

            if action.action == ActionType.EXTRACT:
                output_name = (
                    action.output_key
                    or "result"
                )

                outputs[output_name] = (
                    str(value).strip()
                )

                self.logger.log(
                    "output_extracted",
                    {
                        "step": step_number,
                        "output": output_name,
                        "value": outputs[
                            output_name
                        ]
                    }
                )

                return DiscoveryResult(
                    success=True,
                    steps=completed_steps,
                    outputs=outputs,
                    stop_reason="Goal completed."
                )

        return DiscoveryResult(
            success=False,
            steps=completed_steps,
            outputs=outputs,
            stop_reason=(
                "Maximum discovery steps reached."
            )
        )

    async def _choose_action(
        self,
        goal: str,
        state: dict
    ) -> BrowserAction:

        page_state = json.dumps(
            state,
            indent=2
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": DISCOVERY_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": (
                        f"Goal:\n{goal}\n\n"
                        f"Current browser state:\n"
                        f"{page_state}\n\n"
                        "Choose exactly one next "
                        "browser action."
                    )
                }
            ],
            temperature=0,
            max_tokens=800,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "browser_action",
                    "strict": False,
                    "schema": (
                        BrowserAction
                        .model_json_schema()
                    )
                }
            }
        )

        response_text = (
            response
            .choices[0]
            .message
            .content
        )

        if not response_text:
            raise RuntimeError(
                "Groq did not return "
                "a browser action."
            )

        return BrowserAction.model_validate_json(
            response_text
        )