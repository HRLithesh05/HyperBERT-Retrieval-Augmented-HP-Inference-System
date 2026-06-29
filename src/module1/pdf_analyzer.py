"""Module 1 — PDF Input Analyzer.

Extracts text and hyperparameters from a user-uploaded BERT paper PDF.
Reuses Module 0's extraction patterns for consistency with the corpus.
"""

import re
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from a PDF. Tries PyMuPDF first, falls back to pdfplumber."""
    # Strategy 1: PyMuPDF (fastest, best quality)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()
        return "\n\n".join(pages)
    except Exception:
        pass  # Fall through to pdfplumber

    # Strategy 2: pdfplumber (reliable fallback)
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        if pages:
            return "\n\n".join(pages)
    except Exception:
        pass

    raise RuntimeError(
        f"Could not extract text from '{pdf_path}'. "
        "Neither PyMuPDF nor pdfplumber could read the file. "
        "Install PyMuPDF with: pip install PyMuPDF"
    )


def extract_tables_from_pdf(pdf_path: str) -> list[list[list[str]]]:
    """Extract tables from a PDF using pdfplumber."""
    try:
        import pdfplumber

        tables: list = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        return tables
    except Exception:
        return []


def analyze_pdf(pdf_path: str) -> dict:
    """Analyze a user-uploaded PDF and extract structured HP data.

    Returns a dict with keys:
        model, task, dataset, hyperparameters, missing_params,
        confidence, raw_text, tables, title, abstract
    """
    import sys
    import os

    # ── Dependencies: PyMuPDF or pdfplumber (at least one required) ──
    # extract_text_from_pdf() handles the fallback logic internally

    # Add module0/src to path so we can import HP extraction patterns
    module0_src = os.path.join(
        os.path.dirname(__file__), "..", "..", "module0", "src"
    )
    module0_src = os.path.abspath(module0_src)
    if module0_src not in sys.path:
        sys.path.insert(0, module0_src)

    try:
        from hp.hp_extract import _extract_from_text, _prepare_text
        from hp.hp_validate import validate_hp_json
    except ImportError as e:
        raise RuntimeError(
            f"Could not import HP extraction modules from module0/src/hp: {e}. "
            f"Make sure module0/src/hp/ exists with hp_extract.py and hp_validate.py."
        )

    pdf_path = str(Path(pdf_path).resolve())

    # Step 1: Extract text
    try:
        raw_text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF '{pdf_path}': {e}")

    if not raw_text or len(raw_text) < 100:
        raise ValueError(
            f"Could not extract meaningful text from PDF: {pdf_path}. "
            f"The file may be scanned/image-only (OCR not supported) or corrupted."
        )

    # Step 2: Extract tables (best-effort)
    tables = extract_tables_from_pdf(pdf_path)

    # Step 3: Parse title and abstract from the raw text
    title, abstract = _parse_title_abstract(raw_text)

    # Step 4: Prepare text for HP extraction (include table text)
    table_text = _tables_to_text(tables)
    full_text = f"{title}\n{abstract}\n{raw_text}\n{table_text}"
    prepared = _prepare_text(full_text, max_chars=30000)

    # Step 5: Extract HPs using regex patterns
    hp_json = _extract_from_text(prepared)

    # Step 6: Validate
    hp_json, warnings = validate_hp_json(hp_json)

    # Override model/task from title if not found in text
    if not hp_json.get("model"):
        hp_json["model"] = _guess_model_from_title(title)

    result = {
        **hp_json,
        "raw_text": raw_text,
        "tables": tables,
        "title": title,
        "abstract": abstract,
        "validation_warnings": warnings,
        "pdf_path": pdf_path,
    }

    return result


def _parse_title_abstract(raw_text: str) -> tuple[str, str]:
    """Best-effort extraction of title and abstract from paper text."""
    lines = raw_text.split("\n")
    non_empty = [l.strip() for l in lines if l.strip()]

    # Title is usually the first non-empty line(s)
    title = non_empty[0] if non_empty else ""

    # Abstract: look for "Abstract" heading
    abstract = ""
    for i, line in enumerate(non_empty):
        if re.match(r"^(?:abstract|a\s*b\s*s\s*t\s*r\s*a\s*c\s*t)\s*$", line, re.I):
            # Collect lines until next section heading
            parts = []
            for j in range(i + 1, min(i + 30, len(non_empty))):
                if re.match(r"^\d+\.?\s+\w|^(Introduction|Keywords|1\s)", non_empty[j]):
                    break
                parts.append(non_empty[j])
            abstract = " ".join(parts)
            break

    return title, abstract


def _tables_to_text(tables: list) -> str:
    """Flatten table cells into searchable text."""
    parts: list[str] = []
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            cells = [str(c).strip() for c in row if c]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _guess_model_from_title(title: str) -> str | None:
    """Try to identify the BERT model from the paper title."""
    patterns = [
        (r"(bert[\s\-_]?base[\s\-_]?(?:un)?cased)", re.I),
        (r"((?:distil|albert|roberta|biobert|scibert|clinicalbert|"
         r"pubmedbert|legalbert|finbert|indoBERT|araBERT|"
         r"multilingual[\s\-]?bert|chinese[\s\-]?bert)(?:[\s\-]?"
         r"(?:base|large|v\d+))?)", re.I),
    ]
    for pat, flags in patterns:
        m = re.search(pat, title, flags)
        if m:
            return m.group(1).strip()
    return None
