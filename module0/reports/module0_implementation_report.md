# Module 0 Implementation Report (Data Collection)

Date: 2026-05-10

## Scope
This report covers the completed implementation of Module 0 (Corpus Builder) for the Retrieval-Augmented Hyperparameter Inference System for BERT fine-tuning papers. It documents the data sources, pipeline steps, validations, outputs, and current coverage.

## Environment
- OS: Windows
- Python: 3.11.8
- Database: MongoDB (local)
- Workspace root: E:\major_project_datacollection

## Data Sources (Free/Open)
- Semantic Scholar (Graph API; API key via SEMANTIC_SCHOLAR_API_KEY or config)
- OpenAlex (works metadata and open access links)
- Crossref (DOI metadata and PDF links when available)
- arXiv (metadata + PDF links)

Query inputs used (current config):
- OpenAlex query: "BERT fine-tuning hyperparameters"
- Crossref query: "BERT fine-tuning hyperparameters"
- Semantic Scholar query: "BERT fine-tuning hyperparameters" (fallback: "bert fine tuning")
- arXiv query: all:bert AND all:"fine-tuning"
- Year range: 2018 to 2026

## Pipeline Implementation

### 1) Collect metadata
- Sources: Semantic Scholar, OpenAlex, Crossref, arXiv
- Output: raw records stored in MongoDB collection hyperbert.papers
- Normalization:
  - Title normalization for dedup support
  - Common fields: title, abstract, year, authors, venue, doi, url, pdf_url, open_access_pdf
  - Source traceability: source, source_id, and externalIds (Semantic Scholar)

### 2) PDF URL enrichment (missing PDFs)
- Enrichment attempts:
  - OpenAlex best_oa_location pdf_url
  - Crossref link[] for PDF
  - arXiv direct PDF guess for arXiv source_ids
- Updates stored on each record:
  - pdf_url, open_access_pdf
  - pdf_enriched metadata and errors

### 3) PDF download
- Downloads PDFs for records with pdf_url
- Validations:
  - Response content-type must be PDF or file must start with %PDF
  - Retries with exponential backoff (configurable user-agent)
- Stored:
  - pdf_path, pdf_sha256, pdf_bytes, pdf_downloaded

### 4) Text + table extraction
- Text extraction:
  - PyMuPDF when available, fallback to pdfplumber
- Table extraction:
  - pdfplumber tables
- Stored:
  - raw_text_path, tables_path, text_len, table_count, text_extractor

### 5) Domain refinement (suitability)
- Heuristic scoring to keep only BERT family fine-tuning papers
- Signals:
  - BERT-family model mentions (bert, biobert, scibert, etc.)
  - Fine-tuning or task keywords
  - Exclusion patterns for surveys/reviews/roadmaps (title and abstract only)
- Stored:
  - domain score, hits, is_suitable
  - tags.domain_suitable
- Report: module0/reports/domain_report.json

### 6) QC + clean export (robust dataset)
- QC checks:
  - PDF exists on disk
  - PDF header is valid
  - PDF size >= 10KB
  - Raw text exists and length >= 500 chars
- Duplicates are blocked (if any)
- Clean exports:
  - hyperbert.papers_clean (strict profile)
  - hyperbert.papers_clean_relaxed (relaxed profile)
- Reports:
  - module0/reports/qc_report_strict.json
  - module0/reports/qc_report_relaxed.json

### 7) Schema validation (MongoDB)
- Raw collection validation: warn on missing key fields
- Clean collections: error on missing required fields
- Ensures downstream modules only see valid documents

## Robustness and Reliability Measures
- Filename sanitization for Windows paths
- PDF header validation and minimum size thresholds before acceptance
- Retries with backoff for network and provider rate-limit errors
- Extraction fallback (PyMuPDF primary, pdfplumber fallback)
- Semantic Scholar field constraints: DOI derived from externalIds; API errors handled gracefully
- Schema validation gates for clean exports

## Output Locations
- Raw PDFs: module0/data/pdfs
- Raw text: module0/data/raw_text
- Tables: module0/data/tables
- Reports: module0/reports

## Current Dataset Metrics (latest run)
Domain refinement report:
- Total records: 1022
- Domain suitable: 1001
- Domain unsuitable: 21
- Duplicate candidates: 67

QC export (strict profile):
- Eligible: 435
- Exported: 435
- Blocked: 587
- Duplicate blocked: 67
- Missing PDF: 494
- Missing text: 498
- Small text: 1

QC export (relaxed profile):
- Exported: 435 (same as strict in this run)

Notes:
- Enrichment status is tracked per record (pdf_enriched, pdf_enrich_error) in MongoDB.
- Detailed issue samples are recorded in module0/reports/qc_report_strict.json and module0/reports/qc_report_relaxed.json.

## Known Limitations
- Many papers do not have open-access PDFs, so they are blocked at QC.
- Some enrichment requests fail due to missing OA data or provider rate limits.
- Unpaywall is available but not enabled (requires email in config).
- Some PDFs contain non-standard encodings, which can slightly affect extracted text quality.

## How to Reproduce (Commands)
From workspace root:
1) Collect metadata
   python module0/src/cli.py --config module0/config.json --steps collect
2) Enrich missing PDF URLs
   python module0/src/cli.py --config module0/config.json --steps enrich
3) Download PDFs
   python module0/src/cli.py --config module0/config.json --steps download
4) Extract text and tables
   python module0/src/cli.py --config module0/config.json --steps extract
5) Domain refinement
   python module0/src/cli.py --config module0/config.json --steps refine
6) QC export (strict + relaxed)
   python module0/src/cli.py --config module0/config.json --steps qc

## Summary
Module 0 is implemented end-to-end with metadata collection, PDF enrichment, downloads, extraction, domain filtering, QC, and strict clean export. The clean dataset in papers_clean is robust and schema-validated for downstream modules.
