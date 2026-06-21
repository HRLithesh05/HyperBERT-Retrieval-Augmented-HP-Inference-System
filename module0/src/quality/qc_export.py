import json
from datetime import datetime
from pathlib import Path


def _file_header_ok(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(4) == b"%PDF"
    except OSError:
        return False


def _run_profile(store, profile: dict, reports_dir: Path) -> dict:
    min_pdf_bytes = int(profile.get("min_pdf_bytes", 10000))
    min_text_chars = int(profile.get("min_text_chars", 500))
    require_tables = bool(profile.get("require_tables", False))
    export_only_suitable = bool(profile.get("export_only_suitable", True))
    skip_duplicates = bool(profile.get("skip_duplicates", True))
    profile_name = profile.get("name", "default")

    clean_collection = store.get_collection(profile["collection"])

    stats = {
        "profile": profile_name,
        "total": 0,
        "eligible": 0,
        "exported": 0,
        "blocked": 0,
        "duplicate_blocked": 0,
        "missing_pdf": 0,
        "missing_text": 0,
        "missing_tables": 0,
        "small_pdf": 0,
        "small_text": 0,
        "bad_pdf_header": 0,
    }
    issues = []

    for doc in store.collection.find({}, batch_size=100):
        stats["total"] += 1

        domain_ok = bool(doc.get("tags", {}).get("domain_suitable"))
        if export_only_suitable and not domain_ok:
            stats["blocked"] += 1
            continue

        if skip_duplicates and doc.get("dedup", {}).get("is_duplicate"):
            stats["duplicate_blocked"] += 1
            stats["blocked"] += 1
            issues.append(
                {
                    "source": doc.get("source"),
                    "source_id": doc.get("source_id"),
                    "reason": "duplicate",
                    "details": doc.get("dedup", {}).get("duplicate_of"),
                }
            )
            continue

        pdf_path = doc.get("pdf_path")
        text_path = doc.get("raw_text_path")
        tables_path = doc.get("tables_path")

        missing = []
        pdf_file = Path(pdf_path) if pdf_path else None
        text_file = Path(text_path) if text_path else None
        tables_file = Path(tables_path) if tables_path else None

        if not pdf_file or not pdf_file.exists():
            stats["missing_pdf"] += 1
            missing.append("pdf")
        if not text_file or not text_file.exists():
            stats["missing_text"] += 1
            missing.append("text")
        if require_tables and (not tables_file or not tables_file.exists()):
            stats["missing_tables"] += 1
            missing.append("tables")

        if missing:
            stats["blocked"] += 1
            issues.append(
                {
                    "source": doc.get("source"),
                    "source_id": doc.get("source_id"),
                    "reason": "missing_files",
                    "details": missing,
                }
            )
            continue

        pdf_size = pdf_file.stat().st_size if pdf_file else 0
        if pdf_size < min_pdf_bytes:
            stats["small_pdf"] += 1
            stats["blocked"] += 1
            issues.append(
                {
                    "source": doc.get("source"),
                    "source_id": doc.get("source_id"),
                    "reason": "small_pdf",
                    "details": pdf_size,
                }
            )
            continue

        if not _file_header_ok(pdf_file):
            stats["bad_pdf_header"] += 1
            stats["blocked"] += 1
            issues.append(
                {
                    "source": doc.get("source"),
                    "source_id": doc.get("source_id"),
                    "reason": "bad_pdf_header",
                    "details": pdf_path,
                }
            )
            continue

        text_len = text_file.stat().st_size if text_file else 0
        if text_len < min_text_chars:
            stats["small_text"] += 1
            stats["blocked"] += 1
            issues.append(
                {
                    "source": doc.get("source"),
                    "source_id": doc.get("source_id"),
                    "reason": "small_text",
                    "details": text_len,
                }
            )
            continue

        stats["eligible"] += 1

        clean_doc = {
            "source": doc.get("source"),
            "source_id": doc.get("source_id"),
            "title": doc.get("title"),
            "abstract": doc.get("abstract"),
            "year": doc.get("year"),
            "authors": doc.get("authors"),
            "venue": doc.get("venue"),
            "doi": doc.get("doi"),
            "url": doc.get("url"),
            "pdf_path": pdf_path,
            "raw_text_path": text_path,
            "tables_path": tables_path,
            "tags": doc.get("tags"),
            "domain": doc.get("domain"),
            "dedup": doc.get("dedup"),
            "metadata": doc.get("metadata"),
            "qc": {
                "passed": True,
                "checked_at": datetime.utcnow().isoformat() + "Z",
                "profile": profile_name,
            },
        }

        clean_collection.update_one(
            {"source": clean_doc["source"], "source_id": clean_doc["source_id"]},
            {"$set": clean_doc},
            upsert=True,
        )
        stats["exported"] += 1

    report = {
        "summary": stats,
        "config": {
            "min_pdf_bytes": min_pdf_bytes,
            "min_text_chars": min_text_chars,
            "require_tables": require_tables,
            "export_only_suitable": export_only_suitable,
            "skip_duplicates": skip_duplicates,
            "collection": profile["collection"],
        },
        "issue_samples": issues[:100],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    report_path = reports_dir / f"qc_report_{profile_name}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def qc_and_export(store, config: dict, paths: dict) -> None:
    reports_dir = Path(paths["reports_dir"]).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    profiles = config.get("qc_profiles")
    if not profiles:
        qc_cfg = config.get("qc", {})
        profiles = [
            {
                "name": "default",
                "collection": config["mongodb"].get("clean_collection", "papers_clean"),
                **qc_cfg,
            }
        ]

    for profile in profiles:
        if "collection" not in profile:
            profile["collection"] = config["mongodb"].get("clean_collection", "papers_clean")
        if "name" not in profile:
            profile["name"] = profile["collection"]
        _run_profile(store, profile, reports_dir)
