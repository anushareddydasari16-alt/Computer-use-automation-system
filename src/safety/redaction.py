# Removes sensitive values before logs or evidence are saved.

import re
from typing import Any


SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "ssn",
    "member_ssn",
    "secret",
    "api_key",
}


def redact_value(value: Any):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [redact_value(item) for item in value]

    if isinstance(value, str):
        return redact_text(value)

    return value


def redact_text(text: str) -> str:
    text = re.sub(
        r"\b\d{3}-\d{2}-\d{4}\b",
        "[REDACTED_SSN]",
        text
    )

    text = re.sub(
        r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        text
    )

    return text