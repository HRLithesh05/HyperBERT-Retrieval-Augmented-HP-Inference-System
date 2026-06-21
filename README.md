# HyperBERT — Retrieval-Augmented Hyperparameter Inference System

> **Transparent, evidence-backed hyperparameter inference for BERT fine-tuning papers.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://mongodb.com)

## 🎯 Problem Statement

**92% of BERT fine-tuning papers don't report all 12 standard hyperparameters** (Dodge et al., 2019), making results unreproducible. HyperBERT solves this by:

1. **Reading** a research paper PDF
2. **Extracting** whatever hyperparameters are reported
3. **Finding** similar papers using FAISS vector search over a 435-paper corpus
4. **Inferring** missing HPs using statistical aggregation with full transparency
5. **Validating** values using BERT domain constraints
6. **Generating** a ready-to-run training notebook

Every inferred value has a **citation**, **confidence score**, and **reasoning trace** — no black boxes.

## 🏗 Architecture

```
┌─────────────────────────────────────────────────┐
│  Frontend (React + Vite + TypeScript)           │
│  Landing → Upload → Dashboard → Corpus Explorer │
│  Comparison Dashboard → Evaluation → Notebook   │
│  Port 5173                                      │
├─────────────────────────────────────────────────┤
│  Backend API (Flask)                            │
│  POST /api/analyze → Run M1-M7 + M8 pipeline   │
│  GET  /api/session/:id, /api/compare/:id        │
│  GET  /api/corpus/{papers,stats}                │
│  GET  /api/evaluation/{loo,rag-vs-llm}          │
│  Port 5000                                      │
├─────────────────────────────────────────────────┤
│  Inference Pipeline (8 Modules)                 │
│  M1: PDF Analyzer → M2: Completeness →          │
│  M3: FAISS Retrieval → M4: Constraints →         │
│  M5: Contradiction → M6: Validator →             │
│  M7: Notebook Gen → M8: Meta-Agent + LLM        │
├─────────────────────────────────────────────────┤
│  Data Layer                                     │
│  MongoDB (435 papers) · FAISS Index (384-dim)   │
│  Sentence-Transformers (all-MiniLM-L6-v2)       │
└─────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB (running locally on default port)

### 1. Backend Setup
```bash
cd e:\major_project_datacollection

# Install Python dependencies
pip install -r backend/requirements.txt

# Create .env file with API keys (optional, for LLM comparison)
echo "GEMINI_API_KEY=your_key_here" > .env
echo "GROQ_API_KEY=your_key_here" >> .env

# Start MongoDB
mongod

# Start the backend
python backend/app.py
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Open the App
Navigate to **http://localhost:5173**

## 📊 Key Features

| Feature | Description |
|---------|-------------|
| **PDF Upload & Analysis** | Drag-and-drop any BERT paper PDF → live M1-M7 pipeline animation |
| **Evidence Dashboard** | Per-HP confidence decomposition, evidence table, constraint log |
| **RAG vs LLM Comparison** | Side-by-side comparison: your transparent RAG vs Gemini's black-box suggestions |
| **Meta-Agent** | Adaptive reasoning: boosts confidence when RAG+LLM agree, flags disagreements |
| **Evaluation Dashboard** | LOO accuracy metrics, strategy ablation, confidence calibration radar |
| **Notebook Execution** | Launch generated notebooks directly in embedded JupyterLab |
| **Dataset Auto-Fetch** | Detects 25+ common NLP datasets and auto-generates `load_dataset()` calls |
| **Corpus Explorer** | Browse the 435-paper corpus with filtering and search |

## 📁 Project Structure

```
major_project_datacollection/
├── backend/
│   ├── app.py                 # Flask REST API (all endpoints)
│   ├── requirements.txt       # Python dependencies
│   └── sessions/              # Session storage
├── frontend/
│   ├── src/
│   │   ├── pages/             # React pages (7 pages)
│   │   ├── components/        # Reusable components
│   │   ├── lib/api.ts         # API client
│   │   └── styles/            # CSS design system
│   └── package.json
├── src/
│   ├── module1/               # PDF Analyzer
│   ├── module2/               # Completeness Checker
│   ├── module3/               # FAISS Inference Engine
│   ├── module4/               # Domain Constraints
│   ├── module5/               # Contradiction Detection
│   ├── module6/               # Range Validator
│   ├── module7/               # Notebook Generator
│   └── module8/               # LLM Baseline + Meta-Agent
├── module0/                   # Corpus Builder (4 APIs, FAISS index)
├── evaluation/                # LOO + RAG vs LLM evaluation scripts
└── hyperbert.py               # CLI entry point
```

## 🧪 Running Evaluations

### Leave-One-Out Evaluation
```bash
# Full evaluation (may take a while)
python evaluation/loo_evaluation.py

# Quick test with 20 papers
python evaluation/loo_evaluation.py 20
```

### RAG vs LLM Comparison
```bash
# Compare RAG vs Gemini/Groq on 20 papers
python evaluation/rag_vs_llm_eval.py 20
```

Results are saved to `evaluation/` and automatically displayed on the Evaluation Dashboard.

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Optional | For LLM comparison (Gemini 2.0 Flash) |
| `GROQ_API_KEY` | Optional | Fallback LLM (Llama 3.1 8B via Groq) |

## 📈 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze` | Upload PDF → run full pipeline |
| `GET` | `/api/session/:id` | Fetch session results |
| `GET` | `/api/compare/:id` | RAG vs LLM comparison |
| `GET` | `/api/download/:id/notebook` | Download .ipynb |
| `GET` | `/api/download/:id/script` | Download .py script |
| `GET` | `/api/download/:id/yaml` | Download .yaml config |
| `GET` | `/api/corpus/papers` | Browse corpus (with filters) |
| `GET` | `/api/corpus/stats` | Corpus statistics |
| `GET` | `/api/evaluation/loo` | LOO evaluation results |
| `GET` | `/api/evaluation/rag-vs-llm` | RAG vs LLM eval results |
| `POST` | `/api/launch-notebook/:id` | Start JupyterLab |
| `POST` | `/api/stop-notebook` | Stop JupyterLab |

## 📄 License

This project is part of a capstone research project.
