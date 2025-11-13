from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.config.settings import get_config
from src.utils.faiss_manager import FaissIndexManager

try:
    import chromadb  # type: ignore
    from chromadb.errors import ChromaError  # type: ignore
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore
    ChromaError = Exception  # type: ignore

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Wrapper around ChromaDB client providing TTL and convenience helpers."""

    def __init__(self, config=None) -> None:
        self.config = config or get_config()
        self.ttl_seconds = int(self.config.PERSON_VECTOR_TTL_HOURS) * 3600
        self.faiss_manager = FaissIndexManager()

        if chromadb is None:
            logger.warning("ChromaDB library not available")
            self.client = None
            self.face_collection = None
            self.body_collection = None
            return

        try:
            self.client = chromadb.HttpClient(  # type: ignore[attr-defined]
                host=self.config.CHROMADB_HOST,
                port=self.config.CHROMADB_PORT,
            )
            self.face_collection = self.client.get_or_create_collection(
                name="face_embeddings",
                metadata={"hnsw:space": "cosine"},
            )
            self.body_collection = self.client.get_or_create_collection(
                name="body_embeddings",
                metadata={"hnsw:space": "cosine"},
            )
            self._warm_faiss_indices()
            logger.debug("ChromaDB collections ready")
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to initialize ChromaDB client", extra={"context": {"error": str(exc)}})
            self.client = None
            self.face_collection = None
            self.body_collection = None

    def add_face_embedding(
        self, person_id: str, embedding: np.ndarray, metadata: Dict
    ) -> Tuple[bool, Optional[Exception]]:
        if self.face_collection is None:
            logger.warning("Face collection unavailable; skipping face embedding storage")
            return False, None

        try:
            if embedding.ndim != 1 or embedding.shape[0] != 512:
                raise ValueError("Face embedding must be a 512-dimensional vector")

            expires_at = int(time.time()) + self.ttl_seconds
            metadata = {**metadata, "expires_at": expires_at, "person_id": person_id}
            embedding_list = embedding.tolist()
            self.face_collection.add(
                ids=[person_id],
                embeddings=[embedding_list],
                metadatas=[metadata],
            )
            try:
                self.faiss_manager.add_face_embedding(person_id, embedding)
            except ValueError as exc:
                logger.warning(
                    "Failed to index face embedding in FAISS",
                    extra={"context": {"person_id": person_id, "error": str(exc)}},
                )
            return True, None
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to add face embedding",
                extra={"context": {"person_id": person_id, "error": str(exc)}},
            )
            return False, exc

    def add_body_embedding(
        self, person_id: str, embedding: np.ndarray, metadata: Dict
    ) -> Tuple[bool, Optional[Exception]]:
        if self.body_collection is None:
            logger.warning("Body collection unavailable; skipping body embedding storage")
            return False, None

        try:
            if embedding.ndim != 1 or embedding.shape[0] != 512:
                raise ValueError("Body embedding must be a 512-dimensional vector")

            expires_at = int(time.time()) + self.ttl_seconds
            metadata = {**metadata, "expires_at": expires_at, "person_id": person_id}
            embedding_list = embedding.tolist()
            self.body_collection.add(
                ids=[person_id],
                embeddings=[embedding_list],
                metadatas=[metadata],
            )
            try:
                self.faiss_manager.add_body_embedding(person_id, embedding)
            except ValueError as exc:
                logger.warning(
                    "Failed to index body embedding in FAISS",
                    extra={"context": {"person_id": person_id, "error": str(exc)}},
                )
            return True, None
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to add body embedding",
                extra={"context": {"person_id": person_id, "error": str(exc)}},
            )
            return False, exc

    def search_similar_faces(
        self,
        embedding: np.ndarray,
        n_results: int = 10,
        time_window_hours: Optional[int] = None,
    ) -> Tuple[List[Dict], Optional[Exception]]:
        if self.face_collection is None:
            logger.warning("Face collection unavailable; cannot search")
            return [], None

        try:
            where = None
            if time_window_hours is not None:
                cutoff = int(time.time()) - (time_window_hours * 3600)
                where = {"first_seen": {"$gte": cutoff}}

            faiss_matches = self.faiss_manager.search_faces(embedding, top_k=n_results)
            matches: List[Dict] = []

            if faiss_matches:
                match_ids = [person_id for person_id, _ in faiss_matches]
                records = self.face_collection.get(
                    ids=match_ids,
                    include=["metadatas"],
                )
                metadatas = records.get("metadatas", [{}] * len(match_ids))
                ids = records.get("ids", match_ids)
                metadata_map = {pid: meta for pid, meta in zip(ids, metadatas)}

                cutoff = None
                if time_window_hours is not None:
                    cutoff = int(time.time()) - (time_window_hours * 3600)

                for person_id, similarity in faiss_matches:
                    metadata = metadata_map.get(person_id, {})
                    if cutoff is not None:
                        first_seen = metadata.get("first_seen")
                        if first_seen is None or first_seen < cutoff:
                            continue
                    matches.append(
                        {
                            "person_id": person_id,
                            "similarity": float(similarity),
                            "metadata": metadata,
                        }
                    )

            if not matches:
                query_embedding = embedding.tolist()
                results = self.face_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where,
                    include=["metadatas", "distances"],
                )

                ids = results.get("ids", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for idx, person_id in enumerate(ids):
                    distance = distances[idx] if idx < len(distances) else 0.0
                    metadata = metadatas[idx] if idx < len(metadatas) else {}
                    similarity = 1 - distance
                    matches.append(
                        {"person_id": person_id, "similarity": similarity, "metadata": metadata},
                    )

            matches.sort(key=lambda item: item["similarity"], reverse=True)
            return matches, None
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception("Face similarity search failed", extra={"context": {"error": str(exc)}})
            return [], exc

    def search_similar_bodies(
        self,
        embedding: np.ndarray,
        n_results: int = 10,
        time_window_hours: Optional[int] = None,
    ) -> Tuple[List[Dict], Optional[Exception]]:
        if self.body_collection is None:
            logger.warning("Body collection unavailable; cannot search")
            return [], None

        try:
            where = None
            if time_window_hours is not None:
                cutoff = int(time.time()) - (time_window_hours * 3600)
                where = {"first_seen": {"$gte": cutoff}}

            faiss_matches = self.faiss_manager.search_bodies(embedding, top_k=n_results)
            matches: List[Dict] = []

            if faiss_matches:
                match_ids = [person_id for person_id, _ in faiss_matches]
                records = self.body_collection.get(
                    ids=match_ids,
                    include=["metadatas"],
                )
                metadatas = records.get("metadatas", [{}] * len(match_ids))
                ids = records.get("ids", match_ids)
                metadata_map = {pid: meta for pid, meta in zip(ids, metadatas)}

                cutoff = None
                if time_window_hours is not None:
                    cutoff = int(time.time()) - (time_window_hours * 3600)

                for person_id, similarity in faiss_matches:
                    metadata = metadata_map.get(person_id, {})
                    if cutoff is not None:
                        first_seen = metadata.get("first_seen")
                        if first_seen is None or first_seen < cutoff:
                            continue
                    matches.append(
                        {
                            "person_id": person_id,
                            "similarity": float(similarity),
                            "metadata": metadata,
                        }
                    )

            if not matches:
                query_embedding = embedding.tolist()
                results = self.body_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where,
                    include=["metadatas", "distances"],
                )

                ids = results.get("ids", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for idx, person_id in enumerate(ids):
                    distance = distances[idx] if idx < len(distances) else 0.0
                    metadata = metadatas[idx] if idx < len(metadatas) else {}
                    similarity = 1 - distance
                    matches.append(
                        {"person_id": person_id, "similarity": similarity, "metadata": metadata},
                    )

            matches.sort(key=lambda item: item["similarity"], reverse=True)
            return matches, None
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception("Body similarity search failed", extra={"context": {"error": str(exc)}})
            return [], exc

    def delete_person_embeddings(self, person_id: str) -> Tuple[bool, Optional[Exception]]:
        success = True
        error: Optional[Exception] = None

        for collection in (self.face_collection, self.body_collection):
            if collection is None:
                continue
            try:
                collection.delete(ids=[person_id])
            except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
                logger.exception(
                    "Failed to delete embeddings",
                    extra={"context": {"person_id": person_id, "error": str(exc)}},
                )
                success = False
                error = exc

        try:
            self.faiss_manager.delete_embeddings(person_id)
        except ValueError as exc:
            logger.warning(
                "Failed to remove embeddings from FAISS",
                extra={"context": {"person_id": person_id, "error": str(exc)}},
            )

        return success, error

    def cleanup_expired_embeddings(self) -> Tuple[Dict[str, int], Optional[Exception]]:
        metrics = {"deleted_faces": 0, "deleted_bodies": 0}

        try:
            current_time = int(time.time())

            if self.face_collection is not None:
                expired_faces = self.face_collection.get(
                    where={"expires_at": {"$lte": current_time}},
                    include=[],
                )
                face_ids = expired_faces.get("ids", [])
                if face_ids:
                    self.face_collection.delete(ids=face_ids)
                    metrics["deleted_faces"] = len(face_ids)
                    for face_id in face_ids:
                        self.faiss_manager.delete_embeddings(face_id)

            if self.body_collection is not None:
                expired_bodies = self.body_collection.get(
                    where={"expires_at": {"$lte": current_time}},
                    include=[],
                )
                body_ids = expired_bodies.get("ids", [])
                if body_ids:
                    self.body_collection.delete(ids=body_ids)
                    metrics["deleted_bodies"] = len(body_ids)
                    for body_id in body_ids:
                        self.faiss_manager.delete_embeddings(body_id)

            return metrics, None
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception("Failed to cleanup expired embeddings", extra={"context": {"error": str(exc)}})
            return metrics, exc

    def clear_person_ttl(self, person_id: str) -> Tuple[bool, Optional[Exception]]:
        try:
            for collection in (self.face_collection, self.body_collection):
                if collection is None:
                    continue

                records = collection.get(
                    ids=[person_id],
                    include=["embeddings", "metadatas"],
                )
                if not records.get("ids"):
                    continue

                embeddings = records.get("embeddings", [[]])[0]
                metadata = records.get("metadatas", [{}])[0]
                metadata["expires_at"] = None

                collection.delete(ids=[person_id])
                collection.add(
                    ids=[person_id],
                    embeddings=[embeddings],
                    metadatas=[metadata],
                )
            return True, None
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to clear person TTL",
                extra={"context": {"person_id": person_id, "error": str(exc)}},
            )
            return False, exc

    def get_collection_stats(self) -> Dict[str, int]:
        stats = {"total_faces": 0, "total_bodies": 0, "expired_faces": 0, "expired_bodies": 0}
        current_time = int(time.time())

        try:
            if self.face_collection is not None:
                faces = self.face_collection.count()
                stats["total_faces"] = faces
                expired = self.face_collection.get(
                    where={"expires_at": {"$lte": current_time}},
                    include=[],
                )
                stats["expired_faces"] = len(expired.get("ids", []))

            if self.body_collection is not None:
                bodies = self.body_collection.count()
                stats["total_bodies"] = bodies
                expired = self.body_collection.get(
                    where={"expires_at": {"$lte": current_time}},
                    include=[],
                )
                stats["expired_bodies"] = len(expired.get("ids", []))
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception("Failed to gather ChromaDB stats", extra={"context": {"error": str(exc)}})

        return stats

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _warm_faiss_indices(self) -> None:
        if not self.faiss_manager.is_available():
            return

        try:
            if self.face_collection is not None:
                records = self.face_collection.get(include=["ids", "embeddings"])
                ids = records.get("ids", [])
                embeddings = records.get("embeddings", [])
                face_vectors: Dict[str, np.ndarray] = {}
                for idx, person_id in enumerate(ids):
                    vector = embeddings[idx] if idx < len(embeddings) else None
                    if not vector:
                        continue
                    if isinstance(vector, list) and vector and isinstance(vector[0], list):
                        vector = vector[0]
                    array = np.asarray(vector, dtype=np.float32)
                    if array.size != self.faiss_manager.embedding_dim:
                        continue
                    face_vectors[person_id] = array
                if face_vectors:
                    self.faiss_manager.bulk_load_faces(face_vectors)

            if self.body_collection is not None:
                records = self.body_collection.get(include=["ids", "embeddings"])
                ids = records.get("ids", [])
                embeddings = records.get("embeddings", [])
                body_vectors: Dict[str, np.ndarray] = {}
                for idx, person_id in enumerate(ids):
                    vector = embeddings[idx] if idx < len(embeddings) else None
                    if not vector:
                        continue
                    if isinstance(vector, list) and vector and isinstance(vector[0], list):
                        vector = vector[0]
                    array = np.asarray(vector, dtype=np.float32)
                    if array.size != self.faiss_manager.embedding_dim:
                        continue
                    body_vectors[person_id] = array
                if body_vectors:
                    self.faiss_manager.bulk_load_bodies(body_vectors)
        except (ChromaError, Exception) as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to warm FAISS indices",
                extra={"context": {"error": str(exc)}},
            )

