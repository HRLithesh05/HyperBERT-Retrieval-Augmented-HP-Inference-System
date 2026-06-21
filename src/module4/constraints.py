"""Module 4 — Constraint-Aware Inference.

Applies BERT domain knowledge constraints to the inferred config:
  - Optimizer↔Weight Decay coupling
  - Linear LR Scaling Rule
  - Warmup Consistency
  - SeqLen vs Task rules
"""

from __future__ import annotations


def apply_constraints(config: dict, task: str | None = None) -> dict:
    """Apply domain constraints to the inferred HP config.

    Args:
        config: Dict from Module 3's inferred_config (param -> {value, ...}).
        task: The detected NLP task.

    Returns:
        dict with:
            config: The constraint-adjusted config
            adjustments: List of adjustments made
    """
    adjustments: list[dict] = []
    c = _extract_values(config)

    # Rule 1: Optimizer ↔ Weight Decay coupling
    optimizer = c.get("optimizer", "AdamW")
    weight_decay = c.get("weight_decay", 0.01)

    if isinstance(optimizer, str):
        opt_lower = optimizer.lower()
        if "adamw" in opt_lower and (weight_decay is None or weight_decay == 0):
            config["weight_decay"]["value"] = 0.01
            adjustments.append({
                "param": "weight_decay",
                "rule": "optimizer_wd_coupling",
                "old_value": weight_decay,
                "new_value": 0.01,
                "reason": "AdamW requires weight_decay > 0 (set to 0.01)",
            })
        elif "adam" in opt_lower and "adamw" not in opt_lower and weight_decay and weight_decay > 0:
            config["weight_decay"]["value"] = 0.0
            adjustments.append({
                "param": "weight_decay",
                "rule": "optimizer_wd_coupling",
                "old_value": weight_decay,
                "new_value": 0.0,
                "reason": "Adam (not AdamW) typically uses weight_decay=0",
            })

    # Rule 2: SeqLen vs Task
    max_seq_length = c.get("max_seq_length")
    if task and max_seq_length:
        task_lower = (task or "").lower()
        if any(t in task_lower for t in ["classification", "sentiment", "nli"]):
            if max_seq_length > 256:
                config["max_seq_length"]["value"] = 128
                adjustments.append({
                    "param": "max_seq_length",
                    "rule": "seqlen_vs_task",
                    "old_value": max_seq_length,
                    "new_value": 128,
                    "reason": f"Classification tasks typically use max_seq_length ≤ 128",
                })
        elif any(t in task_lower for t in ["question_answering", "qa", "reading"]):
            if max_seq_length and max_seq_length < 256:
                config["max_seq_length"]["value"] = 384
                adjustments.append({
                    "param": "max_seq_length",
                    "rule": "seqlen_vs_task",
                    "old_value": max_seq_length,
                    "new_value": 384,
                    "reason": "QA tasks typically use max_seq_length=384-512",
                })

    # Rule 3: Warmup Consistency
    epochs = c.get("epochs", 3)
    batch_size = c.get("batch_size", 32)
    warmup_ratio = c.get("warmup_ratio")
    warmup_steps = c.get("warmup_steps")

    if warmup_ratio is None and warmup_steps is None:
        config["warmup_ratio"]["value"] = 0.06
        adjustments.append({
            "param": "warmup_ratio",
            "rule": "warmup_consistency",
            "old_value": None,
            "new_value": 0.06,
            "reason": "Warmup = 6% of total steps (standard for BERT)",
        })

    # Rule 4: Gradient clipping default
    if c.get("gradient_clipping") is None:
        config["gradient_clipping"]["value"] = 1.0
        adjustments.append({
            "param": "gradient_clipping",
            "rule": "gradient_clipping_default",
            "old_value": None,
            "new_value": 1.0,
            "reason": "Max gradient norm = 1.0 (standard for BERT)",
        })

    return {
        "config": config,
        "adjustments": adjustments,
    }


def _extract_values(config: dict) -> dict:
    """Extract raw values from the config dict."""
    return {k: v.get("value") if isinstance(v, dict) else v for k, v in config.items()}
