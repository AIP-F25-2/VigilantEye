from __future__ import annotations

import sys
import types
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from src.ai_modules.person_detector import PersonDetectorService
from src.models import person as person_module


class DummyConfig:
    def __init__(self, storage_base: Path):
        self.MODELS_CACHE_PATH = str(storage_base / "models_cache")
        self.STORAGE_BASE_PATH = str(storage_base / "storage")
        self.PERSON_DETECTION_CONFIDENCE = 0.5
        self.FACE_DETECTION_CONFIDENCE = 0.5
        self.REID_SIMILARITY_THRESHOLD = 0.8
        self.MAX_PERSONS_PER_FRAME = 50
        self.PERSON_MIN_SIZE = 10
        self.SAVE_PERSON_THUMBNAILS = True
        self.USE_GPU_INFERENCE = False
        self.PERSON_VECTOR_TTL_HOURS = 2


class StubModelManager:
    def __init__(self, *args, **kwargs):
        self.download_calls: Dict[str, int] = defaultdict(int)
        self.yolo_path = Path(kwargs.get("config").MODELS_CACHE_PATH) / "yolov8" / "yolov8n.pt"
        self.yolo_path.parent.mkdir(parents=True, exist_ok=True)
        self.yolo_path.write_bytes(b"yolo")

    def download_yolov8_model(self, *_args, **_kwargs):
        return str(self.yolo_path), None

    def download_mtcnn_weights(self):
        return True, None

    def download_arcface_model(self):
        return "arcface/model.pt", None

    def download_osnet_model(self, *_args, **_kwargs):
        return "osnet/osnet_x1_0.pth", None

    def download_mivolo_model(self):
        return "mivolo/model.pth", None


class StubChromaDBManager:
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
        self.face_embeddings[person_id] = embedding
        self.add_face_calls.append({"id": person_id, "metadata": metadata})
        return True, None

    def add_body_embedding(self, person_id, embedding, metadata):
        self.body_embeddings[person_id] = embedding
        self.add_body_calls.append({"id": person_id, "metadata": metadata})
        return True, None

    def search_similar_faces(self, *args, **kwargs):
        return self.similar_face_results, None

    def search_similar_bodies(self, *args, **kwargs):
        return self.similar_body_results, None

    def _get_face(self, ids=None, include=None, where=None):
        return self._build_get_response(self.face_embeddings, ids, include, where)

    def _get_body(self, ids=None, include=None, where=None):
        return self._build_get_response(self.body_embeddings, ids, include, where)

    @staticmethod
    def _build_get_response(store: Dict[str, np.ndarray], ids, include, where):
        if ids is None:
            return {"ids": []}
        present = [idx for idx in ids if idx in store]
        embeddings = [[store[idx].tolist()] for idx in present] if include and "embeddings" in include else []
        metadatas = [[{}] for _ in present] if include and "metadatas" in include else []
        return {"ids": present, "embeddings": embeddings, "metadatas": metadatas}


class FakeSession:
    def __init__(self, store: List[person_module.Person]):
        self.store = store
        self.counter = 0

    def add(self, obj):
        if isinstance(obj, person_module.Person):
            if getattr(obj, "id", None) is None:
                self.counter += 1
                obj.id = f"person-{self.counter}"
            if obj not in self.store:
                self.store.append(obj)

    def commit(self):
        return None

    def rollback(self):
        return None


class FakeQuery:
    def __init__(self, store: List[person_module.Person]):
        self.store = store
        self.filters: Dict[str, object] = {}

    def filter_by(self, **kwargs):
        clone = FakeQuery(self.store)
        clone.filters = {**self.filters, **kwargs}
        return clone

    def first(self):
        for person in self.store:
            if all(getattr(person, key, None) == value for key, value in self.filters.items()):
                return person
        return None


@pytest.fixture(autouse=True)
def reset_singleton():
    PersonDetectorService._instance = None
    yield
    PersonDetectorService._instance = None


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    (tmp_path / "storage" / "persons").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def config(storage_dir: Path) -> DummyConfig:
    return DummyConfig(storage_base=storage_dir)


@pytest.fixture
def person_store(monkeypatch: pytest.MonkeyPatch) -> List[person_module.Person]:
    store: List[person_module.Person] = []
    query = FakeQuery(store)
    monkeypatch.setattr(person_module.Person, "query", query)
    return store


@pytest.fixture
def fake_db_session(monkeypatch: pytest.MonkeyPatch, person_store: List[person_module.Person]) -> FakeSession:
    session = FakeSession(person_store)
    monkeypatch.setattr("src.ai_modules.person_detector.db", types.SimpleNamespace(session=session))
    return session


@pytest.fixture
def detector(monkeypatch: pytest.MonkeyPatch, config: DummyConfig) -> PersonDetectorService:
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=MagicMock))
    monkeypatch.setitem(sys.modules, "mtcnn", types.SimpleNamespace(MTCNN=MagicMock))
    monkeypatch.setitem(
        sys.modules,
        "facenet_pytorch",
        types.SimpleNamespace(InceptionResnetV1=MagicMock(return_value=MagicMock(eval=lambda: MagicMock()))),
    )
    monkeypatch.setitem(sys.modules, "torchreid.utils", types.SimpleNamespace(FeatureExtractor=MagicMock))
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoModel=types.SimpleNamespace(from_pretrained=MagicMock(return_value=MagicMock()))))

    monkeypatch.setattr("src.ai_modules.person_detector.ModelManager", StubModelManager)
    monkeypatch.setattr("src.ai_modules.person_detector.ChromaDBManager", StubChromaDBManager)

    service = PersonDetectorService(config=config)
    service._models_loaded = True
    service.model_manager = StubModelManager(config=config)
    service.chromadb_manager = StubChromaDBManager()
    return service


def _mock_detection_models(service: PersonDetectorService):
    class MockBoxes:
        def __init__(self):
            self.xyxy = [
                [10.0, 10.0, 110.0, 210.0],
                [120.0, 20.0, 200.0, 220.0],
            ]
            self.conf = [0.9, 0.85]

    class MockResult:
        def __init__(self):
            self.boxes = MockBoxes()

    class MockYOLO:
        def predict(self, frame, classes=None):
            return [MockResult()]

    class MockMTCNN:
        def detect(self, _):
            boxes = np.array([[5, 5, 60, 60]])
            probs = np.array([0.95])
            return boxes, probs

    class MockArcFace(torch.nn.Module):
        def forward(self, _tensor):
            return torch.ones((1, 512))

    class MockOSNet:
        def __call__(self, imgs):
            return torch.ones((1, 512))

    class MockMiVOLO(torch.nn.Module):
        def forward(self, _tensor):
            return torch.ones((1, 512))

    service.yolo_model = MockYOLO()
    service.mtcnn_detector = MockMTCNN()
    service.arcface_model = MockArcFace()
    service.osnet_extractor = MockOSNet()
    service.mivolo_model = MockMiVOLO()


def test_load_models_success(monkeypatch: pytest.MonkeyPatch, config: DummyConfig, storage_dir: Path):
    stub_manager = StubModelManager(config=config)

    class ReadyArcFace(torch.nn.Module):
        def __call__(self, *_args, **_kwargs):
            return torch.ones((1, 512))

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=MagicMock(return_value=MagicMock(ckpt_path=stub_manager.yolo_path))))
    monkeypatch.setitem(sys.modules, "mtcnn", types.SimpleNamespace(MTCNN=MagicMock()))
    monkeypatch.setitem(sys.modules, "facenet_pytorch", types.SimpleNamespace(InceptionResnetV1=MagicMock(return_value=ReadyArcFace())))
    monkeypatch.setitem(sys.modules, "torchreid.utils", types.SimpleNamespace(FeatureExtractor=MagicMock(return_value=MagicMock())))
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoModel=types.SimpleNamespace(from_pretrained=MagicMock(return_value=ReadyArcFace()))))
    monkeypatch.setattr("src.ai_modules.person_detector.ModelManager", lambda config=None: stub_manager)
    monkeypatch.setattr("src.ai_modules.person_detector.ChromaDBManager", StubChromaDBManager)

    detector = PersonDetectorService(config=config)
    detector._models_loaded = False
    detector._load_models()

    assert detector.yolo_model is not None
    assert detector.mtcnn_detector is not None
    assert detector.arcface_model is not None
    assert detector.osnet_extractor is not None
    assert detector.mivolo_model is not None
    assert detector._models_loaded is True


def test_load_models_graceful_degradation(monkeypatch: pytest.MonkeyPatch, config: DummyConfig):
    stub_manager = StubModelManager(config=config)

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=MagicMock(return_value=MagicMock(ckpt_path=stub_manager.yolo_path))))
    monkeypatch.setitem(sys.modules, "mtcnn", types.SimpleNamespace(MTCNN=MagicMock()))
    monkeypatch.setitem(sys.modules, "facenet_pytorch", types.SimpleNamespace(InceptionResnetV1=MagicMock(side_effect=RuntimeError("fail"))))
    monkeypatch.setitem(sys.modules, "torchreid.utils", types.SimpleNamespace(FeatureExtractor=MagicMock()))
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoModel=types.SimpleNamespace(from_pretrained=MagicMock(side_effect=RuntimeError("download error")))))
    monkeypatch.setattr("src.ai_modules.person_detector.ModelManager", lambda config=None: stub_manager)
    monkeypatch.setattr("src.ai_modules.person_detector.ChromaDBManager", StubChromaDBManager)

    detector = PersonDetectorService(config=config)
    detector._models_loaded = False
    detector._load_models()

    assert detector.yolo_model is not None
    assert detector.mivolo_model is None


def test_detect_persons_success(detector: PersonDetectorService, fake_db_session: FakeSession, person_store: List[person_module.Person], monkeypatch: pytest.MonkeyPatch):
    _mock_detection_models(detector)
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda *_args, **_kwargs: True)

    frame = np.ones((240, 240, 3), dtype=np.uint8)
    timestamp = datetime.utcnow()

    persons, error = detector.detect_persons(frame, "video-1", timestamp, frame_number=1)
    assert error is None
    assert len(persons) == 2
    assert detector.chromadb_manager.add_body_calls
    assert detector.chromadb_manager.add_face_calls


def test_detect_persons_reid_match_found(detector: PersonDetectorService, fake_db_session: FakeSession, monkeypatch: pytest.MonkeyPatch):
    _mock_detection_models(detector)
    detector.chromadb_manager.similar_body_results = [
        {"person_id": "person-existing", "similarity": 0.95, "metadata": {}}
    ]
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda *_args, **_kwargs: True)

    frame = np.ones((240, 240, 3), dtype=np.uint8)
    timestamp = datetime.utcnow()

    persons, _ = detector.detect_persons(frame, "video-1", timestamp, frame_number=1)
    assert persons[0]["person_tracking_id"] == "person-existing"


def test_detect_persons_no_face_detected(detector: PersonDetectorService, monkeypatch: pytest.MonkeyPatch):
    _mock_detection_models(detector)

    class NoFaceMTCNN:
        def detect(self, _):
            return None

    detector.mtcnn_detector = NoFaceMTCNN()
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda *_args, **_kwargs: True)

    frame = np.ones((240, 240, 3), dtype=np.uint8)
    persons, _ = detector.detect_persons(frame, "video-1", datetime.utcnow(), frame_number=1)
    assert persons[0]["embeddings"]["face"] == []


def test_detect_persons_low_confidence_filtered(detector: PersonDetectorService, monkeypatch: pytest.MonkeyPatch):
    class LowConfidenceBoxes:
        def __init__(self):
            self.xyxy = [[0.0, 0.0, 50.0, 100.0]]
            self.conf = [0.1]

    class LowConfidenceResult:
        def __init__(self):
            self.boxes = LowConfidenceBoxes()

    class LowConfidenceYOLO:
        def predict(self, *_args, **_kwargs):
            return [LowConfidenceResult()]

    detector.yolo_model = LowConfidenceYOLO()
    detector.mtcnn_detector = MagicMock()
    detector.arcface_model = MagicMock()
    detector.osnet_extractor = MagicMock(return_value=torch.ones((1, 512)))

    frame = np.ones((120, 120, 3), dtype=np.uint8)
    persons, _ = detector.detect_persons(frame, "video-1", datetime.utcnow(), frame_number=1)
    assert persons == []


def test_detect_persons_max_persons_limit(config: DummyConfig, monkeypatch: pytest.MonkeyPatch, fake_db_session: FakeSession, person_store: List[person_module.Person]):
    config.MAX_PERSONS_PER_FRAME = 1
    monkeypatch.setattr("src.ai_modules.person_detector.ModelManager", StubModelManager)
    monkeypatch.setattr("src.ai_modules.person_detector.ChromaDBManager", StubChromaDBManager)
    detector = PersonDetectorService(config=config)
    detector._models_loaded = True
    _mock_detection_models(detector)
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda *_args, **_kwargs: True)

    frame = np.ones((240, 240, 3), dtype=np.uint8)
    persons, _ = detector.detect_persons(frame, "video-1", datetime.utcnow(), frame_number=1)
    assert len(persons) == 1


def test_detect_demographics_success(detector: PersonDetectorService):
    class MockMiVOLO(torch.nn.Module):
        def forward(self, _input):
            return torch.ones((1, 512))

    detector.mivolo_model = MockMiVOLO()
    face = np.ones((112, 112, 3), dtype=np.uint8) * 255
    output = detector._detect_demographics(face)
    assert "age" in output
    assert output["gender"] in {"male", "female", "unknown"}


def test_detect_demographics_model_failure(detector: PersonDetectorService):
    class FailingMiVOLO(torch.nn.Module):
        def forward(self, _input):
            raise RuntimeError("failure")

    detector.mivolo_model = FailingMiVOLO()
    face = np.ones((112, 112, 3), dtype=np.uint8)
    output = detector._detect_demographics(face)
    assert output["gender"] == "unknown"


def test_describe_clothing(detector: PersonDetectorService):
    crop = np.full((100, 50, 3), 200, dtype=np.uint8)
    description = detector._describe_clothing(crop)
    assert isinstance(description, str)
    assert description != ""


def test_extract_body_features(detector: PersonDetectorService):
    crop = np.ones((200, 100, 3), dtype=np.uint8)
    features = detector._extract_body_features(crop)
    assert "height_ratio" in features
    assert features["height_ratio"] > 0


def test_create_or_update_person_new_person(detector: PersonDetectorService, fake_db_session: FakeSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda *_args, **_kwargs: True)
    detection_data = {
        "bbox": [0, 0, 10, 10],
        "confidence": 0.9,
        "age": 30,
        "gender": "male",
        "ethnicity": "caucasian",
        "clothing_description": "Dark clothing",
        "body_features": {"height_ratio": 1.8},
    }
    person, error = detector._create_or_update_person(
        "track-1",
        "video-1",
        datetime.utcnow(),
        detection_data,
        np.ones((20, 20, 3), dtype=np.uint8),
    )
    assert error is None
    assert person is not None
    assert person.age_estimate == 30


def test_create_or_update_person_existing_person(detector: PersonDetectorService, fake_db_session: FakeSession, person_store: List[person_module.Person], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda *_args, **_kwargs: True)
    existing = person_module.Person(
        video_id="video-1",
        person_tracking_id="track-1",
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        total_appearances=1,
    )
    person_store.append(existing)

    detection_data = {
        "bbox": [0, 0, 10, 10],
        "confidence": 0.95,
        "age": 35,
        "gender": "female",
        "ethnicity": "asian",
        "clothing_description": "Light clothing",
        "body_features": {"height_ratio": 1.2},
    }
    person, error = detector._create_or_update_person(
        "track-1",
        "video-1",
        datetime.utcnow(),
        detection_data,
        np.ones((20, 20, 3), dtype=np.uint8),
    )
    assert error is None
    assert person.gender == "female"
    assert person.total_appearances >= 2


def test_find_similar_persons_success(detector: PersonDetectorService, person_store: List[person_module.Person]):
    person = person_module.Person(
        id="person-1",
        video_id="video-1",
        person_tracking_id="track-1",
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        total_appearances=1,
    )
    person_store.append(person)
    detector.chromadb_manager.face_embeddings["track-1"] = np.ones(512)
    detector.chromadb_manager.body_embeddings["track-1"] = np.ones(512)
    detector.chromadb_manager.similar_face_results = [{"person_id": "track-1", "similarity": 0.9, "metadata": {}}]
    detector.chromadb_manager.similar_body_results = [{"person_id": "track-1", "similarity": 0.8, "metadata": {}}]

    results, error = detector.find_similar_persons("person-1", top_k=5)
    assert error is None
    assert results
    assert results[0]["person_tracking_id"] == "track-1"


def test_find_similar_persons_no_matches(detector: PersonDetectorService, person_store: List[person_module.Person]):
    person = person_module.Person(
        id="person-1",
        video_id="video-1",
        person_tracking_id="track-1",
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        total_appearances=1,
    )
    person_store.append(person)
    detector.chromadb_manager.face_embeddings["track-1"] = np.ones(512)

    results, error = detector.find_similar_persons("person-1")
    assert error is None
    assert results == []


def test_get_person_details_success(detector: PersonDetectorService, person_store: List[person_module.Person]):
    person = person_module.Person(
        id="person-1",
        video_id="video-1",
        person_tracking_id="track-1",
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        total_appearances=1,
    )
    person_store.append(person)
    detector.chromadb_manager.face_embeddings["track-1"] = np.ones(512)
    detector.chromadb_manager.body_embeddings["track-1"] = np.ones(512)

    details, error = detector.get_person_details("person-1")
    assert error is None
    assert details is not None
    assert details["embeddings"]["face"]


def test_get_person_details_not_found(detector: PersonDetectorService):
    details, error = detector.get_person_details("missing")
    assert details is None
    assert isinstance(error, Exception)


def test_save_person_thumbnail(detector: PersonDetectorService, monkeypatch: pytest.MonkeyPatch, storage_dir: Path):
    monkeypatch.setattr("src.ai_modules.person_detector.cv2.imwrite", lambda path, img: True)
    frame = np.ones((50, 50, 3), dtype=np.uint8)
    bbox = [0, 0, 50, 50]
    path = detector._save_person_thumbnail(frame, bbox, "track-thumb")
    assert path is not None

