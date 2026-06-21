# Module 0 - Slide Content (2 Slides)

## Slide 1: Corpus Builder Scope and Pipeline
- Goal: build a reproducible corpus of BERT fine-tuning papers with metadata, PDFs, extracted text, and tables for downstream modules.
- Environment: Windows, Python 3.11.8, MongoDB local; configuration in module0/config.json; CLI runner in module0/src/cli.py.
- Sources (free/open): Semantic Scholar (API key via SEMANTIC_SCHOLAR_API_KEY), OpenAlex, Crossref, arXiv; Unpaywall optional with email.
- Query setup: keyword-based queries for BERT fine-tuning; year range 2018-2026 in config.
- Step 1 - Collect: normalize titles and core fields (title, abstract, year, authors, venue, doi, url); dedupe; write to raw Mongo collection papers.
- Step 2 - Enrich: fill missing PDF links using OpenAlex best_oa_location, Crossref link[] PDFs, arXiv PDF guess; store pdf_url/open_access_pdf and enrichment metadata/errors.
- Step 3 - Download: retry + backoff with user-agent; validate PDF header and min size; store pdf_path, sha256, byte size.
- Step 4 - Extract: PyMuPDF primary extractor with pdfplumber fallback; table extraction via pdfplumber; store raw_text_path, tables_path, text_len, table_count; sanitize filenames for Windows.

## Slide 2: Quality, Robustness, Outputs, and Metrics
- Domain refinement: heuristic scoring for BERT-family fine-tuning; require fine-tuning/task signals; hard exclude surveys/reviews; tag domain_suitable and write domain_report.json.
- QC export: strict and relaxed profiles enforce PDF and text thresholds, skip duplicates, and export only suitable papers to papers_clean and papers_clean_relaxed.
- Schema validation: raw collection warns on missing fields; clean collections enforce required schema to block invalid records.
- Robustness fixes applied: filename sanitization, PDF header validation, extraction fallback when PyMuPDF fails, retry logic for provider errors, Semantic Scholar field fixes (use externalIds for DOI, handle 400/403 responses).
- Reports produced: module0/reports/domain_report.json, module0/reports/qc_report_strict.json, module0/reports/qc_report_relaxed.json, module0/reports/module0_implementation_report.md.
- Current metrics (2026-05-10): total records 1022; suitable 1001; unsuitable 21; duplicates 67; strict QC exported 435; blocked 587 (missing_pdf 494, missing_text 498, small_text 1).
- Data outputs: module0/data/pdfs, module0/data/raw_text, module0/data/tables; clean collections ready for downstream modules.
