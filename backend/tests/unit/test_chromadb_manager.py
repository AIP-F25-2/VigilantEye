from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pytest

from src.utils.chromadb_manager import ChromaDBManager


class FakeCollection:
    def __init__(self) -> None:
        self.items: Dict[str, Dict[str, object]] = {}

    def add(self, ids, embeddings, metadatas):
        for idx, embedding, metadata in zip(ids, embeddings, metadatas):
            self.items[idx] = {
                "embedding": np.array(embedding),
                "metadata": dict(metadata),
            }

    def delete(self, ids: List[str]):
        for idx in ids:
            self.items.pop(idx, None)

    def query(self, query_embeddings, n_results, where=None, include=None):
        query = np.array(query_embeddings[0])
        query_norm = query / (np.linalg.norm(query) or 1)
        results = []
        for idx, payload in self.items.items():
            metadata = payload["metadata"]
            if where and "first_seen" in where:
                cutoff = where["first_seen"]["$gte"]
                if metadata.get("first_seen", 0) < cutoff:
                    continue
            item = payload["embedding"]
            item_norm = item / (np.linalg.norm(item) or 1)
            similarity = float(np.dot(query_norm, item_norm))
            distance = 1 - similarity
            results.append((idx, metadata, distance))

        results.sort(key=lambda item: item[2])
        selected = results[:n_results]
        ids = [item[0] for item in selected]
        metadatas = [item[1] for item in selected]
        distances = [item[2] for item in selected]
        return {"ids": [ids], "metadatas": [metadatas], "distances": [distances]}

    def get(self, ids=None, where=None, include=None):
        if ids is not None:
            existing = [idx for idx in ids if idx in self.items]
            return {
                "ids": existing,
                "embeddings": [[self.items[idx]["embedding"].tolist()] for idx in existing] if include and "embeddings" in include else [],
                "metadatas": [[self.items[idx]["metadata"]] for idx in existing] if include and "metadatas" in include else [],
            }

        result_ids = []
        if where and "expires_at" in where:
            threshold = where["expires_at"]["$lte"]
            for idx, payload in self.items.items():
                if payload["metadata"].get("expires_at") is not None and payload["metadata"]["expires_at"] <= threshold:
                    result_ids.append(idx)
        return {"ids": result_ids}

    def count(self):
        return len(self.items)


@dataclass
class DummyConfig:
    PERSON_VECTOR_TTL_HOURS: int = 2
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch) -> ChromaDBManager:
    instance = ChromaDBManager(config=DummyConfig())
    instance.face_collection = FakeCollection()
    instance.body_collection = FakeCollection()
    instance.ttl_seconds = 3600
    return instance


def _sample_embedding(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vec = rng.random(512)
    return vec / np.linalg.norm(vec)


def test_add_face_embedding_success(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    current_time = 1_700_000_000
    monkeypatch.setattr(time, "time", lambda: current_time)

    embedding = _sample_embedding(1)
    metadata = {"video_id": "video-123", "first_seen": current_time}
    success, error = manager.add_face_embedding("person-1", embedding, metadata)

    assert success is True
    assert error is None
    stored = manager.face_collection.items["person-1"]
    assert stored["metadata"]["expires_at"] == current_time + manager.ttl_seconds


def test_add_body_embedding_success(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    current_time = 1_700_000_100
    monkeypatch.setattr(time, "time", lambda: current_time)

    embedding = _sample_embedding(2)
    metadata = {"video_id": "video-123", "first_seen": current_time}
    success, error = manager.add_body_embedding("person-2", embedding, metadata)

    assert success is True
    assert error is None
    stored = manager.body_collection.items["person-2"]
    assert stored["metadata"]["expires_at"] == current_time + manager.ttl_seconds


def test_search_similar_faces_success(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    base_time = 1_700_000_000
    monkeypatch.setattr(time, "time", lambda: base_time)

    for idx in range(3):
        manager.add_face_embedding(
            f"person-{idx}",
            _sample_embedding(idx),
            {"video_id": "vid", "first_seen": base_time},
        )

    results, error = manager.search_similar_faces(_sample_embedding(0), n_results=2)
    assert error is None
    assert len(results) == 2
    assert results[0]["person_id"] == "person-0"


def test_search_similar_faces_with_time_window(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1_700_000_000
    monkeypatch.setattr(time, "time", lambda: now)

    manager.add_face_embedding(
        "recent-person",
        _sample_embedding(10),
        {"video_id": "vid", "first_seen": now - 100},
    )
    manager.add_face_embedding(
        "old-person",
        _sample_embedding(11),
        {"video_id": "vid", "first_seen": now - 10_000},
    )

    results, _ = manager.search_similar_faces(_sample_embedding(10), time_window_hours=1)
    assert all(match["person_id"] != "old-person" for match in results)


def test_search_similar_bodies_success(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    base_time = 1_700_010_000
    monkeypatch.setattr(time, "time", lambda: base_time)

    for idx in range(3):
        manager.add_body_embedding(
            f"body-{idx}",
            _sample_embedding(idx + 20),
            {"video_id": "vid", "first_seen": base_time},
        )

    results, error = manager.search_similar_bodies(_sample_embedding(20), n_results=2)
    assert error is None
    assert len(results) == 2


def test_delete_person_embeddings_success(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    current_time = 1_700_020_000
    monkeypatch.setattr(time, "time", lambda: current_time)

    manager.add_face_embedding("person-x", _sample_embedding(30), {"video_id": "vid", "first_seen": current_time})
    manager.add_body_embedding("person-x", _sample_embedding(30), {"video_id": "vid", "first_seen": current_time})

    success, error = manager.delete_person_embeddings("person-x")
    assert error is None
    assert success is True
    assert "person-x" not in manager.face_collection.items
    assert "person-x" not in manager.body_collection.items


def test_cleanup_expired_embeddings(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1_700_030_000
    monkeypatch.setattr(time, "time", lambda: now)

    manager.face_collection.items = {
        "expired-face": {"embedding": _sample_embedding(1), "metadata": {"expires_at": now - 10}},
        "active-face": {"embedding": _sample_embedding(2), "metadata": {"expires_at": now + 1000}},
    }
    manager.body_collection.items = {
        "expired-body": {"embedding": _sample_embedding(3), "metadata": {"expires_at": now - 10}},
        "active-body": {"embedding": _sample_embedding(4), "metadata": {"expires_at": now + 1000}},
    }

    metrics, error = manager.cleanup_expired_embeddings()
    assert error is None
    assert metrics["deleted_faces"] == 1
    assert metrics["deleted_bodies"] == 1
    assert "expired-face" not in manager.face_collection.items
    assert "expired-body" not in manager.body_collection.items


def test_clear_person_ttl_success(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1_700_040_000
    monkeypatch.setattr(time, "time", lambda: now)

    manager.add_face_embedding("person-ttl", _sample_embedding(5), {"video_id": "vid", "first_seen": now})
    manager.add_body_embedding("person-ttl", _sample_embedding(5), {"video_id": "vid", "first_seen": now})

    success, error = manager.clear_person_ttl("person-ttl")
    assert error is None
    assert success is True
    assert manager.face_collection.items["person-ttl"]["metadata"]["expires_at"] is None
    assert manager.body_collection.items["person-ttl"]["metadata"]["expires_at"] is None


def test_get_collection_stats(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1_700_050_000
    monkeypatch.setattr(time, "time", lambda: now)

    manager.face_collection.items = {
        "face-1": {"embedding": _sample_embedding(1), "metadata": {"expires_at": now - 10}},
        "face-2": {"embedding": _sample_embedding(2), "metadata": {"expires_at": now + 1000}},
    }
    manager.body_collection.items = {
        "body-1": {"embedding": _sample_embedding(3), "metadata": {"expires_at": now - 10}},
        "body-2": {"embedding": _sample_embedding(4), "metadata": {"expires_at": now + 1000}},
    }

    stats = manager.get_collection_stats()
    assert stats["total_faces"] == 2
    assert stats["total_bodies"] == 2
    assert stats["expired_faces"] == 1
    assert stats["expired_bodies"] == 1


def test_chromadb_connection_error(manager: ChromaDBManager, monkeypatch: pytest.MonkeyPatch) -> None:
    def raising_add(*_args, **_kwargs):
        raise RuntimeError("connection failed")

    manager.face_collection.add = raising_add  # type: ignore[assignment]
    success, error = manager.add_face_embedding("person-err", _sample_embedding(6), {})
    assert success is False
    assert isinstance(error, Exception)


def test_invalid_embedding_dimension(manager: ChromaDBManager) -> None:
    embedding = np.random.random(256)
    success, error = manager.add_face_embedding("person-dim", embedding, {})
    assert success is False
    assert isinstance(error, Exception)

