import hashlib
import re
import time
from pathlib import Path

import requests
from tqdm import tqdm


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_filename(value: str) -> str:
    value = value.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)[:180]


def download_missing_pdfs(store, pdf_dir: Path, download_cfg: dict) -> None:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    timeout = int(download_cfg.get("timeout_sec", 60))
    user_agent = download_cfg.get("user_agent", "HyperBERT-Collector/0.1")
    retries = int(download_cfg.get("retries", 2))
    backoff_sec = float(download_cfg.get("backoff_sec", 2))

    records = list(store.iter_missing_pdfs())
    if not records:
        return

    pbar = tqdm(records, desc="Download PDFs", unit="paper")
    for record in pbar:
        pdf_url = record.get("pdf_url")
        if not pdf_url:
            continue

        source_id = str(record.get("source_id", "unknown"))
        filename = f"{record['source']}_{_safe_filename(source_id)}.pdf"
        target_path = pdf_dir / filename
        if target_path.exists():
            store.update_pdf_info(record["_id"], {"pdf_path": str(target_path)})
            continue

        last_exc = None
        for attempt in range(retries):
            try:
                response = requests.get(
                    pdf_url,
                    headers={"User-Agent": user_agent, "Accept": "application/pdf"},
                    timeout=timeout,
                )
                response.raise_for_status()

                content = response.content
                content_type = (response.headers.get("Content-Type") or "").lower()
                if not content.startswith(b"%PDF") and "pdf" not in content_type:
                    raise requests.RequestException(f"non-pdf content-type: {content_type}")

                target_path.write_bytes(content)
                sha256 = _sha256(target_path)
                store.update_pdf_info(
                    record["_id"],
                    {
                        "pdf_path": str(target_path),
                        "pdf_sha256": sha256,
                        "pdf_bytes": len(content),
                        "pdf_downloaded": True,
                        "pdf_error": None,
                    },
                )
                last_exc = None
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < retries - 1:
                    time.sleep(backoff_sec * (2**attempt))

        if last_exc is not None:
            store.update_pdf_info(record["_id"], {"pdf_downloaded": False, "pdf_error": str(last_exc)})
