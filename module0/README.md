# Module 0 - Corpus Builder (Data Collection)

This module builds the raw BERT fine-tuning corpus by harvesting metadata, downloading PDFs, and extracting raw text/tables for later hyperparameter extraction.

## What it does

- Collects paper metadata from Semantic Scholar, arXiv, OpenAlex, and Crossref
- Tags each record for BERT fine-tuning relevance
- Deduplicates and stores records in MongoDB
- Enriches missing PDF URLs from open-access sources
- Downloads PDFs when available
- Extracts raw text (PyMuPDF) and tables (pdfplumber)
- Refines domain suitability and generates a quality report
- Runs QC checks and exports a clean corpus collection
- Enforces MongoDB schema validation for raw and clean collections

## Quick start

1) Copy the example config and fill in your values.

2) Create a .env file at the repo root if you want to use environment variables.

	SEMANTIC_SCHOLAR_API_KEY=YOUR_KEY_HERE

3) Install dependencies.

4) Run the pipeline steps.

```bash
# from repo root
python -m pip install -r module0/requirements.txt
python module0/src/cli.py --config module0/config.json --steps all
```

## Notes

- OpenAlex and Crossref are free and do not require API keys.
- Semantic Scholar requires an API key (set SEMANTIC_SCHOLAR_API_KEY in .env or config).
- arXiv does not require a key but is rate limited.
- Use the filter flag in config to enforce BERT fine-tuning scope.
- MongoDB defaults to a local instance at mongodb://localhost:27017.
- Run the refine step after extraction to flag unsuitable papers.
- Run the qc step to export a clean collection (papers_clean).
- Schema validation is applied automatically on pipeline start.
- Use qc_profiles to generate strict and relaxed clean collections.
