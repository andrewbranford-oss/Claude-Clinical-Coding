"""
RAG knowledge base for the NHS Clinical Coding Agent.

Indexes clinical coding guidance markdown documents into Pinecone using local
sentence-transformers embeddings (all-MiniLM-L6-v2, 384-dim, cosine).
Retrieval uses cross-encoder re-ranking: fetch RERANK_POOL candidates
from Pinecone then re-score with a cross-encoder before returning top-k.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import CrossEncoder, SentenceTransformer

load_dotenv(override=True)

DOCS_DIR = Path(__file__).resolve().parent
INDEX_NAME = "coding-guidance"
DIMENSION = 384
RERANK_POOL = 20  # candidates fetched from Pinecone before re-ranking
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CHUNK_WORDS = 150   # tuned for short rule-based guidance docs (~4k words total)
OVERLAP_WORDS = 25  # overlap preserves context at chunk boundaries

GUIDANCE_DOCS = [
    "Endoscopy_Automation_Guidance.md",
    "Endoscopy_Report_breakdown.md",
    "nhs_classifications_browser_user_guide.md",
    "PRD_NHS_Clinical_Coding_Agent.md",
    "nhs_clinical_coder_context.md",
    "nhs_clinical_coder_skills.md",
    "nhs_clinical_coder_agent.md",
]

_index = None
_model = None
_cross_encoder = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    return _cross_encoder


def _get_index():
    global _index
    if _index is not None:
        return _index

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for the index to be ready
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(1)

    _index = pc.Index(INDEX_NAME)
    return _index


def _chunk_markdown(text: str, source: str) -> list[dict]:
    """Sliding word-window chunks with heading context prepended to each window."""
    heading_re = re.compile(r'^#{1,4}\s')
    current_heading = ""
    all_words: list[str] = []
    word_headings: list[str] = []  # nearest heading for each word position

    for line in text.splitlines():
        if heading_re.match(line):
            current_heading = line.strip()
        words = line.split()
        all_words.extend(words)
        word_headings.extend([current_heading] * len(words))

    chunks = []
    start = 0
    idx = 0

    while start < len(all_words):
        end = min(start + CHUNK_WORDS, len(all_words))
        heading = word_headings[start]
        body = " ".join(all_words[start:end])
        chunk_text = f"{heading}\n{body}" if heading and not body.startswith("#") else body

        if len(chunk_text.strip()) >= 80:
            chunks.append({"id": f"{source}::{idx}", "text": chunk_text, "source": source})

        if end >= len(all_words):
            break

        start += CHUNK_WORDS - OVERLAP_WORDS
        idx += 1

    return chunks


def build_index(force: bool = False) -> int:
    """Index all guidance documents. Skips if already indexed unless force=True."""
    index = _get_index()

    all_chunks: list[dict] = []
    for doc_name in GUIDANCE_DOCS:
        doc_path = DOCS_DIR / doc_name
        if doc_path.exists():
            text = doc_path.read_text(encoding="utf-8")
            all_chunks.extend(_chunk_markdown(text, doc_name))
        else:
            print(f"Warning: {doc_name} not found, skipping")

    if not all_chunks:
        raise RuntimeError("No guidance documents found to index")

    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)

    if total_vectors >= len(all_chunks) and not force:
        return total_vectors

    model = _get_model()
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    vectors = [
        (c["id"], emb.tolist(), {"source": c["source"], "text": c["text"]})
        for c, emb in zip(all_chunks, embeddings)
    ]

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i + batch_size])

    return len(all_chunks)


def retrieve(query: str, n_results: int = 6) -> list[str]:
    """Retrieve top-n guidance chunks using Pinecone + cross-encoder re-ranking."""
    index = _get_index()
    build_index()

    model = _get_model()
    query_vector = model.encode([query])[0].tolist()

    # Fetch a larger candidate pool from Pinecone
    pool_size = max(RERANK_POOL, n_results)
    results = index.query(
        vector=query_vector,
        top_k=pool_size,
        include_metadata=True,
    )
    candidates = [match["metadata"]["text"] for match in results["matches"]]

    if len(candidates) <= n_results:
        return candidates

    # Re-rank with cross-encoder and return top n_results
    cross_encoder = _get_cross_encoder()
    pairs = [[query, chunk] for chunk in candidates]
    scores = cross_encoder.predict(pairs)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked[:n_results]]


if __name__ == "__main__":
    print("Building knowledge base index (downloading model on first run)...")
    n = build_index(force=True)
    print(f"Indexed {n} chunks from {len(GUIDANCE_DOCS)} documents.")

    test_query = "colonoscopy with snare resection and biopsy of sigmoid colon"
    print(f"\nTest retrieval: '{test_query}'")
    chunks = retrieve(test_query, n_results=3)
    for i, chunk in enumerate(chunks, 1):
        preview = chunk[:200].replace("\n", " ")
        print(f"\n[{i}] {preview}...")
