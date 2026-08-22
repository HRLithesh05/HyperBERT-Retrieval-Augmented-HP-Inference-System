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

# Encode with sentence-transformer (or SPECTER2)
model_name = faiss_cfg.get("embedding_model", "all-MiniLM-L6-v2")
print(f"Encoding {n} papers with {model_name}...")

# SPECTER2 requires adapter loading
if "specter" in model_name.lower():
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        print("  Loading SPECTER2 base model + adapter...")
        alt_cfg = faiss_cfg.get("alternative_models", {}).get("specter2", {})
        base_model = alt_cfg.get("model_name", "allenai/specter2_base")
        adapter = alt_cfg.get("adapter_name", "allenai/specter2")
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        specter_model = AutoModel.from_pretrained(base_model)
        specter_model.load_adapter(adapter, set_active=True)
        specter_model.eval()

        # Encode in batches
        all_embs = []
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            inputs = tokenizer(batch, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
            with torch.no_grad():
                outputs = specter_model(**inputs)
            embs = outputs.last_hidden_state[:, 0, :]  # CLS token
            # L2-normalize
            embs = torch.nn.functional.normalize(embs, p=2, dim=1)
            all_embs.append(embs.cpu().numpy())
            if (i + batch_size) % 100 == 0:
                print(f"  Encoded {min(i + batch_size, n)}/{n}...")
        embeddings = np.vstack(all_embs).astype(np.float32)
    except ImportError:
        print("  ⚠️ SPECTER2 requires 'transformers' and 'torch'. Falling back to MiniLM.")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts, show_progress_bar=True,
                                  batch_size=64, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)
else:
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,
    )
embeddings = np.array(embeddings, dtype=np.float32)
dim = embeddings.shape[1]

# ── Verify L2-normalization (critical for cosine similarity via IndexFlatIP) ──
norms = np.linalg.norm(embeddings, axis=1)
assert np.allclose(norms, 1.0, atol=1e-5), (
    f"Embeddings are NOT L2-normalized! "
    f"Norm range: [{norms.min():.6f}, {norms.max():.6f}]. "
    f"IndexFlatIP requires unit vectors for cosine similarity."
)
print(f"✅ All {n} embeddings L2-normalized (norm range: [{norms.min():.6f}, {norms.max():.6f}])")

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
