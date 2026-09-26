# Uses Playwright to observe and interact with the live browser.

from pathlib import Path

from playwright.async_api import async_playwright

from src.config import HEADLESS
from src.models.action import ActionType, BrowserAction
from src.surface.base import Surface


class PlaywrightSurface(Surface):

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def open(self):
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS
        )

        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def close(self):
        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

    async def observe(self) -> dict:
        page_text = await self.page.locator("body").inner_text()

        buttons = await self.page.locator(
            "button"
        ).all_inner_texts()

        links = await self.page.locator(
            "a"
        ).all_inner_texts()

        controls = await self.page.locator(
            "input, select, textarea, button"
        ).evaluate_all(
            """
            elements => elements.map(element => {
                let label = "";

                if (element.id) {
                    const linkedLabel = document.querySelector(
                        `label[for="${element.id}"]`
                    );

                    if (linkedLabel) {
                        label = linkedLabel.innerText.trim();
                    }
                }

                return {
                    tag: element.tagName.toLowerCase(),
                    type: element.type || null,
                    name: element.name || null,
                    id: element.id || null,
                    label: label || null,
                    value: element.value || null,
                    text: element.innerText?.trim() || null
                };
            })
            """
        )

        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "text": page_text[:6000],
            "buttons": buttons,
            "links": links,
            "controls": controls
        }

    async def act(self, action: BrowserAction):
        if action.action == ActionType.NAVIGATE:
            if action.value is None:
                raise ValueError(
                    "Navigate action requires a URL."
                )

            await self.page.goto(
                str(action.value),
                timeout=action.timeout_ms
            )

            return None

        if action.action == ActionType.WAIT:
            wait_seconds = float(action.value or 1)

            await self.page.wait_for_timeout(
                wait_seconds * 1000
            )

            return None

        locator = await self._find_target(action)

        if action.action == ActionType.CLICK:
            await locator.click(
                timeout=action.timeout_ms
            )

            return None

        if action.action == ActionType.TYPE:
            if action.value is None:
                raise ValueError(
                    "Type action requires a value."
                )

            await locator.fill(
                str(action.value),
                timeout=action.timeout_ms
            )

            return None

        if action.action == ActionType.SELECT:
            if action.value is None:
                raise ValueError(
                    "Select action requires a value."
                )

            await locator.select_option(
                label=str(action.value),
                timeout=action.timeout_ms
            )

            return None

        if action.action == ActionType.EXTRACT:
            return await locator.inner_text(
                timeout=action.timeout_ms
            )

        raise ValueError(
            f"Unsupported action: {action.action}"
        )

    async def screenshot(self, file_path: str):
        path = Path(file_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        await self.page.screenshot(
            path=str(path),
            full_page=True
        )

    async def _find_target(
        self,
        action: BrowserAction
    ):
        target = action.target

        if target is None:
            raise ValueError(
                "This action requires a target."
            )

        # Use CSS if the model supplied a valid selector.
        if target.css:
            locator = self.page.locator(
                target.css
            )

            if await locator.count() > 0:
                return locator.first

        # Prefer accessibility role and name.
        if target.role and target.name:
            locator = self.page.get_by_role(
                target.role,
                name=target.name
            )

            if await locator.count() > 0:
                return locator.first

        # Handle inputs and dropdowns.
        if action.action in {
            ActionType.TYPE,
            ActionType.SELECT
        }:

            # HTML name such as member_id.
            if target.name:
                locator = self.page.locator(
                    f'[name="{target.name}"]'
                )

                if await locator.count() > 0:
                    return locator.first

            # Clean common extra words added by the model.
            if target.description:
                label = target.description

                for phrase in [
                    " input field",
                    " field",
                    " textbox",
                    " dropdown",
                    " select"
                ]:
                    label = label.replace(
                        phrase,
                        ""
                    )

                locator = self.page.get_by_label(
                    label.strip(),
                    exact=True
                )

                if await locator.count() > 0:
                    return locator.first

            if target.name:
                locator = self.page.get_by_label(
                    target.name,
                    exact=True
                )

                if await locator.count() > 0:
                    return locator.first

        # Visible text is useful for buttons, links, and values.
        if target.text:
            locator = self.page.get_by_text(
                target.text,
                exact=True
            )

            if await locator.count() > 0:
                return locator.first

        if target.name:
            locator = self.page.get_by_text(
                target.name,
                exact=True
            )

            if await locator.count() > 0:
                return locator.first

        if target.description:
            locator = self.page.get_by_text(
                target.description,
                exact=True
            )

            if await locator.count() > 0:
                return locator.first

        raise ValueError(
            f"Could not locate target: {target.description}"
        )