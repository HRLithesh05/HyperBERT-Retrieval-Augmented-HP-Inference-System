import time
import urllib.parse

import requests


def _openalex_pdf_url(base_url: str, source_id: str) -> tuple[str | None, dict | None]:
    encoded = urllib.parse.quote(source_id, safe="")
    url = f"{base_url}/{encoded}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    data = response.json()

    best_oa = data.get("best_oa_location") or {}
    open_access = data.get("open_access") or {}

    pdf_url = best_oa.get("pdf_url") or open_access.get("oa_url")
    landing = best_oa.get("landing_page_url") or open_access.get("oa_url")

    meta = {"best_oa_location": best_oa, "open_access": open_access}
    return pdf_url or landing, meta


def _crossref_pdf_url(base_url: str, doi: str) -> tuple[str | None, dict | None]:
    url = f"{base_url}/{urllib.parse.quote(doi)}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    data = response.json()

    item = (data.get("message") or {})
    links = item.get("link") or []
    for link in links:
        link_url = link.get("URL")
        content_type = (link.get("content-type") or "").lower()
        if not link_url:
            continue
        if "pdf" in content_type or link_url.lower().endswith(".pdf"):
            return link_url, {"link": link}
    return None, None


def _unpaywall_pdf_url(base_url: str, doi: str, email: str) -> tuple[str | None, dict | None]:
    url = f"{base_url}/{urllib.parse.quote(doi)}"
    response = requests.get(url, params={"email": email}, timeout=60)
    response.raise_for_status()
    data = response.json()

    best = data.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf") or best.get("url")
    return pdf_url, {"best_oa_location": best}


def _arxiv_pdf_url(source_id: str) -> str:
    return f"https://arxiv.org/pdf/{source_id}.pdf"


def enrich_pdf_urls(store, config: dict, paths: dict) -> None:
    pdf_cfg = config.get("pdf_enrich", {})
    if not pdf_cfg.get("enabled", True):
        return

    use_openalex = bool(pdf_cfg.get("use_openalex", True))
    use_crossref = bool(pdf_cfg.get("use_crossref", True))
    use_unpaywall = bool(pdf_cfg.get("use_unpaywall", False))
    use_arxiv_guess = bool(pdf_cfg.get("use_arxiv_guess", True))
    request_delay = float(pdf_cfg.get("request_delay_sec", 0.2))

    openalex_base = pdf_cfg.get("openalex_base_url", "https://api.openalex.org/works")
    crossref_base = pdf_cfg.get("crossref_base_url", "https://api.crossref.org/works")
    unpaywall_base = pdf_cfg.get("unpaywall_base_url", "https://api.unpaywall.org/v2")
    unpaywall_email = (pdf_cfg.get("unpaywall_email") or "").strip()

    query = {
        "$or": [
            {"pdf_url": {"$exists": False}},
            {"pdf_url": None},
            {"pdf_downloaded": False},
        ]
    }

    for doc in store.collection.find(query, batch_size=50):
        pdf_url = doc.get("pdf_url")
        enriched_from = None
        extra = None

        try:
            if not pdf_url and use_openalex and doc.get("source") == "openalex" and doc.get("source_id"):
                pdf_url, extra = _openalex_pdf_url(openalex_base, doc["source_id"])
                enriched_from = "openalex"

            if not pdf_url and use_crossref and doc.get("doi"):
                pdf_url, extra = _crossref_pdf_url(crossref_base, doc["doi"])
                if pdf_url:
                    enriched_from = "crossref"

            if not pdf_url and use_unpaywall and unpaywall_email and doc.get("doi"):
                pdf_url, extra = _unpaywall_pdf_url(unpaywall_base, doc["doi"], unpaywall_email)
                if pdf_url:
                    enriched_from = "unpaywall"

            if not pdf_url and use_arxiv_guess and doc.get("source") == "arxiv" and doc.get("source_id"):
                pdf_url = _arxiv_pdf_url(doc["source_id"])
                enriched_from = "arxiv_guess"

            if pdf_url:
                update = {
                    "pdf_url": pdf_url,
                    "open_access_pdf": {"url": pdf_url},
                    "pdf_enriched": {
                        "source": enriched_from,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "extra": extra,
                    },
                }
                store.collection.update_one({"_id": doc["_id"]}, {"$set": update})

        except requests.RequestException as exc:
            store.collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"pdf_enrich_error": str(exc)}},
            )

        if request_delay:
            time.sleep(request_delay)
