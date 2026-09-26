# Command-line entry point for discovery and deterministic replay.

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.agent.discovery import DiscoveryAgent
from src.artifact.compiler import ArtifactCompiler
from src.handoff.controller import HandoffController

from src.config import (
    GROQ_MODEL,
    MAX_STEPS,
    RUN_TIMEOUT_SECONDS,
    TARGET_URL,
)
from src.evidence.logger import EvidenceLogger
from src.models.action import ActionType, Target
from src.models.artifact import (
    CapabilityArtifact,
    Checkpoint,
    InputParameter,
    OutputDefinition,
    ValueType,
)
from src.replay.engine import ReplayEngine
from src.safety.policy import PolicyEngine
from src.surface.playwright_surface import PlaywrightSurface


def load_policy():
    policy_file = Path("config/policy.json")

    with open(policy_file, "r", encoding="utf-8") as file:
        return json.load(file)


def load_artifact(file_path: str) -> CapabilityArtifact:
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return CapabilityArtifact.model_validate(data)


def build_lookup_artifact(discovery_result):
    compiler = ArtifactCompiler()

    reusable_steps = compiler.parameterize_steps(
        steps=discovery_result.steps,
        replacements={
            "10001": "member_id"
        }
    )

    # Use a stable row-based selector for the savings balance.
    for step in reusable_steps:
        if (
            step.action == ActionType.EXTRACT
            and step.output_key == "savings_balance"
        ):
            step.target = Target(
                description="Savings balance",
                css='tr:has-text("Savings") td:nth-child(2)'
            )

    checkpoint_step = 1

    for step_number, step in enumerate(
        reusable_steps,
        start=1
    ):
        if (
            step.action == ActionType.CLICK
            and step.target
            and (
                step.target.name == "Find Member"
                or step.target.text == "Find Member"
                or step.target.description == "Find Member"
            )
        ):
            checkpoint_step = step_number
            break

    artifact = compiler.build(
        name="lookup_savings_balance",
        description=(
            "Looks up a Northwind Community Bank member "
            "and returns the current savings balance."
        ),
        target_origin="http://127.0.0.1:8000",
        inputs=[
            InputParameter(
                name="member_id",
                type=ValueType.STRING,
                description="Member number to search for."
            )
        ],
        outputs=[
            OutputDefinition(
                name="savings_balance",
                type=ValueType.STRING,
                description="Current savings account balance."
            )
        ],
        steps=reusable_steps,
        checkpoints=[
            Checkpoint(
                after_step=checkpoint_step,
                description=(
                    "Member search should reach "
                    "the member details page."
                ),
                expected_text="Member Details"
            )
        ],
        success_condition=(
            "The savings_balance output is extracted "
            "from the member details page."
        )
    )

    artifact_path = (
        "artifacts/lookup_savings_balance.v1.json"
    )

    compiler.save(
        artifact=artifact,
        file_path=artifact_path
    )

    return artifact_path


async def run_discovery(goal: str, target: str):
    policy_config = load_policy()

    policy = PolicyEngine(
    allowed_origins=policy_config["allowed_origins"],
    allowed_routes=policy_config["allowed_routes"],
    allowed_actions=policy_config["allowed_actions"],
    risk_policy=policy_config["risk_policy"]
    )

    run_time = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    logger = EvidenceLogger(
        run_name=f"discovery_{run_time}"
    )

    surface = PlaywrightSurface()

    agent = DiscoveryAgent(
        surface=surface,
        policy=policy,
        logger=logger,
        model=GROQ_MODEL,
        max_steps=MAX_STEPS,
        timeout_seconds=RUN_TIMEOUT_SECONDS
    )

    await surface.open()

    try:
        result = await agent.run(
            goal=goal,
            target_url=target
        )

        print("\nDiscovery Result")
        print("----------------")

        print(
            json.dumps(
                result.model_dump(mode="json"),
                indent=2
            )
        )

        if result.success:
            artifact_path = build_lookup_artifact(
                result
            )

            print("\nCapability Artifact")
            print("-------------------")
            print(f"Saved: {artifact_path}")

    finally:
        await surface.close()


async def run_replay(
    artifact_path: str,
    member_id: str,
    opening_deposit: float | None = None
):
    policy_config = load_policy()

    policy = PolicyEngine(
    allowed_origins=policy_config["allowed_origins"],
    allowed_routes=policy_config["allowed_routes"],
    allowed_actions=policy_config["allowed_actions"],
    risk_policy=policy_config["risk_policy"]
    )

    artifact = load_artifact(
        artifact_path
    )

    run_time = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    logger = EvidenceLogger(
        run_name=f"replay_{run_time}"
    )

    surface = PlaywrightSurface()

# Uses the same browser session when human intervention is required.
    handoff = HandoffController(
    surface=surface,
    logger=logger
    )

    engine = ReplayEngine(
    surface=surface,
    policy=policy,
    logger=logger,
    handoff=handoff
    )


# Build replay inputs from the command-line values.
    await surface.open()

    try:
        # Build replay inputs from the command-line values.
        inputs = {
            "member_id": member_id
        }

        if opening_deposit is not None:
            inputs["opening_deposit"] = opening_deposit

        result = await engine.replay(
            artifact,
            inputs=inputs
        )

        print("\nDeterministic Replay")
        print("LLM decision calls: 0")
        print(result.model_dump_json(indent=2))

    finally:
        await surface.close()


def main():
    parser = argparse.ArgumentParser(
        description="Computer-use automation demo"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    discover_parser = subparsers.add_parser(
        "discover",
        help="Run an LLM-driven discovery session"
    )

    discover_parser.add_argument(
        "--goal",
        required=True,
        help="Goal for the discovery agent"
    )

    discover_parser.add_argument(
        "--target",
        default=TARGET_URL,
        help="Starting URL for the target application"
    )

    replay_parser = subparsers.add_parser(
        "replay",
        help="Replay a saved capability without LLM decisions"
    )

    replay_parser.add_argument(
        "--artifact",
        required=True,
        help="Path to the saved capability artifact"
    )

    replay_parser.add_argument(
        "--member-id",
        required=True,
        help="Member number used for replay"
    )
    replay_parser.add_argument(
        "--opening-deposit",
    type=float,
        required=False,
        help="Opening deposit used for account creation"
    )
    args = parser.parse_args()

    if args.command == "discover":
        asyncio.run(
            run_discovery(
                goal=args.goal,
                target=args.target
            )
        )

    elif args.command == "replay":
        asyncio.run(
            run_replay(
        artifact_path=args.artifact,
        member_id=args.member_id,
        opening_deposit=args.opening_deposit
        )
    )


if __name__ == "__main__":
    main()