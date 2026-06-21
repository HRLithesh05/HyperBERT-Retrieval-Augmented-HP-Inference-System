"""
Module 8: LLM Baseline Comparison — Gemini/Groq HP Suggestion Engine

Queries an LLM to suggest hyperparameters for a given BERT fine-tuning task,
then returns structured results for comparison against the RAG-based pipeline.

This is the capstone differentiator: transparent RAG vs opaque LLM, head-to-head.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

# ── Known defaults for validation ──────────────────────────────────────
BERT_HP_SCHEMA = {
    "learning_rate": {"type": "float", "range": [1e-6, 1e-2]},
    "batch_size": {"type": "int", "range": [4, 256]},
    "epochs": {"type": "int", "range": [1, 100]},
    "optimizer": {"type": "categorical", "values": ["Adam", "AdamW", "SGD"]},
    "weight_decay": {"type": "float", "range": [0.0, 0.5]},
    "max_seq_length": {"type": "int", "range": [32, 2048]},
    "dropout": {"type": "float", "range": [0.0, 0.9]},
    "scheduler": {"type": "categorical", "values": ["linear", "cosine", "constant", "polynomial"]},
    "warmup_steps": {"type": "int", "range": [0, 10000]},
    "warmup_ratio": {"type": "float", "range": [0.0, 0.5]},
    "gradient_clipping": {"type": "float", "range": [0.0, 10.0]},
    "seed": {"type": "int", "range": [0, 99999]},
}


def _build_prompt(task: str, model: str, dataset: str, missing_params: list[str]) -> str:
    """Build a structured prompt for the LLM."""
    param_list = ", ".join(missing_params)
    return f"""You are a machine learning expert specializing in BERT fine-tuning.

A researcher is fine-tuning {model or 'BERT'} for the task "{task or 'text classification'}" on the dataset "{dataset or 'unspecified'}".

They need values for these missing hyperparameters: {param_list}

Based on your knowledge of BERT fine-tuning best practices and common configurations in the literature, suggest appropriate values for each parameter.

IMPORTANT: Return ONLY a valid JSON object with the parameter names as keys and suggested values. No explanations, no markdown, just the JSON.

Example format:
{{"learning_rate": 2e-5, "batch_size": 32, "epochs": 3}}

Now provide your suggestions for: {param_list}"""


def _parse_llm_json(response_text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to find raw JSON
    json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))

    # Last resort: try the whole thing
    return json.loads(response_text.strip())


def _validate_llm_values(raw: dict, missing_params: list[str]) -> dict:
    """Validate and type-cast LLM-suggested values."""
    validated = {}
    for param in missing_params:
        if param not in raw:
            continue
        val = raw[param]
        schema = BERT_HP_SCHEMA.get(param)
        if not schema:
            validated[param] = val
            continue

        try:
            if schema["type"] == "float":
                val = float(val)
                lo, hi = schema["range"]
                val = max(lo, min(hi, val))
            elif schema["type"] == "int":
                val = int(float(val))
                lo, hi = schema["range"]
                val = max(lo, min(hi, val))
            elif schema["type"] == "categorical":
                val = str(val)
                # Try to match case-insensitively
                for candidate in schema["values"]:
                    if candidate.lower() == val.lower():
                        val = candidate
                        break
            validated[param] = val
        except (ValueError, TypeError):
            validated[param] = raw[param]

    return validated


def query_gemini(
    task: str,
    model: str,
    dataset: str,
    missing_params: list[str],
    api_key: Optional[str] = None,
) -> dict:
    """Query Gemini API for HP suggestions.

    Returns:
        {
            "source": "gemini-2.0-flash",
            "suggestions": {"learning_rate": 2e-5, ...},
            "raw_response": "...",
            "latency_ms": 1234,
            "error": null
        }
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "source": "gemini",
            "suggestions": {},
            "raw_response": "",
            "latency_ms": 0,
            "error": "GEMINI_API_KEY not set",
        }

    import urllib.request
    import urllib.error

    prompt = _build_prompt(task, model, dataset, missing_params)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        latency = int((time.perf_counter() - t0) * 1000)

        # Extract text from Gemini response
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        raw_values = _parse_llm_json(text)
        validated = _validate_llm_values(raw_values, missing_params)

        return {
            "source": "gemini-2.0-flash",
            "suggestions": validated,
            "raw_response": text,
            "latency_ms": latency,
            "error": None,
        }

    except Exception as e:
        latency = int((time.perf_counter() - t0) * 1000)
        return {
            "source": "gemini-2.0-flash",
            "suggestions": {},
            "raw_response": str(e),
            "latency_ms": latency,
            "error": str(e),
        }


def query_groq(
    task: str,
    model: str,
    dataset: str,
    missing_params: list[str],
    api_key: Optional[str] = None,
) -> dict:
    """Query Groq API for HP suggestions (fallback)."""
    api_key = api_key or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return {
            "source": "groq",
            "suggestions": {},
            "raw_response": "",
            "latency_ms": 0,
            "error": "GROQ_API_KEY not set",
        }

    import urllib.request
    import urllib.error

    prompt = _build_prompt(task, model, dataset, missing_params)
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a BERT fine-tuning expert. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 512,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        latency = int((time.perf_counter() - t0) * 1000)

        text = body["choices"][0]["message"]["content"]
        raw_values = _parse_llm_json(text)
        validated = _validate_llm_values(raw_values, missing_params)

        return {
            "source": "groq-llama-3.1-8b",
            "suggestions": validated,
            "raw_response": text,
            "latency_ms": latency,
            "error": None,
        }

    except Exception as e:
        latency = int((time.perf_counter() - t0) * 1000)
        return {
            "source": "groq-llama-3.1-8b",
            "suggestions": {},
            "raw_response": str(e),
            "latency_ms": latency,
            "error": str(e),
        }


def compare_rag_vs_llm(
    rag_config: dict,
    llm_suggestions: dict,
    missing_params: list[str],
) -> dict:
    """Compare RAG inferred values against LLM suggestions.

    Returns a per-parameter comparison with agreement analysis.
    """
    comparison = {}
    agreed = 0
    total = 0

    for param in missing_params:
        rag_entry = rag_config.get(param, {})
        rag_val = rag_entry.get("value") if isinstance(rag_entry, dict) else rag_entry
        rag_conf = rag_entry.get("confidence", 0) if isinstance(rag_entry, dict) else 0
        rag_source = rag_entry.get("source", "unknown") if isinstance(rag_entry, dict) else "unknown"

        llm_val = llm_suggestions.get(param)

        # Determine agreement
        agrees = False
        if rag_val is not None and llm_val is not None:
            total += 1
            # For numeric values, check if within 20% tolerance
            try:
                r = float(rag_val)
                l = float(llm_val)
                if r == 0 and l == 0:
                    agrees = True
                elif r != 0:
                    agrees = abs(r - l) / abs(r) <= 0.2
                else:
                    agrees = abs(r - l) <= 1e-6
            except (ValueError, TypeError):
                # For categorical, exact match
                agrees = str(rag_val).lower() == str(llm_val).lower()

            if agrees:
                agreed += 1

        comparison[param] = {
            "rag_value": rag_val,
            "rag_confidence": round(rag_conf * 100, 1) if isinstance(rag_conf, float) and rag_conf <= 1 else rag_conf,
            "rag_source": rag_source,
            "llm_value": llm_val,
            "agrees": agrees,
            "has_both": rag_val is not None and llm_val is not None,
        }

    agreement_pct = round((agreed / total * 100), 1) if total > 0 else 0.0

    return {
        "per_param": comparison,
        "summary": {
            "total_compared": total,
            "agreed": agreed,
            "disagreed": total - agreed,
            "agreement_pct": agreement_pct,
        },
    }


def run_llm_comparison(
    task: str,
    model: str,
    dataset: str,
    missing_params: list[str],
    rag_config: dict,
    gemini_key: Optional[str] = None,
    groq_key: Optional[str] = None,
) -> dict:
    """Run the full LLM comparison pipeline.

    1. Query Gemini (primary)
    2. If Gemini fails, query Groq (fallback)
    3. Compare LLM suggestions against RAG inference
    4. Return full comparison result
    """
    # Try Gemini first
    llm_result = query_gemini(task, model, dataset, missing_params, gemini_key)

    # Fallback to Groq if Gemini failed
    if llm_result["error"] and groq_key:
        print(f"  [M8] Gemini failed ({llm_result['error']}), trying Groq...")
        llm_result = query_groq(task, model, dataset, missing_params, groq_key)

    # Compare
    comparison = compare_rag_vs_llm(rag_config, llm_result["suggestions"], missing_params)

    return {
        "llm_result": llm_result,
        "comparison": comparison,
        "rag_config_summary": {
            param: {
                "value": (entry.get("value") if isinstance(entry, dict) else entry),
                "confidence": (entry.get("confidence", 0) if isinstance(entry, dict) else 0),
            }
            for param, entry in rag_config.items()
            if param in missing_params
        },
    }
