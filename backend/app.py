"""
HyperBERT Backend API — Flask REST server
Connects the React frontend to the M1-M7 inference pipeline.

Endpoints:
  POST /api/analyze          Upload PDF → run M1-M7 → return full JSON result
  GET  /api/session/<id>     Fetch stored session result
  GET  /api/download/<id>/notebook   Download .ipynb
  GET  /api/download/<id>/script     Download .py training script
  GET  /api/download/<id>/yaml       Download config.yaml
  GET  /api/corpus/papers    List papers in corpus (filterable)
  GET  /api/corpus/stats     Corpus statistics
"""

from __future__ import annotations

import json
import os
import sys
import uuid
import time
import textwrap
from datetime import datetime, timezone
from pathlib import Path

# ── Setup sys.path so backend can import existing modules ──────────────
ROOT = Path(__file__).resolve().parent.parent          # e:\major_project_datacollection
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "module0" / "src"))

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])

# ── Load environment variables ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # dotenv not installed; rely on system env vars

# ── Config & directories ───────────────────────────────────────────────
CONFIG_PATH = ROOT / "module0" / "config.json"
SESSIONS_DIR = ROOT / "backend" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

# ── MongoDB ────────────────────────────────────────────────────────────
try:
    _mongo = MongoClient(CONFIG["mongodb"]["uri"], serverSelectionTimeoutMS=3000)
    _mongo.server_info()
    DB = _mongo[CONFIG["mongodb"]["db"]]
    MONGO_OK = True
    print("✅ MongoDB connected")
except Exception as e:
    DB = None
    MONGO_OK = False
    print(f"⚠️  MongoDB unavailable: {e} — using filesystem fallback")


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════

def _load_pipeline_modules():
    """Lazy import the pipeline to avoid startup cost."""
    from src.module1.pdf_analyzer import analyze_pdf
    from src.module2.completeness import check_completeness
    from src.module3.engine import InferenceEngine
    from src.module4.constraints import apply_constraints
    from src.module5.contradictions import detect_contradictions
    from src.module6.validator import validate_config
    from src.module7.notebook_gen import generate_notebook
    return (analyze_pdf, check_completeness, InferenceEngine,
            apply_constraints, detect_contradictions, validate_config,
            generate_notebook)


def _get_session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _save_session(session_id: str, data: dict):
    path = _get_session_path(session_id)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _load_session(session_id: str) -> dict | None:
    path = _get_session_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_strategy_cascade(strategy_used: str, evidence_report: dict) -> dict:
    """Build the S1-S4 cascade data for the frontend."""
    paper_count = evidence_report.get("total_evidence_papers", 0)
    strats = ["S1_narrow", "S2_relaxed", "S3_task_only", "S4_global"]
    labels = {
        "S1_narrow": "Task + Model + Dataset",
        "S2_relaxed": "Task + Model",
        "S3_task_only": "Task Only",
        "S4_global": "Global (All Papers)",
    }
    result = {}
    found_selected = False
    for s in strats:
        if s == strategy_used:
            result[s] = {"status": "selected", "papers": paper_count, "label": labels[s]}
            found_selected = True
        elif not found_selected:
            result[s] = {"status": "skipped", "papers": 0, "label": labels[s]}
        else:
            result[s] = {"status": "pending", "papers": 0, "label": labels[s]}
    return result


def _build_inference_trace(param: str, per_param_report: dict, strategy_used: str, model: str, task: str) -> list[str]:
    """Build a human-readable reasoning trace for a given HP."""
    pp = per_param_report.get(param, {})
    raw = pp.get("raw_values", [])
    agg = pp.get("aggregated", {})
    conf = pp.get("confidence", {})

    trace = [
        f"Searched 435 papers in FAISS index (384-dim sentence vectors)",
        f"Strategy {strategy_used}: filtered to {task}+{model} papers",
    ]

    if raw:
        vals = [str(r["value"]) for r in raw]
        trace.append(f"Found {param} in {len(raw)} evidence papers: [{', '.join(vals)}]")
        weights = [f"Paper{i+1}: sim={r['similarity']:.2f}, rscore={r['rscore']:.2f}" for i, r in enumerate(raw[:4])]
        trace.append(f"Evidence weights (similarity × rscore):\n  " + "\n  ".join(weights))
        if agg.get("value") is not None:
            trace.append(f"Applied {agg.get('method', 'weighted_median')} → {agg['value']}")
        sim = conf.get("similarity", 0.0)
        agr = conf.get("agreement", 0.0)
        sup = conf.get("support", 0.0)
        total = conf.get("confidence", 0.0)
        trace.append(
            f"Confidence: similarity={sim:.2f}, agreement={agr:.2f}, "
            f"support={sup:.2f} → {total*100:.1f}%"
        )
    else:
        trace.append(f"No evidence found for {param} in matched papers")
        trace.append(f"Falling back to BERT default (Devlin et al., 2019)")

    return trace


def _build_distribution(raw_values: list) -> list[dict]:
    """Build histogram distribution data from raw evidence values."""
    from collections import Counter
    vals = [str(r["value"]) for r in raw_values if r.get("value") is not None]
    counter = Counter(vals)
    return [{"v": k, "count": v} for k, v in sorted(counter.items(), key=lambda x: x[0])]


def _enrich_config(inferred_config: dict, evidence_report: dict, user_result: dict, strategy_used: str) -> dict:
    """Attach trace, decomposition, and distribution data to each HP entry."""
    per_param = evidence_report.get("per_param", {})
    task = user_result.get("task", "unknown")
    model = user_result.get("model", "BERT")
    enriched = {}

    for param, entry in inferred_config.items():
        pp = per_param.get(param, {})
        raw = pp.get("raw_values", [])
        conf_obj = pp.get("confidence", {})

        # Decomposition scores
        sim = round(conf_obj.get("similarity", 0.0) * 100)
        agr = round(conf_obj.get("agreement", 0.0) * 100)
        sup = round(conf_obj.get("support", 0.0) * 100)

        entry_conf = entry.get("confidence", 0.0)
        source = entry.get("source", "bert_default")
        papers_count = len(raw) if raw else None

        enriched[param] = {
            **entry,
            "confidence_pct": round(entry_conf * 100, 1),
            "papers": papers_count,
            "confidence_decomposition": {
                "similarity": sim,
                "agreement": agr,
                "support": sup,
            },
            "inference_trace": _build_inference_trace(param, per_param, strategy_used, model, task),
            "distribution": _build_distribution(raw),
        }
    return enriched


def _generate_python_script(validated_config: dict, paper_info: dict) -> str:
    """Generate a HuggingFace TrainingArguments Python script."""
    lines = [
        "# HyperBERT — Auto-Generated Training Script",
        f"# Paper: {paper_info.get('title', 'Unknown')[:80]}",
        f"# Task: {paper_info.get('task', 'unknown')} | Model: {paper_info.get('model', 'BERT')}",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "from transformers import TrainingArguments, Trainer",
        "",
        "training_args = TrainingArguments(",
        '    output_dir="./results",',
    ]

    param_map = {
        "learning_rate": "learning_rate",
        "batch_size": "per_device_train_batch_size",
        "epochs": "num_train_epochs",
        "weight_decay": "weight_decay",
        "warmup_steps": "warmup_steps",
        "warmup_ratio": "warmup_ratio",
        "max_seq_length": None,  # not a TrainingArguments param
        "gradient_clipping": "max_grad_norm",
        "seed": "seed",
    }

    for param, hf_param in param_map.items():
        if hf_param is None:
            continue
        entry = validated_config.get(param, {})
        val = entry.get("value") if isinstance(entry, dict) else entry
        src = entry.get("source", "") if isinstance(entry, dict) else ""
        conf = entry.get("confidence_pct", entry.get("confidence", 0) * 100 if isinstance(entry, dict) else 0)
        if val is not None:
            comment = f"  # {src} — {conf:.0f}% confidence"
            lines.append(f"    {hf_param}={repr(val)},{comment}")

    lines += [
        ")",
        "",
        "# TODO: Add your model, tokenizer, and dataset",
        "# trainer = Trainer(model=model, args=training_args, ...)",
        "# trainer.train()",
    ]
    return "\n".join(lines)


def _generate_yaml_config(validated_config: dict, paper_info: dict) -> str:
    """Generate a YAML config file."""
    import yaml
    data = {
        "hyperbert_generated": True,
        "paper": {
            "title": paper_info.get("title", ""),
            "task": paper_info.get("task", ""),
            "model": paper_info.get("model", ""),
        },
        "hyperparameters": {
            param: {
                "value": (entry.get("value") if isinstance(entry, dict) else entry),
                "source": (entry.get("source", "") if isinstance(entry, dict) else ""),
                "confidence_pct": (entry.get("confidence_pct", 0) if isinstance(entry, dict) else 0),
            }
            for param, entry in validated_config.items()
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


# ══════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "mongo": MONGO_OK,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Main endpoint: Accept PDF upload → run M1-M7 → return enriched result."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Send PDF as 'file' field."}), 400

    uploaded = request.files["file"]
    if not uploaded.filename or not uploaded.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    session_id = str(uuid.uuid4())
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = session_dir / "paper.pdf"
    uploaded.save(str(pdf_path))

    audit_log = []

    def log(module: str, msg: str):
        entry = {"module": module, "timestamp": datetime.now(timezone.utc).isoformat(), "message": msg}
        audit_log.append(entry)
        print(f"[{module}] {msg}")

    try:
        (analyze_pdf, check_completeness, InferenceEngine,
         apply_constraints, detect_contradictions,
         validate_config, generate_notebook) = _load_pipeline_modules()

        # ── M1 ──────────────────────────────────────────────────────
        log("M1", f"Processing PDF: {uploaded.filename}")
        t0 = time.perf_counter()
        user_result = analyze_pdf(str(pdf_path))
        log("M1", f"Extracted {len(user_result.get('text',''))} chars, task={user_result.get('task')}, model={user_result.get('model')}")

        present_hps = {k: v for k, v in user_result.get("hyperparameters", {}).items() if v is not None}
        log("M1", f"Found {len(present_hps)} explicit HPs: {list(present_hps.keys())}")

        user_hp_json = {
            "model": user_result.get("model"),
            "task": user_result.get("task"),
            "dataset": user_result.get("dataset"),
            "hyperparameters": user_result.get("hyperparameters", {}),
            "missing_params": user_result.get("missing_params", []),
            "confidence": user_result.get("confidence", 0.0),
        }

        # ── M2 ──────────────────────────────────────────────────────
        log("M2", "Computing R-Score and completeness")
        completeness = check_completeness(
            user_hp_json,
            weights=CONFIG.get("rscore", {}).get("weights"),
        )
        log("M2", f"R-Score={completeness['rscore']:.3f}, completeness={completeness['completeness_pct']}%, missing={len(completeness['missing_params'])} HPs")

        # Reproducibility score (0-100)
        repro_score = round(completeness["completeness_pct"], 1)

        # ── M3 ──────────────────────────────────────────────────────
        evidence_report = {}
        inferred_config = {}
        strategy_used = "none"
        strategy_cascade = {}

        if completeness["needs_inference"] and MONGO_OK:
            log("M3", "Starting FAISS evidence retrieval")
            engine = InferenceEngine(CONFIG, DB)
            result = engine.infer(
                user_hp_json=user_hp_json,
                missing_params=completeness["missing_params"],
                title=user_result.get("title", ""),
                abstract=user_result.get("abstract", ""),
            )
            inferred_config = result["inferred_config"]
            evidence_report = result["evidence_report"]
            strategy_used = result["strategy_used"]
            strategy_cascade = _build_strategy_cascade(strategy_used, evidence_report)
            log("M3", f"Strategy={strategy_used}, evidence_papers={evidence_report.get('total_evidence_papers', 0)}")
        else:
            log("M3", "Skipped — all HPs present or MongoDB unavailable")
            for param, value in user_hp_json["hyperparameters"].items():
                inferred_config[param] = {
                    "value": value,
                    "source": "extracted_from_paper" if value is not None else "bert_default",
                    "confidence": 1.0 if value is not None else 0.2,
                }
            strategy_cascade = _build_strategy_cascade("none", {})

        # ── M4 ──────────────────────────────────────────────────────
        log("M4", "Applying domain constraints")
        constraint_result = apply_constraints(inferred_config, task=user_hp_json.get("task"))
        inferred_config = constraint_result["config"]
        adjustments = constraint_result["adjustments"]
        for adj in adjustments:
            log("M4", f"Adjusted {adj['param']}: {adj['reason']}")

        # ── M5 ──────────────────────────────────────────────────────
        log("M5", "Running contradiction / outlier detection")
        contradiction_report = detect_contradictions(evidence_report)
        log("M5", contradiction_report.get("summary", "Complete"))

        # ── M6 ──────────────────────────────────────────────────────
        log("M6", "Running self-critique validator")
        validation_result = validate_config(inferred_config)
        validated_config = validation_result["validated_config"]
        log("M6", f"Verdict: {validation_result['verdict']}")

        # ── M7 ──────────────────────────────────────────────────────
        log("M7", "Generating Jupyter notebook")
        nb_path = generate_notebook(
            validated_config=validated_config,
            evidence_report=evidence_report,
            user_hp_json=user_hp_json,
            contradiction_report=contradiction_report,
            validation_result=validation_result,
            output_path=str(session_dir / "training_notebook.ipynb"),
        )
        log("M7", f"Notebook: {nb_path}")

        elapsed = round(time.perf_counter() - t0, 2)
        log("DONE", f"Pipeline complete in {elapsed}s")

        # ── M8: LLM Comparison (async-safe, optional) ────────────────
        llm_comparison = None
        try:
            from src.module8.llm_baseline import run_llm_comparison
            if completeness["missing_params"]:
                log("M8", "Running LLM comparison (Gemini primary, Groq fallback)")
                llm_comparison = run_llm_comparison(
                    task=user_hp_json.get("task", ""),
                    model=user_hp_json.get("model", "BERT"),
                    dataset=user_hp_json.get("dataset", ""),
                    missing_params=completeness["missing_params"],
                    rag_config=validated_config,
                    gemini_key=os.environ.get("GEMINI_API_KEY"),
                    groq_key=os.environ.get("GROQ_API_KEY"),
                )
                summary = llm_comparison.get("comparison", {}).get("summary", {})
                log("M8", f"LLM comparison: {summary.get('agreed', 0)}/{summary.get('total_compared', 0)} params agree ({summary.get('agreement_pct', 0)}%)")
        except Exception as llm_err:
            log("M8", f"LLM comparison skipped: {llm_err}")
            llm_comparison = None

        # ── M8b: Meta-Reasoning Agent ────────────────────────────────
        agent_result = None
        try:
            from src.module8.meta_agent import run_meta_agent
            log("M8b", "Running meta-reasoning agent")
            agent_result = run_meta_agent(
                inferred_config=validated_config,
                per_param_confidence={},
                paper_info={
                    "task": user_hp_json.get("task", ""),
                    "model": user_hp_json.get("model", "BERT"),
                    "dataset": user_hp_json.get("dataset", ""),
                },
                missing_params=completeness["missing_params"],
                gemini_key=os.environ.get("GEMINI_API_KEY"),
                groq_key=os.environ.get("GROQ_API_KEY"),
            )
            # Use agent-enhanced config for downstream
            validated_config = agent_result.get("enhanced_config", validated_config)
            summary = agent_result.get("agent_summary", {})
            log("M8b", f"Agent: {summary.get('accepted', 0)} accepted, "
                       f"{summary.get('confidence_boosted', 0)} boosted, "
                       f"{summary.get('llm_overridden', 0)} LLM-overridden")
        except Exception as agent_err:
            log("M8b", f"Meta-agent skipped: {agent_err}")
            agent_result = None

        # ── Enrich config with trace + decomposition ─────────────────
        enriched_config = _enrich_config(validated_config, evidence_report, user_result, strategy_used)

        # ── Generate additional exports ──────────────────────────────
        paper_info = {
            "title": user_result.get("title", ""),
            "task": user_result.get("task", ""),
            "model": user_result.get("model", ""),
        }
        py_script = _generate_python_script(enriched_config, paper_info)
        (session_dir / "training_script.py").write_text(py_script, encoding="utf-8")

        try:
            yaml_config = _generate_yaml_config(enriched_config, paper_info)
            (session_dir / "config.yaml").write_text(yaml_config, encoding="utf-8")
        except ImportError:
            (session_dir / "config.yaml").write_text("# yaml package not installed\n", encoding="utf-8")

        # ── Build response ────────────────────────────────────────────
        response = {
            "session_id": session_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_seconds": elapsed,

            "paper": {
                "title": user_result.get("title", ""),
                "task": user_result.get("task"),
                "model": user_result.get("model"),
                "dataset": user_result.get("dataset"),
                "reproducibility_score": repro_score,
                "explicit_hp_count": len(present_hps),
                "total_hp_count": 12,
            },

            "completeness": {
                "rscore": completeness["rscore"],
                "present_params": list(present_hps.keys()),
                "missing_params": completeness["missing_params"],
                "completeness_pct": completeness["completeness_pct"],
                "needs_inference": completeness["needs_inference"],
            },

            "strategy_cascade": strategy_cascade,
            "strategy_used": strategy_used,

            "config": enriched_config,

            "evidence_papers": evidence_report.get("papers", [])[:10],

            "constraints": [
                {
                    "param": adj["param"],
                    "rule": adj.get("rule", "Domain Rule"),
                    "old_value": adj.get("old_value"),
                    "new_value": adj.get("new_value"),
                    "explanation": adj.get("reason", ""),
                    "citation": adj.get("citation", ""),
                }
                for adj in adjustments
            ],

            "contradictions": contradiction_report.get("contradictions", []),
            "contradiction_summary": contradiction_report.get("summary", "No contradictions detected"),

            "validation": {
                "verdict": validation_result["verdict"],
                "errors": validation_result.get("errors", []),
                "corrections": validation_result.get("corrections", []),
                "warnings": validation_result.get("warnings", []),
            },

            "audit_log": audit_log,

            "llm_comparison": llm_comparison,

            "agent_decisions": agent_result.get("agent_decisions", []) if agent_result else [],
            "agent_summary": agent_result.get("agent_summary", {}) if agent_result else {},
        }

        _save_session(session_id, response)
        return jsonify(response), 200

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"❌ Pipeline error: {err}")
        return jsonify({"error": str(e), "traceback": err}), 500


# ── SSE Streaming Analyze endpoint ─────────────────────────────────────

@app.route("/api/analyze-stream", methods=["POST"])
def analyze_stream():
    """Stream pipeline progress via Server-Sent Events.
    Each module completion sends an event so the frontend can update in real-time.
    Final event contains the complete result JSON."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    uploaded = request.files["file"]
    if not uploaded.filename or not uploaded.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    session_id = str(uuid.uuid4())
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = session_dir / "paper.pdf"
    uploaded.save(str(pdf_path))

    # We need to read the file data before streaming since the request context will be active
    filename = uploaded.filename

    def generate():
        audit_log = []

        def log(module, msg):
            entry = {"module": module, "timestamp": datetime.now(timezone.utc).isoformat(), "message": msg}
            audit_log.append(entry)
            print(f"[{module}] {msg}")

        def emit(module, step, message):
            """Send an SSE event to the client."""
            data = json.dumps({"module": module, "step": step, "message": message})
            return f"data: {data}\n\n"

        try:
            (analyze_pdf, check_completeness, InferenceEngine,
             apply_constraints, detect_contradictions,
             validate_config, generate_notebook) = _load_pipeline_modules()

            # ── M1 ──
            log("M1", f"Processing PDF: {filename}")
            yield emit("M1", 1, f"Processing PDF: {filename}")
            t0 = time.perf_counter()
            user_result = analyze_pdf(str(pdf_path))
            m1_msg = f"Extracted {len(user_result.get('text',''))} chars, task={user_result.get('task')}, model={user_result.get('model')}"
            log("M1", m1_msg)
            present_hps = {k: v for k, v in user_result.get("hyperparameters", {}).items() if v is not None}
            log("M1", f"Found {len(present_hps)} explicit HPs: {list(present_hps.keys())}")
            yield emit("M1", 1, f"{len(user_result.get('text',''))} chars, {len(present_hps)} HPs found")

            user_hp_json = {
                "model": user_result.get("model"),
                "task": user_result.get("task"),
                "dataset": user_result.get("dataset"),
                "hyperparameters": user_result.get("hyperparameters", {}),
                "missing_params": user_result.get("missing_params", []),
                "confidence": user_result.get("confidence", 0.0),
            }

            # ── M2 ──
            yield emit("M2", 2, "Computing R-Score and completeness")
            log("M2", "Computing R-Score and completeness")
            completeness = check_completeness(user_hp_json, weights=CONFIG.get("rscore", {}).get("weights"))
            m2_msg = f"R-Score={completeness['rscore']:.3f}, {completeness['completeness_pct']}% complete"
            log("M2", m2_msg)
            yield emit("M2", 2, m2_msg)

            repro_score = round(completeness["completeness_pct"], 1)

            # ── M3 ──
            evidence_report = {}
            inferred_config = {}
            strategy_used = "none"
            strategy_cascade = {}

            if completeness["needs_inference"] and MONGO_OK:
                yield emit("M3", 3, "Starting FAISS evidence retrieval")
                log("M3", "Starting FAISS evidence retrieval")
                engine = InferenceEngine(CONFIG, DB)
                result = engine.infer(
                    user_hp_json=user_hp_json,
                    missing_params=completeness["missing_params"],
                    title=user_result.get("title", ""),
                    abstract=user_result.get("abstract", ""),
                )
                inferred_config = result["inferred_config"]
                evidence_report = result["evidence_report"]
                strategy_used = result["strategy_used"]
                strategy_cascade = _build_strategy_cascade(strategy_used, evidence_report)
                m3_msg = f"Strategy={strategy_used}, {evidence_report.get('total_evidence_papers', 0)} papers"
                log("M3", m3_msg)
                yield emit("M3", 3, m3_msg)
            else:
                log("M3", "Skipped — all HPs present or MongoDB unavailable")
                for param, value in user_hp_json["hyperparameters"].items():
                    inferred_config[param] = {
                        "value": value,
                        "source": "extracted_from_paper" if value is not None else "bert_default",
                        "confidence": 1.0 if value is not None else 0.2,
                    }
                strategy_cascade = _build_strategy_cascade("none", {})
                yield emit("M3", 3, "Skipped — all HPs present")

            # ── M4 ──
            yield emit("M4", 4, "Applying domain constraints")
            log("M4", "Applying domain constraints")
            constraint_result = apply_constraints(inferred_config, task=user_hp_json.get("task"))
            inferred_config = constraint_result["config"]
            adjustments = constraint_result["adjustments"]
            m4_msg = f"{len(adjustments)} adjustments applied"
            for adj in adjustments:
                log("M4", f"Adjusted {adj['param']}: {adj['reason']}")
            yield emit("M4", 4, m4_msg)

            # ── M5 ──
            yield emit("M5", 5, "Running contradiction detection")
            log("M5", "Running contradiction / outlier detection")
            contradiction_report = detect_contradictions(evidence_report)
            m5_msg = contradiction_report.get("summary", "No contradictions")
            log("M5", m5_msg)
            yield emit("M5", 5, m5_msg[:50])

            # ── M6 ──
            yield emit("M6", 6, "Running self-critique validator")
            log("M6", "Running self-critique validator")
            validation_result = validate_config(inferred_config)
            validated_config = validation_result["validated_config"]
            m6_msg = f"Verdict: {validation_result['verdict']}"
            log("M6", m6_msg)
            yield emit("M6", 6, m6_msg)

            # ── M7 ──
            yield emit("M7", 7, "Generating Jupyter notebook")
            log("M7", "Generating Jupyter notebook")
            nb_path = generate_notebook(
                validated_config=validated_config,
                evidence_report=evidence_report,
                user_hp_json=user_hp_json,
                contradiction_report=contradiction_report,
                validation_result=validation_result,
                output_path=str(session_dir / "training_notebook.ipynb"),
            )
            log("M7", f"Notebook: {nb_path}")
            yield emit("M7", 7, "training_notebook.ipynb created")

            elapsed = round(time.perf_counter() - t0, 2)
            log("DONE", f"Pipeline complete in {elapsed}s")

            # ── M8: LLM Comparison ──
            llm_comparison = None
            try:
                from src.module8.llm_baseline import run_llm_comparison
                if completeness["missing_params"]:
                    yield emit("M8", 8, "Running LLM comparison")
                    log("M8", "Running LLM comparison")
                    llm_comparison = run_llm_comparison(
                        task=user_hp_json.get("task", ""),
                        model=user_hp_json.get("model", "BERT"),
                        dataset=user_hp_json.get("dataset", ""),
                        missing_params=completeness["missing_params"],
                        rag_config=validated_config,
                        gemini_key=os.environ.get("GEMINI_API_KEY"),
                        groq_key=os.environ.get("GROQ_API_KEY"),
                    )
                    summary = llm_comparison.get("comparison", {}).get("summary", {})
                    m8_msg = f"{summary.get('agreed', 0)}/{summary.get('total_compared', 0)} agree"
                    log("M8", m8_msg)
                    yield emit("M8", 8, m8_msg)
            except Exception as llm_err:
                log("M8", f"LLM comparison skipped: {llm_err}")
                yield emit("M8", 8, "Skipped")

            # ── M8b: Meta-Agent ──
            agent_result = None
            try:
                from src.module8.meta_agent import run_meta_agent
                log("M8b", "Running meta-reasoning agent")
                agent_result = run_meta_agent(
                    inferred_config=validated_config,
                    per_param_confidence={},
                    paper_info={
                        "task": user_hp_json.get("task", ""),
                        "model": user_hp_json.get("model", "BERT"),
                        "dataset": user_hp_json.get("dataset", ""),
                    },
                    missing_params=completeness["missing_params"],
                    gemini_key=os.environ.get("GEMINI_API_KEY"),
                    groq_key=os.environ.get("GROQ_API_KEY"),
                )
                validated_config = agent_result.get("enhanced_config", validated_config)
            except Exception:
                agent_result = None

            # Enrich + exports (same as /api/analyze)
            enriched_config = _enrich_config(validated_config, evidence_report, user_result, strategy_used)
            paper_info = {"title": user_result.get("title", ""), "task": user_result.get("task", ""), "model": user_result.get("model", "")}
            py_script = _generate_python_script(enriched_config, paper_info)
            (session_dir / "training_script.py").write_text(py_script, encoding="utf-8")
            try:
                yaml_config = _generate_yaml_config(enriched_config, paper_info)
                (session_dir / "config.yaml").write_text(yaml_config, encoding="utf-8")
            except ImportError:
                (session_dir / "config.yaml").write_text("# yaml package not installed\n", encoding="utf-8")

            response = {
                "session_id": session_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_seconds": elapsed,
                "paper": {
                    "title": user_result.get("title", ""),
                    "task": user_result.get("task"),
                    "model": user_result.get("model"),
                    "dataset": user_result.get("dataset"),
                    "reproducibility_score": repro_score,
                    "explicit_hp_count": len(present_hps),
                    "total_hp_count": 12,
                },
                "completeness": {
                    "rscore": completeness["rscore"],
                    "present_params": list(present_hps.keys()),
                    "missing_params": completeness["missing_params"],
                    "completeness_pct": completeness["completeness_pct"],
                    "needs_inference": completeness["needs_inference"],
                },
                "strategy_cascade": strategy_cascade,
                "strategy_used": strategy_used,
                "config": enriched_config,
                "evidence_papers": evidence_report.get("papers", [])[:10],
                "constraints": [
                    {"param": adj["param"], "rule": adj.get("rule", "Domain Rule"),
                     "old_value": adj.get("old_value"), "new_value": adj.get("new_value"),
                     "explanation": adj.get("reason", ""), "citation": adj.get("citation", "")}
                    for adj in adjustments
                ],
                "contradictions": contradiction_report.get("contradictions", []),
                "contradiction_summary": contradiction_report.get("summary", "No contradictions detected"),
                "validation": {
                    "verdict": validation_result["verdict"],
                    "errors": validation_result.get("errors", []),
                    "corrections": validation_result.get("corrections", []),
                    "warnings": validation_result.get("warnings", []),
                },
                "audit_log": audit_log,
                "llm_comparison": llm_comparison,
                "agent_decisions": agent_result.get("agent_decisions", []) if agent_result else [],
                "agent_summary": agent_result.get("agent_summary", {}) if agent_result else {},
            }

            _save_session(session_id, response)

            # Final result event
            yield f"event: result\ndata: {json.dumps(response)}\n\n"

        except Exception as e:
            import traceback
            err_msg = str(e)
            print(f"❌ Pipeline error: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'error': err_msg})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    data = _load_session(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(data), 200


# ── Download endpoints ─────────────────────────────────────────────────

def _ensure_download_files(session_id: str) -> dict | None:
    """Ensure all downloadable files exist for a session.
    Auto-generates any missing ones from the session JSON data.
    Returns session data or None if session doesn't exist."""
    data = _load_session(session_id)
    if data is None:
        return None

    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    config = data.get("config", {})

    # Auto-generate notebook if missing
    nb_path = session_dir / "training_notebook.ipynb"
    if not nb_path.exists() and config:
        try:
            from src.module7.notebook_gen import generate_notebook
            generate_notebook(
                validated_config=config,
                evidence_report=data.get("evidence_report", {}),
                user_hp_json={
                    "task": data.get("paper", {}).get("task", ""),
                    "model": data.get("paper", {}).get("model", "BERT"),
                    "dataset": data.get("paper", {}).get("dataset", ""),
                    "hyperparameters": {k: v.get("value") for k, v in config.items()},
                },
                contradiction_report=data.get("contradictions", {}),
                validation_result=data.get("validation", {"verdict": "OK", "validated_config": config}),
                output_path=str(nb_path),
            )
        except Exception as exc:
            print(f"[DOWNLOAD] Auto-generate notebook failed: {exc}")

    # Auto-generate training script if missing
    script_path = session_dir / "training_script.py"
    if not script_path.exists() and config:
        try:
            lines = [
                '"""Auto-generated HyperBERT Training Script"""',
                "from transformers import TrainingArguments, Trainer, AutoModelForSequenceClassification, AutoTokenizer",
                "",
                f"model_name = \"{data.get('paper', {}).get('model', 'bert-base-uncased')}\"",
                "tokenizer = AutoTokenizer.from_pretrained(model_name)",
                "model = AutoModelForSequenceClassification.from_pretrained(model_name)",
                "",
                "training_args = TrainingArguments(",
                "    output_dir='./results',",
            ]
            for param, entry in config.items():
                val = entry.get("value")
                conf = entry.get("confidence_pct", 0)
                src = entry.get("source", "unknown")
                if val is not None:
                    val_str = f"'{val}'" if isinstance(val, str) else str(val)
                    lines.append(f"    {param}={val_str},  # {src} (confidence: {conf}%)")
            lines.extend([")", "", "# trainer = Trainer(model=model, args=training_args, ...)", ""])
            script_path.write_text("\n".join(lines), encoding="utf-8")
        except Exception as exc:
            print(f"[DOWNLOAD] Auto-generate script failed: {exc}")

    # Auto-generate YAML config if missing
    yaml_path = session_dir / "config.yaml"
    if not yaml_path.exists() and config:
        try:
            import yaml
            yaml_data = {"hyperparameters": {}, "metadata": {
                "model": data.get("paper", {}).get("model"),
                "task": data.get("paper", {}).get("task"),
            }}
            for param, entry in config.items():
                yaml_data["hyperparameters"][param] = {
                    "value": entry.get("value"),
                    "source": entry.get("source"),
                    "confidence_pct": entry.get("confidence_pct"),
                }
            yaml_path.write_text(yaml.dump(yaml_data, default_flow_style=False), encoding="utf-8")
        except Exception as exc:
            print(f"[DOWNLOAD] Auto-generate YAML failed: {exc}")

    return data


@app.route("/api/download/<session_id>/notebook", methods=["GET"])
def download_notebook(session_id: str):
    data = _ensure_download_files(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404
    path = SESSIONS_DIR / session_id / "training_notebook.ipynb"
    if not path.exists():
        return jsonify({"error": "Could not generate notebook for this session"}), 404
    return send_file(str(path), as_attachment=True, download_name="training_notebook.ipynb",
                     mimetype="application/json")


@app.route("/api/download/<session_id>/script", methods=["GET"])
def download_script(session_id: str):
    data = _ensure_download_files(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404
    path = SESSIONS_DIR / session_id / "training_script.py"
    if not path.exists():
        return jsonify({"error": "Could not generate script for this session"}), 404
    return send_file(str(path), as_attachment=True, download_name="training_script.py",
                     mimetype="text/plain")


@app.route("/api/download/<session_id>/yaml", methods=["GET"])
def download_yaml(session_id: str):
    data = _ensure_download_files(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404
    path = SESSIONS_DIR / session_id / "config.yaml"
    if not path.exists():
        return jsonify({"error": "Could not generate YAML for this session"}), 404
    return send_file(str(path), as_attachment=True, download_name="hyperbert_config.yaml",
                     mimetype="text/yaml")


@app.route("/api/download/<session_id>/config", methods=["GET"])
def download_config(session_id: str):
    data = _load_session(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404
    config_only = {param: {"value": e.get("value"), "source": e.get("source"), "confidence_pct": e.get("confidence_pct")}
                   for param, e in data.get("config", {}).items()}
    return jsonify(config_only), 200


@app.route("/api/compare/<session_id>", methods=["GET"])
def compare_session(session_id: str):
    """Return the LLM comparison data for a session."""
    data = _load_session(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404

    llm_comparison = data.get("llm_comparison")
    if llm_comparison:
        return jsonify({
            "session_id": session_id,
            "paper": data.get("paper", {}),
            "completeness": data.get("completeness", {}),
            "llm_comparison": llm_comparison,
        }), 200

    # If no comparison exists yet, run it on-demand
    try:
        from src.module8.llm_baseline import run_llm_comparison
        missing = data.get("completeness", {}).get("missing_params", [])
        if not missing:
            return jsonify({"error": "No missing parameters to compare"}), 400

        result = run_llm_comparison(
            task=data.get("paper", {}).get("task", ""),
            model=data.get("paper", {}).get("model", "BERT"),
            dataset=data.get("paper", {}).get("dataset", ""),
            missing_params=missing,
            rag_config=data.get("config", {}),
            gemini_key=os.environ.get("GEMINI_API_KEY"),
            groq_key=os.environ.get("GROQ_API_KEY"),
        )

        # Save it back for caching
        data["llm_comparison"] = result
        _save_session(session_id, data)

        return jsonify({
            "session_id": session_id,
            "paper": data.get("paper", {}),
            "completeness": data.get("completeness", {}),
            "llm_comparison": result,
        }), 200

    except Exception as e:
        return jsonify({"error": f"LLM comparison failed: {str(e)}"}), 500


# ── Corpus endpoints ───────────────────────────────────────────────────

@app.route("/api/corpus/papers", methods=["GET"])
def corpus_papers():
    """Return papers from MongoDB corpus with filtering."""
    if not MONGO_OK:
        # Return demo fallback data
        return jsonify({
            "total": 0,
            "page": 0,
            "per_page": 20,
            "papers": [],
            "info": "MongoDB unavailable. Start MongoDB to browse real corpus data."
        }), 200

    task = request.args.get("task")
    model = request.args.get("model")
    source = request.args.get("source")
    query = request.args.get("q")
    page = int(request.args.get("page", 0))
    per_page = int(request.args.get("per_page", 20))

    filt: dict = {}
    if task:
        filt["hp_json.task"] = {"$regex": task, "$options": "i"}
    if model:
        filt["hp_json.model"] = {"$regex": model, "$options": "i"}
    if source:
        filt["source"] = source
    if query:
        filt["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"abstract": {"$regex": query, "$options": "i"}},
        ]

    collection = DB[CONFIG["mongodb"].get("clean_collection", "papers_clean")]
    total = collection.count_documents(filt)
    raw_papers = list(
        collection.find(filt, {"_id": 0, "title": 1, "source": 1, "year": 1, "rscore": 1, "hp_json": 1})
        .skip(page * per_page)
        .limit(per_page)
    )

    papers = []
    for p in raw_papers:
        hp_data = p.get("hp_json", {})
        p["task"] = hp_data.get("task", "unknown")
        p["model"] = hp_data.get("model", "unknown")
        p["hyperparameters"] = hp_data.get("hyperparameters", {})
        if "hp_json" in p:
            del p["hp_json"]
        papers.append(p)

    return jsonify({"total": total, "page": page, "per_page": per_page, "papers": papers}), 200


@app.route("/api/corpus/stats", methods=["GET"])
def corpus_stats():
    """Return aggregate statistics about the corpus."""
    if not MONGO_OK:
        # Return demo stats so frontend still renders
        return jsonify({
            "total_papers": 435,
            "task_distribution": [
                {"task": "NER", "count": 142},
                {"task": "Text Classification", "count": 98},
                {"task": "Sentiment Analysis", "count": 67},
                {"task": "Question Answering", "count": 55},
                {"task": "Relation Extraction", "count": 38},
                {"task": "Other", "count": 35},
            ],
            "model_distribution": [
                {"model": "bert-base-uncased", "count": 165},
                {"model": "bert-base-cased", "count": 78},
                {"model": "bert-large-uncased", "count": 45},
                {"model": "scibert", "count": 42},
                {"model": "biobert", "count": 38},
            ],
            "hp_coverage": {
                hp: {"count": 0, "pct": pct}
                for hp, pct in [
                    ("learning_rate", 45), ("batch_size", 42), ("epochs", 38),
                    ("optimizer", 31), ("weight_decay", 18), ("max_seq_length", 22),
                    ("dropout", 15), ("scheduler", 12), ("warmup_steps", 10),
                    ("gradient_clipping", 6), ("seed", 8), ("warmup_ratio", 7),
                ]
            },
            "info": "Demo data — start MongoDB for live stats"
        }), 200

    collection = DB[CONFIG["mongodb"].get("clean_collection", "papers_clean")]
    total = collection.count_documents({})

    # Task distribution (data is nested inside hp_json)
    task_pipeline = [
        {"$project": {"task": {"$ifNull": ["$hp_json.task", "unknown"]}}},
        {"$group": {"_id": "$task", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    task_dist = [{"task": d["_id"] or "unknown", "count": d["count"]}
                 for d in collection.aggregate(task_pipeline)]

    # Model distribution
    model_pipeline = [
        {"$project": {"model": {"$ifNull": ["$hp_json.model", "unknown"]}}},
        {"$group": {"_id": "$model", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 10},
    ]
    model_dist = [{"model": d["_id"] or "unknown", "count": d["count"]}
                  for d in collection.aggregate(model_pipeline)]

    # HP coverage (hyperparameters are nested inside hp_json.hyperparameters)
    hp_fields = ["learning_rate", "batch_size", "epochs", "optimizer",
                 "max_seq_length", "weight_decay", "dropout", "scheduler",
                 "warmup_steps", "gradient_clipping", "seed", "warmup_ratio"]
    hp_coverage = {}
    for hp in hp_fields:
        count = collection.count_documents({f"hp_json.hyperparameters.{hp}": {"$ne": None, "$exists": True}})
        hp_coverage[hp] = {"count": count, "pct": round(count / total * 100, 1) if total else 0}

    return jsonify({
        "total_papers": total,
        "task_distribution": task_dist,
        "model_distribution": model_dist,
        "hp_coverage": hp_coverage,
    }), 200


# ── Notebook execution endpoints ───────────────────────────────────────

_jupyter_process = None
_JUPYTER_PORT = 8888


def _ensure_notebook_exists(session_id: str) -> Path | None:
    """Return the notebook path, generating it on-the-fly if the session
    data exists but the .ipynb was never created (e.g. pipeline crashed)."""
    session_dir = SESSIONS_DIR / session_id
    nb_path = session_dir / "training_notebook.ipynb"

    if nb_path.exists():
        return nb_path

    # Try to regenerate from saved session JSON
    data = _load_session(session_id)
    if data and data.get("config"):
        try:
            from src.module7.notebook_gen import generate_notebook
            session_dir.mkdir(parents=True, exist_ok=True)
            generate_notebook(
                validated_config=data["config"],
                evidence_report=data.get("evidence_report", {}),
                user_hp_json={
                    "task": data.get("paper", {}).get("task", ""),
                    "model": data.get("paper", {}).get("model", "BERT"),
                    "dataset": data.get("paper", {}).get("dataset", ""),
                    "hyperparameters": {k: v.get("value") for k, v in data["config"].items()},
                },
                contradiction_report=data.get("contradictions", {}),
                validation_result=data.get("validation", {"verdict": "OK", "validated_config": data["config"]}),
                output_path=str(nb_path),
            )
            return nb_path
        except Exception as exc:
            print(f"[NOTEBOOK] Auto-generate failed: {exc}")

    # Fallback: check test_results
    alt = ROOT / "test_results" / "training_notebook.ipynb"
    if alt.exists():
        return alt

    return None


def _wait_for_jupyter(port: int, timeout: float = 20.0) -> bool:
    """Poll JupyterLab until it responds or timeout."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/jupyter/api?token=hyperbert", timeout=2
            )
            return True
        except Exception:
            time.sleep(0.5)
    return False


@app.route("/api/launch-notebook/<session_id>", methods=["POST"])
def launch_notebook(session_id: str):
    """Launch JupyterLab with the session's generated notebook.
    Fully automatic: installs jupyterlab if needed, generates notebook
    if missing, and starts the server."""
    global _jupyter_process
    import subprocess

    # ── Step 1: Ensure the notebook file exists ──
    nb_path = _ensure_notebook_exists(session_id)
    if nb_path is None:
        return jsonify({
            "error": "No analysis data found for this session. Please upload a PDF first via the Upload page."
        }), 404
    nb_dir = nb_path.parent

    # ── Step 2: Kill any existing Jupyter server ──
    if _jupyter_process and _jupyter_process.poll() is None:
        _jupyter_process.terminate()
        try:
            _jupyter_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _jupyter_process.kill()
        _jupyter_process = None

    # ── Step 3: Auto-install jupyterlab if missing ──
    try:
        import jupyterlab  # noqa: F401
    except ImportError:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "jupyterlab"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Failed to auto-install JupyterLab: {e}"}), 500

    # ── Step 4: Build CSP headers for iframe embedding ──
    tornado_settings = json.dumps({
        "headers": {
            "Content-Security-Policy": "frame-ancestors *",
            "Access-Control-Allow-Origin": "*",
        }
    })

    # ── Step 5: Launch JupyterLab with base_url=/jupyter/ ──
    try:
        _jupyter_process = subprocess.Popen(
            [
                sys.executable, "-m", "jupyter", "lab",
                "--no-browser",
                "--ip=127.0.0.1",
                f"--port={_JUPYTER_PORT}",
                "--ServerApp.token=hyperbert",
                "--ServerApp.base_url=/jupyter/",
                "--ServerApp.allow_origin=*",
                f"--ServerApp.tornado_settings={tornado_settings}",
                "--ServerApp.disable_check_xsrf=True",
                f"--notebook-dir={nb_dir}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Poll for readiness instead of blind sleep
        if not _wait_for_jupyter(_JUPYTER_PORT, timeout=20):
            # Check if process died
            if _jupyter_process.poll() is not None:
                stderr_out = ""
                try:
                    stderr_out = _jupyter_process.stderr.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                return jsonify({"error": f"JupyterLab crashed on startup. {stderr_out[:300]}"}), 500
            # Still not responding but alive — give benefit of the doubt
            return jsonify({
                "error": "JupyterLab is starting but not yet responding. Try again in a few seconds."
            }), 503

        # Return proxied URL (goes through Vite's /jupyter proxy → same origin)
        url = f"/jupyter/lab/tree/{nb_path.name}?token=hyperbert"
        return jsonify({"url": url, "pid": _jupyter_process.pid}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to launch JupyterLab: {str(e)}"}), 500


@app.route("/api/stop-notebook", methods=["POST"])
def stop_notebook():
    """Stop the running JupyterLab server."""
    global _jupyter_process
    import subprocess

    if _jupyter_process and _jupyter_process.poll() is None:
        _jupyter_process.terminate()
        try:
            _jupyter_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _jupyter_process.kill()
        _jupyter_process = None
        return jsonify({"status": "stopped"}), 200

    return jsonify({"status": "not_running"}), 200


# ── Evaluation endpoints ───────────────────────────────────────────────

@app.route("/api/evaluation/loo", methods=["GET"])
def get_loo_results():
    """Return LOO evaluation results if available."""
    path = ROOT / "evaluation" / "loo_results.json"
    if not path.exists():
        return jsonify({"error": "LOO evaluation not yet run. Execute: python evaluation/loo_evaluation.py"}), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8"))), 200


@app.route("/api/evaluation/rag-vs-llm", methods=["GET"])
def get_rag_vs_llm_results():
    """Return RAG vs LLM evaluation results if available."""
    path = ROOT / "evaluation" / "rag_vs_llm_results.json"
    if not path.exists():
        return jsonify({"error": "RAG vs LLM evaluation not yet run. Execute: python evaluation/rag_vs_llm_eval.py"}), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8"))), 200



# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("  HyperBERT Backend API")
    print("  http://localhost:5000")
    print("  MongoDB:", "✅ connected" if MONGO_OK else "⚠️  unavailable")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
