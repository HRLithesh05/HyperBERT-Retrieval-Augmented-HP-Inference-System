import json
import re
from datetime import datetime
from pathlib import Path


MODEL_PATTERNS = [
    r"\bbert\b",
    r"\bbert[- ]base\b",
    r"\bbert[- ]large\b",
    r"\b[a-z0-9-]*bert\b",
]

FINETUNE_PATTERNS = [
    r"\bfine[- ]tuning\b",
    r"\bfine[- ]tune\b",
    r"\bfine[- ]tuned\b",
    r"\bfinetune\b",
    r"\bfinetuned\b",
    r"\btransfer learning\b",
    r"\btask[- ]specific\b",
]

TASK_PATTERNS = [
    r"\bclassification\b",
    r"\btext classification\b",
    r"\bsentiment\b",
    r"\bner\b",
    r"\bnamed entity recognition\b",
    r"\bsequence labeling\b",
    r"\bsequence tagging\b",
    r"\bsequence classification\b",
    r"\bquestion answering\b",
    r"\bqa\b",
    r"\bnli\b",
    r"\bnatural language inference\b",
    r"\brelation extraction\b",
    r"\bparaphrase\b",
    r"\bsemantic textual similarity\b",
    r"\bdetection\b",
]

HP_PATTERNS = [
    r"\blearning rate\b",
    r"\bbatch size\b",
    r"\bepoch\b",
    r"\boptimizer\b",
    r"\badamw\b",
    r"\bweight decay\b",
    r"\bwarmup\b",
    r"\bscheduler\b",
    r"\bsequence length\b",
]

EXCLUDE_PATTERNS = [
    r"\bsurvey\b",
    r"\bsystematic review\b",
    r"\bliterature review\b",
    r"\broadmap\b",
    r"\boverview\b",
    r"\btutorial\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _find_hits(text: str, patterns: list[re.Pattern]) -> list[str]:
    hits = []
    for pat in patterns:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def _load_text_sample(path: str, max_chars: int) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return text[:max_chars]


def refine_domain(store, config: dict, paths: dict) -> None:
    domain_cfg = config.get("domain", {})
    use_raw_text = bool(domain_cfg.get("use_raw_text", True))
    raw_text_max_chars = int(domain_cfg.get("raw_text_max_chars", 50000))
    min_score = int(domain_cfg.get("min_score", 3))
    require_finetune_or_task = bool(domain_cfg.get("require_finetune_or_task", True))
    hard_exclude = bool(domain_cfg.get("hard_exclude", True))

    model_patterns = _compile(MODEL_PATTERNS)
    finetune_patterns = _compile(FINETUNE_PATTERNS)
    task_patterns = _compile(TASK_PATTERNS)
    hp_patterns = _compile(HP_PATTERNS)
    exclude_patterns = _compile(EXCLUDE_PATTERNS)

    reports_dir = Path(paths["reports_dir"]).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    dedup_primary: dict[str, str] = {}
    stats = {
        "total": 0,
        "suitable": 0,
        "unsuitable": 0,
        "duplicates": 0,
    }
    unsuitable_samples = []

    for doc in store.collection.find({}, batch_size=100):
        stats["total"] += 1

        title = doc.get("title") or ""
        abstract = doc.get("abstract") or ""
        base_text = f"{title}\n{abstract}".lower()
        text_blob = base_text

        if use_raw_text and doc.get("raw_text_path"):
            text_blob += "\n" + _load_text_sample(doc["raw_text_path"], raw_text_max_chars).lower()

        model_hits = _find_hits(text_blob, model_patterns)
        finetune_hits = _find_hits(text_blob, finetune_patterns)
        task_hits = _find_hits(text_blob, task_patterns)
        hp_hits = _find_hits(text_blob, hp_patterns)
        # Exclude patterns are checked only against title/abstract to avoid
        # false negatives from references in the full text.
        exclude_hits = _find_hits(base_text, exclude_patterns)

        score = 0
        if model_hits:
            score += 3
        if finetune_hits:
            score += 2
        if task_hits:
            score += 1
        if hp_hits:
            score += 1
        if exclude_hits:
            score -= 3

        has_task_or_finetune = bool(finetune_hits or task_hits or hp_hits)
        is_suitable = bool(model_hits) and (not require_finetune_or_task or has_task_or_finetune)
        if hard_exclude and exclude_hits:
            is_suitable = False
        if score < min_score:
            is_suitable = False

        if is_suitable:
            stats["suitable"] += 1
        else:
            stats["unsuitable"] += 1
            if len(unsuitable_samples) < 50:
                unsuitable_samples.append(
                    {
                        "title": title,
                        "source": doc.get("source"),
                        "source_id": doc.get("source_id"),
                        "score": score,
                        "exclude_hits": exclude_hits,
                    }
                )

        dedup_key = (doc.get("doi") or "").lower().strip() or (doc.get("title_norm") or "")
        dedup = {
            "key": dedup_key,
            "is_duplicate": False,
            "duplicate_of": None,
        }
        if dedup_key:
            if dedup_key in dedup_primary:
                dedup["is_duplicate"] = True
                dedup["duplicate_of"] = dedup_primary[dedup_key]
                stats["duplicates"] += 1
            else:
                dedup_primary[dedup_key] = str(doc["_id"])

        update = {
            "domain": {
                "model_hits": model_hits,
                "finetune_hits": finetune_hits,
                "task_hits": task_hits,
                "hp_hits": hp_hits,
                "exclude_hits": exclude_hits,
                "score": score,
                "is_suitable": is_suitable,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            },
            "tags.domain_suitable": is_suitable,
            "dedup": dedup,
        }

        store.collection.update_one({"_id": doc["_id"]}, {"$set": update})

    report = {
        "summary": stats,
        "config": {
            "min_score": min_score,
            "use_raw_text": use_raw_text,
            "raw_text_max_chars": raw_text_max_chars,
            "require_finetune_or_task": require_finetune_or_task,
            "hard_exclude": hard_exclude,
        },
        "unsuitable_samples": unsuitable_samples,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    report_path = reports_dir / "domain_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
