"""
Base Application Automation Interface
======================================
Defines the standard abstract contract for ATS-specific and portal appliers.
"""
from __future__ import annotations

import abc
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page
    from app.models.job import Job

logger = logging.getLogger(__name__)


class BaseApplier(abc.ABC):
    """
    Abstract interface for executing automated or semi-automated job applications.
    """

    @abc.abstractmethod
    async def apply(
        self,
        job: Job,
        resume_parsed_json: dict[str, Any],
        resume_file_path: str,
        page: Page,
        screenshot_dir: Path,
        application_id: str,
    ) -> dict[str, Any]:
        """
        Execute application flow against a target job posting.

        Parameters
        ----------
        job : Job
            ORM record of the target job posting.
        resume_parsed_json : dict
            Parsed candidate details (full_name, email, phone, skills, etc.).
        resume_file_path : str
            Absolute or relative file path to the user's uploaded resume (PDF/DOCX).
        page : Page
            Playwright page instance in the current browser context.
        screenshot_dir : Path
            Directory path to persist pre-submit or diagnostic screenshots.
        application_id : str
            Unique ID string representing the current application attempt.

        Returns
        -------
        dict
            {
                "status": "submitted" | "pending_review" | "failed" | "skipped",
                "screenshot_path": str | None,
                "error_message": str | None,
            }
        """
        raise NotImplementedError

    @staticmethod
    def _split_name(full_name: str) -> tuple[str, str]:
        """Utility to split full name into (first_name, last_name)."""
        parts = full_name.strip().split()
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])
