"""Build a FAISS IndexFlatIP from the clean corpus (Module 0, Step 4).

Uses sentence-transformers to encode ``title + abstract`` for each
paper in ``papers_clean``, L2-normalises the vectors, and stores them
in a FAISS inner-product index.  This index is what Module 3 queries
at runtime for top-k retrieval.

Outputs
-------
- ``faiss_index.bin``  — serialised FAISS index
- ``faiss_ids.json``   — ordered list mapping index position → MongoDB doc id
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def build_faiss_index(store, config: dict, paths: dict) -> None:
    """Encode clean-corpus papers and build a FAISS index."""
    faiss_cfg = config.get("faiss", {})
    model_name = faiss_cfg.get("embedding_model", "all-MiniLM-L6-v2")
    text_fields = faiss_cfg.get("text_fields", ["title", "abstract"])

    base = Path.cwd()
    index_path = (base / faiss_cfg.get("index_path", "module0/data/faiss_index.bin")).resolve()
    ids_path = (base / faiss_cfg.get("ids_path", "module0/data/faiss_ids.json")).resolve()

    clean_name = config["mongodb"].get("clean_collection", "papers_clean")
    clean_col = store.get_collection(clean_name)

    # gather texts + ids
    print(f"Loading papers from {clean_name} ...")
    doc_ids: list[str] = []
    texts: list[str] = []

    for doc in clean_col.find({}, batch_size=200):
        parts = []
        for field in text_fields:
            val = doc.get(field)
            if val:
                parts.append(str(val).strip())
        text = ". ".join(parts)
        if not text or len(text) < 20:
            continue
        doc_ids.append(str(doc["_id"]))
        texts.append(text)

    n = len(texts)
    if n == 0:
        print("No papers found in clean collection — nothing to index.")
        return

    print(f"Encoding {n} papers with {model_name} ...")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,  # L2-norm → inner product = cosine
    )

    # ensure float32 numpy array
    embeddings = np.array(embeddings, dtype=np.float32)
    dim = embeddings.shape[1]

    print(f"Building IndexFlatIP (dim={dim}, n={n}) ...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # save
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    ids_path.write_text(json.dumps(doc_ids, indent=2), encoding="utf-8")

    print(f"FAISS index saved: {index_path}  ({index.ntotal} vectors, {dim}d)")
    print(f"ID mapping saved:  {ids_path}")

    # write report
    reports_dir = Path(paths["reports_dir"]).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "summary": {
            "total_papers": n,
            "embedding_dim": dim,
            "index_type": "IndexFlatIP",
            "embedding_model": model_name,
        },
        "paths": {
            "index": str(index_path),
            "ids": str(ids_path),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    report_path = reports_dir / "faiss_build_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {report_path}")
