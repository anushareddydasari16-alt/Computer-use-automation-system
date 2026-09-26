# Tests the main safety policy rules.

from src.models.action import (
    ActionType,
    BrowserAction,
    RiskLevel,
)
from src.safety.policy import PolicyEngine


def make_policy():
    return PolicyEngine(
        allowed_origins=[
            "http://127.0.0.1:8000"
        ],
        allowed_routes=[
            "/",
            "/member-search",
            "/new-account"
        ],
        allowed_actions=[
            "navigate",
            "click",
            "type",
            "select",
            "extract",
            "wait"
        ],
        risk_policy={
            "safe": "allow",
            "reversible": "allow",
            "irreversible": "require_human"
        }
    )


def test_allowed_navigation():
    policy = make_policy()

    action = BrowserAction(
        action=ActionType.NAVIGATE,
        value="http://127.0.0.1:8000/"
    )

    allowed, reason = policy.check(action)

    assert allowed is True
    assert reason == "URL allowed by policy."


def test_blocked_origin():
    policy = make_policy()

    action = BrowserAction(
        action=ActionType.NAVIGATE,
        value="https://example.com"
    )

    allowed, reason = policy.check(action)

    assert allowed is False
    assert "not allowed" in reason


def test_blocked_route():
    policy = make_policy()

    action = BrowserAction(
        action=ActionType.NAVIGATE,
        value="http://127.0.0.1:8000/admin"
    )

    allowed, reason = policy.check(action)

    assert allowed is False
    assert "Route '/admin' is not allowed" in reason


def test_irreversible_action_requires_human():
    policy = make_policy()

    action = BrowserAction(
        action=ActionType.CLICK,
        risk=RiskLevel.IRREVERSIBLE,
        reason="Create account"
    )

    allowed, reason = policy.check(action)

    assert allowed is False
    assert reason == (
        "Human approval is required for this action."
    )