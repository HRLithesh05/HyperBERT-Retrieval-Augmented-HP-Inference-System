"""Module 7 — Annotated Notebook Generator.

Generates a Jupyter notebook (.ipynb) with 6 phases:
  Ph0: Prerequisites & Setup
  Ph1: Dataset Preparation
  Ph2: Model Initialization
  Ph3: Training Configuration (with confidence annotations + citations)
  Ph4: Training Loop
  Ph5: Evaluation & Export
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


# ── Known dataset mappings for auto-fetch ──────────────────────────────
# Format: (hf_id, subset_or_none, label_col, text_col, is_glue)
KNOWN_DATASETS = {
    "conll2003":  ("conll2003", None, "ner_tags", "tokens", False),
    "conll":      ("conll2003", None, "ner_tags", "tokens", False),
    "conll-2003": ("conll2003", None, "ner_tags", "tokens", False),
    "squad":      ("rajpurkar/squad", None, "answers", "question", False),
    "squad2":     ("rajpurkar/squad_v2", None, "answers", "question", False),
    "imdb":       ("imdb", None, "label", "text", False),
    "sst2":       ("stanfordnlp/sst2", None, "label", "sentence", False),
    "sst":        ("stanfordnlp/sst2", None, "label", "sentence", False),
    "sst-2":      ("stanfordnlp/sst2", None, "label", "sentence", False),
    "mnli":       ("glue", "mnli", "label", "premise", True),
    "mrpc":       ("glue", "mrpc", "label", "sentence1", True),
    "cola":       ("glue", "cola", "label", "sentence", True),
    "qqp":        ("glue", "qqp", "label", "question1", True),
    "rte":        ("glue", "rte", "label", "sentence1", True),
    "wnli":       ("glue", "wnli", "label", "sentence1", True),
    "qnli":       ("glue", "qnli", "label", "question", True),
    "ag_news":    ("ag_news", None, "label", "text", False),
    "yelp":       ("yelp_review_full", None, "label", "text", False),
    "trec":       ("trec", None, "coarse_label", "text", False),
    "snli":       ("snli", None, "label", "premise", False),
    "emotion":    ("emotion", None, "label", "text", False),
    "tweet_eval": ("tweet_eval", "sentiment", "label", "text", False),
}

# Task → HuggingFace model class mapping
TASK_MODEL_MAP = {
    "ner": ("AutoModelForTokenClassification", "token_classification"),
    "named_entity_recognition": ("AutoModelForTokenClassification", "token_classification"),
    "toponym_recognition": ("AutoModelForTokenClassification", "token_classification"),
    "pos_tagging": ("AutoModelForTokenClassification", "token_classification"),
    "text_classification": ("AutoModelForSequenceClassification", "sequence_classification"),
    "sentiment_analysis": ("AutoModelForSequenceClassification", "sequence_classification"),
    "sentiment": ("AutoModelForSequenceClassification", "sequence_classification"),
    "question_answering": ("AutoModelForQuestionAnswering", "question_answering"),
    "qa": ("AutoModelForQuestionAnswering", "question_answering"),
    "nli": ("AutoModelForSequenceClassification", "sequence_classification"),
    "textual_entailment": ("AutoModelForSequenceClassification", "sequence_classification"),
}


def _resolve_dataset(dataset_name: str) -> tuple | None:
    """Resolve a dataset name to (hf_id, subset, label_col, text_col, is_glue) or None."""
    if not dataset_name:
        return None
    key = dataset_name.lower().strip().replace(" ", "_").replace("-", "_")
    if key in KNOWN_DATASETS:
        return KNOWN_DATASETS[key]
    for known_key, value in KNOWN_DATASETS.items():
        if known_key in key or key in known_key:
            return value
    return None


def _resolve_task_model(task: str) -> tuple[str, str]:
    """Resolve task to (ModelClass, task_type)."""
    if not task:
        return "AutoModelForSequenceClassification", "sequence_classification"
    key = task.lower().strip().replace(" ", "_").replace("-", "_")
    return TASK_MODEL_MAP.get(key, ("AutoModelForSequenceClassification", "sequence_classification"))


def generate_notebook(
    validated_config: dict,
    evidence_report: dict,
    user_hp_json: dict,
    contradiction_report: dict | None = None,
    validation_result: dict | None = None,
    output_path: str = "notebook.ipynb",
) -> str:
    """Generate an annotated Jupyter notebook.

    Returns the path to the generated notebook.
    """
    cells = []

    # Extract flat config values
    config_vals = {}
    for param, entry in validated_config.items():
        if isinstance(entry, dict):
            config_vals[param] = entry.get("value")
        else:
            config_vals[param] = entry

    model_name = user_hp_json.get("model") or "bert-base-uncased"
    task = user_hp_json.get("task") or "text_classification"
    dataset_name = user_hp_json.get("dataset") or "custom_dataset"
    strategy = evidence_report.get("strategy", "unknown")
    n_evidence = evidence_report.get("total_evidence_papers", 0)

    resolved_ds = _resolve_dataset(dataset_name)
    model_class, task_type = _resolve_task_model(task)

    # ===================== Header =====================
    ds_badge = ""
    if resolved_ds:
        ds_badge = f"**Dataset Auto-Fetch**: ✅ `{resolved_ds[0]}` (HuggingFace)  \n"
    else:
        ds_badge = f"**Dataset**: ⚠️ `{dataset_name}` (manual setup required)  \n"

    cells.append(_md_cell(
        f"# 🔬 HyperBERT: Inferred Training Configuration\n"
        f"\n"
        f"**Model**: `{model_name}`  \n"
        f"**Task**: `{task}`  \n"
        f"{ds_badge}"
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n"
        f"**Evidence**: {n_evidence} similar papers (Strategy: {strategy})  \n"
        f"\n"
        f"---\n"
        f"\n"
        f"> This notebook was auto-generated by the HyperBERT system. "
        f"Each hyperparameter is annotated with its confidence level and source."
    ))

    # ===================== Config Summary =====================
    cells.append(_md_cell(_build_config_table(validated_config)))

    # Warnings section
    warnings_md = _build_warnings(contradiction_report, validation_result)
    if warnings_md:
        cells.append(_md_cell(warnings_md))

    # ===================== Ph0: Prerequisites =====================
    cells.append(_md_cell(
        "## Phase 0: Prerequisites & Setup\n"
        "\n"
        "**Before running this notebook, ensure you have:**\n"
        "1. Python 3.8+ installed\n"
        "2. A GPU is recommended but not required (training will be slower on CPU)\n"
        "3. At least 4GB free disk space for model weights\n"
        "\n"
        "**Run the cell below to install all required packages.**\n"
        "If you're on Google Colab, these are pre-installed."
    ))
    cells.append(_code_cell(
        "import subprocess, sys\n"
        "\n"
        "# Install required packages\n"
        "packages = [\n"
        '    "transformers>=4.30.0",\n'
        '    "datasets>=2.14.0",\n'
        '    "evaluate",\n'
        '    "accelerate>=0.20.0",\n'
        '    "scikit-learn",\n'
        '    "seqeval",  # For NER evaluation\n'
        '    "torch>=2.0.0",\n'
        "]\n"
        "\n"
        "for pkg in packages:\n"
        "    try:\n"
        "        subprocess.check_call(\n"
        "            [sys.executable, '-m', 'pip', 'install', '-q', pkg],\n"
        "            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL\n"
        "        )\n"
        "    except Exception:\n"
        "        print(f'Warning: Could not install {pkg}')\n"
        "\n"
        "import torch\n"
        "print(f'PyTorch: {torch.__version__}')\n"
        "print(f'CUDA available: {torch.cuda.is_available()}')\n"
        "if torch.cuda.is_available():\n"
        "    print(f'GPU: {torch.cuda.get_device_name(0)}')"
    ))

    # ===================== Ph1: Dataset Prep =====================
    cells.append(_md_cell("## Phase 1: Dataset Preparation"))

    max_seq = config_vals.get("max_seq_length", 128)

    if resolved_ds:
        hf_id, subset, label_col, text_col = resolved_ds[0], resolved_ds[1], resolved_ds[2], resolved_ds[3]

        # Build dataset load call
        if subset:
            load_call = f'dataset = load_dataset("{hf_id}", "{subset}")'
        else:
            load_call = f'dataset = load_dataset("{hf_id}")'

        if task_type == "token_classification":
            # NER needs special tokenization with label alignment
            cells.append(_code_cell(
                f"from transformers import AutoTokenizer\n"
                f"from datasets import load_dataset\n"
                f"\n"
                f'MODEL_NAME = "{model_name}"\n'
                f"MAX_SEQ_LENGTH = {max_seq}\n"
                f"\n"
                f"tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)\n"
                f"\n"
                f"# Load dataset\n"
                f"{load_call}\n"
                f'print(f"Dataset loaded: {hf_id}")\n'
                f'print(f"Train samples: {{len(dataset[\'train\'])}}")\n'
                f'print(f"Columns: {{dataset[\'train\'].column_names}}")\n'
                f"\n"
                f"# Get label names for NER\n"
                f"label_names = dataset['train'].features['{label_col}'].feature.names\n"
                f'print(f"Labels: {{label_names}}")\n'
                f"\n"
                f"def tokenize_and_align_labels(examples):\n"
                f"    \"\"\"Tokenize and align NER labels with subword tokens.\"\"\"\n"
                f"    tokenized = tokenizer(\n"
                f"        examples['{text_col}'],\n"
                f"        truncation=True,\n"
                f"        max_length=MAX_SEQ_LENGTH,\n"
                f"        is_split_into_words=True,\n"
                f"    )\n"
                f"    labels = []\n"
                f"    for i, label in enumerate(examples['{label_col}']):\n"
                f"        word_ids = tokenized.word_ids(batch_index=i)\n"
                f"        label_ids = []\n"
                f"        prev_word_id = None\n"
                f"        for word_id in word_ids:\n"
                f"            if word_id is None:\n"
                f"                label_ids.append(-100)\n"
                f"            elif word_id != prev_word_id:\n"
                f"                label_ids.append(label[word_id])\n"
                f"            else:\n"
                f"                label_ids.append(-100)  # Subword gets -100\n"
                f"            prev_word_id = word_id\n"
                f"        labels.append(label_ids)\n"
                f"    tokenized['labels'] = labels\n"
                f"    return tokenized\n"
                f"\n"
                f"tokenized = dataset.map(tokenize_and_align_labels, batched=True,\n"
                f"                        remove_columns=dataset['train'].column_names)\n"
                f'print("Tokenization complete with label alignment.")'
            ))
        else:
            # Standard text classification tokenization
            cells.append(_code_cell(
                f"from transformers import AutoTokenizer\n"
                f"from datasets import load_dataset\n"
                f"\n"
                f'MODEL_NAME = "{model_name}"\n'
                f"MAX_SEQ_LENGTH = {max_seq}\n"
                f"\n"
                f"tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)\n"
                f"\n"
                f"# Load dataset\n"
                f"{load_call}\n"
                f'print(f"Dataset loaded: {hf_id}")\n'
                f'print(f"Train samples: {{len(dataset[\'train\'])}}")\n'
                f"\n"
                f"def tokenize_function(examples):\n"
                f"    return tokenizer(\n"
                f"        examples['{text_col}'],\n"
                f'        padding="max_length",\n'
                f"        truncation=True,\n"
                f"        max_length=MAX_SEQ_LENGTH,\n"
                f"    )\n"
                f"\n"
                f"tokenized = dataset.map(tokenize_function, batched=True)\n"
                f'print(f"Tokenization complete. Max seq length: {{MAX_SEQ_LENGTH}}")'
            ))
    else:
        cells.append(_md_cell(
            "⚠️ **Manual dataset setup required.**\n\n"
            "Replace the placeholder below with your dataset path or HuggingFace dataset ID.\n"
            "Examples:\n"
            '- `load_dataset("csv", data_files={"train": "train.csv", "test": "test.csv"})`\n'
            '- `load_dataset("your_username/your_dataset")`'
        ))
        cells.append(_code_cell(
            f"from transformers import AutoTokenizer\n"
            f"from datasets import load_dataset\n"
            f"\n"
            f'MODEL_NAME = "{model_name}"\n'
            f"MAX_SEQ_LENGTH = {max_seq}\n"
            f"\n"
            f"tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)\n"
            f"\n"
            f"# ↓↓↓ REPLACE WITH YOUR DATASET ↓↓↓\n"
            f'# dataset = load_dataset("csv", data_files={{"train": "train.csv", "test": "test.csv"}})\n'
            f'dataset = load_dataset("imdb")  # Placeholder — replace with your data\n'
            f"\n"
            f"def tokenize_function(examples):\n"
            f"    return tokenizer(\n"
            f'        examples["text"],\n'
            f'        padding="max_length",\n'
            f"        truncation=True,\n"
            f"        max_length=MAX_SEQ_LENGTH,\n"
            f"    )\n"
            f"\n"
            f"tokenized = dataset.map(tokenize_function, batched=True)\n"
            f'print(f"Tokenizer loaded: {{MODEL_NAME}}, Max seq length: {{MAX_SEQ_LENGTH}}")'
        ))

    # ===================== Ph2: Model Init =====================
    cells.append(_md_cell("## Phase 2: Model Initialization"))

    dropout_val = config_vals.get("dropout", 0.1)
    if task_type == "token_classification":
        num_labels_comment = "# NUM_LABELS = number of NER tags (auto-detected from dataset)"
        num_labels_code = "NUM_LABELS = len(label_names)"
    elif task_type == "question_answering":
        num_labels_comment = "# QA models use start/end positions"
        num_labels_code = "NUM_LABELS = 2"
    else:
        num_labels_comment = "# Adjust NUM_LABELS for your classification task"
        num_labels_code = "NUM_LABELS = len(set(dataset['train']['label']))"

    cells.append(_code_cell(
        f"from transformers import {model_class}\n"
        f"\n"
        f"{num_labels_comment}\n"
        f"{num_labels_code}\n"
        f'print(f"Number of labels: {{NUM_LABELS}}")\n'
        f"\n"
        f"model = {model_class}.from_pretrained(\n"
        f"    MODEL_NAME,\n"
        f"    num_labels=NUM_LABELS,\n"
        f"    hidden_dropout_prob={dropout_val},\n"
        f"    attention_probs_dropout_prob={dropout_val},\n"
        f")\n"
        f"\n"
        f"total_params = sum(p.numel() for p in model.parameters())\n"
        f"trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)\n"
        f'print(f"Model: {{MODEL_NAME}}")\n'
        f'print(f"Total parameters: {{total_params:,}}")\n'
        f'print(f"Trainable parameters: {{trainable:,}}")'
    ))

    # ===================== Ph3: Training Config =====================
    cells.append(_md_cell(
        "## Phase 3: Training Configuration\n"
        "\n"
        "Each hyperparameter below is annotated with its source and confidence level.\n"
        "- 🟢 **High confidence** (≥70%): Strong corpus evidence\n"
        "- 🟡 **Medium confidence** (30-70%): Partial evidence\n"
        "- 🔴 **Low confidence** (<30%): BERT default fallback"
    ))

    lr = config_vals.get("learning_rate", 2e-5)
    bs = config_vals.get("batch_size", 32)
    epochs = config_vals.get("epochs", 3)
    wd = config_vals.get("weight_decay", 0.01)
    warmup = config_vals.get("warmup_ratio", 0.06)
    scheduler_type = config_vals.get("scheduler", "linear")
    gc = config_vals.get("gradient_clipping", 1.0)
    seed = config_vals.get("seed", 42)

    annotations = _build_annotations(validated_config)

    cells.append(_code_cell(
        f"from transformers import TrainingArguments\n"
        f"\n"
        f"training_args = TrainingArguments(\n"
        f'    output_dir="./results",\n'
        f"\n"
        f"    # === Core Hyperparameters ===\n"
        f"    learning_rate={lr},  {annotations.get('learning_rate', '')}\n"
        f"    per_device_train_batch_size={bs},  {annotations.get('batch_size', '')}\n"
        f"    num_train_epochs={epochs},  {annotations.get('epochs', '')}\n"
        f"\n"
        f"    # === Regularization ===\n"
        f"    weight_decay={wd},  {annotations.get('weight_decay', '')}\n"
        f"    max_grad_norm={gc},  {annotations.get('gradient_clipping', '')}\n"
        f"\n"
        f"    # === Scheduling ===\n"
        f"    warmup_ratio={warmup},  {annotations.get('warmup_ratio', '')}\n"
        f'    lr_scheduler_type="{scheduler_type}",  {annotations.get("scheduler", "")}\n'
        f"\n"
        f"    # === General ===\n"
        f"    seed={seed},  {annotations.get('seed', '')}\n"
        f"\n"
        f"    # === Evaluation & Logging ===\n"
        f'    eval_strategy="epoch",\n'
        f'    save_strategy="epoch",\n'
        f"    logging_steps=50,\n"
        f"    load_best_model_at_end=True,\n"
        f'    metric_for_best_model="eval_loss",\n'
        f'    report_to="none",\n'
        f"    fp16=torch.cuda.is_available(),  # Use mixed precision if GPU available\n"
        f")\n"
        f"\n"
        f'print("Training configuration set.")\n'
        f'print(f"  Learning rate: {{training_args.learning_rate}}")\n'
        f'print(f"  Batch size: {{training_args.per_device_train_batch_size}}")\n'
        f'print(f"  Epochs: {{training_args.num_train_epochs}}")\n'
        f'print(f"  Weight decay: {{training_args.weight_decay}}")\n'
        f'print(f"  FP16: {{training_args.fp16}}")'
    ))

    # ===================== Ph4: Training Loop =====================
    cells.append(_md_cell("## Phase 4: Training"))

    # Build compute_metrics based on task type
    if task_type == "token_classification":
        metric_code = (
            "import evaluate\n"
            "import numpy as np\n"
            "from transformers import DataCollatorForTokenClassification\n"
            "\n"
            'seqeval = evaluate.load("seqeval")\n'
            "\n"
            "def compute_metrics(eval_pred):\n"
            "    logits, labels = eval_pred\n"
            "    predictions = np.argmax(logits, axis=-1)\n"
            "    true_labels = [\n"
            "        [label_names[l] for l in label if l != -100]\n"
            "        for label in labels\n"
            "    ]\n"
            "    true_preds = [\n"
            "        [label_names[p] for p, l in zip(pred, label) if l != -100]\n"
            "        for pred, label in zip(predictions, labels)\n"
            "    ]\n"
            "    results = seqeval.compute(predictions=true_preds, references=true_labels)\n"
            "    return {\n"
            '        "precision": results["overall_precision"],\n'
            '        "recall": results["overall_recall"],\n'
            '        "f1": results["overall_f1"],\n'
            '        "accuracy": results["overall_accuracy"],\n'
            "    }\n"
            "\n"
            "# Data collator handles padding for token classification\n"
            "data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)"
        )
    else:
        metric_code = (
            "import numpy as np\n"
            "from sklearn.metrics import accuracy_score, f1_score\n"
            "\n"
            "def compute_metrics(eval_pred):\n"
            "    logits, labels = eval_pred\n"
            "    predictions = np.argmax(logits, axis=-1)\n"
            "    acc = accuracy_score(labels, predictions)\n"
            '    f1 = f1_score(labels, predictions, average="weighted")\n'
            '    return {"accuracy": acc, "f1": f1}\n'
            "\n"
            "data_collator = None  # Default collator works for classification"
        )

    # Build eval dataset reference
    eval_ds = 'tokenized["validation"] if "validation" in tokenized else tokenized["test"]'

    cells.append(_code_cell(
        f"from transformers import Trainer\n"
        f"{metric_code}\n"
        f"\n"
        f"trainer = Trainer(\n"
        f"    model=model,\n"
        f"    args=training_args,\n"
        f'    train_dataset=tokenized["train"],\n'
        f"    eval_dataset={eval_ds},\n"
        f"    compute_metrics=compute_metrics,\n"
        f"    data_collator=data_collator,\n"
        f")\n"
        f"\n"
        f'print("Trainer initialized successfully.")'
    ))

    # Training cell
    cells.append(_code_cell(
        "# Start training\n"
        "train_result = trainer.train()\n"
        "\n"
        'print(f"\\nTraining complete!")\n'
        'print(f"  Training loss: {train_result.training_loss:.4f}")\n'
        'print(f"  Runtime: {train_result.metrics.get(\'train_runtime\', 0):.1f}s")'
    ))

    # ===================== Ph5: Evaluation =====================
    cells.append(_md_cell("## Phase 5: Evaluation & Export"))

    cells.append(_code_cell(
        "# Evaluate on test/validation set\n"
        "results = trainer.evaluate()\n"
        'print("\\nEvaluation Results:")\n'
        "for key, value in sorted(results.items()):\n"
        "    if isinstance(value, float):\n"
        '        print(f"  {key}: {value:.4f}")\n'
        "    else:\n"
        '        print(f"  {key}: {value}")\n'
        "\n"
        "# Save model\n"
        'trainer.save_model("./final_model")\n'
        'tokenizer.save_pretrained("./final_model")\n'
        'print("\\nModel saved to ./final_model")'
    ))

    # ===================== Evidence Citations =====================
    cells.append(_md_cell(_build_citations(evidence_report)))

    # Build notebook JSON
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }

    output = Path(output_path).resolve()
    output.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output)


# ===================== Helpers =====================

def _md_cell(source: str) -> dict:
    """Create a markdown cell with properly formatted source lines."""
    lines = source.split("\n")
    # Each line must end with \n except possibly the last
    source_lines = [line + "\n" for line in lines[:-1]]
    if lines:
        source_lines.append(lines[-1])  # last line without trailing \n
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source_lines,
    }


def _code_cell(source: str) -> dict:
    """Create a code cell with properly formatted source lines."""
    lines = source.split("\n")
    source_lines = [line + "\n" for line in lines[:-1]]
    if lines:
        source_lines.append(lines[-1])
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source_lines,
        "outputs": [],
        "execution_count": None,
    }


def _build_config_table(config: dict) -> str:
    """Build a markdown table summarizing the config."""
    lines = [
        "### Configuration Summary\n",
        "| Parameter | Value | Source | Confidence |",
        "|-----------|-------|--------|------------|",
    ]
    for param in [
        "learning_rate", "batch_size", "epochs", "optimizer",
        "max_seq_length", "weight_decay", "warmup_ratio",
        "scheduler", "gradient_clipping", "dropout", "seed",
    ]:
        entry = config.get(param, {})
        if isinstance(entry, dict):
            val = entry.get("value", "—")
            src = entry.get("source", "—")
            conf = entry.get("confidence", "—")
            if isinstance(conf, float):
                emoji = "🟢" if conf >= 0.7 else "🟡" if conf >= 0.3 else "🔴"
                conf = f"{emoji} {conf:.0%}"
            src_label = {
                "extracted_from_paper": "📄 Paper",
                "inferred_from_corpus": "🔍 Inferred",
                "bert_default": "📋 Default",
                "auto_corrected": "🔧 Corrected",
            }.get(src, src)
        else:
            val, src_label, conf = entry, "—", "—"
        lines.append(f"| `{param}` | `{val}` | {src_label} | {conf} |")

    return "\n".join(lines)


def _build_annotations(config: dict) -> dict:
    """Build inline code comments for each HP."""
    annotations = {}
    for param, entry in config.items():
        if not isinstance(entry, dict):
            continue
        src = entry.get("source", "")
        conf = entry.get("confidence", 0)
        if src == "extracted_from_paper":
            annotations[param] = "# ← from your paper (100%)"
        elif src == "inferred_from_corpus":
            n = entry.get("support_count", 0)
            annotations[param] = f"# ← inferred ({conf:.0%} conf, {n} papers)"
        elif src == "bert_default":
            annotations[param] = "# ← BERT default (low/no evidence)"
        elif src == "auto_corrected":
            annotations[param] = "# ← auto-corrected by validator"
    return annotations


def _build_warnings(contradiction_report, validation_result) -> str:
    """Build warnings markdown section."""
    parts = []

    if contradiction_report:
        contras = contradiction_report.get("contradictions", [])
        if contras:
            parts.append("### ⚠️ Evidence Warnings\n")
            for c in contras[:5]:
                parts.append(f"- **{c['param']}**: {c['message']}")

    if validation_result:
        corrections = validation_result.get("corrections", [])
        if corrections:
            parts.append("\n### 🔧 Auto-Corrections\n")
            for c in corrections:
                parts.append(f"- **{c['param']}**: {c['message']}")

    return "\n".join(parts) if parts else ""


def _build_citations(evidence_report: dict) -> str:
    """Build citations section."""
    papers = evidence_report.get("papers", [])
    if not papers:
        return "### 📚 Citations\n\nNo corpus papers were used for inference."

    lines = [
        "### 📚 Evidence Citations\n",
        f"The following {len(papers)} papers contributed to the HP inference:\n",
        "| # | Title | Similarity | R-Score | Source |",
        "|---|-------|-----------|---------|--------|",
    ]
    for i, p in enumerate(papers[:15], 1):
        title = p.get("title", "Unknown")[:60]
        sim = f"{p.get('similarity', 0):.3f}"
        rs = f"{p.get('rscore', 0):.3f}"
        src = p.get("source", "—")
        lines.append(f"| {i} | {title} | {sim} | {rs} | {src} |")

    return "\n".join(lines)
