"""
Ollama Client — Local LLM Integration via Ollama REST API

Provides functions to query Ollama (localhost:11434) for:
1. HP extraction from paper text (used in M1 enhanced pipeline)
2. HP suggestion for comparison (used in comparison page)
3. Health checks and model status

Uses urllib.request — no extra dependencies needed.
"""

from __future__ import annotations

import ast
import json
import re
import time
import urllib.request
import urllib.error
from typing import Optional


OLLAMA_BASE = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:4b"

# ── HP schema for validation ──────────────────────────────────────────
BERT_HP_SCHEMA = {
    "learning_rate": {"type": "float", "range": [1e-6, 1e-2]},
    "batch_size": {"type": "int", "range": [4, 256]},
    "epochs": {"type": "int", "range": [1, 100]},
    "optimizer": {"type": "categorical", "values": ["Adam", "AdamW", "SGD", "Adafactor", "LAMB", "RAdam"]},
    "weight_decay": {"type": "float", "range": [0.0, 0.5]},
    "max_seq_length": {"type": "int", "range": [32, 2048]},
    "dropout": {"type": "float", "range": [0.0, 0.9]},
    "scheduler": {"type": "categorical", "values": ["linear", "cosine", "constant", "polynomial", "warmup_linear", "inverse_sqrt"]},
    "warmup_steps": {"type": "int", "range": [0, 10000]},
    "warmup_ratio": {"type": "float", "range": [0.0, 0.5]},
    "gradient_clipping": {"type": "float", "range": [0.0, 10.0]},
    "seed": {"type": "int", "range": [0, 99999]},
}


def check_ollama_health() -> dict:
    """Check if Ollama is running and return status info.
    
    Returns:
        {
            "running": bool,
            "models": ["qwen3:4b", ...],
            "has_qwen": bool,
            "error": str | None
        }
    """
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        
        models = [m.get("name", "") for m in body.get("models", [])]
        # Normalize model names for matching (ollama returns "qwen3:4b" or "qwen3:4b-instruct")
        has_qwen = any("qwen3" in m.lower() for m in models)
        
        return {
            "running": True,
            "models": models,
            "has_qwen": has_qwen,
            "error": None,
        }
    except Exception as e:
        return {
            "running": False,
            "models": [],
            "has_qwen": False,
            "error": str(e),
        }


def _clean_json_str(s: str) -> str:
    """Pre-process text to fix common LLM JSON syntax issues."""
    # Remove markdown code fences if present
    s = re.sub(r'```(?:json)?\s*', '', s)
    s = s.replace('```', '')
    # Remove <think>...</think> tags if any
    s = re.sub(r'<think>.*?</think>', '', s, flags=re.DOTALL)
    # Remove trailing commas before } or ]
    s = re.sub(r',\s*([\}\]])', r'\1', s)
    return s.strip()


def _parse_llm_json(response_text: str, target_params: list[str] | None = None) -> dict:
    """Extract JSON from LLM response with multiple robust fallback layers.
    
    Handles:
    1. Standard JSON with double quotes (json.loads)
    2. Python dict syntax with single quotes (ast.literal_eval)
    3. Trailing commas and single-quote repair
    4. Regex key-value extraction for requested parameters
    """
    if not response_text or not response_text.strip():
        return {}

    cleaned = _clean_json_str(response_text)

    # Candidate strings to try parsing
    candidates = []

    # 1. Regex match for outermost { ... }
    match_outer = re.search(r'(\{.*\})', cleaned, re.DOTALL)
    if match_outer:
        candidates.append(match_outer.group(1).strip())

    # 2. Regex match for non-greedy { ... }
    match_inner = re.search(r'(\{[^{}]*\})', cleaned, re.DOTALL)
    if match_inner:
        candidates.append(match_inner.group(1).strip())

    # 3. Whole cleaned text
    candidates.append(cleaned)

    for cand in candidates:
        cand_clean = re.sub(r',\s*([\}\]])', r'\1', cand)
        
        # Layer 1: Strict JSON
        try:
            res = json.loads(cand_clean)
            if isinstance(res, dict) and res:
                return res
        except Exception:
            pass

        # Layer 2: ast.literal_eval for single-quoted Python dicts (e.g. {'learning_rate': 2e-5})
        try:
            res = ast.literal_eval(cand_clean)
            if isinstance(res, dict) and res:
                return res
        except Exception:
            pass

        # Layer 3: Quote substitution (single to double quotes)
        try:
            fixed_quotes = re.sub(r"(?<!\\)'", '"', cand_clean)
            res = json.loads(fixed_quotes)
            if isinstance(res, dict) and res:
                return res
        except Exception:
            pass

    # Layer 4: Fallback regex parameter extraction
    params_to_find = target_params or list(BERT_HP_SCHEMA.keys())
    extracted = {}
    for param in params_to_find:
        m = re.search(rf'[\'"]?{re.escape(param)}[\'"]?\s*:\s*[\'"]?([^\r\n,}}"\']+)[\'"]?', response_text)
        if m:
            raw_val = m.group(1).strip()
            try:
                if "." in raw_val or "e" in raw_val.lower():
                    extracted[param] = float(raw_val)
                else:
                    extracted[param] = int(raw_val)
            except ValueError:
                extracted[param] = raw_val

    if extracted:
        return extracted

    # Final attempt if everything failed
    return json.loads(cleaned)


def _validate_hp_values(raw: dict, target_params: list[str] | None = None) -> dict:
    """Validate and type-cast HP values against the schema."""
    validated = {}
    params_to_check = target_params if target_params else list(raw.keys())
    
    for param in params_to_check:
        if param not in raw or raw[param] is None:
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
                for candidate in schema["values"]:
                    if candidate.lower() == val.lower():
                        val = candidate
                        break
            validated[param] = val
        except (ValueError, TypeError):
            # Keep the raw value if type conversion fails
            validated[param] = raw[param]

    return validated


def query_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    timeout: int = 60,
) -> dict:
    """Send a prompt to Ollama using the chat API and return the response.
    
    Uses /api/chat (not /api/generate) because Qwen3 is a chat/instruct model.
    
    Returns:
        {
            "text": str,           # Raw response text
            "latency_ms": int,     # Response time in ms
            "model": str,          # Model used
            "error": str | None,   # Error message if failed
        }
    """
    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that responds ONLY with valid JSON objects. No explanations, no reasoning, no commentary. Output nothing except a single JSON object.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": 4096,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        latency = int((time.perf_counter() - t0) * 1000)
        
        # Qwen3 may put JSON in content, thinking, or split across both.
        # Combine everything and let the parser find the JSON.
        msg = body.get("message", {})
        content = msg.get("content", "") or ""
        thinking = msg.get("thinking", "") or ""
        
        # Try content first, then thinking, then both combined
        text = content if content.strip() else thinking
        if not text.strip():
            text = thinking + "\n" + content
        
        return {
            "text": text,
            "latency_ms": latency,
            "model": model,
            "error": None,
        }
    except Exception as e:
        latency = int((time.perf_counter() - t0) * 1000)
        return {
            "text": "",
            "latency_ms": latency,
            "model": model,
            "error": str(e),
        }


def query_ollama_for_extraction(
    paper_text: str,
    existing_hps: dict | None = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Query Ollama to extract hyperparameters from paper text.
    
    This is Step 2 of the enhanced M1 pipeline (Regex → LLM → Validation).
    Only extracts parameters that regex missed.
    
    Args:
        paper_text: Prepared paper text (relevant sections)
        existing_hps: Already-extracted HPs from regex (Step 1)
        model: Ollama model to use
        
    Returns:
        {
            "source": "ollama-qwen3:4b",
            "suggestions": {"learning_rate": 2e-5, ...},
            "raw_response": "...",
            "latency_ms": 1234,
            "error": None
        }
    """
    existing = existing_hps or {}
    missing = [k for k, v in existing.items() if v is None]
    
    if not missing:
        return {
            "source": f"ollama-{model}",
            "suggestions": {},
            "raw_response": "",
            "latency_ms": 0,
            "error": None,
        }
    
    # Truncate paper text to fit context window
    truncated_text = paper_text[:6000]
    param_list = ", ".join(missing)
    
    prompt = f"""You are a machine learning research paper analyzer. Extract hyperparameter values from the following paper text.

IMPORTANT RULES:
1. Only extract values that are EXPLICITLY mentioned in the text
2. Do NOT guess or infer values - only extract what the paper states
3. Return ONLY a valid JSON object with parameter names as keys
4. If a parameter is not found in the text, do NOT include it in the JSON

Parameters to look for: {param_list}

Parameter definitions:
- learning_rate: The learning rate value (e.g., 2e-5, 0.00002, 3×10⁻⁵)
- batch_size: Training batch size (e.g., 16, 32, 64)
- epochs: Number of training epochs
- max_seq_length: Maximum sequence/token length
- optimizer: Optimizer name (Adam, AdamW, SGD, etc.)
- weight_decay: Weight decay / L2 regularization value
- warmup_steps: Number of warmup steps
- warmup_ratio: Warmup ratio/proportion
- scheduler: Learning rate scheduler type
- gradient_clipping: Gradient clipping/norm value
- dropout: Dropout rate/probability
- seed: Random seed value

Paper text:
\"\"\"
{truncated_text}
\"\"\"

Return ONLY valid JSON with found parameters. Example: {{"learning_rate": 2e-5, "batch_size": 32}}
Do not include any explanation or reasoning, just the JSON object. No thinking, no commentary."""

    result = query_ollama(prompt, model=model, temperature=0.1, timeout=90)
    
    if result["error"]:
        return {
            "source": f"ollama-{model}",
            "suggestions": {},
            "raw_response": result["text"],
            "latency_ms": result["latency_ms"],
            "error": result["error"],
        }
    
    try:
        raw_values = _parse_llm_json(result["text"], missing)
        validated = _validate_hp_values(raw_values, missing)
        return {
            "source": f"ollama-{model}",
            "suggestions": validated,
            "raw_response": result["text"],
            "latency_ms": result["latency_ms"],
            "error": None,
        }
    except (json.JSONDecodeError, Exception) as e:
        return {
            "source": f"ollama-{model}",
            "suggestions": {},
            "raw_response": result["text"],
            "latency_ms": result["latency_ms"],
            "error": f"Failed to parse LLM response: {e}",
        }


def query_ollama_for_comparison(
    task: str,
    model_name: str,
    dataset: str,
    missing_params: list[str],
    model: str = DEFAULT_MODEL,
) -> dict:
    """Query Ollama to suggest hyperparameters for comparison against RAG.
    
    This is used by the Comparison page to get LLM suggestions.
    
    Returns:
        {
            "source": "ollama-qwen3:4b",
            "suggestions": {"learning_rate": 2e-5, ...},
            "raw_response": "...",
            "latency_ms": 1234,
            "error": None
        }
    """
    param_list = ", ".join(missing_params)
    
    prompt = f"""You are a machine learning expert specializing in BERT fine-tuning.

A researcher is fine-tuning {model_name or 'BERT'} for the task "{task or 'text classification'}" on the dataset "{dataset or 'unspecified'}".

They need values for these missing hyperparameters: {param_list}

Based on your knowledge of BERT fine-tuning best practices and common configurations in the literature, suggest appropriate values for each parameter.

IMPORTANT: Return ONLY a valid JSON object with the parameter names as keys and suggested values. No explanations, no markdown, just the JSON.

Example format:
{{"learning_rate": 2e-5, "batch_size": 32, "epochs": 3}}

Now provide your suggestions for: {param_list}
Return ONLY the JSON object. No thinking, no reasoning, no explanation."""

    result = query_ollama(prompt, model=model, temperature=0.2, timeout=90)
    
    if result["error"]:
        return {
            "source": f"ollama-{model}",
            "suggestions": {},
            "raw_response": result["text"],
            "latency_ms": result["latency_ms"],
            "error": result["error"],
        }
    
    try:
        raw_values = _parse_llm_json(result["text"], missing_params)
        validated = _validate_hp_values(raw_values, missing_params)
        return {
            "source": f"ollama-{model}",
            "suggestions": validated,
            "raw_response": result["text"],
            "latency_ms": result["latency_ms"],
            "error": None,
        }
    except (json.JSONDecodeError, Exception) as e:
        return {
            "source": f"ollama-{model}",
            "suggestions": {},
            "raw_response": result["text"],
            "latency_ms": result["latency_ms"],
            "error": f"Failed to parse LLM response: {e}",
        }
