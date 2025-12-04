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
        # Cargamos índice FAISS
        self.index = faiss.read_index(index_path)

        # Cargamos los chunks (texto + metadata)
        self.chunks = []
        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                self.chunks.append(json.loads(line))

        print(f"[RAG] Cargados {len(self.chunks)} chunks de {chunks_path}")

        # Modelo de embeddings
        self.embed_model = SentenceTransformer(model_name)

    # ✅ Método original: top-k "a secas"
    def retrieve_context(self, query: str, k: int = 5):
        q_emb = self.embed_model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        distances, indices = self.index.search(q_emb, k)
        results = [self.chunks[i] for i in indices[0] if 0 <= i < len(self.chunks)]
        return results

    # ---------- helpers internos ----------

    def _search_candidates(self, query: str, k: int = 50):
        """
        Devuelve una lista de candidatos con su score:
        [ { "chunk": {...}, "dist": float }, ... ]
        """
        q_emb = self.embed_model.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        distances, indices = self.index.search(q_emb, k)

        cands = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            cands.append({
                "chunk": self.chunks[idx],
                "dist": float(dist),
                "idx": int(idx),
            })
        # cuanto menor dist, más similar → ordenamos por dist asc
        cands.sort(key=lambda x: x["dist"])
        return cands

    def _get_chunk_id(self, chunk_obj, fallback_idx):
        """
        Devuelve un id estable para usar en used_ids.
        Si el chunk tiene campo 'id', se usa ese; si no, se usa el índice numérico.
        """
        cid = chunk_obj.get("id")
        if cid is None:
            # usamos un id sintético basado en el índice
            cid = f"idx_{fallback_idx}"
        return cid

    def _scope_ok(self, meta_scope, requested_scope):
        """
        Regla de scope:
        - Si requested_scope es None o 'any' → siempre OK.
        - Si meta_scope es None → lo aceptamos (chunks sin scope sirven para todos).
        - Si meta_scope == requested_scope → OK.
        """
        if not requested_scope or requested_scope == "any":
            return True
        if meta_scope is None:
            return True
        return meta_scope == requested_scope

    def _pick_by_type(self, candidates, used_ids, chunk_type, n_desired,
                      scope=None, domain_hint=None):
        """
        Selecciona hasta n_desired candidatos de un determinado chunk_type,
        respetando scope y domain_hint cuando se pueda.
        """
        selected = []

        # Primero intentamos con dominio que haga match (si se indica)
        for c in candidates:
            ch = c["chunk"]
            meta = ch.get("metadata", {})
            cid = self._get_chunk_id(ch, c["idx"])

            if cid in used_ids:
                continue

            if not self._scope_ok(meta.get("scope"), scope):
                continue

            if meta.get("chunk_type") != chunk_type:
                continue

            domains = meta.get("domains") or []
            if domain_hint and domains:
                # solo dejamos pasar los que contengan el dominio
                if domain_hint not in domains:
                    continue

            selected.append(ch)
            used_ids.add(cid)
            if len(selected) >= n_desired:
                return selected

        # Si faltan, completamos sin filtrar por dominio
        if len(selected) < n_desired:
            for c in candidates:
                ch = c["chunk"]
                meta = ch.get("metadata", {})
                cid = self._get_chunk_id(ch, c["idx"])

                if cid in used_ids:
                    continue

                if not self._scope_ok(meta.get("scope"), scope):
                    continue

                if meta.get("chunk_type") != chunk_type:
                    continue

                selected.append(ch)
                used_ids.add(cid)
                if len(selected) >= n_desired:
                    break

        return selected

    # ---------- retrieve_mixed_context ----------

    def retrieve_mixed_context(
        self,
        query: str,
        scope: str = "core",
        domain_hint: str | None = None,
        n_defs: int = 1,
        n_ejemplos: int = 3,
        n_casos_borde: int = 1,
        n_dominios: int = 1,
        n_max_total: int = 8,
    ):
        """
        Recupera un contexto mezclado con una proporción aproximada de tipos:
        - definiciones
        - ejemplos
        - casos_borde
        - dominio (si hay domain_hint)
        Usa scope sólo como filtro suave; los chunks sin scope también son válidos.
        """

        if not self.chunks:
            return []

        # Pedimos bastantes candidatos al índice para poder filtrar.
        k_search = min(80, len(self.chunks))
        candidates = self._search_candidates(query, k=k_search)

        used_ids = set()
        final_chunks = []

        # 1) Definiciones
        if n_defs > 0:
            final_chunks += self._pick_by_type(
                candidates, used_ids,
                chunk_type="definicion",
                n_desired=n_defs,
                scope=scope,
                domain_hint=domain_hint,
            )

        # 2) Ejemplos
        if n_ejemplos > 0:
            final_chunks += self._pick_by_type(
                candidates, used_ids,
                chunk_type="ejemplos",
                n_desired=n_ejemplos,
                scope=scope,
                domain_hint=domain_hint,
            )

        # 3) Casos borde
        if n_casos_borde > 0:
            final_chunks += self._pick_by_type(
                candidates, used_ids,
                chunk_type="caso_borde",
                n_desired=n_casos_borde,
                scope=scope,
                domain_hint=domain_hint,
            )

        # 4) Dominio (si procede)
        if domain_hint and n_dominios > 0:
            final_chunks += self._pick_by_type(
                candidates, used_ids,
                chunk_type="dominio",
                n_desired=n_dominios,
                scope=scope,
                domain_hint=domain_hint,
            )

        # 5) Si aún faltan hasta n_max_total, rellenamos con lo mejor que quede (sin mirar chunk_type)
        if len(final_chunks) < n_max_total:
            for c in candidates:
                ch = c["chunk"]
                meta = ch.get("metadata", {})
                cid = self._get_chunk_id(ch, c["idx"])

                if cid in used_ids:
                    continue

                if not self._scope_ok(meta.get("scope"), scope):
                    continue

                final_chunks.append(ch)
                used_ids.add(cid)
                if len(final_chunks) >= n_max_total:
                    break

        return final_chunks
