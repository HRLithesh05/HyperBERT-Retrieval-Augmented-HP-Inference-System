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

    # Connect to MongoDB — prefer .env MONGODB_URI over config.json
    import os
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    mongo_uri = os.environ.get("MONGODB_URI") or config["mongodb"]["uri"]
    mongo = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    mongo.server_info()
    db_name = config["mongodb"].get("db") or config["mongodb"].get("database") or "hyperbert"
    db = mongo[db_name]
    collection = db[config["mongodb"].get("clean_collection", "papers_clean")]

    from src.module3.engine import InferenceEngine
    from src.module3.aggregator import CATEGORICAL_HPS
    from src.module3.confidence import CONFIDENCE_THRESHOLD

    ALL_HPS = [
        "learning_rate", "batch_size", "epochs", "max_seq_length",
        "optimizer", "weight_decay", "warmup_steps", "warmup_ratio",
        "scheduler", "gradient_clipping", "dropout", "seed",
    ]

    # ── Canonical Tolerance Bands ──────────────────────────────────────
    # Precisely defines what "match" means for each parameter type.
    TOLERANCE_BANDS = {
        # Continuous: relative tolerance (fraction)
        "learning_rate":     {"type": "relative", "tol": 0.20},
        "weight_decay":      {"type": "relative", "tol": 0.25},
        "warmup_ratio":      {"type": "absolute", "tol": 0.05},
        "gradient_clipping": {"type": "relative", "tol": 0.20},
        "dropout":           {"type": "absolute", "tol": 0.05},
        # Integer: absolute tolerance
        "epochs":            {"type": "absolute", "tol": 1},
        "warmup_steps":      {"type": "relative", "tol": 0.30},
        # Integer: power-of-2 step
        "batch_size":        {"type": "power_of_2", "tol": 1.0},
        # Integer: exact set
        "max_seq_length":    {"type": "exact_set", "valid": [64, 128, 256, 384, 512]},
        # Integer: exact
        "seed":              {"type": "exact"},
        # Categorical: case-insensitive exact string
        "optimizer":         {"type": "exact_ci"},
        "scheduler":         {"type": "exact_ci"},
    }

    def _check_match(hp_name, inferred_value, true_value):
        """Check if inferred matches true using canonical tolerance bands.
        
        Returns: (is_exact, is_within_tol, error_value_or_None)
        """
        band = TOLERANCE_BANDS.get(hp_name, {"type": "relative", "tol": 0.20})
        btype = band["type"]

        if btype == "exact_ci":
            if inferred_value is not None and str(inferred_value).lower() == str(true_value).lower():
                return True, True, None
            return False, False, None

        # Numeric types
        try:
            inf_num = float(inferred_value) if inferred_value is not None else None
            true_num = float(true_value)
        except (ValueError, TypeError):
            return False, False, None

        if inf_num is None:
            return False, False, None

        error = abs(inf_num - true_num)
        is_exact = error < 1e-8

        if btype == "exact":
            return is_exact, is_exact, error

        if btype == "relative":
            tol = band["tol"]
            if true_num != 0:
                is_within = (error / abs(true_num)) <= tol
            else:
                is_within = error < 1e-6
            return is_exact, is_exact or is_within, error

        if btype == "absolute":
            tol = band["tol"]
            is_within = error <= tol
            return is_exact, is_exact or is_within, error

        if btype == "power_of_2":
            tol = band["tol"]
            if inf_num > 0 and true_num > 0:
                log_diff = abs(math.log2(inf_num) - math.log2(true_num))
                is_within = log_diff <= tol
            else:
                is_within = is_exact
            return is_exact, is_exact or is_within, error

        if btype == "exact_set":
            is_within = int(round(inf_num)) in band.get("valid", [])
            return is_exact, is_exact or is_within, error

        # Fallback
        return is_exact, is_exact, error

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

    # ── Compute Naive Baseline (corpus-wide median/mode) ───────────────
    print("Computing naive baseline (corpus-wide median/mode)...")
    from collections import Counter
    corpus_values: dict[str, list] = defaultdict(list)
    for doc in collection.find({"hp_json": {"$exists": True}}):
        hps = doc.get("hp_json", {}).get("hyperparameters", {})
        for k, v in hps.items():
            if v is not None and k in ALL_HPS:
                corpus_values[k].append(v)

    naive_baselines = {}
    for hp_name in ALL_HPS:
        vals = corpus_values.get(hp_name, [])
        if not vals:
            naive_baselines[hp_name] = None
            continue
        if hp_name in CATEGORICAL_HPS:
            # Mode
            counts = Counter(str(v).lower().strip() for v in vals)
            naive_baselines[hp_name] = counts.most_common(1)[0][0]
        else:
            # Median
            try:
                nums = sorted(float(v) for v in vals)
                mid = len(nums) // 2
                if len(nums) % 2 == 0:
                    naive_baselines[hp_name] = (nums[mid - 1] + nums[mid]) / 2
                else:
                    naive_baselines[hp_name] = nums[mid]
            except (ValueError, TypeError):
                naive_baselines[hp_name] = None

    print(f"  Naive baselines computed for {sum(1 for v in naive_baselines.values() if v is not None)} params")

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

    # Naive baseline accumulators
    naive_total = 0
    naive_exact = 0
    naive_within_tol = 0

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

            # Check accuracy using canonical tolerance bands
            is_exact, is_within_tol, error_val = _check_match(hp_name, inferred_value, true_value)
            if error_val is not None:
                per_hp[hp_name]["errors"].append(error_val)

            if is_exact:
                total_exact += 1
                per_hp[hp_name]["exact_match"] += 1
                per_strategy[strategy]["exact_match"] += 1
                per_hp[hp_name]["by_confidence"][conf_level]["correct"] += 1
            elif is_within_tol:
                per_hp[hp_name]["within_tol"] += 1
                per_hp[hp_name]["by_confidence"][conf_level]["correct"] += 1

            # ── Naive baseline check ───────────────────────────────────
            naive_val = naive_baselines.get(hp_name)
            if naive_val is not None:
                naive_total += 1
                n_exact, n_tol, _ = _check_match(hp_name, naive_val, true_value)
                if n_exact:
                    naive_exact += 1
                    naive_within_tol += 1
                elif n_tol:
                    naive_within_tol += 1

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
            "tolerance_definition": TOLERANCE_BANDS.get(hp_name, {}),
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

    # Naive baseline summary
    naive_emr = round(naive_exact / naive_total * 100, 1) if naive_total > 0 else 0
    naive_tol_rate = round(naive_within_tol / naive_total * 100, 1) if naive_total > 0 else 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "leave_one_out",
        "papers_evaluated": total,
        "total_inferences": total_inferences,
        "elapsed_seconds": elapsed,
        "tolerance_bands": {k: v for k, v in TOLERANCE_BANDS.items()
                           if not isinstance(v.get("valid"), list) or True},
        "overall": {
            "exact_match_rate": overall_emr,
            "total_exact": total_exact,
            "total_inferences": total_inferences,
        },
        "naive_baseline": {
            "description": "Corpus-wide median (continuous) / mode (categorical), ignoring retrieval entirely",
            "exact_match_rate": naive_emr,
            "within_tolerance_rate": naive_tol_rate,
            "total_compared": naive_total,
            "naive_values": {k: str(v) for k, v in naive_baselines.items() if v is not None},
        },
        "lift_over_naive": {
            "emr_lift_pct_points": round(overall_emr - naive_emr, 1),
            "description": f"RAG ({overall_emr}%) vs Naive Baseline ({naive_emr}%) = +{round(overall_emr - naive_emr, 1)} pct points",
        },
        "per_hp": hp_report,
        "per_strategy": strategy_report,
    }

    # ── Confidence Calibration Summary ─────────────────────────────────
    # Aggregate calibration across all HPs
    cal_totals: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for hp_data in per_hp.values():
        for level, counts in hp_data["by_confidence"].items():
            cal_totals[level]["total"] += counts["total"]
            cal_totals[level]["correct"] += counts["correct"]

    calibration_summary = {}
    for level in ["high", "medium", "low"]:
        if cal_totals[level]["total"] > 0:
            acc = round(cal_totals[level]["correct"] / cal_totals[level]["total"] * 100, 1)
            calibration_summary[level] = {
                "total": cal_totals[level]["total"],
                "correct": cal_totals[level]["correct"],
                "accuracy": acc,
            }

    # Check for miscalibration
    high_acc = calibration_summary.get("high", {}).get("accuracy", 0)
    med_acc = calibration_summary.get("medium", {}).get("accuracy", 0)
    miscalibrated = (
        high_acc > 0 and med_acc > 0 and high_acc < med_acc
    )

    report["confidence_calibration"] = {
        "by_level": calibration_summary,
        "is_miscalibrated": miscalibrated,
        "warning": (
            f"High-confidence predictions ({high_acc}%) are LESS accurate than "
            f"medium-confidence ({med_acc}%) — weights may need retuning"
        ) if miscalibrated else None,
        "current_weights": {
            "similarity": 0.4,
            "support_count": 0.3,
            "agreement": 0.3,
            "note": "Defined in src/module3/confidence.py",
        },
    }

    # Save
    output_path = output_path or str(ROOT / "evaluation" / "loo_results.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n✅ Evaluation complete: {output_path}")
    print(f"   Papers: {total}, Inferences: {total_inferences}")
    print(f"   RAG EMR: {overall_emr}%")
    print(f"   Naive Baseline EMR: {naive_emr}%")
    print(f"   Lift: +{round(overall_emr - naive_emr, 1)} pct points")

    return report


if __name__ == "__main__":
    max_p = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_loo_evaluation(max_papers=max_p)

