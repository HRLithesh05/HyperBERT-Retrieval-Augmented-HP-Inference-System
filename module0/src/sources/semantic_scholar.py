import os
import re
from typing import Dict, List

import requests
from tqdm import tqdm


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def fetch_semantic_scholar(query_cfg: dict, source_cfg: dict) -> List[Dict]:
    query = query_cfg["semantic_scholar_query"]
    fallback_query = source_cfg.get("fallback_query")
    year_from = query_cfg.get("year_from")
    year_to = query_cfg.get("year_to")
    use_year_filter = bool(source_cfg.get("use_year_filter", False))
    max_results = int(source_cfg.get("max_results", query_cfg.get("max_results", 100)))

    headers = {"User-Agent": "HyperBERT-Collector/0.1"}
    api_key = source_cfg.get("api_key") or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    fields = source_cfg["fields"]
    base_url = source_cfg["base_url"]

    records = []
    offset = 0
    limit = 100

    pbar = tqdm(total=max_results, desc="Semantic Scholar", unit="paper")
    while offset < max_results:
        params = {
            "query": query,
            "fields": fields,
            "limit": min(limit, max_results - offset),
            "offset": offset,
        }
        if use_year_filter and year_from and year_to:
            params["year"] = f"{year_from}-{year_to}"

        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        if response.status_code == 400 and fallback_query and query != fallback_query:
            params["query"] = fallback_query
            response = requests.get(base_url, params=params, headers=headers, timeout=60)
        if response.status_code >= 400:
            print(f"Semantic Scholar error {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()

        papers = data.get("data", [])
        if not papers:
            break

        for paper in papers:
            source_id = paper.get("paperId")
            title = paper.get("title") or ""
            external_ids = paper.get("externalIds") or {}
            doi = external_ids.get("DOI")
            record = {
                "source": "semantic_scholar",
                "source_id": source_id,
                "title": title,
                "title_norm": _normalize_title(title),
                "abstract": paper.get("abstract"),
                "year": paper.get("year"),
                "authors": [a.get("name") for a in paper.get("authors", [])],
                "venue": paper.get("venue"),
                "publication_types": paper.get("publicationTypes"),
                "doi": doi,
                "external_ids": external_ids,
                "url": paper.get("url"),
                "open_access_pdf": paper.get("openAccessPdf"),
                "pdf_url": (paper.get("openAccessPdf") or {}).get("url"),
                "citation_count": paper.get("citationCount"),
                "reference_count": paper.get("referenceCount"),
                "metadata": {"raw": paper},
            }
            if source_id:
                records.append(record)

        offset += len(papers)
        pbar.update(len(papers))

    pbar.close()
    return records
