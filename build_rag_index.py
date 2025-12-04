#!/usr/bin/env python3
import os, json, glob, re
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

RAW_DIR = "rag_corpus/raw"
OUT_INDEX = "rag_corpus/index.faiss"
OUT_CHUNKS = "rag_corpus/chunks.jsonl"

CHUNK_SIZE = 400   # palabras aprox
CHUNK_OVERLAP = 50 # solape entre chunks

def split_into_paragraphs(text: str):
    paras = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paras if p.strip()]

def split_into_sentences(paragraph: str):
    parts = re.split(r'(?<=[.!?])\s+', paragraph)
    return [s.strip() for s in parts if s.strip()]

def chunk_text(text: str, size_words: int = CHUNK_SIZE, overlap_words: int = CHUNK_OVERLAP):
    paragraphs = split_into_paragraphs(text)
    chunks = []
    current_words = []

    def flush_chunk():
        nonlocal current_words
        if not current_words:
            return
        chunk_text = " ".join(current_words).strip()
        if chunk_text:
            chunks.append(chunk_text)
        current_words = []

    for para in paragraphs:
        sentences = split_into_sentences(para)
        for sent in sentences:
            sent_words = sent.split()
            if len(sent_words) >= size_words:
                flush_chunk()
                chunks.append(" ".join(sent_words))
                continue

            if len(current_words) + len(sent_words) > size_words:
                flush_chunk()
                if overlap_words > 0 and chunks:
                    prev_words = chunks[-1].split()
                    overlap = prev_words[-overlap_words:]
                    current_words = overlap + sent_words
                else:
                    current_words = sent_words
            else:
                current_words.extend(sent_words)

    flush_chunk()
    return chunks

def read_documents():
    docs = []
    for path in glob.glob(os.path.join(RAW_DIR, "*")):
        if not path.lower().endswith((".md", ".txt")):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        docs.append({
            "source": os.path.basename(path),
            "text": text
        })
    return docs

def main():
    docs = read_documents()
    all_chunks = []
    for doc in docs:
        chunks = chunk_text(doc["text"])
        for ch in chunks:
            all_chunks.append({
                "text": ch,
                "metadata": {
                    "source": doc["source"]
                }
            })

    print(f"Total chunks: {len(all_chunks)}")

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    texts = [c["text"] for c in all_chunks]
    embs = model.encode(texts, batch_size=32, show_progress_bar=True)
    embs = np.array(embs).astype("float32")

    dim = embs.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embs)

    os.makedirs(os.path.dirname(OUT_INDEX), exist_ok=True)
    faiss.write_index(index, OUT_INDEX)
    with open(OUT_CHUNKS, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print("Índice RAG construido y guardado en:")
    print(f"  {OUT_INDEX}")
    print(f"  {OUT_CHUNKS}")

if __name__ == "__main__":
    main()
