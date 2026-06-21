"""Rule-based hyperparameter extraction (Module 0, Step 3).

Extracts BERT fine-tuning hyperparameters from paper text using regex
patterns.  No LLM or API calls needed — processes all papers locally
in seconds.

Academic papers report HPs in predictable formats:
  - "learning rate of 2e-5"
  - "batch size of 32"
  - "trained for 3 epochs"
  - "AdamW optimizer with weight decay 0.01"

This engine captures those patterns with high precision.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from hp.hp_schema import HP_FIELDS
from hp.hp_validate import validate_hp_json


# =====================================================================
# Regex pattern definitions for each hyperparameter
# =====================================================================

# Matches floats like 2e-5, 3e-4, 5E-5, 0.00002, 1e-5, 2×10−5
_FLOAT = r"(\d+(?:\.\d+)?(?:\s*[×x*]?\s*10\s*[−\-]?\s*\d+|[eE][−\-+]?\d+)?)"
_INT = r"(\d+)"

# Learning rate patterns
LR_PATTERNS = [
    re.compile(r"learning\s+rate\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"lr\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"learning[\s_-]*rate\s*[=:]\s*" + _FLOAT, re.I),
    re.compile(r"(?:initial|peak|max|base)\s+learning\s+rate\s*(?:of|=|:)?\s*" + _FLOAT, re.I),
    re.compile(r"lr\s*=\s*" + _FLOAT, re.I),
]

# Batch size patterns
BS_PATTERNS = [
    re.compile(r"batch\s*(?:_|\s)?size\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"mini[\s-]?batch(?:es)?\s+(?:of\s+)?" + _INT, re.I),
    re.compile(r"batch(?:es)?\s+of\s+" + _INT, re.I),
    re.compile(r"batch_size\s*=\s*" + _INT, re.I),
]

# Epochs patterns
EPOCH_PATTERNS = [
    re.compile(r"(?:for|over|during|across)?\s*" + _INT + r"\s+epoch", re.I),
    re.compile(r"epoch(?:s)?\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"num[\s_-]?epoch(?:s)?\s*(?:=|:)\s*" + _INT, re.I),
    re.compile(r"train(?:ed|ing)?\s+(?:for\s+)?" + _INT + r"\s+epoch", re.I),
]

# Max sequence length patterns
SEQ_LEN_PATTERNS = [
    re.compile(r"(?:max(?:imum)?[\s_-]?)(?:seq(?:uence)?[\s_-]?)(?:len(?:gth)?)\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"max[\s_-]?len(?:gth)?\s*(?:=|:)\s*" + _INT, re.I),
    re.compile(r"truncat(?:e|ed|ing)\s+(?:to\s+)?" + _INT + r"\s+tokens?", re.I),
    re.compile(r"(?:sequence|input)\s+length\s*(?:of|=|:)?\s*" + _INT, re.I),
    re.compile(r"max_seq_length\s*=\s*" + _INT, re.I),
]

# Optimizer patterns
OPT_PATTERNS = [
    re.compile(r"(?:use[ds]?|with|employ(?:ed)?|adopt(?:ed)?)\s+(?:the\s+)?(AdamW|Adam|SGD|Adafactor|LAMB|RAdam|Adadelta|Adagrad|RMSprop)\s+optimizer", re.I),
    re.compile(r"(AdamW|Adam|SGD|Adafactor|LAMB|RAdam|Adadelta)\s+(?:optimizer|optimiz)", re.I),
    re.compile(r"optimizer\s*(?:=|:|\s+is|\s+was)?\s*(AdamW|Adam|SGD|Adafactor|LAMB|RAdam)", re.I),
    re.compile(r"optimized?\s+(?:using|with|by)\s+(?:the\s+)?(AdamW|Adam|SGD|Adafactor|LAMB|RAdam)", re.I),
]

# Weight decay patterns
WD_PATTERNS = [
    re.compile(r"weight[\s_-]?decay\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"(?:L2|l2)\s+regulariz(?:ation|er)\s*(?:of|=|:)?\s*" + _FLOAT, re.I),
    re.compile(r"weight_decay\s*=\s*" + _FLOAT, re.I),
]

# Warmup patterns
WARMUP_STEPS_PATTERNS = [
    re.compile(r"warmup[\s_-]?step(?:s)?\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"warm[\s_-]?up\s+(?:for\s+)?" + _INT + r"\s+step", re.I),
    re.compile(r"num_warmup_steps\s*=\s*" + _INT, re.I),
]

WARMUP_RATIO_PATTERNS = [
    re.compile(r"warmup[\s_-]?(?:ratio|proportion|fraction|percentage)\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"warmup\s*=\s*" + _FLOAT, re.I),
    re.compile(r"warm[\s_-]?up\s+(?:of\s+)?" + _FLOAT + r"\s*(?:%|percent)", re.I),
]

# Scheduler / LR schedule patterns
SCHED_PATTERNS = [
    re.compile(r"(linear|cosine|polynomial|constant|warmup_linear|inverse_sqrt|slanted.triangular)\s+(?:learning\s+rate\s+)?(?:decay|schedule|scheduler|annealing)", re.I),
    re.compile(r"(?:lr|learning\s+rate)\s+(?:decay|schedule|scheduler)\s*(?:=|:|\s+is|\s+was)?\s*(linear|cosine|polynomial|constant|warmup_linear|inverse_sqrt|slanted)", re.I),
    re.compile(r"scheduler\s*(?:=|:)\s*['\"]?(linear|cosine|polynomial|constant|warmup_linear|step|multi_step|exponential|one_cycle)", re.I),
]

# Gradient clipping patterns
GRAD_CLIP_PATTERNS = [
    re.compile(r"gradient[\s_-]?(?:clip(?:ping)?|norm)\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"clip(?:ped|ping)?\s+(?:the\s+)?gradient(?:s)?\s+(?:at|to)\s*" + _FLOAT, re.I),
    re.compile(r"max[\s_-]?grad[\s_-]?norm\s*(?:=|:)\s*" + _FLOAT, re.I),
]

# Dropout patterns
DROPOUT_PATTERNS = [
    re.compile(r"dropout\s*(?:rate|prob(?:ability)?)?\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"dropout\s*=\s*" + _FLOAT, re.I),
]

# Seed patterns
SEED_PATTERNS = [
    re.compile(r"(?:random\s+)?seed\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"seed\s*=\s*" + _INT, re.I),
]

# Model name patterns
MODEL_PATTERNS = [
    re.compile(r"(bert[\s\-_]?(?:base|large)[\s\-_]?(?:un)?cased)", re.I),
    re.compile(r"((?:distil|albert|roberta|xlnet|electra|de|bio|clinical|sci|pub[Mm]ed|legal|fin|indo|multi[lL]ingual|chinese|korean|japanese|ara|cam|span|tweet|code|hate|twitter|news)[\s\-_]?bert(?:[\s\-_]?(?:base|large|v\d+(?:\.\d+)?))?)", re.I),
    re.compile(r"(bert[\s\-_]?base[\s\-_]?(?:multilingual|chinese)[\s\-_]?(?:un)?cased)", re.I),
    re.compile(r"pre[\s\-]?trained\s+model\s*(?:=|:|\s+is)?\s*['\"]?([a-zA-Z][\w\-/]+bert[\w\-/]*)", re.I),
]

# Task patterns
TASK_PATTERNS_MAP = {
    "text_classification": re.compile(r"text\s+classification|document\s+classification|sentence\s+classification", re.I),
    "sentiment_analysis": re.compile(r"sentiment\s+(?:analysis|classification|detection)", re.I),
    "ner": re.compile(r"named\s+entity\s+recognition|NER|sequence\s+(?:label(?:l)?ing|tagging)", re.I),
    "question_answering": re.compile(r"question\s+answering|QA|reading\s+comprehension|extractive\s+QA", re.I),
    "nli": re.compile(r"natural\s+language\s+inference|NLI|textual\s+entailment", re.I),
    "semantic_textual_similarity": re.compile(r"semantic\s+textual\s+similarity|STS|sentence\s+similarity", re.I),
    "relation_extraction": re.compile(r"relation\s+extraction|RE\b", re.I),
    "token_classification": re.compile(r"token\s+classification|POS\s+tagging|part[\s\-]of[\s\-]speech", re.I),
    "summarization": re.compile(r"summariz(?:ation|ing)|abstractive|extractive\s+summar", re.I),
}

# Dataset patterns
DATASET_PATTERNS = [
    re.compile(r"(?:on\s+(?:the\s+)?|dataset\s*(?:=|:)\s*['\"]?)(SST[\s\-]?2|MRPC|QQP|MNLI|QNLI|RTE|WNLI|CoLA|SQuAD|GLUE|SuperGLUE|CoNLL[\s\-]?\d+|IMDB|AG[\s_]?News|Yelp|DBpedia|Yahoo|TREC|SNLI|MultiNLI|SWAG|STS[\s\-]?B|RACE|OntoNotes)", re.I),
]


# =====================================================================
# Extraction helpers
# =====================================================================

def _parse_scientific(s: str) -> float | None:
    """Parse a number string that may use scientific notation or × notation."""
    if not s:
        return None
    s = s.strip()
    # Handle 2×10−5, 2x10-5 etc.
    m = re.match(r"(\d+(?:\.\d+)?)\s*[×x*]\s*10\s*[−\-]?\s*(\d+)", s)
    if m:
        base = float(m.group(1))
        exp = -int(m.group(2))
        return base * (10 ** exp)
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(s: str) -> int | None:
    """Parse an integer string."""
    try:
        return int(s.strip())
    except (ValueError, AttributeError):
        return None


def _first_match(text: str, patterns: list[re.Pattern]) -> str | None:
    """Return the first capture group from the first matching pattern."""
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


def _extract_from_text(text: str) -> dict:
    """Extract all hyperparameters from paper text using regex."""
    hps: dict = {}

    # Learning rate
    lr_str = _first_match(text, LR_PATTERNS)
    hps["learning_rate"] = _parse_scientific(lr_str) if lr_str else None

    # Batch size
    bs_str = _first_match(text, BS_PATTERNS)
    hps["batch_size"] = _parse_int(bs_str) if bs_str else None

    # Epochs
    ep_str = _first_match(text, EPOCH_PATTERNS)
    hps["epochs"] = _parse_int(ep_str) if ep_str else None

    # Max sequence length
    sl_str = _first_match(text, SEQ_LEN_PATTERNS)
    hps["max_seq_length"] = _parse_int(sl_str) if sl_str else None

    # Optimizer
    opt_str = _first_match(text, OPT_PATTERNS)
    hps["optimizer"] = opt_str.strip() if opt_str else None

    # Weight decay
    wd_str = _first_match(text, WD_PATTERNS)
    hps["weight_decay"] = _parse_scientific(wd_str) if wd_str else None

    # Warmup steps
    ws_str = _first_match(text, WARMUP_STEPS_PATTERNS)
    hps["warmup_steps"] = _parse_int(ws_str) if ws_str else None

    # Warmup ratio
    wr_str = _first_match(text, WARMUP_RATIO_PATTERNS)
    hps["warmup_ratio"] = _parse_scientific(wr_str) if wr_str else None

    # Scheduler
    sched_str = _first_match(text, SCHED_PATTERNS)
    hps["scheduler"] = sched_str.strip().lower() if sched_str else None

    # Gradient clipping
    gc_str = _first_match(text, GRAD_CLIP_PATTERNS)
    hps["gradient_clipping"] = _parse_scientific(gc_str) if gc_str else None

    # Dropout
    do_str = _first_match(text, DROPOUT_PATTERNS)
    hps["dropout"] = _parse_scientific(do_str) if do_str else None

    # Seed
    seed_str = _first_match(text, SEED_PATTERNS)
    hps["seed"] = _parse_int(seed_str) if seed_str else None

    # Model name
    model_str = _first_match(text, MODEL_PATTERNS)
    model = model_str.strip() if model_str else None

    # Task
    task = None
    for task_name, pat in TASK_PATTERNS_MAP.items():
        if pat.search(text):
            task = task_name
            break

    # Dataset
    ds_str = _first_match(text, DATASET_PATTERNS)
    dataset = ds_str.strip() if ds_str else None

    # Missing params
    missing = [f for f in HP_FIELDS if hps.get(f) is None]

    # Confidence = fraction of params found
    found_count = len(HP_FIELDS) - len(missing)
    confidence = round(found_count / len(HP_FIELDS), 2) if HP_FIELDS else 0

    return {
        "model": model,
        "task": task,
        "dataset": dataset,
        "hyperparameters": hps,
        "missing_params": missing,
        "confidence": confidence,
    }


# =====================================================================
# Text preparation (reused from previous version)
# =====================================================================

_SECTION_RE = re.compile(
    r"^[#\d.]*\s*(experiment|setup|training|implementation|"
    r"hyperparameter|configuration|fine[- ]?tun|method|setting|"
    r"evaluation|result)",
    re.IGNORECASE | re.MULTILINE,
)


def _prepare_text(raw_text: str, max_chars: int) -> str:
    """Build extraction-friendly text by keeping intro + relevant sections."""
    if not raw_text:
        return ""

    head = raw_text[:3000]
    rest = raw_text[3000:]

    relevant_chunks: list[str] = []
    for match in _SECTION_RE.finditer(rest):
        start = match.start()
        chunk = rest[start : start + 5000]
        relevant_chunks.append(chunk)

    combined = head + "\n\n".join(relevant_chunks)
    return combined[:max_chars]


# =====================================================================
# Main extraction function
# =====================================================================

def extract_hyperparams(store, config: dict, paths: dict) -> None:
    """Run regex-based HP extraction on all clean papers.

    Results are stored in the ``papers_clean`` collection under the
    ``hp_json`` field.  Papers that already have ``hp_json`` are
    skipped (resume-safe).  No API calls — runs entirely locally.
    """
    hp_cfg = config.get("hp_extract", {})
    max_text_chars = int(hp_cfg.get("max_text_chars", 20000))

    clean_name = config["mongodb"].get("clean_collection", "papers_clean")
    clean_col = store.get_collection(clean_name)

    # get all clean papers that haven't been processed yet
    query = {"hp_json": {"$exists": False}}
    total = clean_col.count_documents(query)
    if total == 0:
        print("All clean papers already have hp_json — nothing to do.")
        return

    print(f"Extracting HPs from {total} papers using regex engine ...")

    reports_dir = Path(paths["reports_dir"]).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "total": total,
        "success": 0,
        "skipped": 0,
        "validation_warnings": 0,
        "params_found": {f: 0 for f in HP_FIELDS},
    }

    for doc in tqdm(clean_col.find(query, batch_size=50), total=total, desc="HP extract"):
        # load raw text
        text_path = doc.get("raw_text_path")
        if not text_path:
            stats["skipped"] += 1
            continue

        try:
            raw_text = Path(text_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            stats["skipped"] += 1
            continue

        # also include title + abstract for better extraction
        title = doc.get("title", "")
        abstract = doc.get("abstract", "")
        full_text = f"{title}\n{abstract}\n{raw_text}"

        paper_text = _prepare_text(full_text, max_text_chars)
        if len(paper_text) < 100:
            stats["skipped"] += 1
            continue

        # Extract
        hp_json = _extract_from_text(paper_text)

        # Validate
        hp_json, warnings = validate_hp_json(hp_json)
        if warnings:
            stats["validation_warnings"] += len(warnings)

        # Track per-param coverage
        hps = hp_json.get("hyperparameters", {})
        for field in HP_FIELDS:
            if hps.get(field) is not None:
                stats["params_found"][field] += 1

        # Store
        update = {
            "hp_json": hp_json,
            "hp_extracted_at": datetime.now(timezone.utc).isoformat(),
            "hp_method": "regex",
        }
        if warnings:
            update["hp_validation_warnings"] = warnings

        clean_col.update_one({"_id": doc["_id"]}, {"$set": update})
        stats["success"] += 1

    # ---- Report ----
    report = {
        "summary": {
            "total": stats["total"],
            "success": stats["success"],
            "skipped": stats["skipped"],
            "validation_warnings": stats["validation_warnings"],
            "method": "regex",
        },
        "hp_coverage": {
            param: {
                "count": count,
                "pct": round(100 * count / stats["success"], 1) if stats["success"] else 0,
            }
            for param, count in stats["params_found"].items()
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    report_path = reports_dir / "hp_extract_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nDone: {stats['success']} success, {stats['skipped']} skipped")
    print(f"HP coverage (out of {stats['success']} papers):")
    for param, count in sorted(stats["params_found"].items(), key=lambda x: -x[1]):
        pct = 100 * count / stats["success"] if stats["success"] else 0
        print(f"  {param}: {count}/{stats['success']} ({pct:.1f}%)")
    print(f"\nReport: {report_path}")
