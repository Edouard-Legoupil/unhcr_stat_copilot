#!/usr/bin/env python3
"""
Convert UNHCR statistical report PDFs into structured Markdown using Docling.

Main outputs per report:
    index.md
    full.md
    raw_docling.md
    structure.json
    figures_tables.json
    footnotes.json
    quality_report.md
    sections/*.md

Key features:
- Docling-first PDF conversion.
- OCR disabled by default to avoid RapidOCR/model issues and duplicate text.
- UNHCR-specific Markdown post-processing.
- Statistical cards demoted to bold/callout text rather than headings.
- CTA/link boxes demoted where appropriate.
- Robust figure/table caption detection.
- Footnote definitions extracted from PDF page flow and appended as Markdown footnotes.
- Section-level files for downstream indexing/RAG.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------
# Input reports
# ---------------------------------------------------------------------

STATREPORTS = [
    ["data/reports/5e57d0c57.pdf", "MID-YEAR TRENDS 2019", "https://www.unhcr.org/media/mid-year-trends-2019"],
    ["data/reports/5ee200e37.pdf", "GLOBAL TRENDS 2019", "https://www.unhcr.org/media/unhcr-global-trends-report-2019"],

    ["data/reports/5fc504d44.pdf", "MID-YEAR TRENDS 2020", "https://www.unhcr.org/media/mid-year-trends-2020"],
    ["data/reports/60b638e37.pdf", "GLOBAL TRENDS 2020", "https://www.unhcr.org/media/global-trends-forced-displacement-2020"],

    ["data/reports/618ae4694.pdf", "MID-YEAR TRENDS 2021", "https://www.unhcr.org/media/mid-year-trends-2021"],
    ["data/reports/62a9d1494.pdf", "GLOBAL TRENDS 2021", "https://www.unhcr.org/media/global-trends-report-2021"],

    ["data/reports/635a578f4.pdf", "MID-YEAR TRENDS 2022", "https://www.unhcr.org/publications/mid-year-trends-2022"],
    ["data/reports/global-trends-report-2022.pdf", "GLOBAL TRENDS 2022", "https://www.unhcr.org/global-trends-report-2022"],

    ["data/reports/Mid-year-trends-2023.pdf", "MID-YEAR TRENDS 2023", "https://www.unhcr.org/media/mid-year-trends-2023"],
    ["data/reports/global-trends-report-2023.pdf", "GLOBAL TRENDS 2023", "https://www.unhcr.org/media/global-trends-report-2023"],

    ["data/reports/mid-year-trends-report-2024.pdf", "MID-YEAR TRENDS 2024", "https://www.unhcr.org/media/mid-year-trends-2024"],
    ["data/reports/global-trends-report-2024.pdf", "GLOBAL TRENDS 2024", "https://www.unhcr.org/media/global-trends-report-2024"],

    ["data/reports/mid-year-trends-report-2025.pdf", "MID-YEAR TRENDS 2025", "https://www.unhcr.org/media/mid-year-trends-2025"],
    ["data/reports/global-trends-report-2025.pdf", "GLOBAL TRENDS 2025", "https://www.unhcr.org/media/global-trends-report-2025"],
]


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

OUTPUT_DIR = Path("data/markdown_reports")

ENABLE_OCR = False
WRITE_RAW_DOCLING_MARKDOWN = True
WRITE_SECTION_FILES = True
ANNOTATE_RUNNING_HEADERS = True

MAX_CAPTION_CONTINUATION_LINES = 3


# ---------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------

@dataclass
class ReportMeta:
    title: str
    year: str
    report_type: str
    source_pdf: str
    source_url: str
    slug: str
    output_dir: str
    generated_at: str


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def normalise_title(title: str) -> str:
    title = title.replace("GLOBALTRENDS", "GLOBAL TRENDS")
    title = re.sub(r"\s+", " ", title).strip()
    return title.upper()


def extract_year(title: str, url: str, path: str) -> str:
    for value in [title, url, path]:
        match = re.search(r"\b(20\d{2})\b", value)
        if match:
            return match.group(1)
    return "unknown-year"


def report_type_from_title(title: str) -> str:
    upper = title.upper()
    if "MID-YEAR" in upper or "MID YEAR" in upper:
        return "Mid-Year Trends"
    if "GLOBAL" in upper:
        return "Global Trends"
    return "Unknown Report Type"


def slugify(text: str) -> str:
    text = text.lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "untitled"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_pdf_page_count(pdf_path: Path) -> int | None:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


# ---------------------------------------------------------------------
# Docling conversion
# ---------------------------------------------------------------------

def build_docling_converter(enable_ocr: bool = ENABLE_OCR):
    """
    Build a Docling converter.

    OCR is disabled by default because UNHCR reports are digitally-born PDFs.
    OCR can create duplicate text, reading-order degradation, and RapidOCR
    backend/model errors.
    """
    from docling.document_converter import DocumentConverter

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import PdfFormatOption

        pipeline_options = PdfPipelineOptions()

        if hasattr(pipeline_options, "generate_page_images"):
            pipeline_options.generate_page_images = True

        if hasattr(pipeline_options, "generate_picture_images"):
            pipeline_options.generate_picture_images = True

        if hasattr(pipeline_options, "images_scale"):
            pipeline_options.images_scale = 2.0

        if hasattr(pipeline_options, "do_table_structure"):
            pipeline_options.do_table_structure = True

        if hasattr(pipeline_options, "do_ocr"):
            pipeline_options.do_ocr = enable_ocr

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

    except Exception:
        return DocumentConverter()


def export_docling_markdown(doc: Any, output_md: Path) -> str:
    """
    Export a Docling document to Markdown, preserving referenced image assets
    when the installed Docling version supports it.
    """
    try:
        from docling_core.types.doc import ImageRefMode

        if hasattr(doc, "save_as_markdown"):
            doc.save_as_markdown(
                output_md,
                image_mode=ImageRefMode.REFERENCED,
            )
            return output_md.read_text(encoding="utf-8")

        if hasattr(doc, "export_to_markdown"):
            return doc.export_to_markdown(
                image_mode=ImageRefMode.REFERENCED
            )

    except Exception:
        pass

    if hasattr(doc, "export_to_markdown"):
        return doc.export_to_markdown()

    raise RuntimeError("Could not export Docling document to Markdown.")


def export_docling_json(doc: Any, json_path: Path) -> dict[str, Any]:
    """
    Export Docling's structured representation if available.
    """
    data: dict[str, Any] = {}

    for method_name in ["export_to_dict", "model_dump", "dict"]:
        if hasattr(doc, method_name):
            try:
                data = getattr(doc, method_name)()
                break
            except Exception:
                continue

    if data:
        json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    return data


# ---------------------------------------------------------------------
# Structural rules
# ---------------------------------------------------------------------

MAIN_SECTION_TITLES = {
    "trends at a glance",
    "statistics for forcibly displaced and all other people protected and/or assisted by unhcr",
    "global forced displacement",
    "refugees",
    "internally displaced people",
    "internally displaced people (idps)",
    "asylum trends",
    "solutions",
    "stateless people",
    "annex tables",
}

SUBSECTION_TITLES = {
    "overview",
    "protracted refugee situations",
    "protracted refugee situation definition",
    "how long do individuals remain as refugees or asylum-seekers?",
    "how is global forced displacement changing in 2026?",
    "by country of origin",
    "by country of asylum",
    "estimated demographic composition of refugees",
    "sustainable development goals - indicator 10.7.4",
    "key changes in internal displacement by country",
    "location and demographics of idps",
    "displacement in the context of disasters",
    "key asylum trends",
    "decisions on individual asylum applications",
    "pending asylum claims",
    "refugee returns",
    "refugee resettlement and sponsorship pathways",
    "refugee local integration",
    "return of idps",
    "acquisition and confirmation of nationality",
    "legal and policy improvements in 2025",
    "the high commissioner's 50 by 35: dignity and solutions initiative to reduce aid dependency and expand solutions",
    "refugee returns in 2025 were mostly under adverse circumstances and/or to fragile contexts",
    "afghan returns under adverse circumstances and to an extremely fragile situation",
    "fragile hope for syrians",
    "sudanese and south sudanese returns",
    "ukrainian returns",
    "burundi, central african republic, nigeria and rwanda",
    "many refugees hope to return, investment is urgently needed",
    "ukrainians continued to receive temporary protection",
    "forced displacement from sudan to neighbouring countries fell, while displacement from south sudan increased.",
    "forced displacement from the central sahel grew",
    "new asylum applications from the americas continued to represent a significant proportion of the global total",
    "the number of rohingya seeking international protection increased",
    "fewer syrians claimed asylum",
    "the democratic republic of the congo was both a significant country of asylum and origin",
    "who is included in unhcr statistics?",
    "front cover",
    "global trends",
}

RUNNING_HEADER_RE = re.compile(
    r"^\s*(?:\d+\s+)?UNHCR\s*>?\s*\**GLOBAL TRENDS\s+\d{4}\**.*$",
    flags=re.IGNORECASE,
)

PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,3}\s*$")

CHAPTER_ONLY_RE = re.compile(
    r"^\s*#{0,6}\s*CHAPTER\s+\d+\s*$",
    flags=re.IGNORECASE,
)

INSIGHT_ONLY_RE = re.compile(
    r"^\s*#{0,6}\s*INSIGHT\s+(\d+)\s*$",
    flags=re.IGNORECASE,
)

IMAGE_LINK_RE = re.compile(r"^\s*\[Image\]\((?P<path>[^)]+)\)\s*$")
IMAGE_MD_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$")

HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")

UPPERCASE_BOX_RE = re.compile(r"^[A-Z0-9 ,;:/()'\-&.%]+$")

STAT_START_RE = re.compile(
    r"""
    ^
    (?:
        \d+(?:[.,]\d+)?
        |
        \d+\s+in\s+\d+
    )
    \s*
    (?:
        million|billion|thousand|per\s+cent|%|m\b|k\b
    )?
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

CTA_LINK_HEADING_RE = re.compile(
    r"^\[?(HOW IS|WHO IS|WHAT ARE|EXPLORE THE DATA|VIEW MAPS|VIEW ANNEX|READ MORE)\b",
    flags=re.IGNORECASE,
)

CAPTION_KIND_RE = r"(figure|fig\.?|table|tab\.?)"

CAPTION_START_RE = re.compile(
    rf"""
    ^\s*
    (?P<kind>{CAPTION_KIND_RE})
    \s+
    (?P<number>\d+[A-Za-z]?)
    \s*
    (?P<sep>[\|\:\-–—]|\\\|)
    \s*
    (?P<title>.*?)
    \s*$
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

CAPTION_HEADING_RE = re.compile(
    rf"""
    ^\s*\#{{1,6}}\s+
    (?P<kind>{CAPTION_KIND_RE})
    \s+
    (?P<number>\d+[A-Za-z]?)
    \s*
    (?P<sep>[\|\:\-–—]|\\\|)
    \s*
    (?P<title>.*?)
    \s*$
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

CAPTION_CONTINUATION_STOP_RE = re.compile(
    r"""
    ^\s*(
        \# |
        CHAPTER\s+\d+ |
        INSIGHT\s+\d+ |
        Overview\b |
        UNHCR\s*> |
        \d{1,3}\s+UNHCR\s*> |
        \d{1,3}\s+See\b |
        \*\*\d{1,3}\s+
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

CAPTION_NOISE_RE = re.compile(
    r"""
    (
        ^\s*$ |
        ^\s*!\[.*\]\(.*\)\s*$ |
        ^\s*\[.*\]\(https?://.*\)\s*$ |
        ^\s*<!--.*-->\s*$
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------
# Footnote rules
# ---------------------------------------------------------------------

FOOTNOTE_DEF_RE = re.compile(
    r"""
    ^
    \s*
    (?:-\s*)?
    (?P<num>\d{1,3})
    \s+
    (?P<body>
        (?:
            See\b|
            Source:|
            Sources:|
            Includes\b|
            This\b|
            The\b|
            All\b|
            At\b|
            In\b|
            Figures?\b|
            Ibid\.|
            Cumulatively\b|
            Statistics\b|
            Arrivals\b|
            Data\b|
            Effective\b|
            High-income\b|
            There\b|
            These\b|
            UNRWA\b|
            Lebanon\b|
            Since\b|
            On\b|
            During\b|
            New\b|
            Disclaimer:
        )
        .*
    )
    \s*$
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

FOOTNOTE_LINK_DEF_RE = re.compile(
    r"""
    ^
    \s*
    (?:-\s*)?
    \[
        (?P<num>\d{1,3})
        \s+
        (?P<label>[^\]]+)
    \]
    \(
        (?P<url>[^)]+)
    \)
    \s*$
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

INLINE_FOOTNOTE_REF_RE = re.compile(
    r"""
    (?<![\w\]])           # not after word char or markdown link close
    (?P<prefix>[.,;:)]?)  # optional punctuation before reference
    \s+
    (?P<num>\d{1,3})
    (?=
        \s+
        (?:[A-Z]|\[|$)
        |
        \s*$
    )
    """,
    flags=re.VERBOSE,
)

HEADING_OR_BLOCK_RE = re.compile(
    r"""
    ^
    \s*
    (
        \# |
        > |
        <table |
        </table |
        <tr |
        </tr |
        <td |
        </td |
        <th |
        </th |
        !\[ |
        \[Image\] |
        \*\*[^*]+\*\*\s*$ |
        <!--
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

PHOTO_CAPTION_RE = re.compile(
    r"^\s*[A-Z][A-Z\s.'’()-]{2,60}\.\s+.+©\s*(UNHCR|ANGELS|OXYGEN|[A-Z])",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------------
# Text cleanup
# ---------------------------------------------------------------------

def clean_inline_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\ufeff", "")
    text = text.replace("\\|", "|")
    text = text.replace("\\!", "!")
    text = text.replace("** **", "")
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)

    replacements = {
        "end2025": "end-2025",
        "end2024": "end-2024",
        "middleincome": "middle-income",
        "asylumseeker": "asylum-seeker",
        "asylumseekers": "asylum-seekers",
        "selfreliance": "self-reliance",
        "responsibilitysharing": "responsibility-sharing",
        "genderbased": "gender-based",
        "nonnegotiable": "non-negotiable",
    }

    for old, new in replacements.items():
        text = re.sub(old, new, text, flags=re.IGNORECASE)

    return text.strip()


def strip_heading_markup(title: str) -> str:
    title = title.strip()
    title = re.sub(r"^\s*#+\s*", "", title)
    title = title.strip("*_ ")
    title = clean_inline_text(title)
    return title


def normalize_heading_key(title: str) -> str:
    title = strip_heading_markup(title)
    title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)
    title = title.lower().strip()
    title = re.sub(r"\s+", " ", title)
    return title


def convert_image_links(markdown: str) -> str:
    """
    Convert Docling's path links to proper Markdown image embeds.
    """
    output: list[str] = []

    for line in markdown.splitlines():
        match = IMAGE_LINK_RE.match(line)
        if match:
            output.append(f"{match.group('path')}")
        else:
            output.append(line)

    return "\n".join(output)


def preprocess_raw_markdown(raw_md: str) -> str:
    raw_md = raw_md.replace("\r\n", "\n").replace("\r", "\n")
    raw_md = convert_image_links(raw_md)

    lines = [line.rstrip() for line in raw_md.splitlines()]

    compact: list[str] = []
    previous_blank = False

    for line in lines:
        blank = not line.strip()

        if blank and previous_blank:
            continue

        compact.append(line)
        previous_blank = blank

    return "\n".join(compact).strip()


# ---------------------------------------------------------------------
# Caption parsing
# ---------------------------------------------------------------------

def normalize_caption_text(text: str) -> str:
    text = strip_heading_markup(text)
    text = text.replace("\\|", "|")
    text = text.replace("**", "")
    text = text.replace("_", "")
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+\|", " |", text)
    text = re.sub(r"\|\s+", "| ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text.strip(" -–—|")


def is_caption_start(line: str) -> re.Match | None:
    clean = normalize_caption_text(line)
    return CAPTION_START_RE.match(clean) or CAPTION_HEADING_RE.match(clean)


def is_bad_caption_title(title: str) -> bool:
    clean = normalize_caption_text(title).lower()

    # Avoid false positives: "Figure 12 shows the flows..."
    if clean.startswith(("shows ", "show ", "shown ", "illustrates ", "presents ")):
        return True

    if len(clean.split()) > 35 and "|" not in clean:
        return True

    return False


def is_probable_caption_continuation(line: str) -> bool:
    clean = normalize_caption_text(line)

    if CAPTION_NOISE_RE.match(clean):
        return False

    if CAPTION_CONTINUATION_STOP_RE.match(clean):
        return False

    if is_caption_start(clean):
        return False

    if len(clean) > 180:
        return False

    if re.match(r"^[-–—]?\s*(19|20)\d{2}(\s*\(.*\))?$", clean):
        return True

    if re.search(r"\b(19|20)\d{2}\b", clean):
        return True

    if "|" in clean:
        return True

    if len(clean.split()) <= 14:
        return True

    return False


def parse_caption_from_lines(
    lines: list[str],
    start_idx: int,
    max_extra_lines: int = MAX_CAPTION_CONTINUATION_LINES,
) -> tuple[dict[str, Any], int] | None:
    first = normalize_caption_text(lines[start_idx])
    match = is_caption_start(first)

    if not match:
        return None

    kind_raw = match.group("kind").lower()
    number = match.group("number")
    title_parts = [match.group("title") or ""]

    next_idx = start_idx + 1
    consumed_extra = 0

    while next_idx < len(lines) and consumed_extra < max_extra_lines:
        candidate = lines[next_idx]

        if is_probable_caption_continuation(candidate):
            title_parts.append(normalize_caption_text(candidate))
            next_idx += 1
            consumed_extra += 1
        else:
            break

    kind = "Table" if kind_raw.startswith("tab") else "Figure"
    title = normalize_caption_text(" ".join(title_parts))

    title = re.sub(
        rf"^{kind}\s+{re.escape(number)}\s*[\|\:\-–—]?\s*",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    if is_bad_caption_title(title):
        return None

    raw = normalize_caption_text(" ".join(lines[start_idx:next_idx]))

    return {
        "kind": kind,
        "number": number,
        "label": f"{kind} {number}",
        "title": title,
        "raw": raw,
        "line_start": start_idx,
        "line_end": next_idx - 1,
    }, next_idx


# ---------------------------------------------------------------------
# Heading classification
# ---------------------------------------------------------------------

def is_stat_box_title(title: str) -> bool:
    clean = strip_heading_markup(title)
    key = normalize_heading_key(clean)

    if key in MAIN_SECTION_TITLES or key in SUBSECTION_TITLES:
        return False

    if STAT_START_RE.match(clean):
        return True

    if re.search(
        r"\b\d+(?:[.,]\d+)?\s*(million|billion|%|per cent|m|k)\b",
        clean,
        flags=re.IGNORECASE,
    ):
        return True

    if re.search(
        r"\bHOSTED\b|\bRESETTLED\b|\bSTATELESS PEOPLE RECEIVED\b|\bARE CHILDREN\b",
        clean,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def is_cta_heading(title: str) -> bool:
    clean = strip_heading_markup(title)
    key = normalize_heading_key(clean)

    if key in SUBSECTION_TITLES:
        return False

    if re.match(r"^\[.*\]\(.*\)$", clean):
        link_text = re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", clean)
        return bool(CTA_LINK_HEADING_RE.match(link_text))

    return bool(CTA_LINK_HEADING_RE.match(clean)) and clean.isupper()


def is_infographic_box_heading(title: str) -> bool:
    clean = strip_heading_markup(title)
    key = normalize_heading_key(clean)

    if key in MAIN_SECTION_TITLES or key in SUBSECTION_TITLES:
        return False

    if clean.lower().startswith(("figure ", "table ")):
        return False

    if UPPERCASE_BOX_RE.match(clean) and len(clean.split()) >= 4:
        return True

    return False


def classify_heading(title: str) -> str:
    """
    Return one of:
    - h2
    - h3
    - insight
    - bold
    - cta
    - drop
    """
    clean = strip_heading_markup(title)
    key = normalize_heading_key(clean)

    if not clean:
        return "drop"

    if CHAPTER_ONLY_RE.match(clean):
        return "drop"

    if INSIGHT_ONLY_RE.match(clean):
        return "insight"

    if is_cta_heading(clean):
        return "cta"

    if is_stat_box_title(clean):
        return "bold"

    if is_infographic_box_heading(clean):
        return "bold"

    if key in MAIN_SECTION_TITLES:
        return "h2"

    if key in SUBSECTION_TITLES:
        return "h3"

    return "h3"


def render_bold_title(title: str) -> list:
    clean = strip_heading_markup(title)
    return [f"**{clean}**"]


def render_cta(title: str) -> list:
    clean = strip_heading_markup(title)

    if re.match(r"^\[.*\]\(.*\)$", clean):
        link_text = re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", clean)
        url = re.sub(r"^\[[^\]]+\]\(([^)]+)\)$", r"\1", clean)
        return [url]

    return [f"**Related:** {clean}"]


def process_heading_line(line: str) -> list:
    match = HEADING_RE.match(line)

    if not match:
        return [line]

    title = strip_heading_markup(match.group("title"))
    classification = classify_heading(title)

    if classification == "drop":
        return [f"<!-- omitted-layout-marker: {title} -->"]

    if classification == "insight":
        return [f"## {title.upper()}"]

    if classification == "h2":
        return [f"## {title}"]

    if classification == "h3":
        return [f"### {title}"]

    if classification == "cta":
        return render_cta(title)

    if classification == "bold":
        return render_bold_title(title)

    return [line]


# ---------------------------------------------------------------------
# Footnote extraction
# ---------------------------------------------------------------------

def parse_footnote_definition(line: str) -> tuple[str, str] | None:
    stripped = line.strip()

    m_link = FOOTNOTE_LINK_DEF_RE.match(stripped)
    if m_link:
        num = m_link.group("num")
        label = clean_inline_text(m_link.group("label"))
        url = m_link.group("url").strip()
        return num, f"{label} {url}"

    m = FOOTNOTE_DEF_RE.match(stripped)
    if m:
        return m.group("num"), clean_inline_text(m.group("body"))

    return None


def is_probable_footnote_continuation(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return False

    if parse_footnote_definition(stripped):
        return False

    if HEADING_OR_BLOCK_RE.match(stripped):
        return False

    if PHOTO_CAPTION_RE.match(stripped):
        return False

    if stripped[0].islower():
        return True

    if stripped.startswith(("and ", "or ", "as well as ", "which ", "where ", "while ")):
        return True

    if re.match(
        r"^(refugees|people|individuals|children|women|men|returns|arrivals)\b",
        stripped,
        flags=re.IGNORECASE,
    ):
        return True

    if len(stripped.split()) >= 8 and re.search(
        r"\b(UNHCR|UNRWA|IDMC|IOM|OCHA|World Bank|accessed|methodology|statistics|dashboard|dataset|Convention|Protocol)\b",
        stripped,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def merge_footnote_body(old: str, new: str) -> str:
    old = clean_inline_text(old)
    new = clean_inline_text(new)

    if not old:
        return new

    if not new:
        return old

    if new in old:
        return old

    if old in new:
        return new

    return f"{old} {new}".strip()


def replace_inline_footnote_refs(markdown: str, valid_numbers: set[str]) -> str:
    def replace_line(line: str) -> str:
        stripped = line.strip()

        if stripped.startswith("[^") or stripped.startswith(("|", "<", ">", "```")):
            return line

        if stripped.startswith("#"):
            return line

        def repl(match: re.Match) -> str:
            prefix = match.group("prefix") or ""
            num = match.group("num")

            if num not in valid_numbers:
                return match.group(0)

            if prefix:
                return f"{prefix}[^{num}]"

            return f" [^{num}]"

        return INLINE_FOOTNOTE_REF_RE.sub(repl, line)

    return "\n".join(replace_line(line) for line in markdown.splitlines())


def extract_and_relocate_footnotes(markdown: str) -> tuple[str, dict[str, str]]:
    """
    Extract footnote definitions from the middle of the body and append them
    as Markdown footnotes at the end.
    """
    lines = markdown.splitlines()

    output: list[str] = []
    footnotes: dict[str, str] = {}

    i = 0

    while i < len(lines):
        line = lines[i]
        parsed = parse_footnote_definition(line)

        if not parsed:
            output.append(line)
            i += 1
            continue

        num, body = parsed
        consumed_until = i + 1

        while consumed_until < len(lines):
            candidate = lines[consumed_until]

            if is_probable_footnote_continuation(candidate):
                body = merge_footnote_body(body, candidate.strip())
                consumed_until += 1
            else:
                break

        if num in footnotes:
            footnotes[num] = merge_footnote_body(footnotes[num], body)
        else:
            footnotes[num] = body

        output.append(f"<!-- footnote-{num}-moved -->")
        i = consumed_until

    cleaned = "\n".join(output)

    cleaned = replace_inline_footnote_refs(cleaned, set(footnotes.keys()))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if footnotes:
        footnote_lines = ["", "## Footnotes", ""]

        for num in sorted(footnotes.keys(), key=lambda x: int(x)):
            body = footnotes[num].strip()
            footnote_lines.append(f"[^{num}]: {body}")

        cleaned += "\n" + "\n".join(footnote_lines).rstrip() + "\n"

    return cleaned, footnotes


# ---------------------------------------------------------------------
# Markdown structure normalization
# ---------------------------------------------------------------------

def normalize_structure(markdown: str) -> tuple[str, list[dict[str, Any]]]:
    lines = markdown.splitlines()
    output: list[str] = []
    captions: list[dict[str, Any]] = []

    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped_plain = strip_heading_markup(line)

        if ANNOTATE_RUNNING_HEADERS and RUNNING_HEADER_RE.match(stripped_plain):
            output.append(f"<!-- running-header: {stripped_plain} -->")
            i += 1
            continue

        if PAGE_NUMBER_RE.match(line):
            output.append(f"<!-- page-number: {line.strip()} -->")
            i += 1
            continue

        if CHAPTER_ONLY_RE.match(stripped_plain):
            output.append(f"<!-- chapter-marker: {stripped_plain} -->")
            i += 1
            continue

        parsed_caption = parse_caption_from_lines(lines, i)
        if parsed_caption:
            caption, next_i = parsed_caption
            captions.append(caption)

            if caption["title"]:
                output.append(f"**{caption['label']} | {caption['title']}**")
            else:
                output.append(f"**{caption['label']}**")

            i = next_i
            continue

        heading_match = HEADING_RE.match(line)
        
        # Handle figure/table descriptions that don't match caption patterns
        if heading_match and strip_heading_markup(line).lower().startswith(("figure ", "table ")):
            # Extract figure/table number and title
            match = re.match(r"(figure|table)\s+(\d+)\s*[\|\:\-\–—]?\s*(.*)", strip_heading_markup(line), re.IGNORECASE)
            if match:
                kind = "Figure" if match.group(1).lower() == "figure" else "Table"
                number = match.group(2)
                title = match.group(3).strip()
                
                # Add as a caption-style paragraph (not a heading)
                if title:
                    output.append(f"**{kind} {number} | {title}**")
                else:
                    output.append(f"**{kind} {number}**")
                
                # Add to captions list for tracking
                captions.append({
                    "kind": kind,
                    "number": number,
                    "label": f"{kind} {number}",
                    "title": title,
                    "raw": strip_heading_markup(line),
                    "line_start": i,
                })
                i += 1
                continue

        if heading_match:
            output.extend(process_heading_line(line))
            i += 1
            continue

        output.append(clean_inline_text(line))
        i += 1

    return repair_line_glitches("\n".join(output)), captions


def repair_line_glitches(markdown: str) -> str:
    lines = markdown.splitlines()
    repaired: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Merge accidental bullet continuation:
        # "without the formal"
        # "- protections accorded..."
        if (
            stripped.startswith("- ")
            and repaired
            and repaired[-1].strip()
            and not repaired[-1].lstrip().startswith(("-", ">", "|", "#", "<", "[^"))
            and not re.match(r"^- \d{1,3}\b", stripped)
            and len(stripped.split()) <= 10
        ):
            repaired[-1] = repaired[-1].rstrip() + " " + stripped[2:].strip()
            continue

        # Merge broken caption year range:
        # "### Figure 2 | ... | 2001"
        # "- 2025"
        if (
            stripped.startswith("- ")
            and repaired
            and repaired[-1].startswith("### Figure")
            and re.match(r"^-\s*(19|20)\d{2}", stripped)
        ):
            repaired[-1] = repaired[-1].rstrip() + stripped.replace("-", " -", 1)
            continue

        repaired.append(line)

    text = "\n".join(repaired)

    text = re.sub(
        r"(#{2,6}\s+Figure\s+\d+\s+\|[^\n]*?\|\s*(?:19|20)\d{2})\n-\s*((?:19|20)\d{2})",
        r"\1 - \2",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\n{3,}", "\n\n", text)

    # Ensure headings have surrounding blank lines.
    text = re.sub(r"(?<!\n)\n(#{2,4}\s+)", r"\n\n\1", text)
    text = re.sub(r"(#{2,4}[^\n]+)\n(?!\n)", r"\1\n\n", text)

    return text.strip()


def slug_anchor(text: str) -> str:
    text = re.sub(r"^#+\s*", "", text).strip()
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text.lower())
    return text


def build_toc(markdown: str) -> str:
    toc_lines: list[str] = []

    for line in markdown.splitlines():
        match = re.match(r"^(#{2,3})\s+(.+)$", line)

        if not match:
            continue

        title = strip_heading_markup(match.group(2))

        if title.lower() == "footnotes":
            continue

        level = len(match.group(1))
        indent = "  " * max(level - 2, 0)

        display_title = title
        if len(display_title) > 120:
            display_title = display_title[:117] + "..."

        toc_lines.append(f"{indent}- #{slug_anchor(title)}")

    return "\n".join(toc_lines) if toc_lines else "_No headings detected._"


def curate_markdown(
    raw_md: str,
    meta: ReportMeta,
) -> tuple[str, list[dict[str, Any]], dict[str, str]]:
    preprocessed = preprocess_raw_markdown(raw_md)

    body, captions = normalize_structure(preprocessed)

    # Move extracted page footnotes out of the narrative flow.
    body, footnotes = extract_and_relocate_footnotes(body)

    # Final repair after footnote relocation.
    body = repair_line_glitches(body)

    toc = build_toc(body)

    front_matter = yaml.safe_dump(
        {
            "title": meta.title,
            "year": meta.year,
            "report_type": meta.report_type,
            "source_pdf": meta.source_pdf,
            "source_url": meta.source_url,
            "converter": "docling",
            "ocr_enabled": ENABLE_OCR,
            "generated_at": meta.generated_at,
            "figures_detected": sum(1 for c in captions if c["kind"] == "Figure"),
            "tables_detected": sum(1 for c in captions if c["kind"] == "Table"),
            "footnotes_detected": len(footnotes),
            "structure_notes": [
                "Docling extraction with post-processing for UNHCR report structure.",
                "Statistical boxes and infographic labels are demoted from headings.",
                "CTA boxes are demoted to related-link text where appropriate.",
                "Figure and table captions are formatted as bold paragraphs to avoid breaking the main TOC structure.",
                "Footnote definitions are extracted from page flow and appended as Markdown footnotes.",
                "Standalone chapter markers and page numbers are retained as HTML comments.",
                "OCR is disabled by default to avoid duplicate text and RapidOCR backend issues.",
            ],
        },
        sort_keys=False,
        allow_unicode=True,
    ).strip()

    markdown = f"""---
{front_matter}
---

# {meta.title}

**Report type:** {meta.report_type}  
**Year:** {meta.year}  
**Source:** {meta.source_url}  
**Local PDF:** `{meta.source_pdf}`

---

## Contents

{toc}

---

{body}
"""

    return repair_line_glitches(markdown), captions, footnotes


# ---------------------------------------------------------------------
# Sections and quality report
# ---------------------------------------------------------------------

def detect_sections(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.splitlines()
    sections: list[dict[str, Any]] = []

    current_title = "Front matter"
    current_lines: list[str] = []
    section_index = 0
    in_yaml = False

    def flush() -> None:
        nonlocal section_index, current_title, current_lines

        text = "\n".join(current_lines).strip()
        if not text:
            return

        sections.append(
            {
                "index": section_index,
                "title": current_title,
                "slug": slugify(current_title),
                "markdown": text,
            }
        )
        section_index += 1

    for line in lines:
        if line.strip() == "---":
            in_yaml = not in_yaml
            current_lines.append(line)
            continue

        if not in_yaml and re.match(r"^##\s+", line):
            title = strip_heading_markup(re.sub(r"^##\s+", "", line))

            if title.lower() not in {"contents", "footnotes"}:
                flush()
                current_title = title
                current_lines = [line]
            else:
                current_lines.append(line)
        else:
            current_lines.append(line)

    flush()
    return sections


def extract_quality_metrics(
    markdown: str,
    page_count: int | None,
    captions: list[dict[str, Any]],
    footnotes: dict[str, str],
) -> dict[str, Any]:
    headings = re.findall(r"^#{1,6}\s+.+$", markdown, flags=re.MULTILINE)
    h2 = re.findall(r"^##\s+.+$", markdown, flags=re.MULTILINE)
    h3 = re.findall(r"^###\s+.+$", markdown, flags=re.MULTILINE)

    figure_captions = [c for c in captions if c["kind"] == "Figure"]
    table_captions = [c for c in captions if c["kind"] == "Table"]

    footnote_defs = re.findall(r"^\[\^\d{1,3}\]:", markdown, flags=re.MULTILINE)
    moved_footnotes = re.findall(r"<!-- footnote-\d{1,3}-moved -->", markdown)
    inline_refs = re.findall(r"\[\^\d{1,3}\]", markdown)

    suspicious_headings: list[str] = []

    for h in headings:
        title = strip_heading_markup(h)

        if is_stat_box_title(title) or CHAPTER_ONLY_RE.match(title):
            suspicious_headings.append(h)

    links = re.findall(r"https?://[^\s)>\]]+", markdown)
    image_refs = re.findall(r"!\[[^\]]*\]\([^)]+\)", markdown)
    comments = re.findall(r"<!-- .*? -->", markdown)

    return {
        "page_count_pdf": page_count,
        "heading_count": len(headings),
        "h2_count": len(h2),
        "h3_count": len(h3),
        "figure_caption_count": len(figure_captions),
        "table_caption_count": len(table_captions),
        "footnote_definition_count": len(footnote_defs),
        "footnotes_extracted_count": len(footnotes),
        "moved_footnote_marker_count": len(moved_footnotes),
        "inline_footnote_ref_count": len(inline_refs),
        "link_count": len(links),
        "image_reference_count": len(image_refs),
        "html_comment_count": len(comments),
        "suspicious_heading_count": len(suspicious_headings),
        "sample_h2": h2[:40],
        "sample_h3": h3[:40],
        "sample_figures": [
            f"{c['label']} | {c['title']}" for c in figure_captions[:25]
        ],
        "sample_tables": [
            f"{c['label']} | {c['title']}" for c in table_captions[:25]
        ],
        "sample_footnotes": [
            f"[^{num}]: {body[:180]}"
            for num, body in sorted(footnotes.items(), key=lambda x: int(x[0]))[:40]
        ],
        "suspicious_headings": suspicious_headings[:50],
    }


def write_quality_report(
    path: Path,
    metrics: dict[str, Any],
    meta: ReportMeta,
) -> None:
    def bullet(items: list[str]) -> str:
        if not items:
            return "_None._"
        return "\n".join(f"- {x}" for x in items)

    report = f"""# Extraction Quality Report

**Title:** {meta.title}  
**Source PDF:** `{meta.source_pdf}`  
**Generated at:** {meta.generated_at}

## Metrics

- PDF pages: {metrics.get("page_count_pdf")}
- Total Markdown headings: {metrics.get("heading_count")}
- H2 headings: {metrics.get("h2_count")}
- H3 headings: {metrics.get("h3_count")}
- Figure captions detected: {metrics.get("figure_caption_count")}
- Table captions detected: {metrics.get("table_caption_count")}
- Footnotes extracted: {metrics.get("footnotes_extracted_count")}
- Footnote definitions in Markdown: {metrics.get("footnote_definition_count")}
- Footnotes moved from page flow: {metrics.get("moved_footnote_marker_count")}
- Inline footnote references: {metrics.get("inline_footnote_ref_count")}
- Links detected: {metrics.get("link_count")}
- Image references detected: {metrics.get("image_reference_count")}
- HTML comments inserted: {metrics.get("html_comment_count")}
- Suspicious headings remaining: {metrics.get("suspicious_heading_count")}

## Sample H2 headings

{bullet(metrics.get("sample_h2", []))}

## Sample H3 headings

{bullet(metrics.get("sample_h3", []))}

## Sample figures

{bullet(metrics.get("sample_figures", []))}

## Sample tables

{bullet(metrics.get("sample_tables", []))}

## Sample footnotes

{bullet(metrics.get("sample_footnotes", []))}

## Suspicious headings to inspect

{bullet(metrics.get("suspicious_headings", []))}

## Human QA checklist

- [ ] Statistical boxes are not in the main TOC.
- [ ] CTA boxes are not promoted to major headings unless semantically useful.
- [ ] Standalone CHAPTER markers are not headings.
- [ ] Figure captions are correctly detected.
- [ ] False caption such as “Figure 12 shows...” is not detected.
- [ ] Figure caption year ranges such as 2001 - 2025 are not split.
- [ ] Footnote definitions are not interrupting narrative paragraphs.
- [ ] A single Footnotes section exists near the end.
- [ ] Image links render as images.
- [ ] Main chapters are H2 and subsections are H3.
"""

    safe_write(path, report)


# ---------------------------------------------------------------------
# Conversion workflow
# ---------------------------------------------------------------------

def convert_one_report(report: list[str], converter: Any) -> dict[str, Any]:
    pdf_file, raw_title, url = report

    pdf_path = Path(pdf_file)
    title = normalise_title(raw_title)
    year = extract_year(title, url, pdf_file)
    report_type = report_type_from_title(title)
    report_slug = slugify(title)

    report_out_dir = OUTPUT_DIR / year / report_slug
    report_out_dir.mkdir(parents=True, exist_ok=True)

    meta = ReportMeta(
        title=title,
        year=year,
        report_type=report_type,
        source_pdf=pdf_path.as_posix(),
        source_url=url,
        slug=report_slug,
        output_dir=report_out_dir.as_posix(),
        generated_at=now_utc(),
    )

    if not pdf_path.exists():
        return {
            "status": "missing",
            "title": title,
            "year": year,
            "report_type": report_type,
            "pdf": pdf_path.as_posix(),
            "url": url,
        }

    print(f"[INFO] Converting with Docling: {pdf_path}")

    raw_md_path = report_out_dir / "raw_docling.md"
    full_md_path = report_out_dir / "full.md"
    index_md_path = report_out_dir / "index.md"
    structure_json_path = report_out_dir / "structure.json"
    captions_json_path = report_out_dir / "figures_tables.json"
    footnotes_json_path = report_out_dir / "footnotes.json"
    quality_report_path = report_out_dir / "quality_report.md"

    try:
        result = converter.convert(pdf_path)
    except ValueError as exc:
        if "RapidOCR" in str(exc) or "Unsupported configuration" in str(exc):
            print(f"[WARN] OCR/RapidOCR failed for {pdf_path}; retrying with OCR disabled.")
            fallback_converter = build_docling_converter(enable_ocr=False)
            result = fallback_converter.convert(pdf_path)
        else:
            raise

    doc = result.document

    raw_markdown = export_docling_markdown(doc, raw_md_path)

    if WRITE_RAW_DOCLING_MARKDOWN:
        safe_write(raw_md_path, raw_markdown)

    docling_json = export_docling_json(doc, structure_json_path)

    curated, captions, footnotes = curate_markdown(raw_markdown, meta)
    safe_write(full_md_path, curated)

    safe_write(
        captions_json_path,
        json.dumps(captions, ensure_ascii=False, indent=2),
    )

    safe_write(
        footnotes_json_path,
        json.dumps(footnotes, ensure_ascii=False, indent=2),
    )

    page_count = read_pdf_page_count(pdf_path)

    metrics = extract_quality_metrics(
        markdown=curated,
        page_count=page_count,
        captions=captions,
        footnotes=footnotes,
    )

    write_quality_report(quality_report_path, metrics, meta)

    section_index_lines: list[str] = []

    if WRITE_SECTION_FILES:
        sections = detect_sections(curated)
        sections_dir = report_out_dir / "sections"
        sections_dir.mkdir(exist_ok=True)

        for section in sections:
            section_file = sections_dir / f"{section['index']:02d}-{section['slug']}.md"
            safe_write(section_file, section["markdown"] + "\n")
            section_index_lines.append(f"- sections/{section_file.name}")

    index_md = f"""# {title}

**Year:** {year}  
**Report type:** {report_type}  
**Source:** {url}  
**PDF:** `{pdf_path.as_posix()}`

## Files

- full.md
- raw_docling.md
- structure.json
- figures_tables.json
- footnotes.json
- quality_report.md

## Detected structure

- PDF pages: {page_count}
- Figures detected: {sum(1 for c in captions if c["kind"] == "Figure")}
- Tables detected: {sum(1 for c in captions if c["kind"] == "Table")}
- Footnotes detected: {len(footnotes)}
- H2 headings: {metrics.get("h2_count")}
- H3 headings: {metrics.get("h3_count")}
- Suspicious headings remaining: {metrics.get("suspicious_heading_count")}

## Sections

{chr(10).join(section_index_lines) if section_index_lines else "_No section files generated._"}
"""

    safe_write(index_md_path, index_md)

    return {
        "status": "ok",
        "title": title,
        "year": year,
        "report_type": report_type,
        "pdf": pdf_path.as_posix(),
        "url": url,
        "output_dir": report_out_dir.as_posix(),
        "full_markdown": full_md_path.as_posix(),
        "raw_markdown": raw_md_path.as_posix(),
        "structure_json": structure_json_path.as_posix(),
        "figures_tables": captions_json_path.as_posix(),
        "footnotes": footnotes_json_path.as_posix(),
        "quality_report": quality_report_path.as_posix(),
        "page_count": page_count,
        "figures_detected": sum(1 for c in captions if c["kind"] == "Figure"),
        "tables_detected": sum(1 for c in captions if c["kind"] == "Table"),
        "footnotes_detected": len(footnotes),
        "suspicious_heading_count": metrics.get("suspicious_heading_count"),
        "docling_json_written": bool(docling_json),
    }


def build_global_readme(results: list[dict[str, Any]]) -> None:
    lines = [
        "# UNHCR Statistical Reports — Structured Markdown",
        "",
        "Generated with a Docling-first PDF-to-Markdown pipeline.",
        "",
        "## Reports",
        "",
    ]

    for year in sorted({r.get("year", "unknown-year") for r in results}):
        lines.append(f"### {year}")
        lines.append("")

        year_results = [r for r in results if r.get("year") == year]

        for r in sorted(year_results, key=lambda x: x.get("title", "")):
            if r["status"] == "ok":
                rel = Path(r["output_dir"]).relative_to(OUTPUT_DIR).as_posix()
                lines.append(
                    f"- {rel}/index.md "
                    f"— {r['report_type']} "
                    f"— pages: {r.get('page_count')} "
                    f"— figures: {r.get('figures_detected', 0)} "
                    f"— tables: {r.get('tables_detected', 0)} "
                    f"— footnotes: {r.get('footnotes_detected', 0)} "
                    f"— suspicious headings: {r.get('suspicious_heading_count', 0)}"
                )
            elif r["status"] == "missing":
                lines.append(f"- MISSING: `{r['pdf']}` — {r['title']}")
            else:
                lines.append(
                    f"- ERROR: `{r.get('pdf')}` — {r.get('title')} — {r.get('error')}"
                )

        lines.append("")

    safe_write(OUTPUT_DIR / "README.md", "\n".join(lines))


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        converter = build_docling_converter(enable_ocr=ENABLE_OCR)
    except ImportError:
        print(
            "[ERROR] Docling is not installed. Run: uv add docling pypdf pyyaml",
            file=sys.stderr,
        )
        return 1

    results: list[dict[str, Any]] = []

    for report in STATREPORTS:
        try:
            result = convert_one_report(report, converter)
            results.append(result)
            print(f"[{result['status'].upper()}] {result['title']}")
        except Exception as exc:
            print(f"[ERROR] Failed: {report[0]} — {exc}", file=sys.stderr)
            traceback.print_exc()
            results.append(
                {
                    "status": "error",
                    "title": normalise_title(report[1]),
                    "year": extract_year(report[1], report[2], report[0]),
                    "report_type": report_type_from_title(report[1]),
                    "pdf": report[0],
                    "url": report[2],
                    "error": str(exc),
                }
            )

    build_global_readme(results)

    print("")
    print(f"Done. Output written to: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())