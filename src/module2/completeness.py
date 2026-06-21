"""Module 2 — Completeness Checker & R-Score.

Evaluates the extracted HP JSON from Module 1, computes an R-Score,
and decides whether Module 3 (inference) needs to run.
"""

from __future__ import annotations

import sys
import os

# Schema constants
HP_FIELDS = [
    "learning_rate", "batch_size", "epochs", "max_seq_length",
    "optimizer", "weight_decay", "warmup_steps", "warmup_ratio",
    "scheduler", "gradient_clipping", "dropout", "seed",
]

DEFAULT_WEIGHTS = {
    "learning_rate": 3.0,
    "batch_size": 3.0,
    "epochs": 2.0,
    "optimizer": 2.0,
    "max_seq_length": 1.0,
    "weight_decay": 1.0,
    "warmup_steps": 0.5,
    "warmup_ratio": 0.5,
    "scheduler": 1.0,
    "dropout": 0.5,
    "seed": 0.5,
    "gradient_clipping": 0.5,
}

# The critical HPs — if ANY of these are missing, inference is needed
CRITICAL_HPS = ["learning_rate", "batch_size", "epochs"]


def check_completeness(hp_json: dict, weights: dict | None = None) -> dict:
    """Check completeness of extracted HP JSON and decide next step.

    Args:
        hp_json: The HP JSON from Module 1 (pdf_analyzer output).
        weights: Optional custom weights for R-Score computation.

    Returns:
        dict with keys:
            rscore: float (0-1 weighted completeness)
            completeness_pct: float (0-100 simple percentage)
            missing_params: list[str] (HP names that are null)
            present_params: list[str] (HP names that have values)
            needs_inference: bool (True if Module 3 should run)
            critical_missing: list[str] (missing HPs from critical set)
            summary: str (human-readable summary)
    """
    w = weights or DEFAULT_WEIGHTS
    hps = hp_json.get("hyperparameters", {})

    present = []
    missing = []
    for field in HP_FIELDS:
        val = hps.get(field)
        if val is not None:
            present.append(field)
        else:
            missing.append(field)

    # R-Score: weighted completeness
    total_weight = sum(w.get(f, 1.0) for f in HP_FIELDS)
    present_weight = sum(w.get(f, 1.0) for f in present)
    rscore = round(present_weight / total_weight, 4) if total_weight > 0 else 0.0

    # Simple completeness percentage
    completeness_pct = round(100 * len(present) / len(HP_FIELDS), 1)

    # Critical HP check
    critical_missing = [f for f in CRITICAL_HPS if f in missing]

    # Decision: need inference if any critical HP is missing, or rscore < 0.5
    needs_inference = bool(critical_missing) or rscore < 0.5

    # Summary
    if not needs_inference:
        summary = (
            f"Paper has {len(present)}/{len(HP_FIELDS)} HPs "
            f"(R-Score={rscore:.2f}). All critical HPs present — "
            f"proceeding to validation."
        )
    else:
        summary = (
            f"Paper has {len(present)}/{len(HP_FIELDS)} HPs "
            f"(R-Score={rscore:.2f}). Missing critical: "
            f"{critical_missing or 'none'}, but R-Score below 0.5. "
            f"Module 3 will infer {len(missing)} missing HPs."
        )

    return {
        "rscore": rscore,
        "completeness_pct": completeness_pct,
        "missing_params": missing,
        "present_params": present,
        "needs_inference": needs_inference,
        "critical_missing": critical_missing,
        "summary": summary,
    }
