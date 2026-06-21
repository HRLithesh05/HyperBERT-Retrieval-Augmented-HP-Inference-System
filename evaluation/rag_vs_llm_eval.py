"""
RAG vs LLM Evaluation — Head-to-Head Accuracy Comparison

For papers in the corpus with reported HPs:
  1. Mask each HP
  2. Get RAG inference (from corpus)
  3. Get LLM suggestion (from Gemini/Groq)
  4. Compare both against ground truth
  5. Output which system is more accurate overall

This produces the key capstone metric:
  "RAG achieved X% EMR vs LLM's Y% EMR"
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "module0" / "src"))


def run_rag_vs_llm_eval(
    config_path: str | None = None,
    max_papers: int = 20,
    output_path: str | None = None,
) -> dict:
    """Run RAG vs LLM head-to-head evaluation.

    Args:
        config_path: Path to config.json
        max_papers: Limit papers (LLM calls are slow + rate-limited)
        output_path: Where to save the JSON report
    """
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    from pymongo import MongoClient

    config_path = config_path or str(ROOT / "module0" / "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    mongo = MongoClient(config["mongodb"]["uri"], serverSelectionTimeoutMS=5000)
    mongo.server_info()
    db = mongo[config["mongodb"]["db"]]
    collection = db[config["mongodb"].get("clean_collection", "papers_clean")]

    from src.module3.engine import InferenceEngine
    from src.module3.aggregator import CATEGORICAL_HPS
    from src.module8.llm_baseline import query_gemini, query_groq

    ALL_HPS = [
        "learning_rate", "batch_size", "epochs", "max_seq_length",
        "optimizer", "weight_decay", "warmup_ratio",
        "scheduler", "gradient_clipping", "dropout",
    ]

    # Gather papers
    papers = []
    for doc in collection.find({"hp_json": {"$exists": True}}):
        hp = doc.get("hp_json", {})
        hps = hp.get("hyperparameters", {})
        reported = {k: v for k, v in hps.items() if v is not None and k in ALL_HPS}
        if len(reported) >= 3:
            papers.append({
                "title": doc.get("title", "")[:80],
                "task": hp.get("task"),
                "model": hp.get("model"),
                "dataset": hp.get("dataset"),
                "reported_hps": reported,
            })

    papers = papers[:max_papers]
    print(f"Evaluating {len(papers)} papers (RAG + LLM) ...\n")

    engine = InferenceEngine(config, db)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")

    rag_results = {"total": 0, "exact": 0, "within_tol": 0}
    llm_results = {"total": 0, "exact": 0, "within_tol": 0}
    per_hp_rag = defaultdict(lambda: {"total": 0, "exact": 0})
    per_hp_llm = defaultdict(lambda: {"total": 0, "exact": 0})
    both_agree_correct = 0
    both_agree_wrong = 0
    rag_only_correct = 0
    llm_only_correct = 0

    for i, paper in enumerate(papers):
        print(f"[{i+1}/{len(papers)}] {paper['title'][:50]}...")

        for hp_name, true_value in paper["reported_hps"].items():
            masked = {k: v for k, v in paper["reported_hps"].items() if k != hp_name}
            user_hp_json = {
                "model": paper["model"],
                "task": paper["task"],
                "dataset": paper["dataset"],
                "hyperparameters": masked,
            }

            # ── RAG inference ──
            try:
                rag = engine.infer(
                    user_hp_json=user_hp_json,
                    missing_params=[hp_name],
                    title=paper["title"],
                    abstract="",
                )
                rag_val = rag["inferred_config"].get(hp_name, {}).get("value")
            except Exception:
                rag_val = None

            # ── LLM inference ──
            try:
                llm_resp = query_gemini(
                    task=paper["task"] or "",
                    model=paper["model"] or "BERT",
                    dataset=paper["dataset"] or "",
                    missing_params=[hp_name],
                    api_key=gemini_key,
                )
                if llm_resp.get("error") and groq_key:
                    llm_resp = query_groq(
                        task=paper["task"] or "",
                        model=paper["model"] or "BERT",
                        dataset=paper["dataset"] or "",
                        missing_params=[hp_name],
                        api_key=groq_key,
                    )
                llm_val = llm_resp.get("suggestions", {}).get(hp_name)
                # Rate limiting
                time.sleep(0.5)
            except Exception:
                llm_val = None

            # ── Compare ──
            rag_correct = _is_correct(rag_val, true_value, hp_name, hp_name in CATEGORICAL_HPS)
            llm_correct = _is_correct(llm_val, true_value, hp_name, hp_name in CATEGORICAL_HPS)

            rag_results["total"] += 1
            llm_results["total"] += 1
            per_hp_rag[hp_name]["total"] += 1
            per_hp_llm[hp_name]["total"] += 1

            if rag_correct:
                rag_results["exact"] += 1
                per_hp_rag[hp_name]["exact"] += 1
            if llm_correct:
                llm_results["exact"] += 1
                per_hp_llm[hp_name]["exact"] += 1

            if rag_correct and llm_correct:
                both_agree_correct += 1
            elif rag_correct and not llm_correct:
                rag_only_correct += 1
            elif not rag_correct and llm_correct:
                llm_only_correct += 1
            else:
                both_agree_wrong += 1

    total = rag_results["total"]
    rag_emr = round(rag_results["exact"] / total * 100, 1) if total > 0 else 0
    llm_emr = round(llm_results["exact"] / total * 100, 1) if total > 0 else 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "rag_vs_llm",
        "papers_evaluated": len(papers),
        "total_comparisons": total,
        "overall": {
            "rag_accuracy": rag_emr,
            "llm_accuracy": llm_emr,
            "rag_wins": rag_emr > llm_emr,
            "margin": round(abs(rag_emr - llm_emr), 1),
        },
        "agreement_analysis": {
            "both_correct": both_agree_correct,
            "rag_only_correct": rag_only_correct,
            "llm_only_correct": llm_only_correct,
            "both_wrong": both_agree_wrong,
        },
        "per_hp_rag": {
            hp: {"total": d["total"], "accuracy": round(d["exact"] / d["total"] * 100, 1) if d["total"] > 0 else 0}
            for hp, d in per_hp_rag.items()
        },
        "per_hp_llm": {
            hp: {"total": d["total"], "accuracy": round(d["exact"] / d["total"] * 100, 1) if d["total"] > 0 else 0}
            for hp, d in per_hp_llm.items()
        },
    }

    output_path = output_path or str(ROOT / "evaluation" / "rag_vs_llm_results.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"  RAG Accuracy: {rag_emr}%")
    print(f"  LLM Accuracy: {llm_emr}%")
    print(f"  Winner: {'RAG ✓' if rag_emr >= llm_emr else 'LLM'}")
    print(f"{'='*50}")

    return report


def _is_correct(predicted, true_value, hp_name, is_categorical, tolerance=0.2):
    """Check if predicted value matches true value."""
    if predicted is None:
        return False
    if is_categorical:
        return str(predicted).lower() == str(true_value).lower()
    try:
        p = float(predicted)
        t = float(true_value)
        if t == 0:
            return abs(p) < 1e-6
        return abs(p - t) / abs(t) <= tolerance
    except (ValueError, TypeError):
        return str(predicted).lower() == str(true_value).lower()


if __name__ == "__main__":
    max_p = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_rag_vs_llm_eval(max_papers=max_p)
