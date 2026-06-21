"""R-Score computation (Module 0, Step 5).

The R-Score (Reporting Score) measures how completely a paper reports
its BERT fine-tuning hyperparameters.  It is a weighted completeness
metric used downstream by Module 3 for confidence weighting — papers
with higher R-Scores contribute more to HP inference.

Formula:  R = Σ(weight_i × present_i) / Σ(weight_i)

Where present_i = 1 if the HP is non-null in hp_json, else 0.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WEIGHTS: dict[str, float] = {
    "learning_rate": 3.0,
    "batch_size": 3.0,
    "epochs": 2.0,
    "optimizer": 2.0,
    "max_seq_length": 1.0,
    "weight_decay": 1.0,
    "warmup_steps": 0.5,
    "warmup_ratio": 0.5,
    "scheduler": 1.0,
    "dropout": 0.5,
    "seed": 0.5,
    "gradient_clipping": 0.5,
}


def _compute_rscore(hp_json: dict, weights: dict[str, float]) -> float:
    """Compute R-Score for a single paper's hp_json."""
    hps = hp_json.get("hyperparameters") or {}

    total_weight = 0.0
    earned_weight = 0.0

    for param, weight in weights.items():
        total_weight += weight
        # handle warmup: count if either warmup_steps or warmup_ratio is present
        if param == "warmup_steps" and hps.get("warmup_steps") is None:
            if hps.get("warmup_ratio") is not None:
                earned_weight += weight
                continue
        if param == "warmup_ratio" and hps.get("warmup_ratio") is None:
            if hps.get("warmup_steps") is not None:
                earned_weight += weight
                continue

        val = hps.get(param)
        if val is not None:
            earned_weight += weight

    if total_weight == 0:
        return 0.0
    return round(earned_weight / total_weight, 4)


def compute_rscores(store, config: dict, paths: dict) -> None:
    """Compute and store R-Scores for all clean papers with hp_json."""
    rscore_cfg = config.get("rscore", {})
    weights = rscore_cfg.get("weights", DEFAULT_WEIGHTS)

    clean_name = config["mongodb"].get("clean_collection", "papers_clean")
    clean_col = store.get_collection(clean_name)

    # only process papers that have hp_json
    query = {"hp_json": {"$exists": True}}
    total = clean_col.count_documents(query)
    if total == 0:
        print("No papers with hp_json found — run hp_extract first.")
        return

    print(f"Computing R-Scores for {total} papers ...")

    scores: list[float] = []
    task_dist: dict[str, int] = {}
    model_dist: dict[str, int] = {}

    for doc in clean_col.find(query, batch_size=200):
        hp_json = doc["hp_json"]
        rscore = _compute_rscore(hp_json, weights)
        scores.append(rscore)

        # track distributions for the report
        task = hp_json.get("task") or "unknown"
        model = hp_json.get("model") or "unknown"
        task_dist[task] = task_dist.get(task, 0) + 1
        model_dist[model] = model_dist.get(model, 0) + 1

        clean_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "rscore": rscore,
                "rscore_computed_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

    # stats
    scores.sort()
    n = len(scores)
    mean_score = sum(scores) / n if n else 0
    median_score = scores[n // 2] if n else 0
    min_score = scores[0] if n else 0
    max_score = scores[-1] if n else 0

    # percentiles
    p25 = scores[int(n * 0.25)] if n > 4 else min_score
    p75 = scores[int(n * 0.75)] if n > 4 else max_score

    # HP coverage stats
    hp_coverage: dict[str, int] = {}
    for doc in clean_col.find(query, {"hp_json.hyperparameters": 1}, batch_size=200):
        hps = doc.get("hp_json", {}).get("hyperparameters", {})
        for param in weights:
            if hps.get(param) is not None:
                hp_coverage[param] = hp_coverage.get(param, 0) + 1

    # sort task and model distributions by count
    task_dist = dict(sorted(task_dist.items(), key=lambda x: -x[1]))
    model_dist = dict(sorted(model_dist.items(), key=lambda x: -x[1]))

    print(f"\nR-Score Stats: mean={mean_score:.3f}, median={median_score:.3f}, "
          f"min={min_score:.3f}, max={max_score:.3f}")
    print(f"HP coverage (out of {n} papers):")
    for param, count in sorted(hp_coverage.items(), key=lambda x: -x[1]):
        print(f"  {param}: {count}/{n} ({100*count/n:.1f}%)")

    # write report
    reports_dir = Path(paths["reports_dir"]).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "summary": {
            "total_papers": n,
            "mean_rscore": round(mean_score, 4),
            "median_rscore": round(median_score, 4),
            "min_rscore": round(min_score, 4),
            "max_rscore": round(max_score, 4),
            "p25_rscore": round(p25, 4),
            "p75_rscore": round(p75, 4),
        },
        "hp_coverage": {
            param: {"count": hp_coverage.get(param, 0), "pct": round(100 * hp_coverage.get(param, 0) / n, 1) if n else 0}
            for param in weights
        },
        "task_distribution": task_dist,
        "model_distribution": model_dist,
        "weights_used": weights,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    report_path = reports_dir / "rscore_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {report_path}")
