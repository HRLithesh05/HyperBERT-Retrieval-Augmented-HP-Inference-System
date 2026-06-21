"""Module 6 — Self-Critique Validator.

Validates the final HP config against BERT domain rules:
  1. LR range:      1e-6 ≤ LR ≤ 1e-3
  2. Batch size:     power-of-2, 4 ≤ BS ≤ 128
  3. Epochs:         1 ≤ E ≤ 20
  4. Max seq length: 32 ≤ MSL ≤ 1024
  5. Weight decay:   0 ≤ WD ≤ 0.3

Auto-corrects errors where possible.
"""

from __future__ import annotations

import math


VALIDATION_RULES = {
    "learning_rate": {
        "min": 1e-6,
        "max": 1e-3,
        "default": 2e-5,
        "type": "float",
    },
    "batch_size": {
        "min": 4,
        "max": 128,
        "default": 32,
        "type": "int",
        "power_of_2": True,
    },
    "epochs": {
        "min": 1,
        "max": 20,
        "default": 3,
        "type": "int",
    },
    "max_seq_length": {
        "min": 32,
        "max": 1024,
        "default": 128,
        "type": "int",
    },
    "weight_decay": {
        "min": 0.0,
        "max": 0.3,
        "default": 0.01,
        "type": "float",
    },
    "dropout": {
        "min": 0.0,
        "max": 0.9,
        "default": 0.1,
        "type": "float",
    },
    "warmup_ratio": {
        "min": 0.0,
        "max": 0.5,
        "default": 0.06,
        "type": "float",
    },
    "gradient_clipping": {
        "min": 0.1,
        "max": 10.0,
        "default": 1.0,
        "type": "float",
    },
}


def validate_config(config: dict) -> dict:
    """Validate config against BERT domain rules.

    Args:
        config: Dict from Module 4's constraint-adjusted config.
                Keys are param names, values are dicts with 'value' key.

    Returns:
        dict with:
            verdict: 'PASS', 'WARN', or 'ERROR'
            errors: list of errors
            warnings: list of warnings
            corrections: list of auto-corrections applied
            validated_config: The corrected config
    """
    errors: list[dict] = []
    warnings: list[dict] = []
    corrections: list[dict] = []

    for param, rules in VALIDATION_RULES.items():
        entry = config.get(param, {})
        value = entry.get("value") if isinstance(entry, dict) else entry

        if value is None:
            continue

        try:
            if rules["type"] == "int":
                value = int(round(float(value)))
            else:
                value = float(value)
        except (ValueError, TypeError):
            errors.append({
                "param": param,
                "verdict": "ERROR",
                "message": f"{param}: Cannot parse value '{value}' as {rules['type']}",
            })
            continue

        # Range check
        if value < rules["min"]:
            old_val = value
            value = rules["default"]
            corrections.append({
                "param": param,
                "old_value": old_val,
                "new_value": value,
                "rule": "range_check",
                "message": f"{param}: {old_val} < min {rules['min']} → corrected to {value}",
            })
            if isinstance(config[param], dict):
                config[param]["value"] = value
                config[param]["source"] = "auto_corrected"

        elif value > rules["max"]:
            old_val = value
            value = rules["default"]
            corrections.append({
                "param": param,
                "old_value": old_val,
                "new_value": value,
                "rule": "range_check",
                "message": f"{param}: {old_val} > max {rules['max']} → corrected to {value}",
            })
            if isinstance(config[param], dict):
                config[param]["value"] = value
                config[param]["source"] = "auto_corrected"

        # Power-of-2 check for batch_size
        if rules.get("power_of_2") and value > 0:
            if not _is_power_of_2(int(value)):
                old_val = int(value)
                value = _nearest_power_of_2(old_val)
                warnings.append({
                    "param": param,
                    "verdict": "WARN",
                    "message": f"{param}: {old_val} is not a power of 2 → adjusted to {value}",
                })
                if isinstance(config[param], dict):
                    config[param]["value"] = value

    # Overall verdict
    if errors:
        verdict = "ERROR"
    elif corrections:
        verdict = "WARN"
    elif warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
        "corrections": corrections,
        "validated_config": config,
    }


def _is_power_of_2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _nearest_power_of_2(n: int) -> int:
    if n <= 0:
        return 1
    lower = 2 ** int(math.log2(n))
    upper = lower * 2
    return lower if (n - lower) <= (upper - n) else upper
