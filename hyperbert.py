"""HyperBERT — Retrieval-Augmented Hyperparameter Inference for BERT.

Usage:
    python hyperbert.py infer --pdf paper.pdf --output results/
    python hyperbert.py infer --pdf paper.pdf --output results/ --config module0/config.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone


def setup_paths():
    """Add necessary directories to sys.path."""
    root = Path(__file__).resolve().parent
    # Add module0/src for HP schema/extraction imports
    module0_src = root / "module0" / "src"
    if str(module0_src) not in sys.path:
        sys.path.insert(0, str(module0_src))
    # Add project root for src.moduleX imports
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def load_config(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except Exception:
        pass


def infer(pdf_path: str, output_dir: str, config_path: str) -> None:
    """Run the full inference pipeline: M1 → M2 → M3 → M4 → M5 → M6 → M7."""
    from pymongo import MongoClient

    from src.module1.pdf_analyzer import analyze_pdf
    from src.module2.completeness import check_completeness
    from src.module3.engine import InferenceEngine
    from src.module4.constraints import apply_constraints
    from src.module5.contradictions import detect_contradictions
    from src.module6.validator import validate_config
    from src.module7.notebook_gen import generate_notebook

    config = load_config(config_path)
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Connect to MongoDB
    mongo = MongoClient(config["mongodb"]["uri"])
    db = mongo[config["mongodb"]["db"]]

    print("=" * 60)
    print("  HyperBERT — Retrieval-Augmented HP Inference")
    print("=" * 60)
    print(f"  PDF: {pdf_path}")
    print(f"  Output: {out}")
    print()

    # ==================== Module 1 ====================
    print("━" * 40)
    print("  Module 1: PDF Input Analyzer")
    print("━" * 40)
    user_result = analyze_pdf(pdf_path)
    print(f"  Title: {user_result.get('title', 'Unknown')[:80]}")
    print(f"  Task:  {user_result.get('task', 'Unknown')}")
    print(f"  Model: {user_result.get('model', 'Unknown')}")

    user_hp_json = {
        "model": user_result.get("model"),
        "task": user_result.get("task"),
        "dataset": user_result.get("dataset"),
        "hyperparameters": user_result.get("hyperparameters", {}),
        "missing_params": user_result.get("missing_params", []),
        "confidence": user_result.get("confidence", 0.0),
    }

    present_hps = {k: v for k, v in user_hp_json["hyperparameters"].items() if v is not None}
    print(f"  Extracted HPs: {len(present_hps)} → {list(present_hps.keys())}")

    # ==================== Module 2 ====================
    print()
    print("━" * 40)
    print("  Module 2: Completeness Checker")
    print("━" * 40)
    completeness = check_completeness(
        user_hp_json,
        weights=config.get("rscore", {}).get("weights"),
    )
    print(f"  R-Score: {completeness['rscore']:.3f}")
    print(f"  Completeness: {completeness['completeness_pct']}%")
    print(f"  Missing: {completeness['missing_params']}")
    print(f"  Needs inference: {completeness['needs_inference']}")

    # ==================== Module 3 ====================
    evidence_report = {}
    inferred_config = {}
    per_param_confidence = {}
    strategy_used = "none"

    if completeness["needs_inference"]:
        print()
        print("━" * 40)
        print("  Module 3: CORE Inference Engine")
        print("━" * 40)
        engine = InferenceEngine(config, db)
        result = engine.infer(
            user_hp_json=user_hp_json,
            missing_params=completeness["missing_params"],
            title=user_result.get("title", ""),
            abstract=user_result.get("abstract", ""),
        )
        inferred_config = result["inferred_config"]
        evidence_report = result["evidence_report"]
        per_param_confidence = result["per_param_confidence"]
        strategy_used = result["strategy_used"]
    else:
        # All HPs present — build config from user values directly
        print("\n  All critical HPs present — skipping inference.")
        for param, value in user_hp_json["hyperparameters"].items():
            inferred_config[param] = {
                "value": value,
                "source": "extracted_from_paper" if value is not None else "bert_default",
                "confidence": 1.0 if value is not None else 0.2,
            }

    # ==================== Module 4 ====================
    print()
    print("━" * 40)
    print("  Module 4: Constraint-Aware Inference")
    print("━" * 40)
    constraint_result = apply_constraints(
        inferred_config,
        task=user_hp_json.get("task"),
    )
    inferred_config = constraint_result["config"]
    adjustments = constraint_result["adjustments"]
    print(f"  Adjustments: {len(adjustments)}")
    for adj in adjustments:
        print(f"    • {adj['param']}: {adj['reason']}")

    # ==================== Module 5 ====================
    print()
    print("━" * 40)
    print("  Module 5: Contradiction Detector")
    print("━" * 40)
    contradiction_report = detect_contradictions(evidence_report)
    print(f"  {contradiction_report['summary']}")
    for c in contradiction_report.get("contradictions", [])[:3]:
        print(f"    • {c['message']}")

    # ==================== Module 6 ====================
    print()
    print("━" * 40)
    print("  Module 6: Self-Critique Validator")
    print("━" * 40)
    validation_result = validate_config(inferred_config)
    print(f"  Verdict: {validation_result['verdict']}")
    for err in validation_result.get("errors", []):
        print(f"    ❌ {err['message']}")
    for corr in validation_result.get("corrections", []):
        print(f"    🔧 {corr['message']}")
    for warn in validation_result.get("warnings", []):
        print(f"    ⚠️ {warn['message']}")

    validated_config = validation_result["validated_config"]

    # ==================== Module 7 ====================
    print()
    print("━" * 40)
    print("  Module 7: Notebook Generator")
    print("━" * 40)
    nb_path = generate_notebook(
        validated_config=validated_config,
        evidence_report=evidence_report,
        user_hp_json=user_hp_json,
        contradiction_report=contradiction_report,
        validation_result=validation_result,
        output_path=str(out / "training_notebook.ipynb"),
    )
    print(f"  Notebook: {nb_path}")

    # ==================== Save Outputs ====================
    # Save inferred config
    config_out = {
        param: {
            "value": entry.get("value") if isinstance(entry, dict) else entry,
            "source": entry.get("source", "") if isinstance(entry, dict) else "",
            "confidence": entry.get("confidence", 0) if isinstance(entry, dict) else 0,
        }
        for param, entry in validated_config.items()
    }
    (out / "inferred_config.json").write_text(
        json.dumps(config_out, indent=2, default=str), encoding="utf-8"
    )

    # Save evidence report
    (out / "evidence_report.json").write_text(
        json.dumps(evidence_report, indent=2, default=str), encoding="utf-8"
    )

    # Save full pipeline report
    full_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pdf_path": pdf_path,
        "user_extraction": {
            "title": user_result.get("title", ""),
            "task": user_hp_json.get("task"),
            "model": user_hp_json.get("model"),
            "extracted_hps": present_hps,
        },
        "completeness": completeness,
        "strategy_used": strategy_used,
        "constraints": adjustments,
        "contradictions": contradiction_report,
        "validation": {
            "verdict": validation_result["verdict"],
            "errors": validation_result.get("errors", []),
            "corrections": validation_result.get("corrections", []),
        },
        "final_config": config_out,
    }
    (out / "pipeline_report.json").write_text(
        json.dumps(full_report, indent=2, default=str), encoding="utf-8"
    )

    # ==================== Summary ====================
    print()
    print("=" * 60)
    print("  ✅ HyperBERT Inference Complete!")
    print("=" * 60)
    print()
    print("  Final Configuration:")
    for param in [
        "learning_rate", "batch_size", "epochs", "optimizer",
        "weight_decay", "max_seq_length", "scheduler",
    ]:
        entry = validated_config.get(param, {})
        val = entry.get("value", "—") if isinstance(entry, dict) else entry
        src = entry.get("source", "—") if isinstance(entry, dict) else "—"
        conf = entry.get("confidence", 0) if isinstance(entry, dict) else 0
        emoji = "🟢" if conf >= 0.7 else "🟡" if conf >= 0.3 else "🔴"
        print(f"    {param:20s} = {str(val):15s} {emoji} {src}")

    print()
    print(f"  Outputs saved to: {out}")
    print(f"    • inferred_config.json")
    print(f"    • evidence_report.json")
    print(f"    • pipeline_report.json")
    print(f"    • training_notebook.ipynb")

    mongo.close()


def main():
    setup_paths()
    load_env()

    parser = argparse.ArgumentParser(
        description="HyperBERT — Retrieval-Augmented HP Inference for BERT"
    )
    subparsers = parser.add_subparsers(dest="command")

    infer_parser = subparsers.add_parser("infer", help="Infer HPs from a paper PDF")
    infer_parser.add_argument("--pdf", required=True, help="Path to the paper PDF")
    infer_parser.add_argument("--output", required=True, help="Output directory")
    infer_parser.add_argument(
        "--config",
        default="module0/config.json",
        help="Path to config JSON (default: module0/config.json)",
    )

    args = parser.parse_args()

    if args.command == "infer":
        infer(args.pdf, args.output, args.config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
