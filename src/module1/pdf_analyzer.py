"""Module 1 — PDF Input Analyzer.

Accepts a single PDF file (the user's paper), extracts text using
pdfplumber, and runs regex-based hyperparameter extraction to produce
the standardised hp_json consumed by the rest of the pipeline.

Public API:
    analyze_pdf(pdf_path: str) -> dict
"""

from __future__ import annotations

import re
from pathlib import Path

# =====================================================================
# HP schema — must stay in sync with module0/src/hp/hp_schema.py
# =====================================================================

HP_FIELDS = [
    "learning_rate", "batch_size", "epochs", "max_seq_length",
    "optimizer", "weight_decay", "warmup_steps", "warmup_ratio",
    "scheduler", "gradient_clipping", "dropout", "seed",
]


# =====================================================================
# PDF text extraction (pdfplumber — no PyMuPDF dependency)
# =====================================================================

def _extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF using pdfplumber."""
    import pdfplumber
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n".join(pages)


def _extract_title(text: str) -> str:
    """Heuristic: take the first non-empty line as the title."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and len(stripped) > 10:
            return stripped[:200]
    return "Untitled"


def _extract_abstract(text: str) -> str:
    """Heuristic: find the abstract section."""
    m = re.search(
        r"(?:^|\n)\s*abstract\s*[\n:.\-—]+\s*(.*?)(?=\n\s*(?:\d+[\s.]?\s*introduction|introduction|1\s|keywords|I\.\s))",
        text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()[:2000]
    # Fallback: take the first 500 chars after any "Abstract" heading
    m2 = re.search(r"abstract\s*[\n:.—\-]+\s*", text, re.IGNORECASE)
    if m2:
        return text[m2.end(): m2.end() + 1000].strip()
    return ""


# =====================================================================
# Regex patterns (identical to module0/src/hp/hp_extract.py)
# =====================================================================

_FLOAT = r"(\d+(?:\.\d+)?(?:\s*[×x*]?\s*10\s*[−\-]?\s*\d+|[eE][−\-+]?\d+)?)"
_INT = r"(\d+)"

LR_PATTERNS = [
    re.compile(r"learning\s+rate\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"lr\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"learning[\s_-]*rate\s*[=:]\s*" + _FLOAT, re.I),
    re.compile(r"(?:initial|peak|max|base)\s+learning\s+rate\s*(?:of|=|:)?\s*" + _FLOAT, re.I),
    re.compile(r"lr\s*=\s*" + _FLOAT, re.I),
]

BS_PATTERNS = [
    re.compile(r"batch\s*(?:_|\s)?size\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"mini[\s-]?batch(?:es)?\s+(?:of\s+)?" + _INT, re.I),
    re.compile(r"batch(?:es)?\s+of\s+" + _INT, re.I),
    re.compile(r"batch_size\s*=\s*" + _INT, re.I),
]

EPOCH_PATTERNS = [
    re.compile(r"(?:for|over|during|across)?\s*" + _INT + r"\s+epoch", re.I),
    re.compile(r"epoch(?:s)?\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"num[\s_-]?epoch(?:s)?\s*(?:=|:)\s*" + _INT, re.I),
    re.compile(r"train(?:ed|ing)?\s+(?:for\s+)?" + _INT + r"\s+epoch", re.I),
]

SEQ_LEN_PATTERNS = [
    re.compile(r"(?:max(?:imum)?[\s_-]?)(?:seq(?:uence)?[\s_-]?)(?:len(?:gth)?)\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"max[\s_-]?len(?:gth)?\s*(?:=|:)\s*" + _INT, re.I),
    re.compile(r"truncat(?:e|ed|ing)\s+(?:to\s+)?" + _INT + r"\s+tokens?", re.I),
    re.compile(r"(?:sequence|input)\s+length\s*(?:of|=|:)?\s*" + _INT, re.I),
    re.compile(r"max_seq_length\s*=\s*" + _INT, re.I),
]

OPT_PATTERNS = [
    re.compile(r"(?:use[ds]?|with|employ(?:ed)?|adopt(?:ed)?)\s+(?:the\s+)?(AdamW|Adam|SGD|Adafactor|LAMB|RAdam|Adadelta|Adagrad|RMSprop)\s+optimizer", re.I),
    re.compile(r"(AdamW|Adam|SGD|Adafactor|LAMB|RAdam|Adadelta)\s+(?:optimizer|optimiz)", re.I),
    re.compile(r"optimizer\s*(?:=|:|\s+is|\s+was)?\s*(AdamW|Adam|SGD|Adafactor|LAMB|RAdam)", re.I),
    re.compile(r"optimized?\s+(?:using|with|by)\s+(?:the\s+)?(AdamW|Adam|SGD|Adafactor|LAMB|RAdam)", re.I),
]

WD_PATTERNS = [
    re.compile(r"weight[\s_-]?decay\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"(?:L2|l2)\s+regulariz(?:ation|er)\s*(?:of|=|:)?\s*" + _FLOAT, re.I),
    re.compile(r"weight_decay\s*=\s*" + _FLOAT, re.I),
]

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

SCHED_PATTERNS = [
    re.compile(r"(linear|cosine|polynomial|constant|warmup_linear|inverse_sqrt|slanted.triangular)\s+(?:learning\s+rate\s+)?(?:decay|schedule|scheduler|annealing)", re.I),
    re.compile(r"(?:lr|learning\s+rate)\s+(?:decay|schedule|scheduler)\s*(?:=|:|\s+is|\s+was)?\s*(linear|cosine|polynomial|constant|warmup_linear|inverse_sqrt|slanted)", re.I),
    re.compile(r"scheduler\s*(?:=|:)\s*['\"]?(linear|cosine|polynomial|constant|warmup_linear|step|multi_step|exponential|one_cycle)", re.I),
]

GRAD_CLIP_PATTERNS = [
    re.compile(r"gradient[\s_-]?(?:clip(?:ping)?|norm)\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"clip(?:ped|ping)?\s+(?:the\s+)?gradient(?:s)?\s+(?:at|to)\s*" + _FLOAT, re.I),
    re.compile(r"max[\s_-]?grad[\s_-]?norm\s*(?:=|:)\s*" + _FLOAT, re.I),
]

DROPOUT_PATTERNS = [
    re.compile(r"dropout\s*(?:rate|prob(?:ability)?)?\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _FLOAT, re.I),
    re.compile(r"dropout\s*=\s*" + _FLOAT, re.I),
]

SEED_PATTERNS = [
    re.compile(r"(?:random\s+)?seed\s*(?:of|=|:|\s+is|\s+was|\s+set\s+to)?\s*" + _INT, re.I),
    re.compile(r"seed\s*=\s*" + _INT, re.I),
]

MODEL_PATTERNS = [
    re.compile(r"(bert[\s\-_]?(?:base|large)[\s\-_]?(?:un)?cased)", re.I),
    re.compile(r"((?:distil|albert|roberta|xlnet|electra|de|bio|clinical|sci|pub[mM]ed|legal|fin|indo|multi[lL]ingual|chinese|korean|japanese|ara|cam|span|tweet|code|hate|twitter|news)[\s\-_]?bert(?:[\s\-_]?(?:base|large|v\d+(?:\.\d+)?))?)", re.I),
    re.compile(r"(bert[\s\-_]?base[\s\-_]?(?:multilingual|chinese)[\s\-_]?(?:un)?cased)", re.I),
    re.compile(r"pre[\s\-]?trained\s+model\s*(?:=|:|\s+is)?\s*['\"]?([a-zA-Z][\w\-/]+bert[\w\-/]*)", re.I),
]

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

DATASET_PATTERNS = [
    re.compile(r"(?:on\s+(?:the\s+)?|dataset\s*(?:=|:)\s*['\"]?)(SST[\s\-]?2|MRPC|QQP|MNLI|QNLI|RTE|WNLI|CoLA|SQuAD|GLUE|SuperGLUE|CoNLL[\s\-]?\d+|IMDB|AG[\s_]?News|Yelp|DBpedia|Yahoo|TREC|SNLI|MultiNLI|SWAG|STS[\s\-]?B|RACE|OntoNotes)", re.I),
]


# =====================================================================
# Parsing helpers
# =====================================================================

def _parse_scientific(s: str) -> float | None:
    if not s:
        return None
    s = s.strip()
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
    try:
        return int(s.strip())
    except (ValueError, AttributeError):
        return None


def _first_match(text: str, patterns: list[re.Pattern]) -> str | None:
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


# =====================================================================
# Text preparation
# =====================================================================

_SECTION_RE = re.compile(
    r"^[#\d.]*\s*(experiment|setup|training|implementation|"
    r"hyperparameter|configuration|fine[- ]?tun|method|setting|"
    r"evaluation|result)",
    re.IGNORECASE | re.MULTILINE,
)


def _prepare_text(raw_text: str, max_chars: int = 20000) -> str:
    if not raw_text:
        return ""
    head = raw_text[:3000]
    rest = raw_text[3000:]
    relevant: list[str] = []
    for match in _SECTION_RE.finditer(rest):
        start = match.start()
        relevant.append(rest[start: start + 5000])
    combined = head + "\n\n".join(relevant)
    return combined[:max_chars]


# =====================================================================
# Core extraction — Step 1: Regex
# =====================================================================

def _extract_from_text(text: str) -> dict:
    """Extract all hyperparameters from paper text using regex."""
    hps: dict = {}

    lr_str = _first_match(text, LR_PATTERNS)
    hps["learning_rate"] = _parse_scientific(lr_str) if lr_str else None

    bs_str = _first_match(text, BS_PATTERNS)
    hps["batch_size"] = _parse_int(bs_str) if bs_str else None

    ep_str = _first_match(text, EPOCH_PATTERNS)
    hps["epochs"] = _parse_int(ep_str) if ep_str else None

    sl_str = _first_match(text, SEQ_LEN_PATTERNS)
    hps["max_seq_length"] = _parse_int(sl_str) if sl_str else None

    opt_str = _first_match(text, OPT_PATTERNS)
    hps["optimizer"] = opt_str.strip() if opt_str else None

    wd_str = _first_match(text, WD_PATTERNS)
    hps["weight_decay"] = _parse_scientific(wd_str) if wd_str else None

    ws_str = _first_match(text, WARMUP_STEPS_PATTERNS)
    hps["warmup_steps"] = _parse_int(ws_str) if ws_str else None

    wr_str = _first_match(text, WARMUP_RATIO_PATTERNS)
    hps["warmup_ratio"] = _parse_scientific(wr_str) if wr_str else None

    sched_str = _first_match(text, SCHED_PATTERNS)
    hps["scheduler"] = sched_str.strip().lower() if sched_str else None

    gc_str = _first_match(text, GRAD_CLIP_PATTERNS)
    hps["gradient_clipping"] = _parse_scientific(gc_str) if gc_str else None

    do_str = _first_match(text, DROPOUT_PATTERNS)
    hps["dropout"] = _parse_scientific(do_str) if do_str else None

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
# Step 2: LLM-based extraction via Ollama (Qwen3-4B)
# =====================================================================

def _extract_with_llm(text: str, regex_result: dict) -> dict:
    """Use Qwen3-4B via Ollama to extract HPs that regex missed.
    
    Only queries the LLM for parameters not found by regex.
    Returns the LLM extraction result dict.
    """
    try:
        from src.module8.ollama_client import (
            check_ollama_health,
            query_ollama_for_extraction,
        )
    except ImportError:
        return {"suggestions": {}, "error": "ollama_client not available"}

    # Check Ollama health first
    health = check_ollama_health()
    if not health["running"]:
        return {"suggestions": {}, "error": f"Ollama not running: {health['error']}"}

    # Query LLM for missing params
    llm_result = query_ollama_for_extraction(
        paper_text=text,
        existing_hps=regex_result.get("hyperparameters", {}),
    )
    return llm_result


# =====================================================================
# Step 3: Validation merge — cross-validate regex + LLM
# =====================================================================

def _validate_and_merge(regex_result: dict, llm_result: dict) -> dict:
    """Merge regex and LLM extraction results with validation.
    
    Priority: regex > LLM (regex is more reliable for standard formats).
    LLM values fill in gaps where regex found nothing.
    
    Adds extraction_sources tracking for transparency.
    """
    regex_hps = regex_result.get("hyperparameters", {})
    llm_suggestions = llm_result.get("suggestions", {})
    
    merged_hps = dict(regex_hps)  # Start with regex results
    extraction_sources = {}
    
    for param in HP_FIELDS:
        regex_val = regex_hps.get(param)
        llm_val = llm_suggestions.get(param)
        
        if regex_val is not None:
            # Regex found it — trust regex
            merged_hps[param] = regex_val
            extraction_sources[param] = "regex"
        elif llm_val is not None:
            # Only LLM found it — validate and use
            merged_hps[param] = llm_val
            extraction_sources[param] = "llm_extracted"
        else:
            # Neither found it — stays None
            merged_hps[param] = None
            extraction_sources[param] = "not_found"
    
    # Also merge task/model/dataset if regex missed them
    merged_model = regex_result.get("model")
    merged_task = regex_result.get("task")
    merged_dataset = regex_result.get("dataset")
    
    # Recalculate missing params and confidence
    missing = [f for f in HP_FIELDS if merged_hps.get(f) is None]
    found_count = len(HP_FIELDS) - len(missing)
    confidence = round(found_count / len(HP_FIELDS), 2) if HP_FIELDS else 0
    
    return {
        "model": merged_model,
        "task": merged_task,
        "dataset": merged_dataset,
        "hyperparameters": merged_hps,
        "missing_params": missing,
        "confidence": confidence,
        "extraction_sources": extraction_sources,
        "llm_extraction": {
            "source": llm_result.get("source", ""),
            "latency_ms": llm_result.get("latency_ms", 0),
            "params_found": list(llm_suggestions.keys()),
            "error": llm_result.get("error"),
        },
    }


# =====================================================================
# Public API — called by backend/app.py
# =====================================================================

def analyze_pdf(pdf_path: str) -> dict:
    """Extract text from a PDF and run the 3-step HP extraction pipeline.
    
    Pipeline:
        Step 1: Regex extraction (fast, reliable for standard formats)
        Step 2: Qwen LLM extraction via Ollama (for params regex missed)
        Step 3: Validation merge (cross-validate and combine both)

    Parameters
    ----------
    pdf_path : str
        Absolute or relative path to the uploaded PDF file.

    Returns
    -------
    dict with keys:
        text, title, abstract, model, task, dataset,
        hyperparameters, missing_params, confidence,
        extraction_sources, llm_extraction
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # 1. Extract raw text using pdfplumber
    raw_text = _extract_text(str(path))
    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Could not extract sufficient text from the PDF.")

    # 2. Extract title and abstract
    title = _extract_title(raw_text)
    abstract = _extract_abstract(raw_text)

    # 3. Prepare text (keep intro + relevant sections)
    prepared = _prepare_text(raw_text, max_chars=20000)

    # ── Step 1: Regex-based HP extraction ──
    regex_result = _extract_from_text(prepared)
    
    # ── Step 2: LLM extraction for missing params ──
    llm_result = {"suggestions": {}, "error": None}
    if regex_result["missing_params"]:
        try:
            print(f"  [M1-LLM] Regex found {len(HP_FIELDS) - len(regex_result['missing_params'])}/{len(HP_FIELDS)} params. "
                  f"Querying Qwen for {len(regex_result['missing_params'])} missing: {regex_result['missing_params']}")
            llm_result = _extract_with_llm(prepared, regex_result)
            if llm_result.get("error"):
                print(f"  [M1-LLM] LLM extraction failed: {llm_result['error']} — using regex-only results")
            else:
                found = list(llm_result.get("suggestions", {}).keys())
                print(f"  [M1-LLM] LLM found {len(found)} additional params: {found} "
                      f"(latency: {llm_result.get('latency_ms', 0)}ms)")
        except Exception as e:
            print(f"  [M1-LLM] LLM extraction error: {e} — using regex-only results")
            llm_result = {"suggestions": {}, "error": str(e)}
    else:
        print(f"  [M1-LLM] Regex found all {len(HP_FIELDS)} params — skipping LLM extraction")

    # ── Step 3: Validation merge ──
    result = _validate_and_merge(regex_result, llm_result)

    # 5. Merge into final output
    result["text"] = raw_text
    result["title"] = title
    result["abstract"] = abstract

    return result
