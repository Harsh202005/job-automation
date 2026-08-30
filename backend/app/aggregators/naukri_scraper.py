"""
Naukri.com Public Job Search Scraper (Best-Effort / Unauthenticated).
====================================================================
Scrapes public search results without credentials or login.
Marked as fragile: handles anti-bot / Cloudflare challenges by gracefully bailing out.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.naukri.com/{query_slug}-jobs-in-{location_slug}"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _slugify(text: str) -> str:
    """Format string into a safe Naukri URL slug."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", clean)


async def scrape_naukri_jobs(
    query: str = "software-engineer",
    location: str = "pune",
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """
    Scrape public job postings from Naukri unauthenticated search.

    Parameters
    ----------
    query : str
        Search keywords (e.g. 'software engineer', 'python developer').
    location : str
        Target city/region (e.g. 'pune', 'bangalore', 'mumbai').
    max_results : int
        Maximum job cards to parse.

    Returns
    -------
    list[dict[str, Any]]
        List of normalised job dicts (source="naukri").
    """
    q_slug = _slugify(query) or "software-engineer"
    loc_slug = _slugify(location) or "pune"
    target_url = _SEARCH_URL.format(query_slug=q_slug, location_slug=loc_slug)

    logger.info("Naukri Scraper ▸ Launching browser for URL: %s", target_url)

    jobs: list[dict[str, Any]] = []

    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415
    except ImportError:
        logger.warning("Playwright is not installed — skipping Naukri scraping.")
        return []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
            )
            page = await context.new_page()

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(3.0)  # Wait for dynamic React hydration

                # ── Challenge / Cloudflare / Bot Wall Detection ──────────────
                page_title = await page.title()
                content = await page.content()

                block_signals = [
                    "cloudflare",
                    "attention required",
                    "security verification",
                    "access denied",
                    "just a moment",
                    "robot",
                ]

                if any(sig in page_title.lower() for sig in block_signals):
                    logger.warning(
                        "Naukri Scraper ▸ Bot protection / verification wall encountered ('%s'). Bailing gracefully.",
                        page_title,
                    )
                    await browser.close()
                    return []

                # ── Extract Job Cards ─────────────────────────────────────────
                card_selectors = [
                    "div.srp-jobtuple-wrapper",
                    "div.cust-job-tuple",
                    "article.jobTuple",
                    "div.jobTuple",
                    "div.styles_job-tuple__i87hJ",
                ]

                cards = []
                for sel in card_selectors:
                    cards = await page.query_selector_all(sel)
                    if cards:
                        break

                logger.info("Naukri Scraper ▸ Found %d candidate job cards", len(cards))

                for card in cards[:max_results]:
                    try:
                        # Title
                        title_elem = await card.query_selector("a.title, .title, h2, h3")
                        title = (await title_elem.inner_text()).strip() if title_elem else ""

                        # Company
                        company_elem = await card.query_selector("a.comp-name, .comp-name, .companyInfo > a, span.comp-name")
                        company = (await company_elem.inner_text()).strip() if company_elem else "Naukri Employer"

                        # Location
                        loc_elem = await card.query_selector(".loc-wrap, .locWdth, span.location, .loc")
                        loc = (await loc_elem.inner_text()).strip() if loc_elem else location.title()

                        # Experience
                        exp_elem = await card.query_selector(".exp-wrap, .expwdth, span.exp, .experience")
                        exp_text = (await exp_elem.inner_text()).strip() if exp_elem else ""

                        # Description / Snippet
                        desc_elem = await card.query_selector(".job-desc, .row6, .desc, .jobDescription")
                        desc = (await desc_elem.inner_text()).strip() if desc_elem else ""

                        # Apply Link
                        link_elem = await card.query_selector("a.title, a.job-title, a")
                        href = (await link_elem.get_attribute("href")) if link_elem else ""
                        clean_url = href.split("?")[0] if href else target_url

                        # Job ID
                        job_id_attr = (await card.get_attribute("data-job-id")) or ""
                        if not job_id_attr:
                            id_match = re.search(r"-([0-9]{8,})-", clean_url)
                            job_id_attr = id_match.group(1) if id_match else str(hash(clean_url or f"{company}-{title}"))

                        # Posted time
                        date_elem = await card.query_selector("span.date, .job-post-day, span.badge")
                        posted_text = (await date_elem.inner_text()).strip() if date_elem else ""

                        if title and len(title) > 2:
                            full_desc = f"{desc} | Experience: {exp_text} | Posted: {posted_text}".strip(" |")
                            jobs.append({
                                "source": "naukri",
                                "source_job_id": str(job_id_attr),
                                "company": company,
                                "title": title,
                                "location": loc,
                                "description": full_desc,
                                "apply_url": clean_url,
                                "posted_at": None,
                                "raw_json": {
                                    "scraped_title": title,
                                    "scraped_company": company,
                                    "scraped_location": loc,
                                    "experience": exp_text,
                                    "posted_relative": posted_text,
                                    "scraped_url": clean_url,
                                },
                            })
                    except Exception as card_err:
                        logger.debug("Error parsing individual Naukri card: %s", card_err)
                        continue

            finally:
                await browser.close()

    except Exception as exc:
        logger.warning("Naukri Scraper ▸ Encountered unexpected error (returning empty list): %s", exc)
        return []

    logger.info("Naukri Scraper ▸ Successfully scraped %d jobs", len(jobs))
    return jobs
