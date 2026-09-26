# Builds and saves a reusable capability from a successful discovery run.

import json
from pathlib import Path

from src.models.action import BrowserAction
from src.models.artifact import (
    CapabilityArtifact,
    Checkpoint,
    InputParameter,
    OutputDefinition,
)


class ArtifactCompiler:

    def parameterize_steps(
        self,
        steps: list[BrowserAction],
        replacements: dict[str, str]
    ) -> list[BrowserAction]:

        reusable_steps = []

        for step in steps:
            value = step.value

            if isinstance(value, str):
                for actual_value, parameter_name in replacements.items():
                    if value == actual_value:
                        value = "{{" + parameter_name + "}}"

            reusable_steps.append(
                step.model_copy(
                    update={"value": value}
                )
            )

        return reusable_steps

    def build(
        self,
        name: str,
        description: str,
        target_origin: str,
        inputs: list[InputParameter],
        outputs: list[OutputDefinition],
        steps: list[BrowserAction],
        checkpoints: list[Checkpoint],
        success_condition: str,
    ) -> CapabilityArtifact:

        return CapabilityArtifact(
            name=name,
            description=description,
            target_origin=target_origin,
            inputs=inputs,
            outputs=outputs,
            steps=steps,
            checkpoints=checkpoints,
            success_condition=success_condition,
        )

    def save(
        self,
        artifact: CapabilityArtifact,
        file_path: str
    ):
        path = Path(file_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                artifact.model_dump(mode="json"),
                file,
                indent=2
            )