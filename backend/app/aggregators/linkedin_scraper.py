"""
LinkedIn Public Job Search Scraper (Best-Effort / Unauthenticated).
===================================================================
Scrapes public search results without credentials or login.
Marked as fragile: handles CAPTCHA/authwall by gracefully bailing out.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.linkedin.com/jobs/search?keywords={query}&location={location}&sortBy=DD"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


async def scrape_linkedin_jobs(
    query: str = "software engineer",
    location: str = "pune",
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """
    Scrape public job postings from LinkedIn unauthenticated search.

    Parameters
    ----------
    query : str
        Search keywords (e.g. 'software engineer', 'python developer').
    location : str
        Target location (e.g. 'pune', 'bangalore', 'india').
    max_results : int
        Maximum job cards to parse.

    Returns
    -------
    list[dict[str, Any]]
        List of normalised job dicts (source="linkedin").
    """
    target_url = _SEARCH_URL.format(query=quote_plus(query), location=quote_plus(location))
    logger.info("LinkedIn Scraper ▸ Launching browser for URL: %s", target_url)

    jobs: list[dict[str, Any]] = []

    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415
    except ImportError:
        logger.warning("Playwright is not installed — skipping LinkedIn scraping.")
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
                locale="en-US",
            )
            page = await context.new_page()

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(2.5)  # Realistic delay for hydration

                # ── CAPTCHA & Authwall Detection ──────────────────────────────
                page_title = await page.title()
                page_content = await page.content()

                authwall_indicators = [
                    "authwall",
                    "checkpoint",
                    "challenge",
                    "sign in",
                    "security verification",
                    "join linkedin",
                ]

                if any(ind in page_title.lower() for ind in authwall_indicators):
                    logger.warning(
                        "LinkedIn Scraper ▸ CAPTCHA / Authwall encountered ('%s'). Bailing gracefully.",
                        page_title,
                    )
                    await browser.close()
                    return []

                # Check for challenge form elements
                captcha_elem = await page.query_selector("input[name='captcha'], #checkpoint-challenge, .challenge-page")
                if captcha_elem:
                    logger.warning("LinkedIn Scraper ▸ Security challenge element found. Bailing gracefully.")
                    await browser.close()
                    return []

                # ── Extract Job Cards ─────────────────────────────────────────
                card_selectors = [
                    "div.base-card",
                    "li.jobs-search__results-list > li",
                    "div.job-search-card",
                    "ul.jobs-search__results-list > li",
                ]

                cards = []
                for sel in card_selectors:
                    cards = await page.query_selector_all(sel)
                    if cards:
                        break

                logger.info("LinkedIn Scraper ▸ Found %d candidate job cards", len(cards))

                for card in cards[:max_results]:
                    try:
                        # Title
                        title_elem = await card.query_selector("h3.base-search-card__title, .base-card__full-link, h3")
                        title = (await title_elem.inner_text()).strip() if title_elem else ""

                        # Company
                        company_elem = await card.query_selector("h4.base-search-card__subtitle, a.hidden-nested-link, h4")
                        company = (await company_elem.inner_text()).strip() if company_elem else "LinkedIn Employer"

                        # Location
                        loc_elem = await card.query_selector("span.job-search-card__location, .job-search-card__location")
                        loc = (await loc_elem.inner_text()).strip() if loc_elem else location.title()

                        # Apply Link & Job ID
                        link_elem = await card.query_selector("a.base-card__full-link, a")
                        href = (await link_elem.get_attribute("href")) if link_elem else ""
                        clean_url = href.split("?")[0] if href else target_url

                        # Extract Job ID
                        job_id_match = re.search(r"view/([0-9]+)", href or "")
                        job_id = job_id_match.group(1) if job_id_match else str(hash(clean_url or f"{company}-{title}"))

                        # Posted date
                        date_elem = await card.query_selector("time, span.job-search-card__listdate")
                        posted_text = (await date_elem.inner_text()).strip() if date_elem else ""

                        if title and len(title) > 2:
                            jobs.append({
                                "source": "linkedin",
                                "source_job_id": str(job_id),
                                "company": company,
                                "title": title,
                                "location": loc,
                                "description": f"LinkedIn public listing for {title} at {company}. Posted {posted_text}.",
                                "apply_url": clean_url,
                                "posted_at": None,
                                "raw_json": {
                                    "scraped_title": title,
                                    "scraped_company": company,
                                    "scraped_location": loc,
                                    "posted_relative": posted_text,
                                    "scraped_url": clean_url,
                                },
                            })
                    except Exception as card_err:
                        logger.debug("Error parsing individual LinkedIn card: %s", card_err)
                        continue

            finally:
                await browser.close()

    except Exception as exc:
        logger.warning("LinkedIn Scraper ▸ Encountered unexpected error (returning empty list): %s", exc)
        return []

    logger.info("LinkedIn Scraper ▸ Successfully scraped %d jobs", len(jobs))
    return jobs
