"""Unit test specific fixtures for AI model mocking."""

import sys
import types
from collections import defaultdict
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import numpy as np
import pytest


class StubModelManager:
    """Stub model manager that doesn't download real models."""

    def __init__(self, *args, **kwargs):
        self.download_calls: Dict[str, int] = defaultdict(int)
        config = kwargs.get("config")
        if config:
            self.yolo_path = Path(config.MODELS_CACHE_PATH) / "yolov8" / "yolov8n.pt"
            self.yolo_path.parent.mkdir(parents=True, exist_ok=True)
            self.yolo_path.write_bytes(b"yolo")
        else:
            self.yolo_path = Path("/tmp/yolov8/yolov8n.pt")
            self.yolo_path.parent.mkdir(parents=True, exist_ok=True)
            self.yolo_path.write_bytes(b"yolo")

    def download_yolov8_model(self, *_args, **_kwargs):
        """Fake YOLOv8 download."""
        self.download_calls["yolov8"] += 1
        return str(self.yolo_path), None

    def download_mtcnn_weights(self):
        """Fake MTCNN download."""
        self.download_calls["mtcnn"] += 1
        return True, None

    def download_arcface_model(self):
        """Fake ArcFace download."""
        self.download_calls["arcface"] += 1
        return "arcface/model.pt", None

    def download_osnet_model(self, *_args, **_kwargs):
        """Fake OSNet download."""
        self.download_calls["osnet"] += 1
        return "osnet/osnet_x1_0.pth", None

    def download_mivolo_model(self):
        """Fake MiVOLO download."""
        self.download_calls["mivolo"] += 1
        return "mivolo/model.pth", None

    def download_blip2_model(self):
        """Fake BLIP-2 download."""
        self.download_calls["blip2"] += 1
        return "blip2/model", None

    def download_whisper_model(self):
        """Fake Whisper download."""
        self.download_calls["whisper"] += 1
        return "whisper/model", None

    def download_yamnet_model(self):
        """Fake YAMNet download."""
        self.download_calls["yamnet"] += 1
        return "yamnet/model", None


class StubChromaDBManager:
    """Stub ChromaDB manager with in-memory storage."""

    def __init__(self, *args, **kwargs):
        self.face_embeddings: Dict[str, np.ndarray] = {}
        self.body_embeddings: Dict[str, np.ndarray] = {}
        self.add_face_calls: List[Dict] = []
        self.add_body_calls: List[Dict] = []
        self.similar_face_results: List[Dict] = []
        self.similar_body_results: List[Dict] = []
        self.face_collection = types.SimpleNamespace(get=self._get_face)
        self.body_collection = types.SimpleNamespace(get=self._get_body)

    def add_face_embedding(self, person_id, embedding, metadata):
        """Add face embedding."""
        self.face_embeddings[person_id] = embedding
        self.add_face_calls.append({"id": person_id, "metadata": metadata})
        return True, None

    def add_body_embedding(self, person_id, embedding, metadata):
        """Add body embedding."""
        self.body_embeddings[person_id] = embedding
        self.add_body_calls.append({"id": person_id, "metadata": metadata})
        return True, None

    def search_similar_faces(self, *args, **kwargs):
        """Search similar faces."""
        return self.similar_face_results, None

    def search_similar_bodies(self, *args, **kwargs):
        """Search similar bodies."""
        return self.similar_body_results, None

    def cleanup_expired_embeddings(self, *args, **kwargs):
        """Cleanup expired embeddings."""
        return True, None

    def _get_face(self, ids=None, include=None, where=None):
        """Get face embeddings."""
        return self._build_get_response(self.face_embeddings, ids, include, where)

    def _get_body(self, ids=None, include=None, where=None):
        """Get body embeddings."""
        return self._build_get_response(self.body_embeddings, ids, include, where)

    @staticmethod
    def _build_get_response(store: Dict[str, np.ndarray], ids, include, where):
        """Build get response."""
        if ids is None:
            return {"ids": []}
        present = [idx for idx in ids if idx in store]
        embeddings = (
            [[store[idx].tolist()] for idx in present] if include and "embeddings" in include else []
        )
        metadatas = [[{}] for _ in present] if include and "metadatas" in include else []
        return {"ids": present, "embeddings": embeddings, "metadatas": metadatas}


@pytest.fixture
def stub_model_manager(tmp_path):
    """Create stub model manager."""
    return StubModelManager(config=types.SimpleNamespace(MODELS_CACHE_PATH=str(tmp_path / "models")))


@pytest.fixture
def stub_chromadb_manager():
    """Create stub ChromaDB manager."""
    return StubChromaDBManager()


@pytest.fixture
def mock_ai_models(monkeypatch):
    """Monkeypatch AI model imports to prevent loading heavy libraries."""
    # Mock ultralytics (YOLOv8)
    mock_yolo = MagicMock()
    mock_yolo.YOLO = MagicMock(return_value=MagicMock())
    monkeypatch.setitem(sys.modules, "ultralytics", mock_yolo)

    # Mock mtcnn
    mock_mtcnn = MagicMock()
    mock_mtcnn.MTCNN = MagicMock(return_value=MagicMock())
    monkeypatch.setitem(sys.modules, "mtcnn", mock_mtcnn)

    # Mock facenet_pytorch
    mock_facenet = MagicMock()
    mock_facenet.InceptionResnetV1 = MagicMock(return_value=MagicMock(eval=lambda: MagicMock()))
    monkeypatch.setitem(sys.modules, "facenet_pytorch", mock_facenet)

    # Mock torchreid
    mock_torchreid = MagicMock()
    mock_torchreid.utils = types.SimpleNamespace(FeatureExtractor=MagicMock())
    monkeypatch.setitem(sys.modules, "torchreid", mock_torchreid)
    monkeypatch.setitem(sys.modules, "torchreid.utils", mock_torchreid.utils)

    # Mock transformers (BLIP-2, Whisper)
    mock_transformers = MagicMock()
    mock_transformers.AutoModel = types.SimpleNamespace(
        from_pretrained=MagicMock(return_value=MagicMock())
    )
    mock_transformers.AutoProcessor = types.SimpleNamespace(
        from_pretrained=MagicMock(return_value=MagicMock())
    )
    monkeypatch.setitem(sys.modules, "transformers", mock_transformers)

    # Mock tensorflow_hub (YAMNet)
    mock_tfhub = MagicMock()
    monkeypatch.setitem(sys.modules, "tensorflow_hub", mock_tfhub)

    # Mock whisper
    mock_whisper = MagicMock()
    mock_whisper.load_model = MagicMock(return_value=MagicMock())
    monkeypatch.setitem(sys.modules, "whisper", mock_whisper)

    # Mock ollama
    mock_ollama = MagicMock()
    mock_ollama.Client = MagicMock(return_value=MagicMock())
    monkeypatch.setitem(sys.modules, "ollama", mock_ollama)

    return {
        "ultralytics": mock_yolo,
        "mtcnn": mock_mtcnn,
        "facenet_pytorch": mock_facenet,
        "torchreid": mock_torchreid,
        "transformers": mock_transformers,
        "tensorflow_hub": mock_tfhub,
        "whisper": mock_whisper,
        "ollama": mock_ollama,
    }


@pytest.fixture
def fake_db_session(monkeypatch):
    """Create fake database session."""
    store = []

    class FakeSession:
        def __init__(self, store):
            self.store = store
            self.counter = 0

        def add(self, obj):
            if getattr(obj, "id", None) is None:
                self.counter += 1
                obj.id = f"obj-{self.counter}"
            if obj not in self.store:
                self.store.append(obj)

        def commit(self):
            return None

        def rollback(self):
            self.store.clear()
            return None

    session = FakeSession(store)
    return session


@pytest.fixture
def fake_query(monkeypatch):
    """Create fake query for database operations."""
    store = []

    class FakeQuery:
        def __init__(self, store):
            self.store = store
            self.filters: Dict[str, object] = {}

        def filter_by(self, **kwargs):
            clone = FakeQuery(self.store)
            clone.filters = {**self.filters, **kwargs}
            return clone

        def first(self):
            for obj in self.store:
                if all(getattr(obj, key, None) == value for key, value in self.filters.items()):
                    return obj
            return None

        def all(self):
            if not self.filters:
                return self.store
            return [
                obj
                for obj in self.store
                if all(getattr(obj, key, None) == value for key, value in self.filters.items())
            ]

    return FakeQuery(store)
