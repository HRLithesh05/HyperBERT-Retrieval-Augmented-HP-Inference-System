"""Module 3 — HP Aggregation.

Aggregates hyperparameter values from the evidence pool using
type-aware methods:
  - Categorical (optimizer, scheduler): Weighted mode
  - Continuous (learning_rate, weight_decay): Weighted median
  - Integer (batch_size, epochs): Weighted median, rounded
"""

from __future__ import annotations

import math
from collections import Counter

# Classify each HP by its aggregation type
CATEGORICAL_HPS = {"optimizer", "scheduler"}
INTEGER_HPS = {"batch_size", "epochs", "max_seq_length", "warmup_steps", "seed"}
CONTINUOUS_HPS = {
    "learning_rate", "weight_decay", "warmup_ratio",
    "gradient_clipping", "dropout",
}

# Common batch sizes for rounding
COMMON_BATCH_SIZES = [4, 8, 16, 32, 64, 128]
COMMON_SEQ_LENGTHS = [64, 128, 256, 384, 512]


def aggregate_evidence(
    evidence_pool,
    missing_params: list[str],
) -> dict:
    """Aggregate HP values from evidence pool for missing parameters.

    Args:
        evidence_pool: EvidencePool from strategy cascade.
        missing_params: List of HP parameter names to infer.

    Returns:
        dict mapping param_name -> {
            value, method, support_count, sources: list[str]
        }
    """
    results = {}

    for param in missing_params:
        evidence = evidence_pool.hp_evidence.get(param, [])
        if not evidence:
            results[param] = {
                "value": None,
                "method": "no_evidence",
                "support_count": 0,
                "sources": [],
            }
            continue

        values = [e[0] for e in evidence]
        similarities = [e[1] for e in evidence]
        rscores = [e[2] for e in evidence]
        titles = [e[3] for e in evidence]

        # Compute weights: similarity × (1 + rscore)
        weights = [s * (1 + r) for s, r in zip(similarities, rscores)]

        if param in CATEGORICAL_HPS:
            value, method = _weighted_mode(values, weights)
        elif param in INTEGER_HPS:
            value, method = _weighted_median_int(values, weights, param)
        else:
            value, method = _weighted_median(values, weights)

        results[param] = {
            "value": value,
            "method": method,
            "support_count": len(evidence),
            "sources": titles[:5],  # top 5 source citations
        }

    return results


def _weighted_mode(values: list, weights: list) -> tuple:
    """Weighted mode for categorical values."""
    weighted_counts: dict = {}
    for v, w in zip(values, weights):
        key = str(v).strip()
        weighted_counts[key] = weighted_counts.get(key, 0) + w

    if not weighted_counts:
        return None, "no_evidence"

    best = max(weighted_counts, key=weighted_counts.get)
    return best, "weighted_mode"


def _weighted_median(values: list, weights: list) -> tuple:
    """Weighted median for continuous values."""
    try:
        numeric = [(float(v), w) for v, w in zip(values, weights)]
    except (ValueError, TypeError):
        return None, "parse_error"

    if not numeric:
        return None, "no_evidence"

    # Sort by value
    numeric.sort(key=lambda x: x[0])
    total_weight = sum(w for _, w in numeric)
    cumulative = 0

    for val, w in numeric:
        cumulative += w
        if cumulative >= total_weight / 2:
            return round(val, 8), "weighted_median"

    return round(numeric[-1][0], 8), "weighted_median"


def _weighted_median_int(
    values: list, weights: list, param: str
) -> tuple:
    """Weighted median for integer values, rounded to common values."""
    val, method = _weighted_median(values, weights)
    if val is None:
        return None, method

    val = int(round(val))

    # Round to nearest common value for specific params
    if param == "batch_size":
        val = _nearest(val, COMMON_BATCH_SIZES)
    elif param == "max_seq_length":
        val = _nearest(val, COMMON_SEQ_LENGTHS)

    return val, "weighted_median_rounded"


def _nearest(val: int, options: list[int]) -> int:
    """Find the nearest value in a list of options."""
    return min(options, key=lambda x: abs(x - val))
