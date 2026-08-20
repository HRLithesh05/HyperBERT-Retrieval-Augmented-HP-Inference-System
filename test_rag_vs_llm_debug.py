"""
RAG vs LLM (Qwen) Full Step-by-Step Debug Script
=================================================
This script tests the entire RAG vs LLM comparison pipeline with verbose 
debug prints at every single stage:

  [Step 1] Check Ollama Server & Model Availability (localhost:11434)
  [Step 2] Check Backend Server Status (localhost:5000)
  [Step 3] Locate or Load a Valid Analysis Session
  [Step 4] Test Direct Ollama Query & Print Raw Model Output
  [Step 5] Test Live Comparison Backend API Endpoint (/api/compare-live/<id>)
  [Step 6] Print Visual Comparison Table (RAG vs Qwen) & Summary

Usage:
  python test_rag_vs_llm_debug.py
  python test_rag_vs_llm_debug.py <optional_session_id>
"""

import sys
import os
import json
import time
import glob
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

OLLAMA_URL = "http://localhost:11434"
BACKEND_URL = "http://localhost:5000"


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num: int, title: str):
    print(f"\n[{step_num}/6] {title}")
    print("-" * 60)


def run_debug():
    print_header("HYPERBERT: RAG vs LLM (QWEN) STEP-BY-STEP DEBUG TRACER")

    # ─────────────────────────────────────────────────────────────────────────
    # [Step 1] Check Ollama Server
    # ─────────────────────────────────────────────────────────────────────────
    print_step(1, "Checking Ollama Service (http://localhost:11434)")
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            print(f"  --> Ollama Status : [ONLINE]")
            print(f"  --> Installed Models : {models}")
            
            has_qwen = any("qwen3" in m.lower() for m in models)
            if has_qwen:
                print(f"  --> Qwen3 Model    : [FOUND] (Ready for comparison)")
            else:
                print(f"  --> Qwen3 Model    : [NOT FOUND] (Run: ollama pull qwen3:4b)")
    except Exception as e:
        print(f"  --> Ollama Status : [FAILED / OFFLINE]")
        print(f"  --> Error Details : {e}")
        print("  [!] Please ensure Ollama is running in background.")

    # ─────────────────────────────────────────────────────────────────────────
    # [Step 2] Check Backend Server
    # ─────────────────────────────────────────────────────────────────────────
    print_step(2, "Checking Backend Server (http://localhost:5000)")
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/api/ollama/status", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  --> Backend Status  : [ONLINE]")
            print(f"  --> Endpoint Response: {json.dumps(data, indent=6)}")
    except Exception as e:
        print(f"  --> Backend Status  : [OFFLINE or NOT RESPONDING]")
        print(f"  --> Error Details   : {e}")
        print("  [!] Please start backend with: python backend/app.py")

    # ─────────────────────────────────────────────────────────────────────────
    # [Step 3] Locate Session
    # ─────────────────────────────────────────────────────────────────────────
    print_step(3, "Locating Analysis Session Data")
    session_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not session_id:
        # Search backend/sessions/*.json
        session_files = glob.glob(str(ROOT_DIR / "backend" / "sessions" / "*.json"))
        # Exclude metadata/non-uuid files if any
        valid_files = [f for f in session_files if os.path.basename(f) != "sessions.json"]
        
        if valid_files:
            # Sort by modification time (most recent first)
            valid_files.sort(key=os.path.getmtime, reverse=True)
            latest_file = valid_files[0]
            session_id = Path(latest_file).stem
            print(f"  --> Found {len(valid_files)} saved sessions on disk.")
            print(f"  --> Selected Most Recent Session: {session_id}")
        else:
            print("  [!] No session files found in backend/sessions/.")
            print("  [!] Creating a temporary mock test payload...")
            session_id = "test_mock_session"

    session_data = {}
    session_file_path = ROOT_DIR / "backend" / "sessions" / f"{session_id}.json"
    if session_file_path.exists():
        with open(session_file_path, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        paper = session_data.get("paper", {})
        print(f"  --> Paper Title    : {paper.get('title', 'Unknown')}")
        print(f"  --> Detected Task  : {paper.get('task', 'Unknown')}")
        print(f"  --> Detected Model : {paper.get('model', 'BERT')}")
        print(f"  --> Detected Dataset: {paper.get('dataset', 'Unknown')}")
        print(f"  --> RAG Strategy   : {session_data.get('strategy_used', 'Unknown')}")
    else:
        print(f"  --> Session File   : Not found on disk, will test with live endpoint directly.")

    # ─────────────────────────────────────────────────────────────────────────
    # [Step 4] Direct Query to Ollama Module
    # ─────────────────────────────────────────────────────────────────────────
    print_step(4, "Testing Direct Ollama Client Function (src/module8/ollama_client.py)")
    try:
        from src.module8.ollama_client import query_ollama_for_comparison

        task = session_data.get("paper", {}).get("task") or "ner"
        model_name = session_data.get("paper", {}).get("model") or "BERT"
        dataset = session_data.get("paper", {}).get("dataset") or "GLUE"
        test_params = ["learning_rate", "batch_size", "epochs", "max_seq_length", "dropout", "optimizer", "scheduler"]

        print(f"  --> Sending Query to Qwen3 via Ollama...")
        print(f"      - Task        : {task}")
        print(f"      - Model       : {model_name}")
        print(f"      - Dataset     : {dataset}")
        print(f"      - Parameters  : {test_params}")

        t0 = time.perf_counter()
        direct_result = query_ollama_for_comparison(
            task=task,
            model_name=model_name,
            dataset=dataset,
            missing_params=test_params,
        )
        elapsed_s = time.perf_counter() - t0

        print(f"\n  --> Direct Ollama Execution Time: {elapsed_s:.2f}s ({direct_result.get('latency_ms', 0)}ms)")
        print(f"  --> Error Field                 : {direct_result.get('error')}")
        print(f"  --> Raw LLM Response Output     :")
        print("      " + str(direct_result.get("raw_response", "")).replace("\n", "\n      "))
        print(f"\n  --> Parsed & Validated JSON Dictionary:")
        print(f"      {json.dumps(direct_result.get('suggestions', {}), indent=6)}")

    except Exception as e:
        print(f"  [!] Direct Ollama client call failed: {e}")
        import traceback
        traceback.print_exc()

    # ─────────────────────────────────────────────────────────────────────────
    # [Step 5] Test Live Comparison Backend API Endpoint
    # ─────────────────────────────────────────────────────────────────────────
    print_step(5, f"Calling Backend Endpoint: POST /api/compare-live/{session_id}")
    api_result = None
    try:
        req = urllib.request.Request(
            f"{BACKEND_URL}/api/compare-live/{session_id}",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=120) as resp:
            api_result = json.loads(resp.read().decode("utf-8"))
        elapsed_s = time.perf_counter() - t0

        print(f"  --> Backend API Response Status : 200 OK (in {elapsed_s:.2f}s)")
        llm_comp = api_result.get("llm_comparison", {})
        llm_res = llm_comp.get("llm_result", {})
        print(f"  --> LLM Source Reported        : {llm_res.get('source')}")
        print(f"  --> LLM Parse Error (if any)   : {llm_res.get('error')}")
    except Exception as e:
        print(f"  [!] Backend API call failed: {e}")
        if hasattr(e, "read"):
            print(f"      Response body: {e.read().decode('utf-8', errors='ignore')}")

    # ─────────────────────────────────────────────────────────────────────────
    # [Step 6] Visual Comparison Table
    # ─────────────────────────────────────────────────────────────────────────
    print_step(6, "Parameter Comparison Breakdown (RAG Inferred vs Qwen LLM)")

    if api_result and "llm_comparison" in api_result:
        comparison = api_result["llm_comparison"].get("comparison", {})
        per_param = comparison.get("per_param", {})
        summary = comparison.get("summary", {})

        print(f"\n{'PARAMETER':<20} | {'RAG VALUE':<15} | {'QWEN VALUE':<15} | {'MATCH?':<10} | {'RAG SOURCE':<18} | {'CONF'}")
        print("-" * 95)

        for param, details in per_param.items():
            rag_val = str(details.get("rag_value"))
            llm_val = str(details.get("llm_value"))
            agrees = details.get("agrees", False)
            match_str = "[AGREE]" if agrees else "[DIFF]"
            rag_src = details.get("rag_source", "unknown")
            rag_conf = f"{details.get('rag_confidence', 0)}%"

            print(f"{param:<20} | {rag_val:<15} | {llm_val:<15} | {match_str:<10} | {rag_src:<18} | {rag_conf}")

        print("-" * 95)
        print(f"Summary: Total Compared: {summary.get('total_compared', 0)} | "
              f"Agreed: {summary.get('agreed', 0)} | "
              f"Disagreed: {summary.get('disagreed', 0)} | "
              f"Agreement Rate: {summary.get('agreement_pct', 0)}%")
        print("=" * 95)
        print("DEBUG RUN COMPLETE: All steps executed successfully.")
    else:
        print("  [!] Could not render comparison table because backend response was incomplete.")


if __name__ == "__main__":
    run_debug()
