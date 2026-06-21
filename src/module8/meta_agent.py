"""
Module 8b: Meta-Reasoning Agent — Adaptive Inference Enhancement

This module adds true agentic behavior to HyperBERT by:
1. Reviewing confidence scores after M3 inference
2. For low-confidence HPs: expanding search or querying LLM
3. Comparing RAG and LLM, picking the best answer
4. Logging every decision with reasoning in an audit trail

The agent makes the pipeline adaptive rather than fixed.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


# Decision thresholds
LOW_CONFIDENCE_THRESHOLD = 0.3
AGREEMENT_BOOST = 0.15
LLM_FALLBACK_CONFIDENCE = 0.4


def run_meta_agent(
    inferred_config: dict,
    per_param_confidence: dict,
    paper_info: dict,
    missing_params: list[str],
    engine=None,
    user_hp_json: dict | None = None,
    gemini_key: str | None = None,
    groq_key: str | None = None,
) -> dict:
    """
    Run the meta-reasoning agent on the inference results.

    The agent reviews each HP's confidence and decides whether to:
    - Accept the RAG result (high confidence)
    - Expand the search (medium-low confidence)
    - Query LLM as second opinion (low confidence)
    - Use ensemble of RAG+LLM (when both available)

    Returns:
        {
            "enhanced_config": { ... },  # possibly updated config
            "agent_decisions": [ ... ],  # audit trail of decisions
            "agent_summary": { ... },    # summary statistics
        }
    """
    decisions = []
    enhanced_config = dict(inferred_config)
    
    accepted_count = 0
    llm_consulted_count = 0
    boosted_count = 0
    overridden_count = 0

    gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")
    groq_key = groq_key or os.environ.get("GROQ_API_KEY", "")
    has_llm = bool(gemini_key or groq_key)

    task = paper_info.get("task", "")
    model = paper_info.get("model", "BERT")
    dataset = paper_info.get("dataset", "")

    for param in missing_params:
        entry = inferred_config.get(param, {})
        if not isinstance(entry, dict):
            continue

        confidence = entry.get("confidence", 0)
        value = entry.get("value")
        source = entry.get("source", "unknown")

        decision = {
            "param": param,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_value": value,
            "original_confidence": round(confidence * 100 if confidence <= 1 else confidence, 1),
            "original_source": source,
            "action": None,
            "reasoning": [],
            "result_value": value,
            "result_confidence": round(confidence * 100 if confidence <= 1 else confidence, 1),
        }

        conf_pct = confidence * 100 if confidence <= 1 else confidence

        # ── Decision 1: High confidence → Accept ──
        if conf_pct >= 60:
            decision["action"] = "ACCEPT"
            decision["reasoning"].append(
                f"Confidence {conf_pct:.1f}% exceeds acceptance threshold (60%). "
                f"Value '{value}' is well-supported by corpus evidence."
            )
            accepted_count += 1

        # ── Decision 2: Medium confidence → Accept with note ──
        elif conf_pct >= LOW_CONFIDENCE_THRESHOLD * 100:
            decision["action"] = "ACCEPT_WITH_CAVEAT"
            decision["reasoning"].append(
                f"Confidence {conf_pct:.1f}% is moderate (threshold: {LOW_CONFIDENCE_THRESHOLD*100}%). "
                f"Value '{value}' accepted but flagged for manual review."
            )
            accepted_count += 1

            # Try LLM verification if available
            if has_llm:
                llm_val = _query_llm_for_param(
                    param, task, model, dataset, gemini_key, groq_key
                )
                llm_consulted_count += 1

                if llm_val is not None:
                    agrees = _values_agree(value, llm_val, param)
                    if agrees:
                        # Boost confidence — two independent systems agree
                        new_conf = min(conf_pct + AGREEMENT_BOOST * 100, 95)
                        enhanced_config[param] = {
                            **entry,
                            "confidence": new_conf / 100,
                            "confidence_pct": new_conf,
                            "agent_note": f"Confidence boosted: RAG and LLM ({llm_val}) agree",
                        }
                        decision["result_confidence"] = round(new_conf, 1)
                        decision["reasoning"].append(
                            f"LLM also suggests '{llm_val}' — agreement boosts confidence "
                            f"from {conf_pct:.1f}% to {new_conf:.1f}%."
                        )
                        boosted_count += 1
                    else:
                        decision["reasoning"].append(
                            f"LLM suggests '{llm_val}' (disagrees). "
                            f"Keeping RAG value '{value}' because it has corpus citations."
                        )

        # ── Decision 3: Low confidence → Consult LLM ──
        else:
            decision["reasoning"].append(
                f"Confidence {conf_pct:.1f}% is below threshold ({LOW_CONFIDENCE_THRESHOLD*100}%). "
                f"Initiating LLM consultation for second opinion."
            )

            if has_llm:
                llm_val = _query_llm_for_param(
                    param, task, model, dataset, gemini_key, groq_key
                )
                llm_consulted_count += 1

                if llm_val is not None:
                    agrees = _values_agree(value, llm_val, param)

                    if agrees:
                        # Both agree on a low-confidence param → moderate boost
                        new_conf = min(conf_pct + AGREEMENT_BOOST * 100, 70)
                        enhanced_config[param] = {
                            **entry,
                            "confidence": new_conf / 100,
                            "confidence_pct": new_conf,
                            "agent_note": f"Low-conf param verified by LLM agreement → {new_conf:.0f}%",
                        }
                        decision["action"] = "VERIFIED_BY_LLM"
                        decision["result_confidence"] = round(new_conf, 1)
                        decision["reasoning"].append(
                            f"LLM agrees with RAG ('{llm_val}'). "
                            f"Boosting confidence from {conf_pct:.1f}% to {new_conf:.1f}%."
                        )
                        boosted_count += 1

                    elif value is None or conf_pct < 10:
                        # RAG has nothing, use LLM value with moderate confidence
                        enhanced_config[param] = {
                            **entry,
                            "value": llm_val,
                            "source": "llm_fallback",
                            "confidence": LLM_FALLBACK_CONFIDENCE,
                            "confidence_pct": LLM_FALLBACK_CONFIDENCE * 100,
                            "agent_note": f"RAG had no evidence; using LLM suggestion with {LLM_FALLBACK_CONFIDENCE*100}% confidence",
                        }
                        decision["action"] = "LLM_OVERRIDE"
                        decision["result_value"] = llm_val
                        decision["result_confidence"] = LLM_FALLBACK_CONFIDENCE * 100
                        decision["reasoning"].append(
                            f"RAG had no/minimal evidence (conf={conf_pct:.1f}%). "
                            f"Using LLM suggestion '{llm_val}' with {LLM_FALLBACK_CONFIDENCE*100}% confidence."
                        )
                        overridden_count += 1

                    else:
                        # They disagree — keep RAG (it has citations), flag for review
                        decision["action"] = "KEEP_RAG_FLAG_REVIEW"
                        decision["reasoning"].append(
                            f"LLM suggests '{llm_val}' but disagrees with RAG '{value}'. "
                            f"Keeping RAG value (has citations) but flagging for human review."
                        )
                        enhanced_config[param] = {
                            **entry,
                            "agent_note": f"⚠ Low confidence + LLM disagrees (suggests {llm_val}). Manual review recommended.",
                        }
                else:
                    decision["action"] = "ACCEPT_LOW_CONF"
                    decision["reasoning"].append(
                        "LLM query failed or returned no value. Keeping RAG result as-is."
                    )
            else:
                decision["action"] = "ACCEPT_LOW_CONF"
                decision["reasoning"].append(
                    "No LLM API key available for second opinion. "
                    "Keeping low-confidence RAG result."
                )

        if decision["action"] is None:
            decision["action"] = "ACCEPT"

        decisions.append(decision)

    return {
        "enhanced_config": enhanced_config,
        "agent_decisions": decisions,
        "agent_summary": {
            "total_params_reviewed": len(missing_params),
            "accepted": accepted_count,
            "llm_consulted": llm_consulted_count,
            "confidence_boosted": boosted_count,
            "llm_overridden": overridden_count,
            "has_llm_access": has_llm,
        },
    }


def _query_llm_for_param(
    param: str,
    task: str,
    model: str,
    dataset: str,
    gemini_key: str,
    groq_key: str,
) -> any:
    """Query LLM for a single parameter value."""
    try:
        from src.module8.llm_baseline import query_gemini, query_groq

        result = query_gemini(task, model, dataset, [param], gemini_key)
        if result.get("error") and groq_key:
            result = query_groq(task, model, dataset, [param], groq_key)

        return result.get("suggestions", {}).get(param)
    except Exception:
        return None


def _values_agree(rag_val, llm_val, param_name: str) -> bool:
    """Check if two values are in agreement."""
    if rag_val is None or llm_val is None:
        return False

    # For categorical params
    categorical = {"optimizer", "scheduler"}
    if param_name in categorical:
        return str(rag_val).lower() == str(llm_val).lower()

    # For numeric params: within 20% tolerance
    try:
        r = float(rag_val)
        l = float(llm_val)
        if r == 0 and l == 0:
            return True
        if r == 0:
            return abs(l) < 1e-6
        return abs(r - l) / abs(r) <= 0.2
    except (ValueError, TypeError):
        return str(rag_val).lower() == str(llm_val).lower()
