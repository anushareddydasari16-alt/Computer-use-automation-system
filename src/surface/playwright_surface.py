# Uses Playwright to observe and interact with the live browser.

from pathlib import Path

from playwright.async_api import async_playwright

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
            headless=False
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

        buttons = await self.page.locator("button").all_inner_texts()
        links = await self.page.locator("a").all_inner_texts()

        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "text": page_text[:6000],
            "buttons": buttons,
            "links": links
        }

    async def act(self, action: BrowserAction):
        if action.action == ActionType.NAVIGATE:
            if action.value is None:
                raise ValueError("Navigate action requires a URL.")

            await self.page.goto(
                str(action.value),
                timeout=action.timeout_ms
            )
            return None

        if action.action == ActionType.WAIT:
            wait_time = float(action.value or 1)
            await self.page.wait_for_timeout(wait_time * 1000)
            return None

        locator = self._find_target(action)

        if action.action == ActionType.CLICK:
            await locator.click(timeout=action.timeout_ms)
            return None

        if action.action == ActionType.TYPE:
            if action.value is None:
                raise ValueError("Type action requires a value.")

            await locator.fill(
                str(action.value),
                timeout=action.timeout_ms
            )
            return None

        if action.action == ActionType.SELECT:
            if action.value is None:
                raise ValueError("Select action requires a value.")

            await locator.select_option(
                label=str(action.value),
                timeout=action.timeout_ms
            )
            return None

        if action.action == ActionType.EXTRACT:
            return await locator.inner_text(
                timeout=action.timeout_ms
            )

        raise ValueError(f"Unsupported action: {action.action}")

    async def screenshot(self, file_path: str):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        await self.page.screenshot(
            path=str(path),
            full_page=True
        )

    def _find_target(self, action: BrowserAction):
        target = action.target

        if target is None:
            raise ValueError("This action requires a target.")

        if target.role and target.name:
            return self.page.get_by_role(
                target.role,
                name=target.name
            ).first

        if target.text:
            return self.page.get_by_text(
                target.text,
                exact=True
            ).first

        if target.css:
            return self.page.locator(target.css).first

        if target.name:
            return self.page.get_by_text(
                target.name,
                exact=True
            ).first

        raise ValueError(
            f"Could not locate target: {target.description}"
        )