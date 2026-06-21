import json
import re
from pathlib import Path

import pdfplumber
from tqdm import tqdm


def _extract_text(pdf_path: Path) -> tuple[str, str]:
    try:
        import fitz

        doc = fitz.open(pdf_path)
        try:
            text = "\n".join(page.get_text("text") for page in doc)
        finally:
            doc.close()
        return text, "pymupdf"
    except Exception:
        # Fallback to pdfplumber if PyMuPDF is unavailable on the host.
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return "\n".join(pages), "pdfplumber"


def _extract_tables(pdf_path: Path) -> list:
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
    return tables


def _safe_filename(value: str) -> str:
    value = value.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)[:180]


def extract_missing_text(store, pdf_dir: Path, raw_text_dir: Path, tables_dir: Path) -> None:
    raw_text_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    records = list(store.iter_with_pdfs())
    if not records:
        return

    pbar = tqdm(records, desc="Extract text", unit="paper")
    for record in pbar:
        pdf_path = Path(record["pdf_path"])
        if not pdf_path.exists():
            continue

        source_id = str(record.get("source_id", "unknown"))
        base_name = f"{record['source']}_{_safe_filename(source_id)}"
        text_path = raw_text_dir / f"{base_name}.txt"
        tables_path = tables_dir / f"{base_name}.json"

        if text_path.exists() and tables_path.exists():
            continue

        try:
            text, extractor = _extract_text(pdf_path)
            tables = _extract_tables(pdf_path)

            text_path.write_text(text, encoding="utf-8")
            tables_path.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")

            store.update_text_info(
                record["_id"],
                {
                    "raw_text_path": str(text_path),
                    "tables_path": str(tables_path),
                    "text_len": len(text),
                    "table_count": len(tables),
                    "text_extractor": extractor,
                },
            )
        except Exception as exc:
            store.update_text_info(record["_id"], {"text_extracted": False, "text_error": str(exc)})
