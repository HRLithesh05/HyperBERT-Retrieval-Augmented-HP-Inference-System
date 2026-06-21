# Domain Refinement

This step scores every collected paper to decide whether it is suitable for the BERT fine-tuning corpus.

Heuristics:
- Requires a BERT-family mention in title/abstract (or raw text if enabled)
- Requires fine-tuning or task evidence (or hyperparameter evidence)
- Excludes surveys/reviews/roadmaps and pretraining-only papers
- Writes a domain report to module0/reports/domain_report.json

QC/export step:
- Validates PDFs and extracted text sizes
- Checks PDF header bytes
- Exports clean subsets per qc_profiles (papers_clean, papers_clean_relaxed)
- Writes module0/reports/qc_report_<profile>.json
