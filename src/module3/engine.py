"""Module 3 — Inference Engine (Orchestrator).

The main CORE engine that ties retriever, strategy, aggregator, and
confidence together.  Takes a user's partially-extracted HP JSON and
infers the missing values from the corpus.
"""

from __future__ import annotations

from src.module3.retriever import FAISSRetriever
from src.module3.strategy import (
    BERT_DEFAULTS,
    EvidencePool,
    run_strategy_cascade,
)
from src.module3.aggregator import aggregate_evidence
from src.module3.confidence import calibrate_confidence, CONFIDENCE_THRESHOLD


class InferenceEngine:
    """Core retrieval-augmented hyperparameter inference engine."""

    def __init__(self, config: dict, mongo_db, retriever=None):
        self.config = config
        # Use pre-built retriever if provided, otherwise create new one
        self.retriever = retriever if retriever is not None else FAISSRetriever(config, mongo_db)
        self.min_evidence = config.get("inference", {}).get("min_evidence", 3)
        self.top_k = config.get("inference", {}).get("top_k", 20)

    def infer(
        self,
        user_hp_json: dict,
        missing_params: list[str],
        title: str = "",
        abstract: str = "",
    ) -> dict:
        """Infer missing hyperparameters.

        Args:
            user_hp_json: HP JSON from Module 1.
            missing_params: List of HP names to infer.
            title: Paper title (for query construction).
            abstract: Paper abstract (for query construction).

        Returns:
            dict with:
                inferred_config: Complete HP dict (user + inferred)
                evidence_report: Per-param evidence details
                strategy_used: Which strategy succeeded
                per_param_confidence: Confidence per HP
        """
        print("\n=== Module 3: CORE Inference Engine ===")

        # Build query from title + abstract
        query_text = f"{title} {abstract}".strip()
        if not query_text:
            query_text = "BERT fine-tuning hyperparameters"

        user_task = user_hp_json.get("task")
        user_model = user_hp_json.get("model")
        user_dataset = user_hp_json.get("dataset")

        print(f"  Query: {query_text[:80]}...")
        print(f"  Task: {user_task}, Model: {user_model}, Dataset: {user_dataset}")
        print(f"  Missing params: {missing_params}")

        # Run S1 → S4 cascade
        print("\n  Running adaptive strategy cascade:")
        evidence_pool = run_strategy_cascade(
            self.retriever,
            query_text,
            user_task=user_task,
            user_model=user_model,
            user_dataset=user_dataset,
            min_evidence=self.min_evidence,
            top_k=self.top_k,
        )

        # Aggregate evidence for missing params
        print(f"\n  Aggregating evidence from {evidence_pool.support_count} papers...")
        aggregated = aggregate_evidence(evidence_pool, missing_params)

        # Compute confidence per param
        per_param_confidence = {}
        for param in missing_params:
            evidence = evidence_pool.hp_evidence.get(param, [])
            per_param_confidence[param] = calibrate_confidence(param, evidence)

        # Build final config: user values + inferred values + defaults
        inferred_config = self._build_config(
            user_hp_json, aggregated, per_param_confidence
        )

        # Build evidence report
        evidence_report = self._build_report(
            evidence_pool, aggregated, per_param_confidence
        )

        print(f"\n  Strategy used: {evidence_pool.strategy}")
        print(f"  Evidence papers: {evidence_pool.support_count}")

        return {
            "inferred_config": inferred_config,
            "evidence_report": evidence_report,
            "strategy_used": evidence_pool.strategy,
            "per_param_confidence": per_param_confidence,
        }

    def _build_config(
        self,
        user_hp_json: dict,
        aggregated: dict,
        confidence: dict,
    ) -> dict:
        """Merge user HPs + inferred HPs + BERT defaults."""
        user_hps = user_hp_json.get("hyperparameters", {})
        config = {}

        for param in [
            "learning_rate", "batch_size", "epochs", "max_seq_length",
            "optimizer", "weight_decay", "warmup_steps", "warmup_ratio",
            "scheduler", "gradient_clipping", "dropout", "seed",
        ]:
            # Priority: user value > inferred value > BERT default
            user_val = user_hps.get(param)
            if user_val is not None:
                config[param] = {
                    "value": user_val,
                    "source": "extracted_from_paper",
                    "confidence": 1.0,
                }
                continue

            agg = aggregated.get(param, {})
            inferred_val = agg.get("value")
            conf = confidence.get(param, {})
            conf_score = conf.get("confidence", 0.0)

            if inferred_val is not None and conf_score >= CONFIDENCE_THRESHOLD:
                config[param] = {
                    "value": inferred_val,
                    "source": "inferred_from_corpus",
                    "confidence": conf_score,
                    "method": agg.get("method", ""),
                    "support_count": agg.get("support_count", 0),
                    "citations": agg.get("sources", []),
                }
            else:
                # Fallback to BERT defaults
                default_val = BERT_DEFAULTS.get(param)
                config[param] = {
                    "value": default_val,
                    "source": "bert_default",
                    "confidence": 0.2,
                    "reason": (
                        "low confidence inference"
                        if inferred_val is not None
                        else "no evidence in corpus"
                    ),
                }

        return config

    def _build_report(
        self,
        evidence_pool: EvidencePool,
        aggregated: dict,
        confidence: dict,
    ) -> dict:
        """Build a detailed evidence report."""
        return {
            "strategy": evidence_pool.strategy,
            "total_evidence_papers": evidence_pool.support_count,
            "papers": evidence_pool.papers[:20],
            "per_param": {
                param: {
                    "aggregated": aggregated.get(param, {}),
                    "confidence": confidence.get(param, {}),
                    "raw_values": [
                        {"value": e[0], "similarity": round(e[1], 3), "rscore": round(e[2], 3)}
                        for e in evidence_pool.hp_evidence.get(param, [])[:10]
                    ],
                }
                for param in aggregated
            },
        }
