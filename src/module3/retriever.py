"""Module 3 — FAISS Retriever.

Loads the pre-built FAISS index and ID mapping from Module 0,
encodes user queries, and retrieves the most similar papers from MongoDB.
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from bson import ObjectId


class FAISSRetriever:
    """Vector similarity retriever backed by FAISS + MongoDB."""

    def __init__(self, config: dict, mongo_db):
        """Initialize retriever.

        Args:
            config: Full config dict (must have 'faiss' and 'mongodb' keys).
            mongo_db: pymongo Database instance.
        """
        faiss_cfg = config.get("faiss", {})
        base = Path.cwd()

        index_path = str((base / faiss_cfg["index_path"]).resolve())
        ids_path = str((base / faiss_cfg["ids_path"]).resolve())

        self.index = faiss.read_index(index_path)
        with open(ids_path, "r", encoding="utf-8") as f:
            self.id_list = json.load(f)

        self.clean_col = mongo_db[
            config["mongodb"].get("clean_collection", "papers_clean")
        ]

        # Load embedding model (lazy)
        self._model = None
        self._model_name = faiss_cfg.get("embedding_model", "all-MiniLM-L6-v2")

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode_query(self, text: str) -> np.ndarray:
        """Encode a query string into a normalized embedding vector."""
        vec = self.model.encode([text], normalize_embeddings=True)
        return vec.astype("float32")

    def retrieve(self, query_text: str, top_k: int = 20) -> list[dict]:
        """Retrieve the top-k most similar papers.

        Args:
            query_text: The user paper's title + abstract.
            top_k: Number of results to return.

        Returns:
            List of MongoDB documents with an added 'similarity' field.
        """
        query_vec = self.encode_query(query_text)
        scores, indices = self.index.search(query_vec, min(top_k, len(self.id_list)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.id_list):
                continue
            doc_id = self.id_list[idx]
            doc = self.clean_col.find_one({"_id": ObjectId(doc_id)})
            if doc:
                doc["similarity"] = float(score)
                results.append(doc)

        return results

    def retrieve_filtered(
        self,
        query_text: str,
        task: str | None = None,
        model_name: str | None = None,
        dataset: str | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        """Retrieve top-k papers, optionally pre-filtered by task/model/dataset.

        Retrieves a larger pool from FAISS (3x top_k), then filters by
        metadata in Python.  This avoids needing a separate FAISS index
        per task.
        """
        # Get a wider pool
        candidates = self.retrieve(query_text, top_k=top_k * 3)

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
