"""Module 5 — Evidence Contradiction Detector.

Detects contradictions and outliers in the evidence pool:
  - IQR-based outlier flagging for numeric HPs
  - Disagreement detection between papers
  - Confidence adjustment for high-spread parameters
"""

from __future__ import annotations

import math


def detect_contradictions(evidence_report: dict) -> dict:
    """Analyze evidence for contradictions and outliers.

    Args:
        evidence_report: From Module 3's evidence_report.

    Returns:
        dict with:
            contradictions: list of detected issues
            adjusted_confidence: dict of param -> adjusted confidence
            summary: str
    """
    contradictions: list[dict] = []
    adjusted_confidence: dict = {}

    per_param = evidence_report.get("per_param", {})

    for param, data in per_param.items():
        raw_values = data.get("raw_values", [])
        if len(raw_values) < 2:
            continue

        values = [rv["value"] for rv in raw_values]

        # Skip categorical
        if all(isinstance(v, str) for v in values):
            unique = set(v.lower().strip() for v in values)
            if len(unique) > 1:
                contradictions.append({
                    "param": param,
                    "type": "categorical_disagreement",
                    "severity": "warning",
                    "values": list(unique),
                    "message": (
                        f"{param}: Papers disagree — values: {unique}"
                    ),
                })
            continue

        # Numeric outlier detection via IQR
        try:
            nums = sorted(float(v) for v in values)
        except (ValueError, TypeError):
            continue

        if len(nums) < 3:
            continue

        q1 = _percentile(nums, 25)
        q3 = _percentile(nums, 75)
        iqr = q3 - q1

        if iqr == 0:
            continue  # all same value

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = [v for v in nums if v < lower or v > upper]

        if outliers:
            contradictions.append({
                "param": param,
                "type": "outlier",
                "severity": "warning",
                "outlier_values": outliers,
                "iqr_range": [round(lower, 6), round(upper, 6)],
                "message": (
                    f"{param}: {len(outliers)} outlier(s) detected "
                    f"outside IQR range [{lower:.6f}, {upper:.6f}]"
                ),
            })

        # Check for high spread (coefficient of variation)
        mean = sum(nums) / len(nums)
        if mean != 0:
            std = math.sqrt(sum((x - mean) ** 2 for x in nums) / len(nums))
            cv = std / abs(mean)

            if cv > 1.0:
                contradictions.append({
                    "param": param,
                    "type": "high_spread",
                    "severity": "info",
                    "cv": round(cv, 3),
                    "message": (
                        f"{param}: High spread (CV={cv:.2f}) — "
                        f"confidence may be reduced"
                    ),
                })
                # Reduce confidence for high-spread params
                orig_conf = data.get("confidence", {}).get("confidence", 0.5)
                penalty = min(0.3, cv * 0.15)
                adjusted_confidence[param] = round(
                    max(0.1, orig_conf - penalty), 3
                )

    summary = (
        f"Found {len(contradictions)} issue(s) across "
        f"{len(per_param)} parameters."
    )
    if not contradictions:
        summary = "No contradictions or outliers detected in evidence."

    return {
        "contradictions": contradictions,
        "adjusted_confidence": adjusted_confidence,
        "summary": summary,
    }


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute percentile from a sorted list."""
    n = len(sorted_values)
    k = (n - 1) * pct / 100
    f = int(k)
    c = f + 1
    if c >= n:
        return sorted_values[-1]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])
