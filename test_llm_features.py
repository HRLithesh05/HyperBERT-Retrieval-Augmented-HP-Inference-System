"""
Automated Test Suite — HyperBERT LLM-Enhanced Extraction + Comparison
=====================================================================

Tests all new components:
  T1: Ollama Client — health check, JSON parsing, validation
  T2: Ollama Query — live comparison query  
  T3: Enhanced M1 — regex + LLM + merge pipeline
  T4: Backend Endpoints — Flask API tests
  T5: Frontend — TypeScript compilation check

Run: python test_llm_features.py
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

# Setup paths
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "module0" / "src"))

# ═══════════════════════════════════════════════════════════════════
# Test infrastructure
# ═══════════════════════════════════════════════════════════════════

class TestResults:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def add(self, suite: str, name: str, passed: bool, detail: str = "", duration: float = 0):
        self.results.append({
            "suite": suite,
            "name": name,
            "passed": passed,
            "detail": detail,
            "duration_ms": round(duration * 1000),
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        dur = f" ({duration*1000:.0f}ms)" if duration > 0 else ""
        print(f"  {status}  {name}{dur}")
        if not passed and detail:
            for line in detail.split("\n")[:5]:
                print(f"         {line}")
    
    def print_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        elapsed = time.time() - self.start_time
        
        print("\n" + "═" * 65)
        print(f"  TEST REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("═" * 65)
        
        # Group by suite
        suites = {}
        for r in self.results:
            suites.setdefault(r["suite"], []).append(r)
        
        for suite, tests in suites.items():
            suite_passed = sum(1 for t in tests if t["passed"])
            suite_total = len(tests)
            suite_status = "✅" if suite_passed == suite_total else "❌"
            print(f"\n  {suite_status} {suite} ({suite_passed}/{suite_total})")
            for t in tests:
                status = "✅" if t["passed"] else "❌"
                dur = f" [{t['duration_ms']}ms]" if t["duration_ms"] > 0 else ""
                print(f"     {status} {t['name']}{dur}")
                if not t["passed"] and t["detail"]:
                    for line in t["detail"].split("\n")[:3]:
                        print(f"        └─ {line}")
        
        print(f"\n{'─' * 65}")
        overall = "ALL TESTS PASSED ✅" if failed == 0 else f"{failed} TEST(S) FAILED ❌"
        print(f"  {overall}  |  {passed}/{total} passed  |  {elapsed:.1f}s total")
        print("─" * 65 + "\n")
        
        return failed == 0


results = TestResults()


# ═══════════════════════════════════════════════════════════════════
# T1: Ollama Client Unit Tests
# ═══════════════════════════════════════════════════════════════════

def test_ollama_client():
    print("\n🧪 T1: Ollama Client Unit Tests")
    print("─" * 40)
    
    # T1.1: Import test
    t0 = time.time()
    try:
        from src.module8.ollama_client import (
            check_ollama_health,
            query_ollama,
            query_ollama_for_extraction,
            query_ollama_for_comparison,
            _parse_llm_json,
            _validate_hp_values,
            BERT_HP_SCHEMA,
        )
        results.add("T1: Ollama Client", "Import all functions", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "Import all functions", False, str(e), time.time()-t0)
        return  # Can't continue
    
    # T1.2: Health check
    t0 = time.time()
    try:
        health = check_ollama_health()
        assert isinstance(health, dict), "Health should return dict"
        assert "running" in health, "Missing 'running' key"
        assert "models" in health, "Missing 'models' key"
        assert "has_qwen" in health, "Missing 'has_qwen' key"
        assert health["running"] is True, "Ollama not running"
        assert health["has_qwen"] is True, "Qwen3 model not found"
        results.add("T1: Ollama Client", "Health check — Ollama running + Qwen3 available", True, 
                    f"Models: {health['models']}", time.time()-t0)
    except AssertionError as e:
        results.add("T1: Ollama Client", "Health check", False, str(e), time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "Health check", False, str(e), time.time()-t0)
    
    # T1.3: JSON parsing — standard JSON
    t0 = time.time()
    try:
        parsed = _parse_llm_json('{"learning_rate": 2e-5, "batch_size": 32}')
        assert parsed["learning_rate"] == 2e-5
        assert parsed["batch_size"] == 32
        results.add("T1: Ollama Client", "Parse standard JSON", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "Parse standard JSON", False, str(e), time.time()-t0)
    
    # T1.4: JSON parsing — with think tags (Qwen3 specific)
    t0 = time.time()
    try:
        parsed = _parse_llm_json(
            '<think>Let me analyze this...</think>\n'
            '```json\n{"epochs": 3, "optimizer": "AdamW"}\n```'
        )
        assert parsed["epochs"] == 3
        assert parsed["optimizer"] == "AdamW"
        results.add("T1: Ollama Client", "Parse JSON with <think> tags + code block", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "Parse JSON with <think> tags + code block", False, str(e), time.time()-t0)
    
    # T1.5: JSON parsing — raw JSON without code blocks
    t0 = time.time()
    try:
        parsed = _parse_llm_json('Here is the result: {"dropout": 0.1, "seed": 42}')
        assert parsed["dropout"] == 0.1
        assert parsed["seed"] == 42
        results.add("T1: Ollama Client", "Parse raw JSON in text", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "Parse raw JSON in text", False, str(e), time.time()-t0)
    
    # T1.6: HP validation — type casting and clamping
    t0 = time.time()
    try:
        validated = _validate_hp_values({
            "learning_rate": "0.00002",
            "batch_size": "32.0",
            "epochs": 3,
            "optimizer": "adamw",  # Should match case-insensitively
            "weight_decay": 999,    # Should clamp to 0.5
        })
        assert validated["learning_rate"] == 2e-5, f"LR should be 2e-5, got {validated['learning_rate']}"
        assert validated["batch_size"] == 32, f"BS should be 32, got {validated['batch_size']}"
        assert validated["epochs"] == 3
        assert validated["optimizer"] == "AdamW", f"Optimizer should be AdamW, got {validated['optimizer']}"
        assert validated["weight_decay"] == 0.5, f"WD should be clamped to 0.5, got {validated['weight_decay']}"
        results.add("T1: Ollama Client", "HP validation (type-cast + clamp + case match)", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "HP validation (type-cast + clamp + case match)", False, str(e), time.time()-t0)
    
    # T1.7: Schema completeness
    t0 = time.time()
    try:
        expected_params = [
            "learning_rate", "batch_size", "epochs", "optimizer",
            "weight_decay", "max_seq_length", "dropout", "scheduler",
            "warmup_steps", "warmup_ratio", "gradient_clipping", "seed"
        ]
        for p in expected_params:
            assert p in BERT_HP_SCHEMA, f"Missing schema for: {p}"
        results.add("T1: Ollama Client", "Schema covers all 12 HP fields", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T1: Ollama Client", "Schema covers all 12 HP fields", False, str(e), time.time()-t0)


# ═══════════════════════════════════════════════════════════════════
# T2: Live Ollama Query Test
# ═══════════════════════════════════════════════════════════════════

def test_ollama_query():
    print("\n🧪 T2: Live Ollama Query Tests")
    print("─" * 40)
    
    from src.module8.ollama_client import query_ollama_for_comparison, query_ollama_for_extraction
    
    # T2.1: Comparison query
    t0 = time.time()
    try:
        result = query_ollama_for_comparison(
            task="sentiment_analysis",
            model_name="BERT-base-uncased",
            dataset="IMDB",
            missing_params=["learning_rate", "batch_size", "epochs", "weight_decay"],
        )
        assert result["error"] is None, f"Query error: {result['error']}"
        assert result["source"] == "ollama-qwen3:4b"
        assert len(result["suggestions"]) > 0, "No suggestions returned"
        assert result["latency_ms"] > 0, "No latency recorded"
        
        # Validate returned values are sensible for BERT
        sugg = result["suggestions"]
        if "learning_rate" in sugg:
            assert 1e-6 <= sugg["learning_rate"] <= 1e-2, f"LR out of range: {sugg['learning_rate']}"
        if "batch_size" in sugg:
            assert 4 <= sugg["batch_size"] <= 256, f"BS out of range: {sugg['batch_size']}"
        if "epochs" in sugg:
            assert 1 <= sugg["epochs"] <= 100, f"Epochs out of range: {sugg['epochs']}"
        
        results.add("T2: Live Ollama Query", 
                    f"Comparison query — {len(sugg)} params returned",
                    True, f"Values: {sugg}", time.time()-t0)
    except Exception as e:
        results.add("T2: Live Ollama Query", "Comparison query", False, str(e), time.time()-t0)
    
    # T2.2: Extraction query (simulated paper text)
    t0 = time.time()
    try:
        sample_text = """
        We fine-tune BERT-base-uncased for sentiment classification on the IMDB dataset.
        The model is trained for 4 epochs with a learning rate of 3e-5. We use a batch size
        of 16 and the AdamW optimizer with weight decay of 0.01. The maximum sequence length
        is set to 256 tokens with a dropout rate of 0.1.
        """
        existing_hps = {
            "learning_rate": None, "batch_size": None, "epochs": None,
            "optimizer": None, "weight_decay": None, "max_seq_length": None,
            "dropout": None, "warmup_steps": None, "warmup_ratio": None,
            "scheduler": None, "gradient_clipping": None, "seed": None,
        }
        result = query_ollama_for_extraction(
            paper_text=sample_text,
            existing_hps=existing_hps,
        )
        assert result["error"] is None, f"Extraction error: {result['error']}"
        sugg = result["suggestions"]
        assert len(sugg) > 0, "No HPs extracted"
        
        # The paper clearly mentions these — LLM should find at least some
        found_params = list(sugg.keys())
        results.add("T2: Live Ollama Query", 
                    f"Extraction query — found {len(found_params)} params",
                    True, f"Found: {found_params}\nValues: {sugg}", time.time()-t0)
    except Exception as e:
        results.add("T2: Live Ollama Query", "Extraction query", False, str(e), time.time()-t0)


# ═══════════════════════════════════════════════════════════════════
# T3: Enhanced M1 Pipeline Tests
# ═══════════════════════════════════════════════════════════════════

def test_m1_pipeline():
    print("\n🧪 T3: Enhanced M1 Pipeline Tests")
    print("─" * 40)
    
    # T3.1: Import
    t0 = time.time()
    try:
        from src.module1.pdf_analyzer import (
            _extract_from_text,
            _extract_with_llm,
            _validate_and_merge,
            HP_FIELDS,
            analyze_pdf,
        )
        results.add("T3: M1 Pipeline", "Import all functions", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T3: M1 Pipeline", "Import all functions", False, str(e), time.time()-t0)
        return
    
    # T3.2: Regex extraction still works
    t0 = time.time()
    try:
        text = """
        We use BERT-base-uncased for named entity recognition on CoNLL-2003.
        Training uses a learning rate of 5e-5 with batch size 32 for 10 epochs.
        We apply AdamW optimizer with weight decay of 0.01. The max sequence length is 128 tokens. We set a dropout rate of 0.1.
        """
        result = _extract_from_text(text)
        hps = result["hyperparameters"]
        
        assert hps["learning_rate"] == 5e-5, f"LR: {hps['learning_rate']}"
        assert hps["batch_size"] == 32, f"BS: {hps['batch_size']}"
        assert hps["epochs"] == 10, f"Epochs: {hps['epochs']}"
        assert hps["max_seq_length"] == 128, f"Seq len: {hps['max_seq_length']}"
        assert hps["dropout"] == 0.1, f"Dropout: {hps['dropout']}"
        assert result["task"] == "ner", f"Task: {result['task']}"
        
        found = [k for k, v in hps.items() if v is not None]
        results.add("T3: M1 Pipeline", f"Regex extraction — {len(found)}/12 params found", 
                    True, f"Found: {found}", time.time()-t0)
    except Exception as e:
        results.add("T3: M1 Pipeline", "Regex extraction", False, str(e), time.time()-t0)
    
    # T3.3: Validation merge logic
    t0 = time.time()
    try:
        regex_result = {
            "hyperparameters": {
                "learning_rate": 5e-5,
                "batch_size": 32,
                "epochs": None,  # Missed by regex
                "optimizer": "AdamW",
                "weight_decay": None,  # Missed by regex
                "max_seq_length": 128,
                "dropout": 0.1,
                "warmup_steps": None,
                "warmup_ratio": None,
                "scheduler": None,
                "gradient_clipping": None,
                "seed": None,
            },
            "model": "BERT-base-uncased",
            "task": "ner",
            "dataset": "CoNLL-2003",
        }
        llm_result = {
            "source": "ollama-qwen3:4b",
            "suggestions": {
                "epochs": 3,
                "weight_decay": 0.01,
                "warmup_ratio": 0.1,
            },
            "latency_ms": 5000,
            "error": None,
        }
        
        merged = _validate_and_merge(regex_result, llm_result)
        
        # Regex values should be preserved
        assert merged["hyperparameters"]["learning_rate"] == 5e-5, "Regex LR should be kept"
        assert merged["hyperparameters"]["batch_size"] == 32, "Regex BS should be kept"
        assert merged["hyperparameters"]["optimizer"] == "AdamW", "Regex optimizer should be kept"
        
        # LLM values should fill gaps
        assert merged["hyperparameters"]["epochs"] == 3, "LLM epochs should fill gap"
        assert merged["hyperparameters"]["weight_decay"] == 0.01, "LLM WD should fill gap"
        assert merged["hyperparameters"]["warmup_ratio"] == 0.1, "LLM warmup_ratio should fill gap"
        
        # Source tracking
        assert merged["extraction_sources"]["learning_rate"] == "regex"
        assert merged["extraction_sources"]["epochs"] == "llm_extracted"
        assert merged["extraction_sources"]["seed"] == "not_found"
        
        # LLM extraction metadata
        assert merged["llm_extraction"]["source"] == "ollama-qwen3:4b"
        assert merged["llm_extraction"]["latency_ms"] == 5000
        assert "epochs" in merged["llm_extraction"]["params_found"]
        
        found = [k for k, v in merged["hyperparameters"].items() if v is not None]
        results.add("T3: M1 Pipeline", f"Validate & merge — {len(found)}/12 after merge (regex:{sum(1 for v in merged['extraction_sources'].values() if v=='regex')}, llm:{sum(1 for v in merged['extraction_sources'].values() if v=='llm_extracted')})",
                    True, f"Sources: {merged['extraction_sources']}", time.time()-t0)
    except Exception as e:
        results.add("T3: M1 Pipeline", "Validate & merge", False, str(e), time.time()-t0)
    
    # T3.4: LLM extraction function (live test)
    t0 = time.time()
    try:
        test_text = """
        We fine-tune RoBERTa-base on SST-2 for sentiment analysis. We train for 5 epochs
        using a cosine learning rate schedule with warmup for 500 steps. The gradient
        clipping norm is set to 1.0 and the random seed is 42.
        """
        regex_res = _extract_from_text(test_text)
        llm_res = _extract_with_llm(test_text, regex_res)
        
        assert llm_res is not None, "LLM extraction returned None"
        if llm_res.get("error"):
            results.add("T3: M1 Pipeline", "LLM extraction (live)", False, 
                        f"Error: {llm_res['error']}", time.time()-t0)
        else:
            found = list(llm_res.get("suggestions", {}).keys())
            results.add("T3: M1 Pipeline", f"LLM extraction (live) — found {len(found)} additional params",
                        True, f"LLM found: {found}", time.time()-t0)
    except Exception as e:
        results.add("T3: M1 Pipeline", "LLM extraction (live)", False, str(e), time.time()-t0)
    
    # T3.5: Merge prioritizes regex over LLM
    t0 = time.time()
    try:
        regex_result = {
            "hyperparameters": {"learning_rate": 5e-5, "batch_size": None},
            "model": "BERT", "task": "ner", "dataset": None,
        }
        llm_result = {
            "source": "ollama-qwen3:4b",
            "suggestions": {"learning_rate": 2e-5, "batch_size": 16},  # LLM disagrees on LR
            "latency_ms": 1000, "error": None,
        }
        merged = _validate_and_merge(regex_result, llm_result)
        
        # Regex LR should win (5e-5, not LLM's 2e-5)
        assert merged["hyperparameters"]["learning_rate"] == 5e-5, \
            f"Regex should take priority! Got {merged['hyperparameters']['learning_rate']}"
        # LLM batch_size should fill the gap
        assert merged["hyperparameters"]["batch_size"] == 16
        assert merged["extraction_sources"]["learning_rate"] == "regex"
        assert merged["extraction_sources"]["batch_size"] == "llm_extracted"
        
        results.add("T3: M1 Pipeline", "Regex priority over LLM in conflicts", True, 
                    "LR=5e-5 (regex, not LLM's 2e-5)", time.time()-t0)
    except Exception as e:
        results.add("T3: M1 Pipeline", "Regex priority over LLM in conflicts", False, str(e), time.time()-t0)
    
    # T3.6: Graceful fallback when LLM fails
    t0 = time.time()
    try:
        regex_result = {
            "hyperparameters": {"learning_rate": 5e-5, "batch_size": None},
            "model": "BERT", "task": "ner", "dataset": None,
        }
        failed_llm = {
            "source": "ollama-qwen3:4b",
            "suggestions": {},
            "latency_ms": 0,
            "error": "Connection refused",
        }
        merged = _validate_and_merge(regex_result, failed_llm)
        
        # Should still have regex values
        assert merged["hyperparameters"]["learning_rate"] == 5e-5
        assert merged["hyperparameters"]["batch_size"] is None  # LLM failed, stays None
        assert merged["llm_extraction"]["error"] == "Connection refused"
        
        results.add("T3: M1 Pipeline", "Graceful fallback on LLM failure", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T3: M1 Pipeline", "Graceful fallback on LLM failure", False, str(e), time.time()-t0)


# ═══════════════════════════════════════════════════════════════════
# T4: Backend API Endpoint Tests
# ═══════════════════════════════════════════════════════════════════

def test_backend_endpoints():
    print("\n🧪 T4: Backend API Endpoint Tests")
    print("─" * 40)
    
    import urllib.request
    import urllib.error
    
    BACKEND = "http://localhost:5000/api"
    
    # T4.1: Check if backend is running
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{BACKEND}/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        assert resp.status == 200
        results.add("T4: Backend API", "Backend health check", True, 
                    f"Status: {data}", time.time()-t0)
        backend_running = True
    except Exception as e:
        results.add("T4: Backend API", "Backend health check — NOT RUNNING", False, 
                    f"Start with: python backend/app.py\nError: {str(e)[:100]}", time.time()-t0)
        backend_running = False
    
    if not backend_running:
        results.add("T4: Backend API", "Ollama status endpoint (SKIPPED — backend not running)", False, "Backend not running")
        results.add("T4: Backend API", "Live comparison endpoint (SKIPPED — backend not running)", False, "Backend not running")
        return
    
    # T4.2: Ollama status endpoint
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{BACKEND}/ollama/status", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        assert resp.status == 200
        assert "running" in data
        assert "has_qwen" in data
        assert "models" in data
        results.add("T4: Backend API", f"Ollama status endpoint — running={data['running']}, qwen={data['has_qwen']}", 
                    True, f"Models: {data.get('models', [])}", time.time()-t0)
    except Exception as e:
        results.add("T4: Backend API", "Ollama status endpoint", False, str(e), time.time()-t0)
    
    # T4.3: Find a valid session for testing compare-live
    t0 = time.time()
    sessions_dir = ROOT / "backend" / "sessions"
    session_files = list(sessions_dir.glob("*.json")) if sessions_dir.exists() else []
    
    if not session_files:
        results.add("T4: Backend API", "Live comparison (SKIPPED — no sessions)", False, 
                    "No session files found in backend/sessions/")
        return
    
    # Find a session with missing params
    test_session = None
    for sf in session_files[:10]:
        try:
            with open(sf, encoding="utf-8") as f:
                sdata = json.load(f)
            missing = sdata.get("completeness", {}).get("missing_params", [])
            if missing and sdata.get("config"):
                test_session = sf.stem
                break
        except:
            continue
    
    if not test_session:
        # Use any session — the endpoint will compare all params
        test_session = session_files[0].stem
    
    results.add("T4: Backend API", f"Found test session: {test_session[:16]}...", True, duration=time.time()-t0)
    
    # T4.4: Live comparison endpoint
    t0 = time.time()
    try:
        req = urllib.request.Request(
            f"{BACKEND}/compare-live/{test_session}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        
        assert resp.status == 200
        assert "llm_comparison" in data, "Missing llm_comparison"
        assert "comparison" in data["llm_comparison"], "Missing comparison data"
        
        comp = data["llm_comparison"]["comparison"]
        summary = comp.get("summary", {})
        per_param = comp.get("per_param", {})
        
        assert len(per_param) > 0, "No params compared"
        assert "total_compared" in summary
        assert "agreed" in summary
        assert "agreement_pct" in summary
        
        # Validate per-param structure
        for param, entry in list(per_param.items())[:1]:
            assert "rag_value" in entry, f"Missing rag_value for {param}"
            assert "llm_value" in entry, f"Missing llm_value for {param}"
            assert "agrees" in entry, f"Missing agrees for {param}"
            assert "has_both" in entry, f"Missing has_both for {param}"
        
        llm_info = data["llm_comparison"].get("llm_result", {})
        latency = llm_info.get("latency_ms", "?")
        
        results.add("T4: Backend API", 
                    f"Live comparison — {len(per_param)} params, {summary.get('agreed', 0)}/{summary.get('total_compared', 0)} agree ({summary.get('agreement_pct', 0)}%)",
                    True,
                    f"LLM: {llm_info.get('source', '?')}, Latency: {latency}ms",
                    time.time()-t0)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if hasattr(e, 'read') else ""
        results.add("T4: Backend API", "Live comparison endpoint", False, 
                    f"HTTP {e.code}: {body[:200]}", time.time()-t0)
    except Exception as e:
        results.add("T4: Backend API", "Live comparison endpoint", False, 
                    f"{str(e)[:200]}", time.time()-t0)
    
    # T4.5: Existing compare endpoint still works
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{BACKEND}/compare/{test_session}", method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        assert resp.status == 200
        results.add("T4: Backend API", "Legacy compare endpoint still works", True, duration=time.time()-t0)
    except Exception as e:
        results.add("T4: Backend API", "Legacy compare endpoint", False, str(e)[:100], time.time()-t0)


# ═══════════════════════════════════════════════════════════════════
# T5: Frontend Compilation Test
# ═══════════════════════════════════════════════════════════════════

def test_frontend():
    print("\n🧪 T5: Frontend Compilation Tests")
    print("─" * 40)
    
    import subprocess
    
    # T5.1: TypeScript compilation
    t0 = time.time()
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(ROOT / "frontend"),
            capture_output=True, text=True, timeout=120,
            shell=True,
        )
        if result.returncode == 0:
            results.add("T5: Frontend", "TypeScript compilation — clean", True, duration=time.time()-t0)
        else:
            results.add("T5: Frontend", "TypeScript compilation", False, 
                        result.stderr[:500], time.time()-t0)
    except Exception as e:
        results.add("T5: Frontend", "TypeScript compilation", False, str(e), time.time()-t0)
    
    # T5.2: Check ComparisonDashboard has key components
    t0 = time.time()
    try:
        comp_path = ROOT / "frontend" / "src" / "pages" / "ComparisonDashboard.tsx"
        content = comp_path.read_text(encoding="utf-8")
        
        checks = {
            "runLiveComparison import": "runLiveComparison" in content,
            "getOllamaStatus import": "getOllamaStatus" in content,
            "OllamaStatusBadge component": "OllamaStatusBadge" in content,
            "ConfidenceRing component": "ConfidenceRing" in content,
            "ParamCard component": "ParamCard" in content,
            "handleLiveComparison handler": "handleLiveComparison" in content,
            "Run Live Comparison button": "Run Live Comparison" in content,
            "glass-panel styling": "glass-panel" in content,
            "AnimatePresence animation": "AnimatePresence" in content,
            "inference_trace display": "inference_trace" in content,
        }
        
        all_pass = all(checks.values())
        failed_checks = [k for k, v in checks.items() if not v]
        
        if all_pass:
            results.add("T5: Frontend", f"ComparisonDashboard — all {len(checks)} components present", 
                        True, duration=time.time()-t0)
        else:
            results.add("T5: Frontend", "ComparisonDashboard component checks", False,
                        f"Missing: {failed_checks}", time.time()-t0)
    except Exception as e:
        results.add("T5: Frontend", "ComparisonDashboard component checks", False, str(e), time.time()-t0)
    
    # T5.3: Check api.ts has new functions
    t0 = time.time()
    try:
        api_path = ROOT / "frontend" / "src" / "lib" / "api.ts"
        content = api_path.read_text(encoding="utf-8")
        
        checks = {
            "getOllamaStatus function": "export async function getOllamaStatus" in content,
            "runLiveComparison function": "export async function runLiveComparison" in content,
            "ollama/status endpoint": "/ollama/status" in content,
            "compare-live endpoint": "/compare-live/" in content,
        }
        
        all_pass = all(checks.values())
        failed_checks = [k for k, v in checks.items() if not v]
        
        if all_pass:
            results.add("T5: Frontend", f"api.ts — all {len(checks)} new functions present", 
                        True, duration=time.time()-t0)
        else:
            results.add("T5: Frontend", "api.ts function checks", False,
                        f"Missing: {failed_checks}", time.time()-t0)
    except Exception as e:
        results.add("T5: Frontend", "api.ts function checks", False, str(e), time.time()-t0)


# ═══════════════════════════════════════════════════════════════════
# Run all tests
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  HyperBERT — Automated Test Suite")
    print("  LLM-Enhanced Extraction + RAG vs LLM Comparison")
    print("=" * 65)
    
    test_ollama_client()
    test_ollama_query()
    test_m1_pipeline()
    test_backend_endpoints()
    test_frontend()
    
    all_passed = results.print_summary()
    sys.exit(0 if all_passed else 1)
