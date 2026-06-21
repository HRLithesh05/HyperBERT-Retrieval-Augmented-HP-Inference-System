import re
from typing import Dict, List

import requests
from tqdm import tqdm


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _extract_year(item: dict) -> int | None:
    for key in ("published-print", "published-online", "created"):
        date_parts = (item.get(key) or {}).get("date-parts")
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
            if isinstance(year, int):
                return year
    return None


def fetch_crossref(query_cfg: dict, source_cfg: dict) -> List[Dict]:
    query = query_cfg["crossref_query"]
    year_from = query_cfg.get("year_from")
    year_to = query_cfg.get("year_to")

    base_url = source_cfg["base_url"]
    rows = int(source_cfg.get("rows", 100))
    max_results = int(source_cfg.get("max_results", 200))

    records: List[Dict] = []
    offset = 0

    pbar = tqdm(total=max_results, desc="Crossref", unit="paper")
    while offset < max_results:
        params = {
            "query.bibliographic": query,
            "rows": min(rows, max_results - offset),
            "offset": offset,
        }
        filters = []
        if year_from:
            filters.append(f"from-pub-date:{year_from}-01-01")
        if year_to:
            filters.append(f"until-pub-date:{year_to}-12-31")
        if filters:
            params["filter"] = ",".join(filters)

        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        items = (data.get("message") or {}).get("items", [])
        if not items:
            break

        for item in items:
            titles = item.get("title") or []
            title = titles[0] if titles else ""
            doi = item.get("DOI")
            pdf_url = None
            for link in item.get("link", []) or []:
                link_url = link.get("URL")
                content_type = (link.get("content-type") or "").lower()
                if not link_url:
                    continue
                if "pdf" in content_type or link_url.lower().endswith(".pdf"):
                    pdf_url = link_url
                    break

            record = {
                "source": "crossref",
                "source_id": doi or item.get("URL"),
                "title": title,
                "title_norm": _normalize_title(title),
                "abstract": item.get("abstract"),
                "year": _extract_year(item),
                "authors": [
                    " ".join(filter(None, [a.get("given"), a.get("family")]))
                    for a in item.get("author", [])
                ],
                "venue": (item.get("container-title") or [None])[0],
                "publication_types": item.get("type"),
                "doi": doi,
                "external_ids": None,
                "url": item.get("URL"),
                "open_access_pdf": {"url": pdf_url} if pdf_url else None,
                "pdf_url": pdf_url,
                "citation_count": item.get("is-referenced-by-count"),
                "reference_count": None,
                "metadata": {"raw": item},
            }
            if record["source_id"]:
                records.append(record)

        offset += len(items)
        pbar.update(len(items))

    pbar.close()
    return records
