# Module 0 - Full Data Collection Process and Procedure

Date: 2026-05-10

## 1) Purpose and scope
Module 0 builds a reproducible corpus of BERT fine-tuning papers with metadata, PDFs, extracted text, and tables for downstream modules. It covers collection, enrichment, download, extraction, domain filtering, quality control, and clean export.

## 2) Environment and dependencies
- OS: Windows
- Python: 3.11.8
- Database: MongoDB (local instance)
- Workspace root: E:\major_project_datacollection

Dependencies (module0/requirements.txt):
- requests==2.32.3
- pymongo==4.6.3
- pymupdf==1.24.5
- pdfplumber==0.11.4
- tqdm==4.66.4
- python-dotenv==1.0.1

## 3) Project structure
Module 0 layout:
- module0/config.json
- module0/config.example.json
- module0/requirements.txt
- module0/README.md
- module0/src/
  - cli.py
  - pipeline.py
  - db/mongo.py
  - sources/openalex.py
  - sources/crossref.py
  - sources/semantic_scholar.py
  - sources/arxiv.py
  - pdf/enrich.py
  - pdf/download.py
  - pdf/extract.py
  - quality/domain_refine.py
  - quality/qc_export.py
- module0/data/
  - pdfs/
  - raw_text/
  - tables/
- module0/reports/
  - domain_report.json
  - qc_report_strict.json
  - qc_report_relaxed.json
  - qc_report.json (legacy)
  - module0_implementation_report.md
  - module0_implementation_presentation.md

Root files:
- .env (holds SEMANTIC_SCHOLAR_API_KEY)
- .gitignore (excludes .env)
- .venv/ (Python virtual environment)

## 4) Configuration details (module0/config.json)
Query:
- openalex_query: "BERT fine-tuning hyperparameters"
- crossref_query: "BERT fine-tuning hyperparameters"
- semantic_scholar_query: "BERT fine-tuning hyperparameters"
- arxiv_query: all:bert AND all:"fine-tuning"
- year_from: 2018
- year_to: 2026
- max_results: 400

Source settings:
- openalex: enabled, base_url, per_page, max_results
- semantic_scholar: enabled, base_url, fields, api_key, max_results, use_year_filter, fallback_query
- crossref: enabled, base_url, rows, max_results
- arxiv: enabled, base_url, retries, backoff_sec, max_results

MongoDB:
- uri: mongodb://localhost:27017
- db: hyperbert
- collection: papers
- clean_collection: papers_clean
- clean_collections: papers_clean and papers_clean_relaxed

Validation:
- raw_action: warn
- clean_action: error
- level: moderate

Paths:
- pdf_dir: module0/data/pdfs
- raw_text_dir: module0/data/raw_text
- tables_dir: module0/data/tables
- reports_dir: module0/reports

Domain scoring:
- use_raw_text: true
- raw_text_max_chars: 50000
- min_score: 3
- require_finetune_or_task: true
- hard_exclude: true

Download:
- timeout_sec: 60
- user_agent: HyperBERT-Collector/0.1
- retries: 3
- backoff_sec: 2

PDF enrichment:
- enabled: true
- use_openalex: true
- use_crossref: true
- use_unpaywall: false
- use_arxiv_guess: true
- request_delay_sec: 0.2
- unpaywall_email: "" (empty by default)

QC default:
- min_pdf_bytes: 10000
- min_text_chars: 500
- require_tables: false
- export_only_suitable: true
- skip_duplicates: true

QC profiles:
- strict: min_pdf_bytes 10000, min_text_chars 500, collection papers_clean
- relaxed: min_pdf_bytes 5000, min_text_chars 200, collection papers_clean_relaxed

## 5) Environment variable and .env support
- .env is loaded automatically by module0/src/cli.py
- Use SEMANTIC_SCHOLAR_API_KEY in .env to access Semantic Scholar
- Config field sources.semantic_scholar.api_key can also be used (left empty by default)

## 6) Database design (MongoDB)
Collections:
- Raw: hyperbert.papers
- Clean: hyperbert.papers_clean
- Clean relaxed: hyperbert.papers_clean_relaxed

Indexes created (raw):
- unique compound: (source, source_id)
- title_norm
- year
- tags.is_candidate
- tags.domain_suitable
- dedup.is_duplicate

Indexes created (clean):
- unique compound: (source, source_id)
- tags.domain_suitable
- dedup.is_duplicate

Schema validation:
- Raw: warns if missing required fields
  - required: source, source_id, title
  - optional: year (int or null)
- Clean: errors if missing required fields
  - required: source, source_id, title, pdf_path, raw_text_path, tags, qc
  - tags.domain_suitable must be boolean
  - qc.passed and qc.checked_at required

## 7) Pipeline entry points
CLI: module0/src/cli.py
- Loads .env
- Reads config JSON
- Creates Pipeline(config)
- Steps: collect, enrich, download, extract, refine, qc, or all

Orchestration: module0/src/pipeline.py
- Ensures indexes and schema
- Runs each step in order
- Resolves output paths relative to workspace root

## 8) Source collection details

OpenAlex (module0/src/sources/openalex.py):
- Uses cursor-based pagination
- Filters by publication date if year_from/year_to present
- Extracts:
  - source/source_id/title/title_norm/abstract/year/authors/venue
  - publication_types, doi, external_ids, url
  - open_access_pdf and pdf_url from best_oa_location or open_access
  - citation_count, reference_count

Crossref (module0/src/sources/crossref.py):
- Uses query.bibliographic with offset pagination
- Filters by published date range if year_from/year_to present
- Extracts:
  - doi, title, abstract, authors, venue, year
  - PDF url from link[] when content-type indicates PDF or URL ends with .pdf

Semantic Scholar (module0/src/sources/semantic_scholar.py):
- Uses Graph API search with offset paging
- API key via SEMANTIC_SCHOLAR_API_KEY or config
- Fallback query used on 400 response
- Extracts:
  - paperId, title, abstract, year, authors, venue
  - DOI from externalIds (external_ids.DOI)
  - openAccessPdf and pdf_url
  - citation_count, reference_count

arXiv (module0/src/sources/arxiv.py):
- Uses Atom API
- Retries with exponential backoff
- Extracts:
  - id, title, abstract, year, authors, pdf_url
  - source_id from entry id tail

## 9) Tagging and initial filtering
During collection (pipeline._tag_and_filter):
- is_bert: "bert" appears in title or abstract
- is_finetune: "fine-tun" or "fine tun" appears in title or abstract
- is_candidate: is_bert and is_finetune
- tags stored on each record
- If filter.require_bert_finetune is true, non-candidates are dropped before insert

## 10) PDF URL enrichment
module0/src/pdf/enrich.py
- Runs for records with missing pdf_url or pdf_downloaded false
- Sources (in order):
  1) OpenAlex best_oa_location for OpenAlex records
  2) Crossref link[] for records with DOI
  3) Unpaywall (optional, requires email)
  4) arXiv PDF guess for arXiv records
- Updates:
  - pdf_url and open_access_pdf
  - pdf_enriched metadata with source and timestamp
- Errors captured in pdf_enrich_error
- Throttled via request_delay_sec

## 11) PDF download and validation
module0/src/pdf/download.py
- Safe filenames: source + sanitized source_id
- Validates content:
  - content-type contains "pdf" or file starts with %PDF
- Retries with exponential backoff
- Stores:
  - pdf_path, pdf_sha256, pdf_bytes, pdf_downloaded
- Errors captured in pdf_error

## 12) Text and table extraction
module0/src/pdf/extract.py
- Extracts text with PyMuPDF; falls back to pdfplumber
- Extracts tables with pdfplumber
- Writes:
  - raw_text_path (.txt)
  - tables_path (.json)
- Stores:
  - text_len, table_count, text_extractor
- Errors captured in text_error

## 13) Domain refinement and dedup
module0/src/quality/domain_refine.py
- Uses patterns for:
  - model mentions (bert variants)
  - fine-tuning keywords
  - task keywords
  - hyperparameter keywords
  - exclude patterns (survey, review, roadmap, overview, tutorial)
- Scoring:
  - +3 if model hits
  - +2 if finetune hits
  - +1 if task hits
  - +1 if hyperparameter hits
  - -3 if exclude hits
- Logic:
  - require_finetune_or_task gate
  - hard_exclude for exclude patterns
  - min_score threshold
- Dedup:
  - key is DOI or normalized title
  - marks duplicates and counts them
- Updates:
  - domain section (hits, score, is_suitable, updated_at)
  - tags.domain_suitable
  - dedup info
- Writes report: module0/reports/domain_report.json

## 14) QC and clean export
module0/src/quality/qc_export.py
- Runs for each profile in qc_profiles
- Checks in order:
  - domain_suitable is true (if export_only_suitable)
  - not duplicate (if skip_duplicates)
  - pdf exists
  - text exists
  - tables exist (if require_tables)
  - pdf size >= min_pdf_bytes
  - pdf header starts with %PDF
  - text length >= min_text_chars
- On pass, writes clean document with:
  - core metadata, pdf_path, raw_text_path, tables_path
  - tags, domain, dedup, metadata
  - qc block (passed, checked_at, profile)
- Reports:
  - module0/reports/qc_report_strict.json
  - module0/reports/qc_report_relaxed.json

## 15) Reports and what they contain
- domain_report.json: counts of suitable/unsuitable/duplicates and config used
- qc_report_strict.json: QC stats and issue samples for strict profile
- qc_report_relaxed.json: QC stats and issue samples for relaxed profile
- module0_implementation_report.md: implementation summary
- module0_implementation_presentation.md: 2-slide presentation content

## 16) Outputs on disk
- PDFs: module0/data/pdfs
- Raw text: module0/data/raw_text
- Tables: module0/data/tables
- Reports: module0/reports

## 17) Reproducible run procedure
From workspace root:
1) Install dependencies
   - e:/major_project_datacollection/.venv/Scripts/python.exe -m pip install -r module0/requirements.txt
2) Set API key (in .env)
   - SEMANTIC_SCHOLAR_API_KEY=YOUR_KEY_HERE
3) Run steps
   - python module0/src/cli.py --config module0/config.json --steps collect
   - python module0/src/cli.py --config module0/config.json --steps enrich
   - python module0/src/cli.py --config module0/config.json --steps download
   - python module0/src/cli.py --config module0/config.json --steps extract
   - python module0/src/cli.py --config module0/config.json --steps refine
   - python module0/src/cli.py --config module0/config.json --steps qc

## 18) Latest metrics (from reports)
Domain report:
- total: 1022
- suitable: 1001
- unsuitable: 21
- duplicates: 67

QC strict report:
- total: 1022
- eligible: 435
- exported: 435
- blocked: 587
- duplicate_blocked: 67
- missing_pdf: 494
- missing_text: 498
- small_text: 1
- bad_pdf_header: 0

QC relaxed report:
- exported: 435 (same as strict for this run)

## 19) Known limitations
- Open access availability limits PDF coverage.
- Provider rate limits or missing OA data can block enrichment.
- Some PDFs contain non-standard encodings which can affect extracted text.
- Unpaywall support is present but disabled by default (email required).

## 20) Summary
Module 0 is fully implemented end-to-end. It collects data from multiple sources, enriches and downloads PDFs, extracts text and tables, filters by domain, validates quality, and exports clean collections with schema validation and reports for traceability.
