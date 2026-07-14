"""Module 3 — FAISS Retriever (Performance-Optimized).

Loads the pre-built FAISS index and ID mapping from Module 0,
encodes user queries, and retrieves the most similar papers from MongoDB.

KEY OPTIMIZATION: Uses batch MongoDB queries ($in) instead of individual
find_one() calls, reducing network roundtrips from ~60 to 1 per retrieve().
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import faiss
import numpy as np
from bson import ObjectId


class FAISSRetriever:
    """Vector similarity retriever backed by FAISS + MongoDB."""

    def __init__(self, config: dict, mongo_db, preload_model: bool = False):
        """Initialize retriever.

        Args:
            config: Full config dict (must have 'faiss' and 'mongodb' keys).
            mongo_db: pymongo Database instance.
            preload_model: If True, load the sentence-transformer model immediately.
        """
        faiss_cfg = config.get("faiss", {})
        base = Path(__file__).resolve().parent.parent.parent

        index_path = str((base / faiss_cfg["index_path"]).resolve())
        ids_path = str((base / faiss_cfg["ids_path"]).resolve())

        self.index = faiss.read_index(index_path)
        with open(ids_path, "r", encoding="utf-8") as f:
            self.id_list = json.load(f)

        self.clean_col = mongo_db[
            config["mongodb"].get("clean_collection", "papers_clean")
        ]

        # Embedding model (lazy by default, eager if preload_model=True)
        self._model = None
        self._model_name = faiss_cfg.get("embedding_model", "all-MiniLM-L6-v2")

        # Cache: query text → embedding vector
        self._embed_cache: dict[str, np.ndarray] = {}
        # Cache: doc_id string → MongoDB document (avoids re-fetching)
        self._doc_cache: dict[str, dict] = {}

        if preload_model:
            _ = self.model  # Force load now

    @property
    def model(self):
        if self._model is None:
            t0 = time.perf_counter()
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            print(f"  [Retriever] Model loaded in {time.perf_counter()-t0:.1f}s")
        return self._model

    def encode_query(self, text: str) -> np.ndarray:
        """Encode a query string into a normalized embedding vector (cached)."""
        if text in self._embed_cache:
            return self._embed_cache[text]
        t0 = time.perf_counter()
        vec = self.model.encode([text], normalize_embeddings=True).astype("float32")
        self._embed_cache[text] = vec
        print(f"  [Retriever] Query encoded in {time.perf_counter()-t0:.2f}s")
        return vec

    def retrieve(self, query_text: str, top_k: int = 20) -> list[dict]:
        """Retrieve the top-k most similar papers.

        Uses BATCH MongoDB query ($in) instead of individual find_one() calls.
        Caches documents so repeated calls (S1→S4) don't re-fetch from the network.
        """
        query_vec = self.encode_query(query_text)
        scores, indices = self.index.search(query_vec, min(top_k, len(self.id_list)))

        # Collect IDs and scores, separate cached vs uncached
        id_score_map: dict[str, float] = {}
        ordered_ids: list[str] = []
        uncached_ids: list[str] = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.id_list):
                continue
            doc_id = self.id_list[idx]
            id_score_map[doc_id] = float(score)
            ordered_ids.append(doc_id)
            if doc_id not in self._doc_cache:
                uncached_ids.append(doc_id)

        # BATCH fetch all uncached documents in ONE MongoDB query
        if uncached_ids:
            t0 = time.perf_counter()
            cursor = self.clean_col.find(
                {"_id": {"$in": [ObjectId(did) for did in uncached_ids]}}
            )
            for doc in cursor:
                str_id = str(doc["_id"])
                self._doc_cache[str_id] = doc
            elapsed = time.perf_counter() - t0
            print(f"  [Retriever] Fetched {len(uncached_ids)} docs from MongoDB in {elapsed:.2f}s")

        # Build results in FAISS-sorted order
        results = []
        for doc_id in ordered_ids:
            doc = self._doc_cache.get(doc_id)
            if doc:
                # Create a shallow copy so we don't mutate the cache
                result = dict(doc)
                result["similarity"] = id_score_map[doc_id]
                results.append(result)

        return results

    def retrieve_filtered(
        self,
        query_text: str,
        task: str | None = None,
        model_name: str | None = None,
        dataset: str | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        """Retrieve top-k papers, filtered by task/model/dataset.

        Uses 2x pool (not 3x) since documents are now cached.
        """
        candidates = self.retrieve(query_text, top_k=top_k * 2)

        filtered = []
        for doc in candidates:
            hp = doc.get("hp_json", {})
            doc_task = (hp.get("task") or "").lower()
            doc_model = (hp.get("model") or "").lower()
            doc_dataset = (hp.get("dataset") or "").lower()

            if task and task.lower() not in doc_task and doc_task not in task.lower():
                continue
            if model_name and model_name.lower() not in doc_model and doc_model not in model_name.lower():
                continue
            if dataset and dataset.lower() not in doc_dataset and doc_dataset not in dataset.lower():
                continue

            filtered.append(doc)

            if len(filtered) >= top_k:
                break

        return filtered
