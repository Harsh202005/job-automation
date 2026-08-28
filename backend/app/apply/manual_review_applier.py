"""
Manual Review Applier (Fill-and-Pause)
=====================================
Used for LinkedIn, Indeed, Naukri, and unverified portal sources.
Pre-fills available form fields, captures a full-page screenshot,
and STOPS before clicking submit.
Always marks application status as "pending_review".
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

from app.apply.base_applier import BaseApplier

if TYPE_CHECKING:
    from playwright.async_api import Page
    from app.models.job import Job

logger = logging.getLogger(__name__)


class ManualReviewApplier(BaseApplier):
    """
    Safely fills accessible form fields, captures full-page screenshot,
    and pauses for human approval/submission. NEVER auto-submits.
    """

    async def apply(
        self,
        job: Job,
        resume_parsed_json: dict[str, Any],
        resume_file_path: str,
        page: Page,
        screenshot_dir: Path,
        application_id: str,
    ) -> dict[str, Any]:
        screenshot_path = screenshot_dir / f"{application_id}_review.png"
        full_name = resume_parsed_json.get("full_name", "")
        first_name, last_name = self._split_name(full_name)
        email = resume_parsed_json.get("email", "")
        phone = resume_parsed_json.get("phone", "")

        try:
            logger.info("ManualReviewApplier: Navigating to %s (source: %s)", job.apply_url, job.source)
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(2500)

            # Best-effort fill standard fields if form inputs are immediately visible
            try:
                # Name
                if await page.locator("input[name*='name' i], input#name").count() > 0:
                    await page.locator("input[name*='name' i], input#name").first.fill(full_name)
                elif await page.locator("input[name*='first' i]").count() > 0:
                    await page.locator("input[name*='first' i]").first.fill(first_name)
                    if last_name and await page.locator("input[name*='last' i]").count() > 0:
                        await page.locator("input[name*='last' i]").first.fill(last_name)

                # Email
                if await page.locator("input[type='email'], input[name*='email' i]").count() > 0:
                    await page.locator("input[type='email'], input[name*='email' i]").first.fill(email)

                # Phone
                if await page.locator("input[type='tel'], input[name*='phone' i]").count() > 0:
                    await page.locator("input[type='tel'], input[name*='phone' i]").first.fill(phone)

                # Resume file upload
                if resume_file_path and Path(resume_file_path).exists():
                    file_input = page.locator("input[type='file']").first
                    if await file_input.count() > 0:
                        await file_input.set_input_files(str(Path(resume_file_path).resolve()))
                        await page.wait_for_timeout(1000)

            except Exception as fill_err:
                logger.warning("Non-fatal error during best-effort field fill: %s", fill_err)

            # Capture full-page screenshot for candidate review
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info("Manual review screenshot saved: %s", screenshot_path)

            return {
                "status": "pending_review",
                "screenshot_path": str(screenshot_path),
                "error_message": f"Pre-filled for {job.source.capitalize()}. Ready for candidate review and manual submission.",
            }

        except Exception as exc:
            logger.exception("ManualReviewApplier navigation/screenshot failed: %s", exc)
            try:
                if not screenshot_path.exists():
                    await page.screenshot(path=str(screenshot_path), full_page=False)
            except Exception:
                pass

            return {
                "status": "pending_review",
                "screenshot_path": str(screenshot_path) if screenshot_path.exists() else None,
                "error_message": f"Navigation error on {job.source}: {exc}. Requires direct manual application.",
            }
