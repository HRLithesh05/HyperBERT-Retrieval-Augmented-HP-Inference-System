"""Module 3 — Dataset & Task Taxonomy Normalization.

Canonicalizes dataset and task names so that string-based strategy
filtering (S1/S2) doesn't miss matches due to trivial naming variations
like "CoNLL-2003" vs "conll2003" or "NER" vs "token_classification".

Public API:
    normalize_dataset(name: str) -> str
    normalize_task(name: str) -> str
"""

from __future__ import annotations

import re

# ── Dataset Aliases ────────────────────────────────────────────────────
# Maps common variations to a single canonical name.
DATASET_ALIASES: dict[str, str] = {
    # CoNLL family
    "conll-2003": "conll2003", "conll 2003": "conll2003", "conll-03": "conll2003",
    "conll-2000": "conll2000", "conll 2000": "conll2000",
    # GLUE benchmarks
    "sst-2": "sst2", "sst 2": "sst2", "sst-binary": "sst2",
    "mrpc": "mrpc",
    "qqp": "qqp",
    "mnli": "mnli", "multi-nli": "mnli", "multinli": "mnli",
    "qnli": "qnli",
    "rte": "rte",
    "wnli": "wnli",
    "cola": "cola",
    "sts-b": "stsb", "sts b": "stsb", "stsb": "stsb",
    # SQuAD
    "squad v1": "squad", "squad1.1": "squad", "squad 1.1": "squad",
    "squad v1.1": "squad", "squad-1.1": "squad",
    "squad v2": "squad2", "squad2.0": "squad2", "squad 2.0": "squad2",
    "squad v2.0": "squad2", "squad-2.0": "squad2",
    # Others
    "imdb": "imdb", "imdb reviews": "imdb",
    "ag news": "agnews", "ag_news": "agnews", "ag-news": "agnews",
    "snli": "snli",
    "swag": "swag",
    "race": "race",
    "ontonotes": "ontonotes", "ontonotes 5": "ontonotes", "ontonotes5": "ontonotes",
    "yelp": "yelp", "yelp reviews": "yelp",
    "dbpedia": "dbpedia",
    "trec": "trec",
    "yahoo": "yahoo", "yahoo answers": "yahoo",
    "wikitext": "wikitext", "wikitext-2": "wikitext2", "wikitext-103": "wikitext103",
    "superglue": "superglue", "super glue": "superglue", "super-glue": "superglue",
}

# ── Task Aliases ───────────────────────────────────────────────────────
TASK_ALIASES: dict[str, str] = {
    # NER / token classification
    "ner": "token_classification",
    "named entity recognition": "token_classification",
    "sequence labeling": "token_classification",
    "sequence tagging": "token_classification",
    "pos tagging": "token_classification",
    "part of speech tagging": "token_classification",
    "part-of-speech tagging": "token_classification",
    "token classification": "token_classification",
    # Text classification
    "text classification": "text_classification",
    "document classification": "text_classification",
    "sentence classification": "text_classification",
    # Sentiment
    "sentiment analysis": "sentiment_analysis",
    "sentiment classification": "sentiment_analysis",
    "sentiment detection": "sentiment_analysis",
    "opinion mining": "sentiment_analysis",
    # QA
    "question answering": "question_answering",
    "qa": "question_answering",
    "reading comprehension": "question_answering",
    "extractive qa": "question_answering",
    "machine reading comprehension": "question_answering",
    "mrc": "question_answering",
    # NLI
    "nli": "nli",
    "natural language inference": "nli",
    "textual entailment": "nli",
    # STS
    "sts": "semantic_textual_similarity",
    "semantic textual similarity": "semantic_textual_similarity",
    "sentence similarity": "semantic_textual_similarity",
    # RE
    "relation extraction": "relation_extraction",
    "re": "relation_extraction",
    # Summarization
    "summarization": "summarization",
    "text summarization": "summarization",
    "abstractive summarization": "summarization",
    "extractive summarization": "summarization",
}

# Precompute lowercase lookup
_DATASET_LOOKUP = {k.lower().strip(): v for k, v in DATASET_ALIASES.items()}
_TASK_LOOKUP = {k.lower().strip(): v for k, v in TASK_ALIASES.items()}


def _clean(name: str) -> str:
    """Lowercase, strip, collapse whitespace and remove special chars."""
    name = name.lower().strip()
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name


def normalize_dataset(name: str | None) -> str | None:
    """Normalize a dataset name to its canonical form.

    Returns the canonical name if an alias exists, otherwise returns
    the cleaned (lowercased, stripped) original name.
    """
    if not name:
        return name
    cleaned = _clean(name)
    return _DATASET_LOOKUP.get(cleaned, cleaned)


def normalize_task(name: str | None) -> str | None:
    """Normalize a task name to its canonical form.

    Returns the canonical name if an alias exists, otherwise returns
    the cleaned (lowercased, stripped) original name.
    """
    if not name:
        return name
    cleaned = _clean(name)
    return _TASK_LOOKUP.get(cleaned, cleaned)
