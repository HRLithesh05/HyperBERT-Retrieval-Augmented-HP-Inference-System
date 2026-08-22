"""Module 5 — Cross-Parameter Plausibility Checker.

Validates that the final inferred configuration doesn't contain
individually valid but collectively implausible parameter combinations.

Rules:
  1. High learning rate + small batch size → training instability
  2. Both warmup_steps and warmup_ratio set → mutual exclusivity
  3. Large sequence length + large batch → GPU OOM risk
  4. Very low LR + few epochs → underfitting risk
  5. SGD without weight decay → unusual for BERT fine-tuning
  6. High dropout + few epochs → insufficient training signal
"""

from __future__ import annotations


def check_cross_param_plausibility(config: dict) -> list[dict]:
    """Check cross-parameter plausibility of inferred configuration.

    Args:
        config: dict mapping param_name -> {value, source, confidence, ...}
                OR param_name -> raw_value.

    Returns:
        List of warning dicts with {rule, params, message, severity}.
    """
    warnings: list[dict] = []

    def _val(param: str):
        """Extract the raw value from a config entry."""
        entry = config.get(param)
        if entry is None:
            return None
        if isinstance(entry, dict):
            return entry.get("value")
        return entry

    lr = _val("learning_rate")
    bs = _val("batch_size")
    epochs = _val("epochs")
    seq_len = _val("max_seq_length")
    optimizer = _val("optimizer")
    wd = _val("weight_decay")
    warmup_steps = _val("warmup_steps")
    warmup_ratio = _val("warmup_ratio")
    dropout = _val("dropout")

    # ── Rule 1: High LR + Small Batch ───────────────────────────────
    if lr is not None and bs is not None:
        try:
            lr_f, bs_i = float(lr), int(bs)
            if lr_f >= 3e-5 and bs_i <= 8:
                warnings.append({
                    "rule": "high_lr_small_batch",
                    "params": ["learning_rate", "batch_size"],
                    "message": (
                        f"High learning rate ({lr_f:.0e}) with very small "
                        f"batch size ({bs_i}) may cause training instability. "
                        f"Consider reducing LR or increasing batch size."
                    ),
                    "severity": "warning",
                })
        except (ValueError, TypeError):
            pass

    # ── Rule 2: Both warmup_steps and warmup_ratio set ──────────────
    if warmup_steps is not None and warmup_ratio is not None:
        try:
            ws_i = int(warmup_steps)
            wr_f = float(warmup_ratio)
            if ws_i > 0 and wr_f > 0:
                warnings.append({
                    "rule": "warmup_conflict",
                    "params": ["warmup_steps", "warmup_ratio"],
                    "message": (
                        f"Both warmup_steps ({ws_i}) and warmup_ratio "
                        f"({wr_f}) are set. These are typically mutually "
                        f"exclusive — most frameworks use one or the other."
                    ),
                    "severity": "info",
                })
        except (ValueError, TypeError):
            pass

    # ── Rule 3: Long sequence + Large batch → OOM risk ──────────────
    if seq_len is not None and bs is not None:
        try:
            sl_i, bs_i = int(seq_len), int(bs)
            if sl_i >= 384 and bs_i >= 64:
                warnings.append({
                    "rule": "oom_risk",
                    "params": ["max_seq_length", "batch_size"],
                    "message": (
                        f"Large sequence length ({sl_i}) with large batch "
                        f"size ({bs_i}) may cause GPU out-of-memory on "
                        f"typical hardware (< 24GB). Consider gradient "
                        f"accumulation or reducing batch size."
                    ),
                    "severity": "warning",
                })
        except (ValueError, TypeError):
            pass

    # ── Rule 4: Very low LR + few epochs → underfitting ─────────────
    if lr is not None and epochs is not None:
        try:
            lr_f, ep_i = float(lr), int(epochs)
            if ep_i <= 2 and lr_f < 1e-5:
                warnings.append({
                    "rule": "underfit_risk",
                    "params": ["learning_rate", "epochs"],
                    "message": (
                        f"Very low learning rate ({lr_f:.0e}) with only "
                        f"{ep_i} epoch(s) — the model may underfit. "
                        f"Consider increasing LR or training for more epochs."
                    ),
                    "severity": "warning",
                })
        except (ValueError, TypeError):
            pass

    # ── Rule 5: SGD without weight decay ────────────────────────────
    if optimizer is not None and wd is not None:
        try:
            opt_str = str(optimizer).strip().upper()
            wd_f = float(wd)
            if opt_str == "SGD" and wd_f == 0:
                warnings.append({
                    "rule": "sgd_no_decay",
                    "params": ["optimizer", "weight_decay"],
                    "message": (
                        "SGD without weight decay is unusual for BERT "
                        "fine-tuning. Consider using AdamW or adding "
                        "weight decay for regularization."
                    ),
                    "severity": "info",
                })
        except (ValueError, TypeError):
            pass

    # ── Rule 6: High dropout + few epochs ───────────────────────────
    if dropout is not None and epochs is not None:
        try:
            do_f, ep_i = float(dropout), int(epochs)
            if do_f >= 0.3 and ep_i <= 2:
                warnings.append({
                    "rule": "high_dropout_few_epochs",
                    "params": ["dropout", "epochs"],
                    "message": (
                        f"High dropout ({do_f}) with only {ep_i} epoch(s) "
                        f"may prevent the model from learning effectively. "
                        f"Consider reducing dropout or training longer."
                    ),
                    "severity": "info",
                })
        except (ValueError, TypeError):
            pass

    return warnings
