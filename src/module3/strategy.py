"""Module 3 — Adaptive Strategy Loop (S1 → S4).

Implements the four retrieval strategies from the architecture:
  S1 Narrow Match:  task + model + dataset
  S2 Relaxed Match: task + model
  S3 Task Only:     task dimension only
  S4 Global Fallback: all BERT papers in corpus
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvidencePool:
    """A collection of evidence papers with their HP data."""
    strategy: str
    papers: list[dict] = field(default_factory=list)
    hp_values: dict[str, list] = field(default_factory=dict)
    # For each HP, store (value, similarity, rscore, paper_title)
    hp_evidence: dict[str, list[tuple]] = field(default_factory=dict)
    support_count: int = 0

    def add_paper(self, doc: dict) -> None:
        """Add a paper's HP values to the evidence pool."""
        hp_json = doc.get("hp_json", {})
        hps = hp_json.get("hyperparameters", {})
        sim = doc.get("similarity", 0.5)
        rscore = doc.get("rscore", 0.0)
        title = doc.get("title", "Unknown")[:100]

        has_any = False
        for param, value in hps.items():
            if value is not None:
                has_any = True
                if param not in self.hp_values:
                    self.hp_values[param] = []
                    self.hp_evidence[param] = []
                self.hp_values[param].append(value)
                self.hp_evidence[param].append((value, sim, rscore, title))

        if has_any:
            self.support_count += 1
            self.papers.append({
                "title": title,
                "source": doc.get("source", ""),
                "source_id": doc.get("source_id", ""),
                "similarity": sim,
                "rscore": rscore,
                "model": hp_json.get("model"),
                "task": hp_json.get("task"),
                "hyperparameters": hps,  # Include actual HP values for evidence table
            })


# Default BERT paper hyperparameters (Devlin et al., 2019)
BERT_DEFAULTS = {
    "learning_rate": 2e-5,
    "batch_size": 32,
    "epochs": 3,
    "max_seq_length": 128,
    "optimizer": "AdamW",
    "weight_decay": 0.01,
    "warmup_steps": None,
    "warmup_ratio": 0.1,
    "scheduler": "linear",
    "gradient_clipping": 1.0,
    "dropout": 0.1,
    "seed": 42,
}


def run_strategy_cascade(
    retriever,
    query_text: str,
    user_task: str | None,
    user_model: str | None,
    user_dataset: str | None,
    min_evidence: int = 3,
    top_k: int = 20,
) -> EvidencePool:
    """Execute S1 → S4 adaptive strategy cascade.

    Falls through to next strategy when evidence count < min_evidence.

    Returns:
        The EvidencePool from the first strategy with sufficient evidence,
        or the global fallback pool.
    """
    strategies = []

    # S1: Narrow — task + model + dataset
    if user_task and user_model and user_dataset:
        strategies.append(("S1_narrow", user_task, user_model, user_dataset))

    # S2: Relaxed — task + model
    if user_task and user_model:
        strategies.append(("S2_relaxed", user_task, user_model, None))

    # S3: Task only
    if user_task:
        strategies.append(("S3_task_only", user_task, None, None))

    # S4: Global fallback (always)
    strategies.append(("S4_global", None, None, None))

    for name, task, model, dataset in strategies:
        pool = EvidencePool(strategy=name)

        if task or model or dataset:
            docs = retriever.retrieve_filtered(
                query_text, task=task, model_name=model,
                dataset=dataset, top_k=top_k,
            )
        else:
            docs = retriever.retrieve(query_text, top_k=top_k)

        for doc in docs:
            pool.add_paper(doc)

        if pool.support_count >= min_evidence:
            print(f"  Strategy {name}: {pool.support_count} evidence papers ✓")
            return pool
        else:
            print(
                f"  Strategy {name}: {pool.support_count} evidence papers "
                f"(< {min_evidence}) — cascading..."
            )

    # If we get here, return whatever the last (S4) pool has
    return pool
