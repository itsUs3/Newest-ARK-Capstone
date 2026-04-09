from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

try:
    import faiss
except Exception as exc:
    faiss = None
    FAISS_IMPORT_ERROR = exc
else:
    FAISS_IMPORT_ERROR = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


logger = logging.getLogger(__name__)


class SocialVectorStore:
    def __init__(self, persist_dir: Path, embedding_model_name: str, local_model_path: Optional[Path] = None, embedder=None):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.persist_dir / "social.faiss"
        self.metadata_path = self.persist_dir / "social_metadata.json"
        self.embedding_model_name = embedding_model_name
        self.local_model_path = local_model_path
        self.embedder = embedder or self._load_embedder()
        self.index = None
        self.metadata: List[Dict] = []
        self.dimension = 384
        self._load_persisted_index()

    def _load_embedder(self):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is required for social vector search.")

        candidate_paths = [
            self.local_model_path,
            Path("backend/models/real_estate_embeddings"),
            Path("models/real_estate_embeddings"),
        ]
        for candidate in candidate_paths:
            if candidate and Path(candidate).exists():
                logger.info(f"Loading social embeddings from local path: {candidate}")
                return SentenceTransformer(str(candidate))

        logger.info(f"Loading social embeddings model: {self.embedding_model_name}")
        return SentenceTransformer(self.embedding_model_name)

    def _load_persisted_index(self) -> None:
        if faiss is None:
            raise RuntimeError(f"faiss-cpu is required for social vector search: {FAISS_IMPORT_ERROR}")

        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                self.dimension = self.index.d
                return
            except Exception as exc:
                logger.warning(f"Failed to load persisted social FAISS index, rebuilding: {exc}")

        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        embeddings = self.embedder.encode(texts, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        return embeddings

    def rebuild(self, docs: List[Dict]) -> None:
        self.metadata = [dict(doc) for doc in docs]
        if not docs:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.save()
            return

        texts = [doc.get("text", "") for doc in docs]
        embeddings = self._embed_texts(texts)
        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.save()

    def add_documents(self, docs: List[Dict]) -> None:
        if not docs:
            return

        if self.index is None:
            self.rebuild(docs)
            return

        embeddings = self._embed_texts([doc.get("text", "") for doc in docs])
        self.index.add(embeddings)
        self.metadata.extend(dict(doc) for doc in docs)
        self.save()

    def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        if not query or self.index is None or not self.metadata:
            return []

        query_embedding = self._embed_texts([query])
        top_k = min(max(top_k, 1), len(self.metadata))
        scores, indices = self.index.search(query_embedding, top_k * 4)
        results: List[Dict] = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = dict(self.metadata[idx])
            item["vector_score"] = float(score)
            if filters and not self._passes_filters(item, filters):
                continue
            results.append(item)
            if len(results) >= top_k:
                break

        return results

    def _passes_filters(self, item: Dict, filters: Dict) -> bool:
        location_tags = {tag.lower() for tag in item.get("location_tags", [])}
        normalized_locations = {tag.lower() for tag in filters.get("location_tags", [])}
        if normalized_locations and location_tags:
            if not location_tags.intersection(normalized_locations):
                return False

        after_timestamp = filters.get("after_timestamp")
        if after_timestamp and item.get("timestamp"):
            if str(item["timestamp"]) < str(after_timestamp):
                return False

        return True

    def save(self) -> None:
        if self.index is None or faiss is None:
            return

        faiss.write_index(self.index, str(self.index_path))
        self.metadata_path.write_text(
            json.dumps(self.metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
