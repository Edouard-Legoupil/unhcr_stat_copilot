#!/usr/bin/env python3
"""
Convert locally downloaded UNHCR statistical report PDFs into organised Markdown files.

Output structure:

data/markdown_reports/
├── README.md
├── 2019/
│   ├── mid-year-trends-2019.md
│   └── global-trends-2019.md
├── 2020/
│   ├── mid-year-trends-2020.md
│   └── global-trends-2020.md
...

Recommended dependency:
    pip install pymupdf

Fallback dependency:
    pip install pypdf
"""

from pathlib import Path
from datetime import datetime
import re
import textwrap


# ---------------------------------------------------------------------
# Input reports
# ---------------------------------------------------------------------

statreports = [
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
WRAP_WIDTH = 100
MIN_TEXT_CHARS_PER_PAGE = 20


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def normalise_title(title: str) -> str:
    """
    Normalise report titles.
    """
    title = title.replace("GLOBALTRENDS", "GLOBAL TRENDS")
    title = re.sub(r"\s+", " ", title).strip()
    return title.upper()


def extract_year(title: str, url: str = "") -> str:
    """
    Extract the first four-digit year from title or URL.
    """
    match = re.search(r"\b(20\d{2})\b", title)
    if match:
        return match.group(1)

    match = re.search(r"\b(20\d{2})\b", url)
    if match:
        return match.group(1)

    return "unknown-year"


def report_type_from_title(title: str) -> str:
    """
    Return a standard report type.
    """
    title_upper = title.upper()

    if "MID-YEAR" in title_upper or "MID YEAR" in title_upper:
        return "Mid-Year Trends"

    if "GLOBAL" in title_upper:
        return "Global Trends"

    return "Unknown Report Type"


def slugify(text: str) -> str:
    """
    Create a filesystem-safe slug.
    """
    text = text.lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def clean_text(text: str) -> str:
    """
    Basic cleanup for PDF-extracted text.
    """
    if not text:
        return ""

    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing spaces
    lines = [line.rstrip() for line in text.splitlines()]

    cleaned_lines = []
    buffer = ""

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if buffer:
                cleaned_lines.append(buffer.strip())
                buffer = ""
            cleaned_lines.append("")
            continue

        # Keep likely headings as separate lines
        if is_probable_heading(stripped):
            if buffer:
                cleaned_lines.append(buffer.strip())
                buffer = ""
            cleaned_lines.append(stripped)
            continue

        # Join lines that are likely part of the same paragraph
        if buffer:
            buffer += " " + stripped
        else:
            buffer = stripped

    if buffer:
        cleaned_lines.append(buffer.strip())

    text = "\n".join(cleaned_lines)

    # Remove repeated spaces
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def is_probable_heading(line: str) -> bool:
    """
    Heuristic to identify likely headings.
    """
    if len(line) > 90:
        return False

    if len(line.split()) > 12:
        return False

    if line.isupper() and len(line) > 3:
        return True

    if re.match(r"^\d+(\.\d+)*\s+[A-Z]", line):
        return True

    if re.match(r"^(CHAPTER|SECTION|ANNEX|TABLE|FIGURE)\b", line.upper()):
        return True

    return False


def format_markdown_text(text: str) -> str:
    """
    Convert cleaned text into more readable Markdown.
    """
    lines = text.splitlines()
    output = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            output.append("")
            continue

        if is_probable_heading(stripped):
            output.append(f"### {stripped}")
        else:
            wrapped = textwrap.fill(
                stripped,
                width=WRAP_WIDTH,
                break_long_words=False,
                break_on_hyphens=False,
            )
            output.append(wrapped)

    markdown = "\n\n".join(output)

    # Avoid duplicated Markdown heading markers
    markdown = re.sub(r"###\s+###\s+", "### ", markdown)

    return markdown.strip()


# ---------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------

def extract_with_pymupdf(pdf_path: Path):
    """
    Extract page text using PyMuPDF.
    Returns a list of page texts.
    """
    import fitz  # PyMuPDF

    page_texts = []

    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text")
            page_texts.append(text or "")

    return page_texts


def extract_with_pypdf(pdf_path: Path):
    """
    Fallback text extraction using pypdf.
    Returns a list of page texts.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    page_texts = []

    for page in reader.pages:
        text = page.extract_text() or ""
        page_texts.append(text)

    return page_texts


def extract_pdf_text(pdf_path: Path):
    """
    Try PyMuPDF first, then pypdf.
    """
    try:
        return extract_with_pymupdf(pdf_path), "pymupdf"
    except ImportError:
        pass
    except Exception as exc:
        print(f"[WARN] PyMuPDF failed for {pdf_path}: {exc}")

    try:
        return extract_with_pypdf(pdf_path), "pypdf"
    except ImportError as exc:
        raise RuntimeError(
            "No PDF extraction library available. Install one of:\n"
            "  pip install pymupdf\n"
            "or\n"
            "  pip install pypdf"
        ) from exc


# ---------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------

def build_markdown_document(
    pdf_path: Path,
    title: str,
    url: str,
    year: str,
    report_type: str,
    page_texts: list[str],
    extractor: str,
) -> str:
    """
    Build one complete Markdown document.
    """
    generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    front_matter = f"""---
title: "{title}"
year: "{year}"
report_type: "{report_type}"
source_pdf: "{pdf_path.as_posix()}"
source_url: "{url}"
extraction_tool: "{extractor}"
generated_at: "{generated_at}"
---

# {title}

**Report type:** {report_type}  
**Year:** {year}  
**Source:** [{url}]({url})  
**Local PDF:** `{pdf_path.as_posix()}`

---

## Contents

"""

    toc_lines = []
    body_sections = []

    for idx, raw_text in enumerate(page_texts, start=1):
        cleaned = clean_text(raw_text)

        if len(cleaned) < MIN_TEXT_CHARS_PER_PAGE:
            cleaned_md = "_No extractable text found on this page._"
        else:
            cleaned_md = format_markdown_text(cleaned)

        toc_lines.append(f"- [Page {idx}](#page-{idx})")

        body_sections.append(
            f"""## Page {idx}

{cleaned_md}
"""
        )

    return front_matter + "\n".join(toc_lines) + "\n\n---\n\n" + "\n\n---\n\n".join(body_sections)


def write_report_markdown(report):
    """
    Convert one report to Markdown and write it to disk.
    """
    pdf_file, raw_title, url = report

    pdf_path = Path(pdf_file)
    title = normalise_title(raw_title)
    year = extract_year(title, url)
    report_type = report_type_from_title(title)

    if not pdf_path.exists():
        print(f"[MISSING] {pdf_path}")
        return {
            "status": "missing",
            "title": title,
            "year": year,
            "report_type": report_type,
            "pdf_path": pdf_path,
            "url": url,
            "markdown_path": None,
            "pages": 0,
        }

    year_dir = OUTPUT_DIR / year
    year_dir.mkdir(parents=True, exist_ok=True)

    filename = slugify(title) + ".md"
    markdown_path = year_dir / filename

    print(f"[INFO] Extracting {title} from {pdf_path}")

    page_texts, extractor = extract_pdf_text(pdf_path)

    markdown = build_markdown_document(
        pdf_path=pdf_path,
        title=title,
        url=url,
        year=year,
        report_type=report_type,
        page_texts=page_texts,
        extractor=extractor,
    )

    t(markdown, encoding="utf-8")

    print(f"[OK] Wrote {markdown_path}")

    return {
        "status": "ok",
        "title": title,
        "year": year,
        "report_type": report_type,
        "pdf_path": pdf_path,
        "url": url,
        "markdown_path": markdown_path,
        "pages": len(page_texts),
    }


def build_index(results):
    """
    Build a README index for all converted reports.
    """
    lines = [
        "# UNHCR Statistical Reports Markdown Index",
        "",
        "This folder contains Markdown conversions of locally downloaded UNHCR statistical reports.",
        "",
        "## Reports",
        "",
    ]

    ok_results = [r for r in results if r["status"] == "ok"]
    missing_results = [r for r in results if r["status"] == "missing"]

    for year in sorted(set(r["year"] for r in results)):
        lines.append(f"### {year}")
        lines.append("")

        year_results = [r for r in ok_results if r["year"] == year]

        for r in sorted(year_results, key=lambda x: x["report_type"]):
            rel_md = r["markdown_path"].relative_to(OUTPUT_DIR).as_posix()
            lines.append(
                f"- {rel_md} "
                f"— {r['report_type']}, {r['pages']} pages "
                f"— {r['url']}"
            )

        if not year_results:
            lines.append("_No converted reports._")

        lines.append("")

    if missing_results:
        lines.extend([
            "## Missing local PDFs",
            "",
            "The following files were listed but not found locally:",
            "",
        ])

        for r in missing_results:
            lines.append(f"- `{r['pdf_path'].as_posix()}` — {r['title']}")

        lines.append("")

    readme = "\n".join(lines)
    readme_path = OUTPUT_DIR / "README.md"
    readme_path.write_text(readme, encoding="utf-8")

    print(f"[OK] Wrote {readme_path}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for report in statreports:
        try:
            result = write_report_markdown(report)
            results.append(result)
        except Exception as exc:
            print(f"[ERROR] Failed to process {report[0]}: {exc}")
            results.append({
                "status": "error",
                "title": normalise_title(report[1]),
                "year": extract_year(report[1], report[2]),
                "report_type": report_type_from_title(report[1]),
                "pdf_path": Path(report[0]),
                "url": report[2],
                "markdown_path": None,
                "pages": 0,
                "error": str(exc),
            })

    build_index(results)

    print("")
    print("Done.")
    print(f"Markdown reports written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()