"""Corpus Quality Audit for HyperBERT.

Scans all papers in the MongoDB corpus and flags potential issues:
  - Learning rates outside [1e-7, 1e-1] (likely extraction errors)
  - Batch sizes that aren't powers of 2 (suspicious)
  - Epochs > 50 (likely pre-training, not fine-tuning)
  - Missing task or model fields
  - Duplicate papers (same title)
  - Very short abstracts (< 50 chars)

Generates a JSON report with flagged papers and summary statistics.

Usage:
    python evaluation/corpus_audit.py [--limit N]
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def is_power_of_2(n: int) -> bool:
    """Check if n is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def run_corpus_audit(
    config_path: str | None = None,
    limit: int | None = None,
    output_path: str | None = None,
) -> dict:
    """Audit the corpus for data quality issues.

    Args:
        config_path: Path to config.json.
        limit: Max papers to audit (None = all).
        output_path: Where to save the JSON report.

    Returns:
        Audit report dict.
    """
    import os
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    config_path = config_path or str(ROOT / "module0" / "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    uri = os.environ.get("MONGODB_URI", config["mongodb"]["uri"])
    mongo = MongoClient(uri, serverSelectionTimeoutMS=5000)
    mongo.server_info()
    db = mongo[config["mongodb"]["db"]]
    collection = db[config["mongodb"].get("clean_collection", "papers_clean")]

    print("Scanning corpus for quality issues...")

    issues: list[dict] = []
    titles_seen: dict[str, list[str]] = defaultdict(list)  # title -> [doc_ids]

    # Counters
    total_papers = 0
    papers_with_hps = 0
    field_coverage: dict[str, int] = Counter()
    task_counts: dict[str, int] = Counter()
    model_counts: dict[str, int] = Counter()

    query = {}
    cursor = collection.find(query)
    if limit:
        cursor = cursor.limit(limit)

    for doc in cursor:
        total_papers += 1
        doc_id = str(doc["_id"])
        title = doc.get("title", "")[:120]
        hp_json = doc.get("hp_json", {})
        hps = hp_json.get("hyperparameters", {})

        # Track title duplicates
        title_key = title.lower().strip()
        if title_key and len(title_key) > 10:
            titles_seen[title_key].append(doc_id)

        # Track task/model coverage
        task = hp_json.get("task")
        model = hp_json.get("model")
        dataset = hp_json.get("dataset")

        if task:
            task_counts[task] += 1
        if model:
            model_counts[model.lower()] += 1

        # Count HP field coverage
        has_any_hp = False
        for k, v in hps.items():
            if v is not None:
                field_coverage[k] += 1
                has_any_hp = True
        if has_any_hp:
            papers_with_hps += 1

        # ── Check: Missing task ─────────────────────────────────────
        if not task:
            issues.append({
                "doc_id": doc_id,
                "title": title,
                "type": "missing_task",
                "severity": "warning",
                "message": "No task field detected",
            })

        # ── Check: Missing model ────────────────────────────────────
        if not model:
            issues.append({
                "doc_id": doc_id,
                "title": title,
                "type": "missing_model",
                "severity": "warning",
                "message": "No model field detected",
            })

        # ── Check: Learning rate out of range ───────────────────────
        lr = hps.get("learning_rate")
        if lr is not None:
            try:
                lr_f = float(lr)
                if lr_f < 1e-7 or lr_f > 0.1:
                    issues.append({
                        "doc_id": doc_id,
                        "title": title,
                        "type": "lr_out_of_range",
                        "severity": "error",
                        "value": lr_f,
                        "message": f"Learning rate {lr_f:.2e} outside expected range [1e-7, 0.1]",
                    })
            except (ValueError, TypeError):
                pass

        # ── Check: Batch size not power of 2 ────────────────────────
        bs = hps.get("batch_size")
        if bs is not None:
            try:
                bs_i = int(bs)
                if bs_i > 0 and not is_power_of_2(bs_i):
                    issues.append({
                        "doc_id": doc_id,
                        "title": title,
                        "type": "bs_not_power_of_2",
                        "severity": "info",
                        "value": bs_i,
                        "message": f"Batch size {bs_i} is not a power of 2 (unusual but possible)",
                    })
            except (ValueError, TypeError):
                pass

        # ── Check: Epochs > 50 (likely pre-training) ────────────────
        epochs = hps.get("epochs")
        if epochs is not None:
            try:
                ep_i = int(epochs)
                if ep_i > 50:
                    issues.append({
                        "doc_id": doc_id,
                        "title": title,
                        "type": "epochs_too_high",
                        "severity": "warning",
                        "value": ep_i,
                        "message": f"Epochs={ep_i} — likely pre-training, not fine-tuning",
                    })
            except (ValueError, TypeError):
                pass

        # ── Check: Short abstract ───────────────────────────────────
        abstract = doc.get("abstract", "")
        if abstract and len(abstract.strip()) < 50:
            issues.append({
                "doc_id": doc_id,
                "title": title,
                "type": "short_abstract",
                "severity": "info",
                "message": f"Abstract very short ({len(abstract)} chars) — may affect retrieval quality",
            })

        # ── Check: Dropout > 0.5 ───────────────────────────────────
        dropout = hps.get("dropout")
        if dropout is not None:
            try:
                do_f = float(dropout)
                if do_f > 0.5:
                    issues.append({
                        "doc_id": doc_id,
                        "title": title,
                        "type": "dropout_too_high",
                        "severity": "warning",
                        "value": do_f,
                        "message": f"Dropout={do_f} — unusually high for BERT fine-tuning",
                    })
            except (ValueError, TypeError):
                pass

    # ── Check: Duplicate titles ─────────────────────────────────────
    duplicates = {title: ids for title, ids in titles_seen.items() if len(ids) > 1}
    for title, ids in duplicates.items():
        issues.append({
            "doc_ids": ids,
            "title": title[:80],
            "type": "duplicate_title",
            "severity": "warning",
            "message": f"Title appears {len(ids)} times in corpus",
        })

    # Summary
    issue_counts = Counter(i["type"] for i in issues)
    severity_counts = Counter(i["severity"] for i in issues)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_type": "corpus_quality",
        "total_papers": total_papers,
        "papers_with_hps": papers_with_hps,
        "summary": {
            "total_issues": len(issues),
            "by_type": dict(issue_counts),
            "by_severity": dict(severity_counts),
            "duplicate_titles": len(duplicates),
        },
        "field_coverage": {
            k: {"count": v, "pct": round(v / total_papers * 100, 1) if total_papers > 0 else 0}
            for k, v in sorted(field_coverage.items(), key=lambda x: -x[1])
        },
        "task_distribution": dict(task_counts.most_common(20)),
        "model_distribution": dict(model_counts.most_common(20)),
        "issues": issues,
    }

    # Save
    output_path = output_path or str(ROOT / "evaluation" / "corpus_audit.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\n✅ Corpus audit complete: {output_path}")
    print(f"   Papers: {total_papers}, With HPs: {papers_with_hps}")
    print(f"   Issues found: {len(issues)}")
    for itype, count in issue_counts.most_common():
        print(f"     {itype}: {count}")

    return report


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "--limit" else None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            lim = int(sys.argv[idx + 1])
    run_corpus_audit(limit=lim)
