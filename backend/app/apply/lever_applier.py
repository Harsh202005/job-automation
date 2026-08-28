"""
Lever ATS Form Applier
======================
Fills and submits standard Lever application forms.
Flags postings with custom questions or captcha for manual review.
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


class LeverApplier(BaseApplier):
    """
    Automates submission on Lever hosted career pages (jobs.lever.co).
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
        screenshot_path = screenshot_dir / f"{application_id}_lever.png"
        full_name = resume_parsed_json.get("full_name", "")
        email = resume_parsed_json.get("email", "")
        phone = resume_parsed_json.get("phone", "")

        try:
            logger.info("LeverApplier: Navigating to %s", job.apply_url)
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # If on posting overview page, click "Apply for this job" / .postings-btn
            apply_btn = page.locator("a.postings-btn, a:has-text('Apply for this job')").first
            if await apply_btn.count() > 0 and not page.url.endswith("/apply"):
                logger.info("Navigating to Lever application form view...")
                await apply_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)

            # 1. Fill Name
            name_input = page.locator("input[name='name'], input#name").first
            if await name_input.count() > 0:
                await name_input.fill(full_name)

            # 2. Fill Email
            email_input = page.locator("input[name='email'], input[type='email']").first
            if await email_input.count() > 0:
                await email_input.fill(email)

            # 3. Fill Phone
            phone_input = page.locator("input[name='phone'], input[type='tel']").first
            if await phone_input.count() > 0:
                await phone_input.fill(phone)

            # 4. Fill Current Company / Org if present in experience
            org_input = page.locator("input[name='org']").first
            if await org_input.count() > 0:
                exps = resume_parsed_json.get("experience", [])
                company = exps[0].get("company", "") if exps else ""
                if company:
                    await org_input.fill(company)

            # 5. Upload Resume File
            if resume_file_path and Path(resume_file_path).exists():
                file_input = page.locator("input#resume-upload-input, input[type='file']").first
                if await file_input.count() > 0:
                    logger.info("Uploading resume to Lever form: %s", resume_file_path)
                    await file_input.set_input_files(str(Path(resume_file_path).resolve()))
                    await page.wait_for_timeout(1500)

            # 6. Check for custom required questions
            custom_questions = page.locator(
                "div.application-question:has(span.required), "
                "div.custom-question:has(span.required), "
                "div.application-question:has-text('*')"
            )
            count = await custom_questions.count()
            has_unfilled_custom = False
            if count > 0:
                for i in range(count):
                    q = custom_questions.nth(i)
                    inputs = q.locator("input, textarea, select")
                    if await inputs.count() > 0:
                        val = await inputs.first.input_value() if await inputs.first.is_visible() else "filled"
                        if not val:
                            has_unfilled_custom = True
                            break

            if has_unfilled_custom:
                logger.info("Lever form contains custom questions requiring manual candidate input.")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                return {
                    "status": "pending_review",
                    "screenshot_path": str(screenshot_path),
                    "error_message": "Application contains custom questions requiring manual candidate response.",
                }

            # 7. Check for Captcha / Cloudflare challenges
            if await page.locator("iframe[src*='recaptcha'], iframe[src*='hcaptcha'], #cf-turnstile").count() > 0:
                logger.info("Captcha detected on Lever form.")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                return {
                    "status": "pending_review",
                    "screenshot_path": str(screenshot_path),
                    "error_message": "Captcha challenge detected on application form.",
                }

            # 8. Submit Application
            submit_btn = page.locator(
                "button#btn-submit, button[type='submit']:has-text('Submit'), button.postings-btn"
            ).first
            if await submit_btn.count() > 0:
                logger.info("Submitting Lever application...")
                await submit_btn.click()
                await page.wait_for_timeout(4000)

                body_text = (await page.inner_text("body")).lower()
                if (
                    "thank you for applying" in body_text
                    or "application submitted" in body_text
                    or "received your application" in body_text
                    or "/thanks" in page.url
                    or "/confirmation" in page.url
                ):
                    logger.info("Lever application successfully submitted.")
                    return {
                        "status": "submitted",
                        "screenshot_path": None,
                        "error_message": None,
                    }

            # Fallback to screenshot if status ambiguous
            await page.screenshot(path=str(screenshot_path), full_page=True)
            return {
                "status": "pending_review",
                "screenshot_path": str(screenshot_path),
                "error_message": "Form pre-filled; submitted verification inconclusive. Saved for manual review.",
            }

        except Exception as exc:
            logger.exception("LeverApplier failed: %s", exc)
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pass
            return {
                "status": "failed",
                "screenshot_path": str(screenshot_path) if screenshot_path.exists() else None,
                "error_message": f"Lever automation error: {exc}",
            }
