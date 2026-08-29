"""
Resume Parser Module
====================
Extracts structured data from PDF and DOCX resume files with sub-second performance.

Strategy:
  1. Raw text extraction  — High-speed pypdfium2 (C++ engine) with pdfplumber fallback (PDF) / python-docx (DOCX)
  2. Section segmentation — regex-based header detection
  3. Entity extraction    — Fast heuristics + targeted spaCy NER for PERSON / ORG
  4. Section parsing      — Structured line-level parsing per section
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

# ── spaCy lazy-load / pre-warm singleton ─────────────────────────────────────
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
    "experience": re.compile(
        r"^\s*(work\s+experience|professional\s+experience|employment(\s+history)?|experience|work\s+history)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "education": re.compile(
        r"^\s*(education(\s+background)?|academic\s+(background|qualifications?|history)|qualifications?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "skills": re.compile(
        r"^\s*(technical\s+skills|key\s+skills|skills?\s*(summary|set)?|competencies|expertise|technologies|tools)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "summary": re.compile(
        r"^\s*(summary|profile|objective|about\s+me|professional\s+summary|executive\s+summary)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "certifications": re.compile(
        r"^\s*(certifications?|certificates?|licenses?|courses?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "projects": re.compile(
        r"^\s*(projects?|key\s+projects?|personal\s+projects?|portfolio)\s*:?\s*$",
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

_RE_DEGREE = re.compile(
    r"\b(b\.?s\.?|b\.?e\.?|b\.?tech|b\.?sc|bachelor|m\.?s\.?|m\.?e\.?|m\.?tech|"
    r"m\.?sc|master|ph\.?d|doctorate|associate|diploma|high\s+school|secondary)\b",
    re.IGNORECASE,
)
_RE_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_RE_INSTITUTION = re.compile(
    r"\b(university|college|institute|school|academy|polytechnic|campus|faculty)\b",
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
    """
    Extract text from a PDF.
    Uses pypdfium2 for ultra-fast C++ extraction (<10ms),
    falling back to pdfplumber if necessary.
    """
    # 1. Fast path: pypdfium2
    try:
        import pypdfium2 as pdfium  # noqa: PLC0415

        pdf = pdfium.PdfDocument(file_path)
        try:
            pages_text: list[str] = []
            for page in pdf:
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                if text and text.strip():
                    pages_text.append(text.strip())
            full_text = "\n\n".join(pages_text)
            if full_text.strip():
                return full_text
        finally:
            pdf.close()
    except Exception as exc:
        logger.debug("pypdfium2 extraction skipped/failed: %s, falling back to pdfplumber", exc)

    # 2. Fallback: pdfplumber fast stream extraction
    try:
        import pdfplumber  # noqa: PLC0415

        pages: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=False) or page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ""


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


def extract_raw_text(file_path: Path | str) -> str:
    """Dispatch to the correct extractor based on file extension."""
    file_path = Path(file_path)
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
    matches: list[tuple[int, int, str]] = []
    for name, pattern in _SECTION_HEADERS.items():
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end(), name))

    if not matches:
        return {"header": text}

    matches.sort(key=lambda x: x[0])

    sections: dict[str, str] = {}
    sections["header"] = text[: matches[0][0]].strip()

    for i, (start, end, name) in enumerate(matches):
        section_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        section_text = text[end:section_end].strip()
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


def _extract_name(header_text: str, warnings: list[str]) -> str:
    """
    Extract candidate's name using fast line heuristics + spaCy PERSON verification on header block.
    """
    # 1. Fast heuristic: candidate name is almost always the first prominent line of the header
    candidate_lines: list[str] = []
    for line in header_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip contact / url lines
        if _RE_EMAIL.search(line) or _RE_PHONE.search(line) or _RE_URL.search(line):
            continue
        # Skip if too long, has numbers, or contains common resume label words
        if len(line) > 60 or any(c.isdigit() for c in line):
            continue
        if re.search(r"\b(resume|curriculum|vitae|profile|cv)\b", line, re.IGNORECASE):
            continue
        candidate_lines.append(line)
        if len(candidate_lines) >= 3:
            break

    if candidate_lines:
        first_candidate = candidate_lines[0]
        # If line is 2-4 words, uppercase or title-case, it's very likely the name
        words = first_candidate.split()
        if 1 <= len(words) <= 4 and not any(len(w) > 25 for w in words):
            return first_candidate

    # 2. Targeted spaCy NER on top header block
    nlp = _get_nlp()
    if nlp:
        doc = nlp(header_text[:400])
        persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON" and len(ent.text.strip()) > 2]
        if persons:
            return max(persons, key=len)

    if candidate_lines:
        warnings.append("Name extracted via fallback heuristic — verify accuracy.")
        return candidate_lines[0]

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Skills extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_skills(skills_text: str, full_text: str = "") -> list[str]:
    """
    Extract skill tokens from the Skills section.
    Handles comma-separated, bullet-separated, pipe-separated, and newline-separated lists.
    """
    raw_skills: list[str] = []

    if skills_text:
        # Normalise common separators
        normalised = re.sub(r"[•·▪▸►\-\*\|,;/]", "\n", skills_text)
        for line in normalised.splitlines():
            token = line.strip()
            # Handle category prefixes like "Programming Languages: Python, Java"
            if ":" in token:
                parts = token.split(":", 1)
                token = parts[1].strip() if len(parts) > 1 else token
            if token and 2 <= len(token) <= 50:
                raw_skills.append(token)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in raw_skills:
        clean_s = s.strip("()[]{}'\"., ")
        key = clean_s.lower()
        if key and key not in seen and len(clean_s) >= 2:
            seen.add(key)
            unique.append(clean_s)

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
    from datetime import datetime, timezone  # noqa: PLC0415

    start = _parse_date(start_str)
    end_lower = end_str.strip().lower()
    if end_lower in ("present", "current", "now"):
        end = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        end = _parse_date(end_str)

    if start is None or end is None or end < start:
        return 0.0

    delta = relativedelta(end, start)
    return round(delta.years + delta.months / 12, 2)


def _extract_experience(exp_text: str, warnings: list[str]) -> tuple[list[dict[str, str]], float]:
    """
    Parse the experience section into a list of job entries with fast structural extraction.
    Each entry: {title, company, duration, description}
    """
    if not exp_text:
        return [], 0.0

    entries: list[dict[str, str]] = []
    total_years = 0.0

    # Split into blocks on empty lines
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
            block_text_clean = block_text.replace(date_match.group(0), "").strip()
        else:
            block_text_clean = block_text

        lines_clean = [l.strip() for l in block_text_clean.splitlines() if l.strip()]
        if not lines_clean:
            continue

        # ── Title & Company Fast Structural Analysis ────────────────────────
        first_line = lines_clean[0]
        # Check delimiters like "Title at Company", "Title | Company", "Title - Company", "Title, Company"
        delimiters = [
            r"\s+at\s+",
            r"\s*@\s*",
            r"\s*\|\s*",
            r"\s*–\s*",
            r"\s*—\s*",
            r"\s*-\s*",
            r"\s*,\s*",
        ]
        found_split = False
        for delim in delimiters:
            parts = re.split(delim, first_line, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                entry["title"] = parts[0].strip()
                entry["company"] = parts[1].strip()
                found_split = True
                break

        if not found_split:
            entry["title"] = first_line
            if len(lines_clean) > 1:
                entry["company"] = lines_clean[1]

        desc_start = 2 if (entry["company"] and len(lines_clean) > 1 and entry["company"] == lines_clean[1]) else 1
        entry["description"] = " ".join(lines_clean[desc_start:])

        if entry["title"] or entry["company"]:
            entries.append(entry)
        else:
            warnings.append(f"Could not parse an experience block: {block_text[:60]!r}")

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

    entries: list[dict[str, str]] = []

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
            entry["year"] = year_m[-1]

        # Degree
        degree_m = _RE_DEGREE.search(block_text)
        if degree_m:
            for line in block:
                if _RE_DEGREE.search(line):
                    entry["degree"] = line.strip()
                    break

        # Institution (fast regex check)
        for line in block:
            if _RE_INSTITUTION.search(line):
                entry["institution"] = line.strip()
                break

        if not entry["institution"] and len(block) > 1:
            # Fallback to second line if not equal to degree line
            second_line = block[1].strip()
            if second_line != entry["degree"]:
                entry["institution"] = second_line

        if entry["degree"] or entry["institution"]:
            entries.append(entry)
        else:
            warnings.append(f"Could not parse an education block: {block_text[:60]!r}")

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_resume_with_raw_text(file_path: str | Path) -> tuple[dict[str, Any], str]:
    """
    Parse a PDF or DOCX resume file and return both structured dict and extracted raw text.
    Eliminates redundant text extraction passes.
    """
    file_path = Path(file_path)
    result = ParsedResume()

    # ── 1. Raw text extraction (Single pass) ─────────────────────────────────
    try:
        raw_text = extract_raw_text(file_path)
    except Exception as exc:
        result.parse_warnings.append(f"Text extraction failed: {exc}")
        return result.to_dict(), ""

    if not raw_text.strip():
        result.parse_warnings.append("Extracted text is empty — the file may be image-based or corrupt.")
        return result.to_dict(), ""

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
        result.full_name = _extract_name(header_text, result.parse_warnings)
    except Exception as exc:
        result.parse_warnings.append(f"Name extraction error: {exc}")

    # ── 5. Skills ───────────────────────────────────────────────────────────
    try:
        result.skills = _extract_skills(sections.get("skills", ""), raw_text)
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

    return result.to_dict(), raw_text


def parse_resume(file_path: str | Path) -> dict[str, Any]:
    """
    Parse a PDF or DOCX resume file and return a structured dict.
    """
    parsed_dict, _ = parse_resume_with_raw_text(file_path)
    return parsed_dict
