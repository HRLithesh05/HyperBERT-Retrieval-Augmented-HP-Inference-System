import re
from typing import Dict, List

import requests
from tqdm import tqdm


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def fetch_openalex(query_cfg: dict, source_cfg: dict) -> List[Dict]:
    query = query_cfg["openalex_query"]
    year_from = query_cfg.get("year_from")
    year_to = query_cfg.get("year_to")

    base_url = source_cfg["base_url"]
    per_page = int(source_cfg.get("per_page", 200))
    max_results = int(source_cfg.get("max_results", 200))

    records: List[Dict] = []
    cursor = "*"

    pbar = tqdm(total=max_results, desc="OpenAlex", unit="paper")
    while len(records) < max_results:
        params = {
            "search": query,
            "per_page": min(per_page, max_results - len(records)),
            "cursor": cursor,
        }
        filters = []
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            filters.append(f"to_publication_date:{year_to}-12-31")
        if filters:
            params["filter"] = ",".join(filters)

        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            title = work.get("title") or ""
            doi = work.get("doi")
            open_access = work.get("open_access") or {}
            best_oa = work.get("best_oa_location") or {}
            pdf_url = best_oa.get("pdf_url") or open_access.get("oa_url")
            landing = best_oa.get("landing_page_url") or open_access.get("oa_url")
            primary_location = work.get("primary_location") or {}
            primary_source = primary_location.get("source") or {}

            record = {
                "source": "openalex",
                "source_id": work.get("id"),
                "title": title,
                "title_norm": _normalize_title(title),
                "abstract": work.get("abstract") or None,
                "year": work.get("publication_year"),
                "authors": [
                    a.get("author", {}).get("display_name")
                    for a in work.get("authorships", [])
                    if a.get("author")
                ],
                "venue": primary_source.get("display_name"),
                "publication_types": work.get("type"),
                "doi": doi,
                "external_ids": work.get("ids"),
                "url": work.get("id"),
                "open_access_pdf": {"url": pdf_url or landing} if (pdf_url or landing) else None,
                "pdf_url": pdf_url,
                "citation_count": work.get("cited_by_count"),
                "reference_count": work.get("referenced_works_count"),
                "metadata": {"raw": work},
            }
            if record["source_id"]:
                records.append(record)

        pbar.update(len(results))
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break

    pbar.close()
    return records
