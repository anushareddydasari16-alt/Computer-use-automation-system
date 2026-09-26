# Enforces the configured automation safety policy.

from urllib.parse import urlparse

from src.models.action import (
    ActionType,
    BrowserAction,
)


class PolicyEngine:

    def __init__(
        self,
        allowed_origins: list[str],
        allowed_routes: list[str] | None = None,
        allowed_actions: list[str] | None = None,
        risk_policy: dict | None = None
    ):
        self.allowed_origins = set(
            allowed_origins
        )

        self.allowed_routes = set(
            allowed_routes or []
        )

        self.allowed_actions = {
            ActionType(action)
            for action in (
                allowed_actions
                or [item.value for item in ActionType]
            )
        }

        self.risk_policy = risk_policy or {
            "safe": "allow",
            "reversible": "allow",
            "irreversible": "require_human"
        }

    def check(
        self,
        action: BrowserAction
    ) -> tuple[bool, str]:

        if action.action not in self.allowed_actions:
            return (
                False,
                f"Action type '{action.action.value}' "
                "is not allowed."
            )

        risk_rule = self.risk_policy.get(
            action.risk.value,
            "deny"
        )

        if risk_rule == "deny":
            return (
                False,
                f"Risk level '{action.risk.value}' "
                "is blocked by policy."
            )

        if risk_rule == "require_human":
            return (
                False,
                "Human approval is required for this action."
            )

        if action.action == ActionType.NAVIGATE:
            if not isinstance(action.value, str):
                return (
                    False,
                    "Navigation requires a URL."
                )

            return self.check_url(
                action.value
            )

        return (
            True,
            "Action allowed by policy."
        )

    def check_url(
        self,
        url: str
    ) -> tuple[bool, str]:

        parsed = urlparse(url)

        origin = (
            f"{parsed.scheme}://{parsed.netloc}"
        )

        if origin not in self.allowed_origins:
            return (
                False,
                f"Origin '{origin}' is not allowed."
            )

        route = parsed.path or "/"

        if (
        self.allowed_routes
        and route not in self.allowed_routes
    ):
         return (
            False,
        f"Route '{route}' is not allowed."
    )

        return (
            True,
            "URL allowed by policy."
        )