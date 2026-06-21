"""Post-LLM validation for extracted hyperparameters.

Applies sanity-check rules so that obviously wrong values (e.g. a
learning rate of 500) are nullified before they enter the corpus and
pollute downstream inference in Module 3.
"""

import copy
from hp.hp_schema import HP_FIELDS


# ---------- range rules ----------

_RANGE_RULES: dict[str, dict] = {
    "learning_rate":     {"type": float, "min": 1e-7, "max": 1.0},
    "batch_size":        {"type": int,   "min": 1,    "max": 2048},
    "epochs":            {"type": int,   "min": 1,    "max": 200},
    "max_seq_length":    {"type": int,   "min": 8,    "max": 4096},
    "weight_decay":      {"type": float, "min": 0.0,  "max": 1.0},
    "warmup_steps":      {"type": int,   "min": 0,    "max": 100_000},
    "warmup_ratio":      {"type": float, "min": 0.0,  "max": 1.0},
    "gradient_clipping":  {"type": float, "min": 0.0,  "max": 100.0},
    "dropout":           {"type": float, "min": 0.0,  "max": 1.0},
    "seed":              {"type": int,   "min": 0,    "max": 2**31},
}

_VALID_OPTIMIZERS = {
    "adam", "adamw", "sgd", "adafactor", "adagrad", "lamb",
    "rmsprop", "radam", "nadam", "adadelta", "adamax",
}

_VALID_SCHEDULERS = {
    "linear", "cosine", "cosine_with_restarts", "polynomial",
    "constant", "constant_with_warmup", "linear_with_warmup",
    "warmup_linear", "inverse_sqrt", "reduce_on_plateau",
    "step", "multi_step", "exponential", "one_cycle",
}


def validate_hp_json(hp_json: dict) -> tuple[dict, list[str]]:
    """Validate and sanitise an extracted HP JSON dict.

    Returns a (cleaned_hp_json, warnings) tuple.  Invalid values are
    set to ``None`` and their parameter name is added to
    ``missing_params``.
    """
    hp_json = copy.deepcopy(hp_json)
    warnings: list[str] = []

    hps = hp_json.get("hyperparameters") or {}

    for field, rule in _RANGE_RULES.items():
        val = hps.get(field)
        if val is None:
            continue

        # coerce type
        try:
            val = rule["type"](val)
        except (TypeError, ValueError):
            warnings.append(f"{field}: could not coerce {val!r} to {rule['type'].__name__}")
            hps[field] = None
            continue

        if not (rule["min"] <= val <= rule["max"]):
            warnings.append(
                f"{field}: {val} outside valid range [{rule['min']}, {rule['max']}]"
            )
            hps[field] = None
            continue

        hps[field] = val

    # optimizer: must be a known name
    opt = hps.get("optimizer")
    if opt is not None:
        opt_lower = str(opt).lower().strip()
        if opt_lower not in _VALID_OPTIMIZERS:
            # be lenient — check if it *contains* a known name
            matched = [o for o in _VALID_OPTIMIZERS if o in opt_lower]
            if matched:
                hps["optimizer"] = matched[0]
            else:
                warnings.append(f"optimizer: unknown value {opt!r}")
                hps["optimizer"] = str(opt).strip()

    # scheduler: normalise
    sched = hps.get("scheduler")
    if sched is not None:
        sched_lower = str(sched).lower().strip().replace(" ", "_")
        if sched_lower not in _VALID_SCHEDULERS:
            matched = [s for s in _VALID_SCHEDULERS if s in sched_lower]
            if matched:
                hps["scheduler"] = matched[0]
            else:
                warnings.append(f"scheduler: unknown value {sched!r}")
                hps["scheduler"] = str(sched).strip()

    # rebuild missing_params
    missing = [f for f in HP_FIELDS if hps.get(f) is None]
    hp_json["hyperparameters"] = hps
    hp_json["missing_params"] = missing

    # clamp confidence
    try:
        conf = float(hp_json.get("confidence", 0))
        hp_json["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        hp_json["confidence"] = 0.0

    # ensure top-level strings
    for key in ("model", "task", "dataset"):
        val = hp_json.get(key)
        if val is not None:
            hp_json[key] = str(val).strip() or None

    return hp_json, warnings
