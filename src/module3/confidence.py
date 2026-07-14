"""Module 3 — Confidence Calibration.

Computes per-parameter confidence scores based on:
  - Mean similarity of supporting papers
  - Variance/spread of values (lower = more confident)
  - Number of supporting papers
"""

from __future__ import annotations

import math

# Minimum confidence threshold — below this we fall back to BERT defaults.
# Set low (0.15) so corpus-inferred values are preferred over generic defaults
# even with limited evidence. The UI shows the confidence % so users can judge.
CONFIDENCE_THRESHOLD = 0.15


def calibrate_confidence(
    param: str,
    evidence: list[tuple],  # (value, similarity, rscore, title)
) -> dict:
    """Compute calibrated confidence for a single HP parameter.

    Returns:
        dict with: confidence (float 0-1), level (str), details (dict)
    """
    if not evidence:
        return {
            "confidence": 0.0,
            "level": "none",
            "details": {"reason": "no evidence found"},
        }

    values = [e[0] for e in evidence]
    similarities = [e[1] for e in evidence]
    rscores = [e[2] for e in evidence]
    n = len(evidence)

    # Factor 1: Mean similarity (0-1)
    mean_sim = sum(similarities) / n

    # Factor 2: Support count factor (logarithmic, capped at 1.0)
    support_factor = min(1.0, math.log2(n + 1) / math.log2(10))

    # Factor 3: Value agreement (1 - normalized variance)
    agreement = _compute_agreement(values, param)

    # Composite confidence
    confidence = (
        0.4 * mean_sim +
        0.3 * support_factor +
        0.3 * agreement
    )
    confidence = round(max(0.0, min(1.0, confidence)), 3)

    # Classification
    if confidence >= 0.7:
        level = "high"
    elif confidence >= CONFIDENCE_THRESHOLD:
        level = "medium"
    else:
        level = "low"

    return {
        "confidence": confidence,
        "level": level,
        "details": {
            "mean_similarity": round(mean_sim, 3),
            "support_count": n,
            "support_factor": round(support_factor, 3),
            "agreement": round(agreement, 3),
        },
    }


def _compute_agreement(values: list, param: str) -> float:
    """Compute agreement score (0-1) for a list of values.

    For categorical: fraction of majority vote.
    For numeric: 1 - normalized coefficient of variation.
    """
    if not values:
        return 0.0

    # Check if categorical
    if all(isinstance(v, str) for v in values):
        from collections import Counter
        counts = Counter(v.lower().strip() for v in values)
        majority = counts.most_common(1)[0][1]
        return majority / len(values)

    # Numeric agreement
    try:
        nums = [float(v) for v in values]
    except (ValueError, TypeError):
        return 0.5

    if len(nums) < 2:
        return 0.8  # single value = decent confidence

    mean = sum(nums) / len(nums)
    if mean == 0:
        return 1.0 if all(n == 0 for n in nums) else 0.5

    variance = sum((x - mean) ** 2 for x in nums) / len(nums)
    std = math.sqrt(variance)
    cv = std / abs(mean)  # coefficient of variation

    # Map CV to agreement: CV=0 → 1.0, CV≥2 → 0.0
    agreement = max(0.0, 1.0 - cv / 2.0)
    return agreement
