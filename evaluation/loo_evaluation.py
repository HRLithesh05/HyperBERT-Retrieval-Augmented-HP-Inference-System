"""
Leave-One-Out Evaluation for HyperBERT

For each paper in the corpus that has reported HP values:
  1. Mask each HP one at a time
  2. Run the inference engine as if that HP were "missing"
  3. Compare inferred value vs actual ground truth
  4. Compute accuracy metrics

Outputs a JSON report with:
  - Per-HP accuracy (EMR, MAE, within-tolerance)
  - Per-strategy accuracy
  - Confidence calibration analysis
  - Overall summary statistics
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "module0" / "src"))


def run_loo_evaluation(
    config_path: str | None = None,
    max_papers: int | None = None,
    output_path: str | None = None,
) -> dict:
    """Run Leave-One-Out evaluation on the corpus.

    Args:
        config_path: Path to config.json (defaults to module0/config.json)
        max_papers: Limit papers to evaluate (for quick testing)
        output_path: Where to save the JSON report

    Returns:
        Evaluation report dict
    """
    from pymongo import MongoClient

    config_path = config_path or str(ROOT / "module0" / "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    # Connect to MongoDB
    mongo = MongoClient(config["mongodb"]["uri"], serverSelectionTimeoutMS=5000)
    mongo.server_info()
    db = mongo[config["mongodb"]["db"]]
    collection = db[config["mongodb"].get("clean_collection", "papers_clean")]

    # Import inference modules
    from src.module3.engine import InferenceEngine
    from src.module3.aggregator import CATEGORICAL_HPS
    from src.module3.confidence import CONFIDENCE_THRESHOLD

    ALL_HPS = [
        "learning_rate", "batch_size", "epochs", "max_seq_length",
        "optimizer", "weight_decay", "warmup_steps", "warmup_ratio",
        "scheduler", "gradient_clipping", "dropout", "seed",
    ]

    # Gather papers that have at least 2 reported HPs
    print("Gathering papers with reported hyperparameters...")
    papers_with_hps = []
    for doc in collection.find({"hp_json": {"$exists": True}}):
        hp = doc.get("hp_json", {})
        hps = hp.get("hyperparameters", {})
        reported = {k: v for k, v in hps.items() if v is not None and k in ALL_HPS}
        if len(reported) >= 2:
            papers_with_hps.append({
                "doc_id": str(doc["_id"]),
                "title": doc.get("title", "")[:80],
                "task": hp.get("task"),
                "model": hp.get("model"),
                "dataset": hp.get("dataset"),
                "reported_hps": reported,
            })

    if max_papers:
        papers_with_hps = papers_with_hps[:max_papers]

    total = len(papers_with_hps)
    print(f"Found {total} papers with ≥2 reported HPs\n")

    if total == 0:
        return {"error": "No papers with sufficient HPs found in corpus"}

    # Initialize engine
    engine = InferenceEngine(config, db)

    # Results accumulators
    per_hp: dict = defaultdict(lambda: {
        "total": 0, "exact_match": 0, "within_tol": 0,
        "errors": [],  # absolute errors for MAE
        "by_confidence": defaultdict(lambda: {"total": 0, "correct": 0}),
    })
    per_strategy: dict = defaultdict(lambda: {"total": 0, "exact_match": 0})
    total_inferences = 0
    total_exact = 0

    t0 = time.perf_counter()

    for i, paper in enumerate(papers_with_hps):
        print(f"[{i+1}/{total}] {paper['title'][:60]}...")

        for hp_name, true_value in paper["reported_hps"].items():
            # Build a user_hp_json with this HP masked out
            masked_hps = {k: v for k, v in paper["reported_hps"].items() if k != hp_name}
            user_hp_json = {
                "model": paper["model"],
                "task": paper["task"],
                "dataset": paper["dataset"],
                "hyperparameters": masked_hps,
            }

            try:
                result = engine.infer(
                    user_hp_json=user_hp_json,
                    missing_params=[hp_name],
                    title=paper["title"],
                    abstract="",
                )
            except Exception as e:
                print(f"  Error inferring {hp_name}: {e}")
                continue

            inferred_entry = result["inferred_config"].get(hp_name, {})
            inferred_value = inferred_entry.get("value")
            confidence = inferred_entry.get("confidence", 0)
            strategy = result["strategy_used"]

            total_inferences += 1

            # Classify confidence level
            if confidence >= 0.7:
                conf_level = "high"
            elif confidence >= CONFIDENCE_THRESHOLD:
                conf_level = "medium"
            else:
                conf_level = "low"

            per_hp[hp_name]["total"] += 1
            per_hp[hp_name]["by_confidence"][conf_level]["total"] += 1
            per_strategy[strategy]["total"] += 1

            # Check accuracy
            is_exact = False
            is_within_tol = False

            if hp_name in CATEGORICAL_HPS:
                # Categorical: exact string match (case-insensitive)
                if inferred_value is not None and str(inferred_value).lower() == str(true_value).lower():
                    is_exact = True
                    is_within_tol = True
            else:
                # Numeric: exact match + within-tolerance
                try:
                    inf_num = float(inferred_value) if inferred_value is not None else None
                    true_num = float(true_value)

                    if inf_num is not None:
                        error = abs(inf_num - true_num)
                        per_hp[hp_name]["errors"].append(error)

                        # Exact match (within 1e-8)
                        if abs(inf_num - true_num) < 1e-8:
                            is_exact = True

                        # Within-tolerance: 20% relative or for very small values
                        if true_num != 0:
                            rel_error = abs(inf_num - true_num) / abs(true_num)
                            is_within_tol = rel_error <= 0.2
                        else:
                            is_within_tol = abs(inf_num) < 1e-6

                        # Special: batch_size within 1 power-of-2 step
                        if hp_name == "batch_size" and inf_num > 0 and true_num > 0:
                            log_diff = abs(math.log2(inf_num) - math.log2(true_num))
                            is_within_tol = is_within_tol or log_diff <= 1.0
                except (ValueError, TypeError):
                    pass

            if is_exact:
                total_exact += 1
                per_hp[hp_name]["exact_match"] += 1
                per_strategy[strategy]["exact_match"] += 1
                per_hp[hp_name]["by_confidence"][conf_level]["correct"] += 1
            elif is_within_tol:
                per_hp[hp_name]["within_tol"] += 1
                per_hp[hp_name]["by_confidence"][conf_level]["correct"] += 1

    elapsed = round(time.perf_counter() - t0, 2)

    # Build final report
    hp_report = {}
    for hp_name, data in per_hp.items():
        n = data["total"]
        if n == 0:
            continue
        emr = round(data["exact_match"] / n * 100, 1)
        tol_rate = round((data["exact_match"] + data["within_tol"]) / n * 100, 1)
        mae = round(sum(data["errors"]) / len(data["errors"]), 6) if data["errors"] else None

        # Confidence calibration
        cal = {}
        for level, counts in data["by_confidence"].items():
            if counts["total"] > 0:
                cal[level] = {
                    "total": counts["total"],
                    "correct": counts["correct"],
                    "accuracy": round(counts["correct"] / counts["total"] * 100, 1),
                }

        hp_report[hp_name] = {
            "total": n,
            "exact_match_rate": emr,
            "within_tolerance_rate": tol_rate,
            "mae": mae,
            "calibration": cal,
        }

    strategy_report = {
        name: {
            "total": data["total"],
            "exact_match_rate": round(data["exact_match"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
        }
        for name, data in per_strategy.items()
    }

    overall_emr = round(total_exact / total_inferences * 100, 1) if total_inferences > 0 else 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "leave_one_out",
        "papers_evaluated": total,
        "total_inferences": total_inferences,
        "elapsed_seconds": elapsed,
        "overall": {
            "exact_match_rate": overall_emr,
            "total_exact": total_exact,
            "total_inferences": total_inferences,
        },
        "per_hp": hp_report,
        "per_strategy": strategy_report,
    }

    # Save
    output_path = output_path or str(ROOT / "evaluation" / "loo_results.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n✅ Evaluation complete: {output_path}")
    print(f"   Papers: {total}, Inferences: {total_inferences}, EMR: {overall_emr}%")

    return report


if __name__ == "__main__":
    max_p = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_loo_evaluation(max_papers=max_p)
