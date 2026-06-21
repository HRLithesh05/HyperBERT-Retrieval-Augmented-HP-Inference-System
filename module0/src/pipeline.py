from pathlib import Path

from db.mongo import MongoStore
from pdf.download import download_missing_pdfs
from pdf.enrich import enrich_pdf_urls
from pdf.extract import extract_missing_text
from quality.domain_refine import refine_domain
from quality.qc_export import qc_and_export


class Pipeline:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.store = MongoStore(config["mongodb"])
        self.store.ensure_indexes(config)
        self.store.ensure_schema(config)

    def collect_metadata(self) -> None:
        from sources.arxiv import fetch_arxiv
        from sources.crossref import fetch_crossref
        from sources.openalex import fetch_openalex
        from sources.semantic_scholar import fetch_semantic_scholar

        query = self.config["query"]
        sources = self.config["sources"]
        filter_cfg = self.config.get("filter", {})
        require_bert = bool(filter_cfg.get("require_bert_finetune", False))

        if sources.get("openalex", {}).get("enabled", True):
            openalex_papers = fetch_openalex(query, sources["openalex"])
            self.store.upsert_many(self._tag_and_filter(openalex_papers, require_bert))

        if sources.get("crossref", {}).get("enabled", True):
            crossref_papers = fetch_crossref(query, sources["crossref"])
            self.store.upsert_many(self._tag_and_filter(crossref_papers, require_bert))

        if sources.get("semantic_scholar", {}).get("enabled", True):
            ss_papers = fetch_semantic_scholar(query, sources["semantic_scholar"])
            self.store.upsert_many(self._tag_and_filter(ss_papers, require_bert))

        if sources.get("arxiv", {}).get("enabled", True):
            try:
                arxiv_papers = fetch_arxiv(query, sources["arxiv"])
                self.store.upsert_many(self._tag_and_filter(arxiv_papers, require_bert))
            except Exception as exc:
                print(f"arXiv fetch failed: {exc}")

    def download_pdfs(self) -> None:
        paths = self._resolve_paths()
        download_cfg = self.config["download"]
        download_missing_pdfs(self.store, paths["pdf_dir"], download_cfg)

    def enrich_pdfs(self) -> None:
        paths = self._resolve_paths()
        enrich_pdf_urls(self.store, self.config, paths)

    def extract_text(self) -> None:
        paths = self._resolve_paths()
        extract_missing_text(
            self.store,
            pdf_dir=paths["pdf_dir"],
            raw_text_dir=paths["raw_text_dir"],
            tables_dir=paths["tables_dir"],
        )

    def refine_domain(self) -> None:
        paths = self._resolve_paths()
        refine_domain(self.store, self.config, paths)

    def qc_and_export(self) -> None:
        paths = self._resolve_paths()
        qc_and_export(self.store, self.config, paths)

    # ---- NEW: Module 0 Steps 3, 4, 5 ----

    def extract_hyperparams(self) -> None:
        """Step 3: Two-Pass LLM HP extraction on clean papers."""
        from hp.hp_extract import extract_hyperparams

        paths = self._resolve_paths()
        extract_hyperparams(self.store, self.config, paths)

    def build_faiss_index(self) -> None:
        """Step 4: Build FAISS vector index from clean papers."""
        from index.faiss_build import build_faiss_index

        paths = self._resolve_paths()
        build_faiss_index(self.store, self.config, paths)

    def compute_rscores(self) -> None:
        """Step 5: Compute R-Scores for all papers with hp_json."""
        from quality.rscore import compute_rscores

        paths = self._resolve_paths()
        compute_rscores(self.store, self.config, paths)

    # ---- helpers ----

    def _resolve_paths(self) -> dict:
        base = Path.cwd()
        paths = self.config["paths"]
        return {
            "pdf_dir": (base / paths["pdf_dir"]).resolve(),
            "raw_text_dir": (base / paths["raw_text_dir"]).resolve(),
            "tables_dir": (base / paths["tables_dir"]).resolve(),
            "reports_dir": (base / paths.get("reports_dir", "module0/reports")).resolve(),
        }

    def _tag_and_filter(self, records: list[dict], require_bert: bool) -> list[dict]:
        tagged = []
        for record in records:
            title = (record.get("title") or "").lower()
            abstract = (record.get("abstract") or "").lower()
            combined = f"{title} {abstract}"

            is_bert = "bert" in combined
            is_finetune = "fine-tun" in combined or "fine tun" in combined
            is_candidate = is_bert and is_finetune

            record["tags"] = {
                "is_bert": is_bert,
                "is_finetune": is_finetune,
                "is_candidate": is_candidate,
            }

            if require_bert and not is_candidate:
                continue
            tagged.append(record)

        return tagged
