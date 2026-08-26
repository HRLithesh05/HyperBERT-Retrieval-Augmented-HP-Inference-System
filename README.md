# HyperBERT — Retrieval-Augmented Hyperparameter Inference for BERT

> **When 92% of BERT papers don't report all their hyperparameters, HyperBERT reads the paper, finds what's missing, and infers every value — with citations, confidence scores, and full evidence trails.**

---

## Overview

HyperBERT is a full-stack research tool that addresses the **BERT reproducibility crisis**. Given any BERT fine-tuning paper as a PDF, it:

1. **Extracts** reported hyperparameters using regex + section-aware parsing + optional LLM augmentation
2. **Scores** the paper's reproducibility via a weighted R-Score across 12 hyperparameters
3. **Retrieves** similar papers from a 455-paper corpus using FAISS semantic search
4. **Infers** missing values through statistical aggregation with three-axis confidence scoring
5. **Validates** all values against BERT domain constraints and detects contradictions
6. **Generates** a ready-to-run Jupyter notebook with per-parameter confidence annotations

Every inferred value carries a **citation trail**, **confidence decomposition** (similarity × agreement × support), and a **full reasoning trace**.

### Evaluation Results

| Metric | Value |
|--------|-------|
| **Overall Exact Match Rate** | **74.6%** |
| Papers Evaluated (LOO) | 84 |
| Total Inferences | 291 |
| Corpus Size | 455 papers |

<details>
<summary><strong>Per-Parameter Accuracy</strong></summary>

| Parameter | N | Exact Match | Within Tolerance |
|-----------|:-:|:-----------:|:----------------:|
| learning_rate | 45 | 73.3% | 73.3% |
| batch_size | 67 | 55.2% | 80.6% |
| epochs | 55 | 54.5% | 61.8% |
| max_seq_length | 17 | 76.5% | 88.2% |
| optimizer | 34 | 94.1% | 94.1% |
| weight_decay | 25 | 100% | 100% |
| warmup_steps | 6 | 100% | 100% |
| warmup_ratio | 3 | 100% | 100% |
| scheduler | 15 | 100% | 100% |
| gradient_clipping | 3 | 100% | 100% |
| dropout | 18 | 94.4% | 94.4% |
| seed | 3 | 100% | 100% |

</details>

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend — React 18 + Vite + TypeScript                     │
│  8 Pages: Landing, Upload, Results, Comparison, Notebook,    │
│           Corpus Explorer, Evaluation, Methodology           │
│  Auth: Auth0 (optional) with guest mode (5 free analyses)    │
│  Port: 5173                                                  │
├──────────────────────────────────────────────────────────────┤
│  Backend API — Flask + SSE Streaming                         │
│  15+ REST endpoints with real-time pipeline progress         │
│  Session persistence: MongoDB + filesystem fallback          │
│  Port: 5000                                                  │
├──────────────────────────────────────────────────────────────┤
│  Inference Pipeline (8 Modules)                              │
│  M1: PDF Analyzer → M2: Completeness → M3: FAISS Retrieval  │
│  → M4: Domain Constraints → M5: Contradiction Detection     │
│  → M6: Self-Critique Validator → M7: Notebook Generator      │
│  → M8: Meta-Agent + LLM Comparison                          │
├──────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  MongoDB Atlas (455 papers) · FAISS Index (384-dim)          │
│  Sentence-Transformers (all-MiniLM-L6-v2, 22.7M params)     │
└──────────────────────────────────────────────────────────────┘
```

---

## Pipeline Modules

### M1 — PDF Analyzer
Extracts text from PDFs using `pdfplumber`, identifies the task/model/dataset, and runs section-aware HP extraction with regex patterns. Optionally augments with an LLM (Qwen via Ollama) for parameters regex misses.

### M2 — Completeness Checker
Computes a weighted **R-Score** (Reproducibility Score) measuring how many of 12 standard hyperparameters the paper reports. Identifies exactly which parameters are missing.

### M3 — Evidence Retrieval & Inference
Encodes the paper abstract into a 384-dim vector, searches the FAISS index for similar papers, and uses a **4-strategy cascade** (S1: task+model+dataset → S2: task+model → S3: task-only → S4: global) to find evidence. Infers missing values via weighted median aggregation with three-axis confidence scoring.

### M4 — Domain Constraints
Applies 18 BERT-specific rules (e.g., AdamW couples weight_decay, batch_size must be power-of-2, learning_rate range bounds) to validate and correct inferred values.

### M5 — Contradiction Detection
Uses IQR-based outlier detection across evidence papers to flag contradictory values. Reports when an inferred value disagrees with the corpus consensus.

### M6 — Self-Critique Validator
Final validation pass against hard domain bounds (e.g., learning_rate ∈ [1e-6, 1e-2]). Auto-corrects out-of-range values and logs every correction with rationale.

### M7 — Notebook Generator
Generates a **task-aware** Jupyter notebook with 6 phases:
- Branches template by task type (NER → `tokenize_and_align_labels` + `seqeval`, Classification → standard tokenization + `accuracy/f1`)
- Auto-fetches datasets from HuggingFace (25+ known datasets mapped)
- Falls back to synthetic demo data when dataset isn't recognized, so notebooks always run out of the box
- Every HP is annotated with source and confidence in code comments

### M8 — Meta-Agent & LLM Comparison
- **Meta-Agent**: Adaptive reasoning agent that reviews each HP's confidence and optionally consults an LLM for low-confidence values. Logs every decision with expandable reasoning traces.
- **LLM Baseline**: Side-by-side comparison of RAG-inferred values vs Gemini/Groq LLM suggestions, showing agreement rates and per-HP verdicts.

---

## Features

| Feature | Description |
|---------|-------------|
| **Real-time Pipeline** | SSE streaming shows each module completing live during analysis |
| **Inference Dashboard** | Per-HP confidence decomposition, evidence trails, value distributions |
| **RAG vs LLM Comparison** | Side-by-side: cited RAG values vs black-box LLM suggestions |
| **Notebook Generation** | Download `.ipynb`, `.py`, `.yaml`, or `.json` — or launch embedded JupyterLab |
| **Corpus Explorer** | Browse 455 papers with task/model filtering and HP coverage stats |
| **Evaluation Dashboard** | LOO accuracy metrics, per-HP bars, strategy ablation, confidence calibration |
| **Session History** | Per-user analysis history with MongoDB persistence |
| **Auth0 Integration** | Optional Google sign-in with 5-analysis guest limit (works without Auth0 configured) |
| **Dark/Light Theme** | Professional Indigo/Cobalt palette with theme toggle |
| **Duplicate Detection** | Content-hash based deduplication returns cached results instantly |

---

## Quick Start

### Prerequisites
- **Python** 3.10+
- **Node.js** 18+
- **MongoDB** (Atlas or local on port 27017)

### 1. Clone & Install

```bash
git clone https://github.com/HRLithesh05/major_project_datacollection.git
cd major_project_datacollection

# Python dependencies
pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Environment Setup

Create a `.env` file in the project root:

```env
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=<app>
```

**(Optional)** For LLM comparison features, add:
```env
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

**(Optional)** For Auth0 authentication, create `frontend/.env`:
```env
VITE_AUTH0_DOMAIN=your_auth0_domain
VITE_AUTH0_CLIENT_ID=your_auth0_client_id
```

> **Note:** The system works fully without API keys or Auth0 — LLM comparison is skipped and all users get unlimited guest access.

### 3. Start

```bash
# Terminal 1: Backend
python backend/app.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 4. Open

Navigate to **http://localhost:5173** — upload any BERT fine-tuning paper PDF.

---

## Running Evaluations

```bash
# Leave-One-Out evaluation (full corpus — ~45s)
python evaluation/loo_evaluation.py

# Quick test with N papers
python evaluation/loo_evaluation.py 20

# RAG vs LLM comparison (requires GEMINI_API_KEY or GROQ_API_KEY)
python evaluation/rag_vs_llm_eval.py 10
```

Results are saved to `evaluation/` and automatically displayed on the Evaluation Dashboard.

---

## CLI Usage

```bash
# Run inference on a PDF from the command line
python hyperbert.py infer --pdf paper.pdf --output results/

# With custom config
python hyperbert.py infer --pdf paper.pdf --output results/ --config module0/config.json
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend health check |
| `GET` | `/api/status` | Retriever readiness + MongoDB status |
| `POST` | `/api/analyze` | Upload PDF → run M1–M8 → return JSON |
| `POST` | `/api/analyze-stream` | Upload PDF → SSE stream pipeline progress |
| `GET` | `/api/session/:id` | Fetch stored session results |
| `GET` | `/api/sessions?guest_id=` | List user's analysis history |
| `GET` | `/api/compare/:id` | RAG vs LLM comparison data |
| `GET` | `/api/download/:id/notebook` | Download `.ipynb` |
| `GET` | `/api/download/:id/script` | Download `.py` training script |
| `GET` | `/api/download/:id/yaml` | Download `.yaml` config |
| `GET` | `/api/download/:id/config` | Download `.json` config |
| `GET` | `/api/corpus/papers` | Browse corpus (with task/model filters) |
| `GET` | `/api/corpus/stats` | Corpus statistics |
| `POST` | `/api/launch-notebook/:id` | Launch embedded JupyterLab |
| `POST` | `/api/stop-notebook` | Stop JupyterLab server |
| `GET` | `/api/evaluation/loo` | LOO evaluation results |
| `GET` | `/api/evaluation/rag-vs-llm` | RAG vs LLM eval results |

---

## Project Structure

```
├── backend/
│   ├── app.py                        # Flask API server (15+ endpoints, SSE streaming)
│   ├── requirements.txt              # Python dependencies
│   └── sessions/                     # Per-session analysis storage (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── pages/                    # 8 React pages
│   │   │   ├── Landing.tsx           # Hero page with live corpus stats
│   │   │   ├── UploadProcess.tsx     # PDF drag-and-drop + pipeline animation
│   │   │   ├── ResultsDashboard.tsx  # HP table, evidence trails, exports
│   │   │   ├── ComparisonDashboard.tsx # RAG vs LLM side-by-side
│   │   │   ├── NotebookViewer.tsx    # Embedded JupyterLab viewer
│   │   │   ├── CorpusExplorer.tsx    # 455-paper corpus browser
│   │   │   ├── EvaluationDashboard.tsx # LOO accuracy metrics & charts
│   │   │   └── Methodology.tsx       # Architecture & methodology page
│   │   ├── components/               # NavBar, ThemeToggle, AuthGuard, etc.
│   │   ├── contexts/                 # AuthContext (Auth0), SessionContext
│   │   ├── lib/api.ts                # API client with SSE support
│   │   └── styles/globals.css        # Design system (CSS variables)
│   ├── package.json
│   └── vite.config.ts                # Vite config with API proxy
│
├── src/
│   ├── module1/pdf_analyzer.py       # PDF text extraction + HP regex
│   ├── module2/completeness.py       # R-Score computation
│   ├── module3/
│   │   ├── retriever.py              # FAISS search + MongoDB document fetch
│   │   ├── engine.py                 # Inference orchestrator (4-strategy cascade)
│   │   ├── aggregator.py             # Weighted median/mode aggregation
│   │   ├── confidence.py             # Three-axis confidence scoring
│   │   ├── strategy.py              # S1–S4 retrieval strategy cascade
│   │   └── taxonomy.py               # Task/dataset name normalization
│   ├── module4/constraints.py        # 18 BERT domain rules
│   ├── module5/
│   │   ├── contradictions.py         # IQR outlier detection
│   │   └── plausibility.py           # Cross-parameter plausibility checks
│   ├── module6/validator.py          # Range validation + auto-correction
│   ├── module7/notebook_gen.py       # Task-aware Jupyter notebook generator
│   └── module8/
│       ├── meta_agent.py             # Adaptive reasoning agent
│       ├── llm_baseline.py           # Gemini/Groq LLM comparison
│       └── ollama_client.py          # Local Ollama LLM client
│
├── evaluation/
│   ├── loo_evaluation.py             # Leave-One-Out accuracy evaluation
│   ├── rag_vs_llm_eval.py            # Head-to-head RAG vs LLM benchmark
│   ├── retrieval_eval.py             # FAISS retrieval quality evaluation
│   └── corpus_audit.py              # Corpus coverage & quality audit
│
├── hyperbert.py                      # CLI entry point
├── rebuild_faiss.py                  # Rebuild FAISS index from MongoDB
└── .env                              # Environment variables (gitignored)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite, Framer Motion, Recharts, Lucide Icons |
| **Backend** | Python 3.11, Flask, Flask-CORS, Server-Sent Events |
| **Database** | MongoDB Atlas (pymongo) |
| **Search** | FAISS (384-dim cosine similarity), Sentence-Transformers (all-MiniLM-L6-v2) |
| **PDF Parsing** | pdfplumber, PyMuPDF |
| **LLM** | Google Gemini 2.0 Flash, Groq (Llama 3.1), Ollama (Qwen, local) |
| **Auth** | Auth0 (optional, popup-based Google sign-in) |
| **Notebook** | JupyterLab (optional, for embedded execution) |

---

## Environment Variables

| Variable | Location | Required | Description |
|----------|----------|----------|-------------|
| `MONGODB_URI` | `.env` | **Yes** | MongoDB connection string |
| `GEMINI_API_KEY` | `.env` | No | Google Gemini API key for LLM comparison |
| `GROQ_API_KEY` | `.env` | No | Groq API key (Llama 3.1 fallback) |
| `VITE_AUTH0_DOMAIN` | `frontend/.env` | No | Auth0 tenant domain |
| `VITE_AUTH0_CLIENT_ID` | `frontend/.env` | No | Auth0 application client ID |

> Without API keys, the system works fully — LLM comparison and Auth0 are gracefully skipped.

---

## License

Academic research project — Capstone/Major Project.
