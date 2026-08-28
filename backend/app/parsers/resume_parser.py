"""
Resume Parser Module
====================
Extracts structured data from PDF and DOCX resume files.

Strategy:
  1. Raw text extraction  — pdfplumber (PDF) / python-docx (DOCX)
  2. Section segmentation — regex-based header detection
  3. Entity extraction    — spaCy NER for PERSON / ORG / DATE + regex for
                             email / phone
  4. Section parsing      — heuristic line-level parsing per section
  5. Duration estimation  — date-range arithmetic via dateutil

All errors are caught; partial data + warnings are returned rather than
raising so the API layer always gets a usable response.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

# ── spaCy lazy-load (avoid paying startup cost if module is imported but
#    parse() is never called) ────────────────────────────────────────────────
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy  # noqa: PLC0415

        try:
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
        except OSError:
            logger.warning(
                "spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm\n"
                "Falling back to regex-only extraction."
            )
            _nlp = None
    return _nlp


# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns
# ─────────────────────────────────────────────────────────────────────────────
_RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_RE_PHONE = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{4}"
)
_RE_URL = re.compile(r"https?://\S+|www\.\S+")

# Section headers — ordered by priority (more specific first)
_SECTION_HEADERS = {
    "experience":  re.compile(
        r"^\s*(work\s+experience|professional\s+experience|employment(\s+history)?|experience)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "education":   re.compile(
        r"^\s*(education(\s+background)?|academic\s+(background|qualifications?))\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "skills":      re.compile(
        r"^\s*(technical\s+skills|key\s+skills|skills?\s*(summary|set)?|competencies|expertise)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "summary":     re.compile(
        r"^\s*(summary|profile|objective|about\s+me|professional\s+summary)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "certifications": re.compile(
        r"^\s*(certifications?|certificates?|licenses?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# Date-range pattern: "Jan 2020 – Present", "03/2018 - 06/2021", etc.
_RE_DATE_RANGE = re.compile(
    r"(?P<start>"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
    r"|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s,\.]+\d{4}"
    r"|\d{1,2}[/\-]\d{4}"
    r"|\d{4}"
    r")"
    r"\s*(?:–|—|-|to)\s*"
    r"(?P<end>"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
    r"|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s,\.]+\d{4}"
    r"|\d{1,2}[/\-]\d{4}"
    r"|\d{4}"
    r"|present|current|now"
    r")",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ParsedResume:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[dict[str, str]] = field(default_factory=list)
    education: list[dict[str, str]] = field(default_factory=list)
    total_experience_years: float = 0.0
    parse_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "experience": self.experience,
            "education": self.education,
            "total_experience_years": self.total_experience_years,
            "parse_warnings": self.parse_warnings,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_text_pdf(file_path: Path) -> str:
    """Extract text from a PDF using pdfplumber."""
    import pdfplumber  # noqa: PLC0415

    pages: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                pages.append(text)
    return "\n".join(pages)


def _extract_text_docx(file_path: Path) -> str:
    """Extract text from a DOCX using python-docx."""
    from docx import Document  # noqa: PLC0415

    doc = Document(file_path)
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    # Also pull text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)
    return "\n".join(paragraphs)


def extract_raw_text(file_path: Path) -> str:
    """Dispatch to the correct extractor based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_pdf(file_path)
    if suffix in (".docx", ".doc"):
        return _extract_text_docx(file_path)
    raise ValueError(f"Unsupported file type: '{suffix}'. Only PDF and DOCX are supported.")


# ─────────────────────────────────────────────────────────────────────────────
# Section segmentation
# ─────────────────────────────────────────────────────────────────────────────

def _segment_sections(text: str) -> dict[str, str]:
    """
    Split resume text into named sections.

    Returns a dict: section_name -> section_text.
    The 'header' key always holds text before the first recognised section.
    """
    # Collect all section matches with their positions
    matches: list[tuple[int, int, str]] = []  # (start, end, section_name)
    for name, pattern in _SECTION_HEADERS.items():
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end(), name))

    if not matches:
        return {"header": text}

    # Sort by position
    matches.sort(key=lambda x: x[0])

    sections: dict[str, str] = {}
    sections["header"] = text[: matches[0][0]].strip()

    for i, (start, end, name) in enumerate(matches):
        section_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        section_text = text[end:section_end].strip()
        # If we already saw this section, append
        if name in sections:
            sections[name] = sections[name] + "\n" + section_text
        else:
            sections[name] = section_text

    return sections


# ─────────────────────────────────────────────────────────────────────────────
# Contact extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_email(text: str) -> str:
    m = _RE_EMAIL.search(text)
    return m.group(0) if m else ""


def _extract_phone(text: str) -> str:
    m = _RE_PHONE.search(text)
    return m.group(0).strip() if m else ""


def _extract_name_spacy(header_text: str, warnings: list[str]) -> str:
    """
    Use spaCy PERSON entities to find the candidate's name in the header block.
    Falls back to the first non-empty, non-contact line.
    """
    nlp = _get_nlp()
    if nlp:
        # Limit to the first ~500 chars to stay fast and focused
        doc = nlp(header_text[:500])
        persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            # The longest PERSON entity in the header is most likely the full name
            return max(persons, key=len)

    # Fallback: first non-blank line that contains no email/phone/URL
    for line in header_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if _RE_EMAIL.search(line) or _RE_PHONE.search(line) or _RE_URL.search(line):
            continue
        # Skip lines that look like addresses or are too long to be a name
        if len(line) > 60 or any(c.isdigit() for c in line):
            continue
        warnings.append("Name extracted via fallback heuristic — verify accuracy.")
        return line

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Skills extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_skills(skills_text: str) -> list[str]:
    """
    Extract skill tokens from the Skills section.
    Handles comma-separated, bullet-separated, and newline-separated lists.
    """
    if not skills_text:
        return []

    # Normalise common separators to newlines
    normalised = re.sub(r"[•·▪▸►\-\*\|,;/]", "\n", skills_text)
    raw_skills: list[str] = []
    for line in normalised.splitlines():
        token = line.strip()
        if token and len(token) < 80:  # sanity-check length
            raw_skills.append(token)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in raw_skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Experience extraction
# ─────────────────────────────────────────────────────────────────────────────

def _parse_date(date_str: str) -> Any:
    """Parse a fuzzy date string into a datetime; return None on failure."""
    try:
        return dateutil_parser.parse(date_str, fuzzy=True, default=dateutil_parser.parse("1900-01-01"))
    except Exception:
        return None


def _compute_duration_years(start_str: str, end_str: str) -> float:
    """Return fractional years between two date strings. Returns 0 on failure."""
    from datetime import datetime  # noqa: PLC0415

    start = _parse_date(start_str)
    end_lower = end_str.strip().lower()
    if end_lower in ("present", "current", "now"):
        end = datetime.utcnow()
    else:
        end = _parse_date(end_str)

    if start is None or end is None or end < start:
        return 0.0

    delta = relativedelta(end, start)
    return round(delta.years + delta.months / 12, 2)


def _extract_experience(exp_text: str, warnings: list[str]) -> tuple[list[dict[str, str]], float]:
    """
    Parse the experience section into a list of job entries.

    Each entry: {title, company, duration, description}
    Also returns the summed total experience in years.
    """
    if not exp_text:
        return [], 0.0

    nlp = _get_nlp()
    entries: list[dict[str, str]] = []
    total_years = 0.0

    # Split into blocks — a blank line or a line that looks like a new job header
    # acts as a delimiter.
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in exp_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(stripped)
    if current:
        blocks.append(current)

    for block in blocks:
        if not block:
            continue

        block_text = "\n".join(block)
        entry: dict[str, str] = {
            "title": "",
            "company": "",
            "duration": "",
            "description": "",
        }

        # ── Duration ────────────────────────────────────────────────────────
        date_match = _RE_DATE_RANGE.search(block_text)
        if date_match:
            start_str = date_match.group("start")
            end_str = date_match.group("end")
            entry["duration"] = date_match.group(0).strip()
            total_years += _compute_duration_years(start_str, end_str)
            # Remove the date range from the block so it doesn't pollute other fields
            block_text_clean = block_text.replace(date_match.group(0), "").strip()
        else:
            block_text_clean = block_text

        lines_clean = [l.strip() for l in block_text_clean.splitlines() if l.strip()]

        # ── Title & Company via spaCy ────────────────────────────────────
        if nlp and lines_clean:
            doc = nlp(lines_clean[0])
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            if orgs:
                entry["company"] = orgs[0]

        # ── Heuristic: first line = title (or "Title at Company") ────────
        if lines_clean:
            first_line = lines_clean[0]
            at_split = re.split(r"\s+at\s+|\s*@\s*", first_line, maxsplit=1, flags=re.IGNORECASE)
            if len(at_split) == 2:
                entry["title"] = at_split[0].strip()
                entry["company"] = at_split[1].strip()
            else:
                entry["title"] = first_line
            # Second line might be the company if not yet found
            if not entry["company"] and len(lines_clean) > 1:
                entry["company"] = lines_clean[1]
            # Rest is description
            desc_start = 2 if entry["company"] == (lines_clean[1] if len(lines_clean) > 1 else "") else 1
            entry["description"] = " ".join(lines_clean[desc_start:])

        if entry["title"] or entry["company"]:
            entries.append(entry)
        else:
            warnings.append(f"Could not parse an experience block: {block_text[:80]!r}")

    return entries, round(total_years, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Education extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_education(edu_text: str, warnings: list[str]) -> list[dict[str, str]]:
    """
    Parse the education section into a list of education entries.

    Each entry: {degree, institution, year}
    """
    if not edu_text:
        return []

    nlp = _get_nlp()
    entries: list[dict[str, str]] = []

    # Degree keywords for detection
    _RE_DEGREE = re.compile(
        r"\b(b\.?s\.?|b\.?e\.?|b\.?tech|b\.?sc|bachelor|m\.?s\.?|m\.?e\.?|m\.?tech|"
        r"m\.?sc|master|ph\.?d|doctorate|associate|diploma|high\s+school|secondary)\b",
        re.IGNORECASE,
    )
    _RE_YEAR = re.compile(r"\b(19|20)\d{2}\b")

    # Split into blocks on blank lines
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in edu_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(stripped)
    if current:
        blocks.append(current)

    for block in blocks:
        if not block:
            continue
        block_text = "\n".join(block)
        entry: dict[str, str] = {"degree": "", "institution": "", "year": ""}

        # Year
        year_m = _RE_YEAR.findall(block_text)
        if year_m:
            entry["year"] = year_m[-1]  # Last year mentioned is graduation year

        # Degree
        degree_m = _RE_DEGREE.search(block_text)
        if degree_m:
            # Grab the whole line containing the degree keyword
            for line in block:
                if _RE_DEGREE.search(line):
                    entry["degree"] = line.strip()
                    break

        # Institution via spaCy ORG, or fallback to second line
        if nlp:
            doc = nlp(block_text[:300])
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            if orgs:
                entry["institution"] = orgs[0]

        if not entry["institution"] and len(block) > 1:
            entry["institution"] = block[1].strip()

        if entry["degree"] or entry["institution"]:
            entries.append(entry)
        else:
            warnings.append(f"Could not parse an education block: {block_text[:80]!r}")

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_resume(file_path: str | Path) -> dict[str, Any]:
    """
    Parse a PDF or DOCX resume file and return a structured dict.

    Parameters
    ----------
    file_path : str | Path
        Absolute or relative path to the resume file.

    Returns
    -------
    dict
        Structured resume data matching the ParsedResume schema, always
        including a ``parse_warnings`` list.
    """
    file_path = Path(file_path)
    result = ParsedResume()

    # ── 1. Raw text extraction ──────────────────────────────────────────────
    try:
        raw_text = extract_raw_text(file_path)
    except Exception as exc:
        result.parse_warnings.append(f"Text extraction failed: {exc}")
        return result.to_dict()

    if not raw_text.strip():
        result.parse_warnings.append("Extracted text is empty — the file may be image-based or corrupt.")
        return result.to_dict()

    # ── 2. Section segmentation ─────────────────────────────────────────────
    try:
        sections = _segment_sections(raw_text)
    except Exception as exc:
        result.parse_warnings.append(f"Section segmentation failed: {exc}")
        sections = {"header": raw_text}

    header_text = sections.get("header", raw_text[:500])

    # ── 3. Contact info ─────────────────────────────────────────────────────
    try:
        result.email = _extract_email(raw_text)
    except Exception as exc:
        result.parse_warnings.append(f"Email extraction error: {exc}")

    try:
        result.phone = _extract_phone(raw_text)
    except Exception as exc:
        result.parse_warnings.append(f"Phone extraction error: {exc}")

    # ── 4. Name ─────────────────────────────────────────────────────────────
    try:
        result.full_name = _extract_name_spacy(header_text, result.parse_warnings)
    except Exception as exc:
        result.parse_warnings.append(f"Name extraction error: {exc}")

    # ── 5. Skills ───────────────────────────────────────────────────────────
    try:
        result.skills = _extract_skills(sections.get("skills", ""))
    except Exception as exc:
        result.parse_warnings.append(f"Skills extraction error: {exc}")

    # ── 6. Experience ───────────────────────────────────────────────────────
    try:
        result.experience, result.total_experience_years = _extract_experience(
            sections.get("experience", ""),
            result.parse_warnings,
        )
    except Exception as exc:
        result.parse_warnings.append(f"Experience extraction error: {exc}")

    # ── 7. Education ────────────────────────────────────────────────────────
    try:
        result.education = _extract_education(
            sections.get("education", ""),
            result.parse_warnings,
        )
    except Exception as exc:
        result.parse_warnings.append(f"Education extraction error: {exc}")

    return result.to_dict()
