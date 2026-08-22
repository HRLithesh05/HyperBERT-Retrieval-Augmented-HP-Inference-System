"""Retrieval Quality Evaluation for HyperBERT.

Evaluates whether the FAISS retrieval component returns methodologically
relevant papers — separate from the end-to-end HP accuracy.

Metrics:
  - Precision@k: Fraction of top-k papers sharing task+model with the query
  - MRR (Mean Reciprocal Rank): Where the first "relevant" paper appears
  - Task Match Rate: Fraction of papers matching the query's task

Usage:
    python evaluation/retrieval_eval.py [max_papers]
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "module0" / "src"))


def run_retrieval_evaluation(
    config_path: str | None = None,
    max_papers: int | None = None,
    top_k_values: list[int] | None = None,
    output_path: str | None = None,
) -> dict:
    """Evaluate retrieval quality using leave-one-out methodology.

    For each paper in the corpus:
      1. Use the paper's title+abstract as the query
      2. Retrieve top-k papers (excluding the query paper itself)
      3. Check how many share task, model, or dataset

    Args:
        config_path: Path to config.json.
        max_papers: Limit papers to evaluate.
        top_k_values: List of k values for Precision@k (default [5, 10, 20]).
        output_path: Where to save the JSON report.

    Returns:
        Evaluation report dict.
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

    from src.module3.retriever import FAISSRetriever
    from src.module3.taxonomy import normalize_task, normalize_dataset

    if top_k_values is None:
        top_k_values = [5, 10, 20]
    max_k = max(top_k_values)

    print("Loading retriever...")
    retriever = FAISSRetriever(config, db, preload_model=True)

    # Gather papers with task/model info
    print("Gathering papers with task/model metadata...")
    papers = []
    for doc in collection.find({"hp_json": {"$exists": True}}):
        hp = doc.get("hp_json", {})
        task = hp.get("task")
        model = hp.get("model")
        title = doc.get("title", "")
        abstract = doc.get("abstract", "")

        if not title or (not task and not model):
            continue

        papers.append({
            "doc_id": str(doc["_id"]),
            "title": title[:200],
            "abstract": abstract[:500],
            "task": normalize_task(task),
            "model": (model or "").lower(),
            "dataset": normalize_dataset(hp.get("dataset")),
        })

    if max_papers:
        papers = papers[:max_papers]

    total = len(papers)
    print(f"Evaluating retrieval for {total} papers\n")

    if total == 0:
        return {"error": "No papers with task/model metadata found"}

    # Accumulators
    precision_at = {k: [] for k in top_k_values}
    reciprocal_ranks = []
    task_match_rates = {k: [] for k in top_k_values}

    t0 = time.perf_counter()

    for i, paper in enumerate(papers):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"[{i+1}/{total}] {paper['title'][:60]}...")

        query = f"{paper['title']}. {paper['abstract']}"
        results = retriever.retrieve(query, top_k=max_k + 5)

        # Exclude the query paper itself from results
        results = [r for r in results if str(r.get("_id", "")) != paper["doc_id"]][:max_k]

        # Check relevance for each retrieved paper
        for k in top_k_values:
            top_k_results = results[:k]
            relevant_count = 0
            task_matches = 0

            for doc in top_k_results:
                doc_hp = doc.get("hp_json", {})
                doc_task = normalize_task(doc_hp.get("task"))
                doc_model = (doc_hp.get("model") or "").lower()

                # Relevant = shares at least task
                if paper["task"] and doc_task and (
                    paper["task"] in doc_task or doc_task in paper["task"]
                ):
                    task_matches += 1
                    # Bonus: also shares model
                    if paper["model"] and doc_model and (
                        paper["model"] in doc_model or doc_model in paper["model"]
                    ):
                        relevant_count += 1
                    else:
                        relevant_count += 0.5  # partial credit for task-only match

            if top_k_results:
                precision_at[k].append(relevant_count / len(top_k_results))
                task_match_rates[k].append(task_matches / len(top_k_results))

        # MRR: find rank of first relevant paper
        found_rank = None
        for rank, doc in enumerate(results, 1):
            doc_hp = doc.get("hp_json", {})
            doc_task = normalize_task(doc_hp.get("task"))
            doc_model = (doc_hp.get("model") or "").lower()

            if paper["task"] and doc_task and (
                paper["task"] in doc_task or doc_task in paper["task"]
            ):
                if paper["model"] and doc_model and (
                    paper["model"] in doc_model or doc_model in paper["model"]
                ):
                    found_rank = rank
                    break

        reciprocal_ranks.append(1.0 / found_rank if found_rank else 0.0)

    elapsed = round(time.perf_counter() - t0, 2)

    # Build report
    def _mean(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "retrieval_quality",
        "papers_evaluated": total,
        "elapsed_seconds": elapsed,
        "metrics": {
            f"precision_at_{k}": {
                "mean": _mean(precision_at[k]),
                "total_queries": len(precision_at[k]),
            }
            for k in top_k_values
        },
        "task_match_rate": {
            f"at_{k}": _mean(task_match_rates[k])
            for k in top_k_values
        },
        "mrr": {
            "mean_reciprocal_rank": _mean(reciprocal_ranks),
            "total_queries": len(reciprocal_ranks),
            "queries_with_match": sum(1 for rr in reciprocal_ranks if rr > 0),
        },
    }

    # Save
    output_path = output_path or str(ROOT / "evaluation" / "retrieval_eval_results.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n✅ Retrieval evaluation complete: {output_path}")
    print(f"   Papers: {total}, Elapsed: {elapsed}s")
    for k in top_k_values:
        print(f"   Precision@{k}: {_mean(precision_at[k]):.4f}")
    print(f"   MRR: {_mean(reciprocal_ranks):.4f}")
    print(f"   Task Match Rate@{top_k_values[0]}: {_mean(task_match_rates[top_k_values[0]]):.4f}")

    return report


if __name__ == "__main__":
    max_p = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_retrieval_evaluation(max_papers=max_p)
