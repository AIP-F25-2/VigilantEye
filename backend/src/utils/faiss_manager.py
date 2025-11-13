from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class FaissIndexManager:
    """Lightweight wrapper that keeps FAISS indices in sync with stored embeddings."""

    def __init__(self, embedding_dim: int = 512) -> None:
        self.embedding_dim = embedding_dim
        self._faiss = self._load_faiss()
        self._face_index = None
        self._body_index = None
        self._face_ids: List[str] = []
        self._body_ids: List[str] = []
        self._face_vectors: Dict[str, np.ndarray] = {}
        self._body_vectors: Dict[str, np.ndarray] = {}

    @staticmethod
    def _load_faiss():
        try:
            import faiss  # type: ignore

            return faiss
        except ImportError:
            logger.warning("FAISS library not available; similarity acceleration disabled")
            return None

    def is_available(self) -> bool:
        return self._faiss is not None

    # ------------------------------------------------------------------ #
    # Bulk bootstrap
    # ------------------------------------------------------------------ #
    def bulk_load_faces(self, embeddings: Dict[str, np.ndarray]) -> None:
        if not self.is_available():
            return
        self._face_vectors = {pid: self._prepare_vector(vec) for pid, vec in embeddings.items()}
        self._rebuild_face_index()

    def bulk_load_bodies(self, embeddings: Dict[str, np.ndarray]) -> None:
        if not self.is_available():
            return
        self._body_vectors = {pid: self._prepare_vector(vec) for pid, vec in embeddings.items()}
        self._rebuild_body_index()

    # ------------------------------------------------------------------ #
    # Add / delete
    # ------------------------------------------------------------------ #
    def add_face_embedding(self, person_id: str, embedding: np.ndarray) -> None:
        if not self.is_available():
            return
        self._face_vectors[person_id] = self._prepare_vector(embedding)
        self._rebuild_face_index()

    def add_body_embedding(self, person_id: str, embedding: np.ndarray) -> None:
        if not self.is_available():
            return
        self._body_vectors[person_id] = self._prepare_vector(embedding)
        self._rebuild_body_index()

    def delete_embeddings(self, person_id: str) -> None:
        if not self.is_available():
            return

        removed = False
        if person_id in self._face_vectors:
            self._face_vectors.pop(person_id, None)
            removed = True

        if person_id in self._body_vectors:
            self._body_vectors.pop(person_id, None)
            removed = True

        if removed:
            self._rebuild_face_index()
            self._rebuild_body_index()

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search_faces(
        self,
        embedding: np.ndarray,
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        if not self.is_available() or not self._face_index or not self._face_ids:
            return []

        query = self._prepare_vector(embedding, normalize_only=True)
        scores, indices = self._face_index.search(query, min(top_k, len(self._face_ids)))
        return self._build_results(scores, indices, self._face_ids)

    def search_bodies(
        self,
        embedding: np.ndarray,
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        if not self.is_available() or not self._body_index or not self._body_ids:
            return []

        query = self._prepare_vector(embedding, normalize_only=True)
        scores, indices = self._body_index.search(query, min(top_k, len(self._body_ids)))
        return self._build_results(scores, indices, self._body_ids)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _prepare_vector(self, vector: np.ndarray, normalize_only: bool = False) -> np.ndarray:
        array = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if array.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding must be {self.embedding_dim}-dimensional, got {array.shape[1]}"
            )
        norms = np.linalg.norm(array, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normalized = array / norms
        if normalize_only:
            return normalized
        return normalized.squeeze(0)

    def _rebuild_face_index(self) -> None:
        if not self.is_available():
            return

        vectors = list(self._face_vectors.values())
        ids = list(self._face_vectors.keys())
        if not vectors:
            self._face_index = None
            self._face_ids = []
            return

        self._face_index = self._faiss.IndexFlatIP(self.embedding_dim)
        matrix = np.stack(vectors, axis=0)
        self._face_index.add(matrix)
        self._face_ids = ids

    def _rebuild_body_index(self) -> None:
        if not self.is_available():
            return

        vectors = list(self._body_vectors.values())
        ids = list(self._body_vectors.keys())
        if not vectors:
            self._body_index = None
            self._body_ids = []
            return

        self._body_index = self._faiss.IndexFlatIP(self.embedding_dim)
        matrix = np.stack(vectors, axis=0)
        self._body_index.add(matrix)
        self._body_ids = ids

    @staticmethod
    def _build_results(
        scores: np.ndarray,
        indices: np.ndarray,
        ids: List[str],
    ) -> List[Tuple[str, float]]:
        matches: List[Tuple[str, float]] = []
        if scores.size == 0 or indices.size == 0:
            return matches

        for score, index in zip(scores[0], indices[0]):
            if index < 0 or index >= len(ids):
                continue
            matches.append((ids[index], float(score)))
        return matches


