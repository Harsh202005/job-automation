"""
Greenhouse ATS Form Applier
===========================
Fills and submits standard Greenhouse application forms.
Flags postings with unhandled required custom questions for manual review.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

from app.apply.base_applier import BaseApplier

if TYPE_CHECKING:
    from playwright.async_api import Page, FrameLocator
    from app.models.job import Job

logger = logging.getLogger(__name__)


class GreenhouseApplier(BaseApplier):
    """
    Automates submission on Greenhouse hosted career pages & embedded iframes.
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
        screenshot_path = screenshot_dir / f"{application_id}_greenhouse.png"
        full_name = resume_parsed_json.get("full_name", "")
        first_name, last_name = self._split_name(full_name)
        email = resume_parsed_json.get("email", "")
        phone = resume_parsed_json.get("phone", "")

        try:
            logger.info("GreenhouseApplier: Navigating to %s", job.apply_url)
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # Determine if form is in main frame or iframe #grnhse_app
            target: Any = page
            if await page.locator("iframe#grnhse_app").count() > 0:
                logger.info("Detected Greenhouse iframe #grnhse_app")
                target = page.frame_locator("iframe#grnhse_app")

            # 1. Fill Name
            if await target.locator("#first_name").count() > 0:
                await target.locator("#first_name").fill(first_name)
                if last_name and await target.locator("#last_name").count() > 0:
                    await target.locator("#last_name").fill(last_name)
            elif await target.locator("input[name='first_name']").count() > 0:
                await target.locator("input[name='first_name']").fill(first_name)
                if last_name and await target.locator("input[name='last_name']").count() > 0:
                    await target.locator("input[name='last_name']").fill(last_name)
            elif await target.locator("#name").count() > 0:
                await target.locator("#name").fill(full_name)

            # 2. Fill Email
            for email_sel in ["#email", "input[name='email']", "input[type='email']"]:
                if await target.locator(email_sel).count() > 0:
                    await target.locator(email_sel).first.fill(email)
                    break

            # 3. Fill Phone
            for phone_sel in ["#phone", "input[name='phone']", "input[type='tel']"]:
                if await target.locator(phone_sel).count() > 0:
                    await target.locator(phone_sel).first.fill(phone)
                    break

            # 4. Upload Resume File
            if resume_file_path and Path(resume_file_path).exists():
                file_input = target.locator(
                    "input[type='file'][name*='resume' i], input#resume, input[type='file']"
                ).first
                if await file_input.count() > 0:
                    logger.info("Uploading resume from %s", resume_file_path)
                    await file_input.set_input_files(str(Path(resume_file_path).resolve()))
                    await page.wait_for_timeout(1000)

            # 5. Check for required custom questions / captcha
            # Standard Greenhouse fields: first_name, last_name, email, phone, resume, cover_letter, linkedin, website
            has_custom_required = False
            custom_fields = target.locator(
                "div.field:has(label span.asterisk), div.field:has(label:has-text('*')), "
                "div[data-required='true'], input[required]:not(#first_name):not(#last_name):not(#email):not(#phone)"
            )
            count = await custom_fields.count()
            if count > 0:
                # Inspect if any unfilled required input exists
                for i in range(count):
                    field = custom_fields.nth(i)
                    inputs = field.locator("input, select, textarea")
                    if await inputs.count() > 0:
                        val = await inputs.first.input_value() if await inputs.first.is_visible() else "filled"
                        if not val:
                            has_custom_required = True
                            break

            if has_custom_required:
                logger.info("Found custom required questions on Greenhouse form. Marking for manual review.")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                return {
                    "status": "pending_review",
                    "screenshot_path": str(screenshot_path),
                    "error_message": "Application form contains custom required questions requiring manual candidate input.",
                }

            # 6. Check for reCAPTCHA/hCaptcha
            if await page.locator("iframe[src*='recaptcha'], iframe[src*='hcaptcha'], div.g-recaptcha").count() > 0:
                logger.info("Captcha detected on Greenhouse form.")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                return {
                    "status": "pending_review",
                    "screenshot_path": str(screenshot_path),
                    "error_message": "Captcha challenge detected on application form.",
                }

            # 7. Submit Application
            submit_btn = target.locator(
                "input#submit_app, button#submit_app, button[type='submit']:has-text('Submit'), input[type='submit']"
            ).first

            if await submit_btn.count() > 0:
                logger.info("Clicking Greenhouse submit button...")
                await submit_btn.click()
                # Wait for navigation or confirmation banner
                await page.wait_for_timeout(4000)

                # Check for success indicators
                body_text = (await page.inner_text("body")).lower()
                if (
                    "thank you for applying" in body_text
                    or "application submitted" in body_text
                    or "received your application" in body_text
                    or await page.locator("#application_confirmation, div.confirmation").count() > 0
                ):
                    logger.info("Greenhouse application submitted successfully.")
                    return {
                        "status": "submitted",
                        "screenshot_path": None,
                        "error_message": None,
                    }

            # Fallback if submission confirmation wasn't unambiguous
            await page.screenshot(path=str(screenshot_path), full_page=True)
            return {
                "status": "pending_review",
                "screenshot_path": str(screenshot_path),
                "error_message": "Form pre-filled; submitted verification inconclusive. Saved for confirmation.",
            }

        except Exception as exc:
            logger.exception("GreenhouseApplier failed: %s", exc)
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pass
            return {
                "status": "failed",
                "screenshot_path": str(screenshot_path) if screenshot_path.exists() else None,
                "error_message": f"Greenhouse automation error: {exc}",
            }
