# Tests that sensitive values are removed before logging.

from src.safety.redaction import (
    redact_text,
    redact_value,
)


def test_redacts_sensitive_dictionary_values():
    data = {
        "username": "demo-user",
        "api_key": "secret-key-123",
        "password": "mypassword"
    }

    redacted = redact_value(data)

    assert redacted["username"] == "demo-user"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"


def test_redacts_ssn_from_text():
    text = "Member SSN is 123-45-6789"

    redacted = redact_text(text)

    assert "123-45-6789" not in redacted
    assert "[REDACTED_SSN]" in redacted