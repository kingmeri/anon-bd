# rag_client.py
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

INDEX_PATH = "rag_corpus/index.faiss"
CHUNKS_PATH = "rag_corpus/chunks.jsonl"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class RAGClient:
    def __init__(self,
                 index_path: str = INDEX_PATH,
                 chunks_path: str = CHUNKS_PATH,
                 model_name: str = MODEL_NAME):
        self.index = faiss.read_index(index_path)

        self.chunks = []
        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                self.chunks.append(json.loads(line))

        self.embed_model = SentenceTransformer(model_name)

    def retrieve_context(self, query: str, k: int = 5):
        q_emb = self.embed_model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        distances, indices = self.index.search(q_emb, k)
        results = [self.chunks[i] for i in indices[0]]
        return results
