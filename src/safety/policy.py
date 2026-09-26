# Checks whether a browser action is allowed before it is executed.

from urllib.parse import urlparse

from src.models.action import ActionType, BrowserAction, RiskLevel


class PolicyEngine:

    def __init__(self, allowed_origins: list[str]):
        self.allowed_origins = allowed_origins

        self.allowed_actions = {
            ActionType.NAVIGATE,
            ActionType.CLICK,
            ActionType.TYPE,
            ActionType.SELECT,
            ActionType.EXTRACT,
            ActionType.WAIT,
        }

    def check(self, action: BrowserAction) -> tuple[bool, str]:

        if action.action not in self.allowed_actions:
            return False, f"Action '{action.action}' is not allowed."

        if action.risk == RiskLevel.IRREVERSIBLE:
            return False, "Human approval is required for this action."

        if action.action == ActionType.NAVIGATE:
            if action.value is None:
                return False, "Navigation requires a URL."

            if not self._origin_is_allowed(str(action.value)):
                return False, "Navigation target is outside the allowed origin."

        return True, "Action allowed."

    def _origin_is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)

        origin = f"{parsed.scheme}://{parsed.netloc}"

        return origin in self.allowed_origins