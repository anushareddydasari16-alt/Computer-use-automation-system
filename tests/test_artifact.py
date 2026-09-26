# Tests reusable capability artifact generation.

from src.artifact.compiler import ArtifactCompiler
from src.models.action import (
    ActionType,
    BrowserAction,
    Target,
)


def test_parameterizes_discovered_value():
    compiler = ArtifactCompiler()

    steps = [
        BrowserAction(
            action=ActionType.TYPE,
            target=Target(
                description="Member Number",
                name="member_id"
            ),
            value="10001"
        )
    ]

    reusable_steps = compiler.parameterize_steps(
        steps=steps,
        replacements={
            "10001": "member_id"
        }
    )

    assert reusable_steps[0].value == "{{member_id}}"


def test_original_step_is_not_changed():
    compiler = ArtifactCompiler()

    original_step = BrowserAction(
        action=ActionType.TYPE,
        target=Target(
            description="Member Number",
            name="member_id"
        ),
        value="10001"
    )

    reusable_steps = compiler.parameterize_steps(
        steps=[original_step],
        replacements={
            "10001": "member_id"
        }
    )

    assert original_step.value == "10001"
    assert reusable_steps[0].value == "{{member_id}}"