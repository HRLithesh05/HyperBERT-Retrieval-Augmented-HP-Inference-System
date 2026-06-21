import re
import xml.etree.ElementTree as ET
from typing import Dict, List

import time

import requests
from tqdm import tqdm


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def fetch_arxiv(query_cfg: dict, source_cfg: dict) -> List[Dict]:
    query = query_cfg["arxiv_query"]
    max_results = int(source_cfg.get("max_results", 100))
    base_url = source_cfg["base_url"]

    start = 0
    batch_size = 100
    records: List[Dict] = []

    retries = int(source_cfg.get("retries", 3))
    backoff_sec = float(source_cfg.get("backoff_sec", 3))
    headers = {"User-Agent": "HyperBERT-Collector/0.1"}

    pbar = tqdm(total=max_results, desc="arXiv", unit="paper")
    while start < max_results:
        params = {
            "search_query": query,
            "start": start,
            "max_results": min(batch_size, max_results - start),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        response = None
        for attempt in range(retries):
            try:
                response = requests.get(base_url, params=params, headers=headers, timeout=60)
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == retries - 1:
                    raise
                time.sleep(backoff_sec * (2**attempt))

        root = ET.fromstring(response.text)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        if not entries:
            break

        for entry in entries:
            entry_id = entry.findtext("{http://www.w3.org/2005/Atom}id") or ""
            title = entry.findtext("{http://www.w3.org/2005/Atom}title") or ""
            summary = entry.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            published = entry.findtext("{http://www.w3.org/2005/Atom}published") or ""
            year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None

            authors = [a.findtext("{http://www.w3.org/2005/Atom}name") for a in entry.findall("{http://www.w3.org/2005/Atom}author")]
            pdf_url = ""
            for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href", "")
                    break

            source_id = entry_id.rsplit("/", 1)[-1]

            record = {
                "source": "arxiv",
                "source_id": source_id,
                "title": title.strip(),
                "title_norm": _normalize_title(title),
                "abstract": summary.strip(),
                "year": year,
                "authors": [a for a in authors if a],
                "doi": None,
                "external_ids": {"arxiv": source_id},
                "url": entry_id,
                "open_access_pdf": {"url": pdf_url} if pdf_url else None,
                "pdf_url": pdf_url,
                "citation_count": None,
                "reference_count": None,
                "metadata": {"raw": {"published": published}},
            }
            if source_id:
                records.append(record)

        start += len(entries)
        pbar.update(len(entries))

    pbar.close()
    return records
