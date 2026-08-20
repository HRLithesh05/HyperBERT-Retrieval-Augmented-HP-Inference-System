"""Rebuild FAISS index from current MongoDB data.

Reads all papers from papers_clean, computes embeddings, and saves
a new FAISS index + ID mapping that matches the current MongoDB ObjectIds.
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import faiss
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

# Load config
config = json.load(open(ROOT / "module0" / "config.json", encoding="utf-8"))
faiss_cfg = config.get("faiss", {})

# Connect to MongoDB
uri = os.environ.get("MONGODB_URI", config["mongodb"]["uri"])
client = MongoClient(uri, serverSelectionTimeoutMS=10000)
db_name = config["mongodb"].get("database", "hyperbert")
db = client[db_name]
clean_col = db[config["mongodb"].get("clean_collection", "papers_clean")]

# Gather texts + IDs
print("Loading papers from MongoDB...")
doc_ids = []
texts = []
text_fields = faiss_cfg.get("text_fields", ["title", "abstract"])

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
print(f"Found {n} papers")

if n == 0:
    print("ERROR: No papers found!")
    sys.exit(1)

# Encode with sentence-transformer
model_name = faiss_cfg.get("embedding_model", "all-MiniLM-L6-v2")
print(f"Encoding {n} papers with {model_name}...")
model = SentenceTransformer(model_name)
embeddings = model.encode(
    texts,
    show_progress_bar=True,
    batch_size=64,
    normalize_embeddings=True,
)
embeddings = np.array(embeddings, dtype=np.float32)
dim = embeddings.shape[1]

# Build FAISS index
print(f"Building FAISS IndexFlatIP (dim={dim}, n={n})...")
index = faiss.IndexFlatIP(dim)
index.add(embeddings)

# Save
index_path = ROOT / faiss_cfg.get("index_path", "module0/data/faiss_index.bin")
ids_path = ROOT / faiss_cfg.get("ids_path", "module0/data/faiss_ids.json")

index_path.parent.mkdir(parents=True, exist_ok=True)
faiss.write_index(index, str(index_path))
ids_path.write_text(json.dumps(doc_ids, indent=2), encoding="utf-8")

print(f"✅ FAISS index saved: {index_path} ({index.ntotal} vectors, {dim}d)")
print(f"✅ ID mapping saved: {ids_path} ({len(doc_ids)} IDs)")

# Verify
print("\nVerification:")
test_ids = doc_ids[:3]
from bson import ObjectId
for tid in test_ids:
    doc = clean_col.find_one({"_id": ObjectId(tid)})
    print(f"  ID {tid[:12]}... → {doc['title'][:50]}..." if doc else f"  ID {tid[:12]}... → NOT FOUND")
