# Saves structured run events and keeps sensitive values out of evidence logs.

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.safety.redaction import redact_value


class EvidenceLogger:

    def __init__(self, run_name: str, base_folder: str = "evidence"):
        self.run_folder = Path(base_folder) / run_name
        self.run_folder.mkdir(parents=True, exist_ok=True)

        self.log_file = self.run_folder / "events.jsonl"

    def log(self, event: str, details: dict[str, Any]):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": redact_value(details)
        }

        with open(self.log_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")

    def file_path(self, file_name: str) -> str:
        return str(self.run_folder / file_name)