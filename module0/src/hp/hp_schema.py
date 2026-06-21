"""Canonical HP JSON schema and helpers for Module 0 Step 3.

This schema is the contract between the corpus (Module 0) and the
retrieval engine (Module 3).  Every clean paper will have an
``hp_json`` field conforming to this structure after LLM extraction.
"""

# ---------- schema definition ----------

HP_FIELDS = [
    "learning_rate",
    "batch_size",
    "epochs",
    "max_seq_length",
    "optimizer",
    "weight_decay",
    "warmup_steps",
    "warmup_ratio",
    "scheduler",
    "gradient_clipping",
    "dropout",
    "seed",
]

EMPTY_HP_JSON: dict = {
    "model": None,
    "task": None,
    "dataset": None,
    "hyperparameters": {f: None for f in HP_FIELDS},
    "missing_params": list(HP_FIELDS),
    "confidence": 0.0,
}

# ---------- prompt templates ----------

EXTRACT_SYSTEM_PROMPT = (
    "You are a meticulous ML research assistant.  "
    "Given the text of a research paper, extract every BERT fine-tuning "
    "hyperparameter you can find.  Return ONLY valid JSON matching the "
    "schema below — no markdown, no commentary.\n\n"
    "Schema:\n"
    "{\n"
    '  "model": "<string or null>",\n'
    '  "task": "<string or null>",\n'
    '  "dataset": "<string or null>",\n'
    '  "hyperparameters": {\n'
    '    "learning_rate": <float or null>,\n'
    '    "batch_size": <int or null>,\n'
    '    "epochs": <int or null>,\n'
    '    "max_seq_length": <int or null>,\n'
    '    "optimizer": "<string or null>",\n'
    '    "weight_decay": <float or null>,\n'
    '    "warmup_steps": <int or null>,\n'
    '    "warmup_ratio": <float or null>,\n'
    '    "scheduler": "<string or null>",\n'
    '    "gradient_clipping": <float or null>,\n'
    '    "dropout": <float or null>,\n'
    '    "seed": <int or null>\n'
    "  },\n"
    '  "missing_params": ["<param names not found>"],\n'
    '  "confidence": <float 0-1>\n'
    "}\n\n"
    "Rules:\n"
    "- Use null for any parameter not explicitly stated in the paper.\n"
    "- List all null parameters in missing_params.\n"
    "- For model, use the exact name (e.g. bert-base-uncased, biobert-v1.1).\n"
    "- For task, use a canonical name: text_classification, ner, "
    "question_answering, nli, sentiment_analysis, relation_extraction, "
    "semantic_textual_similarity, summarization, token_classification, other.\n"
    "- confidence is your self-assessed reliability of the extraction (0-1).\n"
    "- If the paper reports multiple fine-tuning runs, extract the PRIMARY or "
    "best-performing configuration.\n"
)

EXTRACT_USER_TEMPLATE = "Paper text:\n\n{text}\n\nExtract hyperparameters as JSON."

VERIFY_SYSTEM_PROMPT = (
    "You are a careful verifier.  You are given a research paper's text and "
    "a previously extracted JSON of hyperparameters.  Your job:\n"
    "1. Check each value against the paper text.\n"
    "2. Fix any incorrect values.\n"
    "3. Fill in any values that were missed (set to null incorrectly).\n"
    "4. Update missing_params and confidence accordingly.\n"
    "5. Return ONLY the corrected JSON — same schema, no commentary.\n"
)

VERIFY_USER_TEMPLATE = (
    "Paper text:\n\n{text}\n\n"
    "Previously extracted JSON:\n{json}\n\n"
    "Verify and correct the JSON."
)
