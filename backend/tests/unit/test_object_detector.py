import numpy as np
import pytest

from src.ai_modules.object_detector import ObjectDetectorService
from src.config.constants import ObjectCategory, ThreatLevel
from src.utils.model_manager import ModelManager


@pytest.fixture(autouse=True)
def reset_object_detector_singleton():
    ObjectDetectorService._instance = None
    yield
    ObjectDetectorService._instance = None


@pytest.fixture
def sample_frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


def test_load_models_success(mocker):
    mocker.patch.object(
        ModelManager,
        "download_yolov8_model",
        return_value=("models_cache/yolov8/yolov8n.pt", None),
    )
    yolo_mock = mocker.Mock()
    yolo_mock.to.return_value = yolo_mock

    mocker.patch("ultralytics.YOLO", return_value=yolo_mock)

    detector = ObjectDetectorService()
    detector._load_models()

    assert detector.yolo_model is yolo_mock
    assert detector._models_loaded is True
    yolo_mock.to.assert_called_once()


def test_load_models_yolo_unavailable(mocker):
    mocker.patch.object(
        ModelManager,
        "download_yolov8_model",
        return_value=(None, RuntimeError("download failure")),
    )

    detector = ObjectDetectorService()
    detector._load_models()

    assert detector.yolo_model is None
    assert detector._models_loaded is True


def test_detect_objects_success(mocker, sample_frame):
    detections = [
        {"bbox": [10, 10, 100, 100], "confidence": 0.9, "class_id": 43, "class_name": "knife"},
        {"bbox": [150, 150, 260, 260], "confidence": 0.85, "class_id": 24, "class_name": "backpack"},
        {"bbox": [300, 300, 360, 360], "confidence": 0.82, "class_id": 39, "class_name": "bottle"},
    ]
    mocker.patch.object(ObjectDetectorService, "_run_yolo_detection", return_value=detections)

    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()

    result, error = detector.detect_objects(sample_frame)

    assert error is None
    assert len(result["objects"]) == 3
    threat_levels = {obj["class_name"]: obj["threat_level"] for obj in result["objects"]}
    assert threat_levels["knife"] == ThreatLevel.HIGH
    assert threat_levels["backpack"] == ThreatLevel.MEDIUM
    assert threat_levels["bottle"] == ThreatLevel.LOW
    assert result["threat_summary"]["max_threat_level"] == ThreatLevel.HIGH


def test_detect_objects_with_person_relationships(mocker, sample_frame):
    detections = [
        {"bbox": [100, 100, 160, 160], "confidence": 0.92, "class_id": 43, "class_name": "knife"},
    ]
    mocker.patch.object(ObjectDetectorService, "_run_yolo_detection", return_value=detections)

    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()

    persons = [{"person_id": "person_1", "bbox": [90, 90, 200, 200]}]
    result, error = detector.detect_objects(sample_frame, persons)

    assert error is None
    assert len(result["relationships"]) == 1
    relationship = result["relationships"][0]
    assert relationship["relationship"] == "holding"
    assert relationship["spatial_proximity"] == "high"


def test_detect_objects_no_suspicious_items(mocker, sample_frame):
    detections = [
        {"bbox": [10, 10, 100, 100], "confidence": 0.95, "class_id": 62, "class_name": "chair"},
    ]
    mocker.patch.object(ObjectDetectorService, "_run_yolo_detection", return_value=detections)

    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()
    detector.detect_all_objects = False

    result, error = detector.detect_objects(sample_frame)

    assert error is None
    assert result["objects"] == []


def test_detect_objects_all_objects_mode(mocker, sample_frame):
    detections = [
        {"bbox": [10, 10, 120, 120], "confidence": 0.93, "class_id": 43, "class_name": "knife"},
        {"bbox": [200, 200, 280, 280], "confidence": 0.88, "class_id": 62, "class_name": "chair"},
    ]
    mocker.patch.object(ObjectDetectorService, "_run_yolo_detection", return_value=detections)

    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()
    detector.detect_all_objects = True

    result, error = detector.detect_objects(sample_frame)

    assert error is None
    assert len(result["objects"]) == 2
    chair = next(obj for obj in result["objects"] if obj["class_name"] == "chair")
    assert chair["threat_level"] == ThreatLevel.NONE
    assert chair["category"] == ObjectCategory.COMMON_OBJECT


def test_detect_objects_low_confidence_filtered(mocker, sample_frame):
    detections = [
        {"bbox": [10, 10, 120, 120], "confidence": 0.9, "class_id": 43, "class_name": "knife"},
        {"bbox": [200, 200, 250, 250], "confidence": 0.3, "class_id": 24, "class_name": "backpack"},
    ]
    mocker.patch.object(ObjectDetectorService, "_run_yolo_detection", return_value=detections)

    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()

    result, error = detector.detect_objects(sample_frame)

    assert error is None
    assert len(result["objects"]) == 1
    assert result["objects"][0]["class_name"] == "knife"


def test_detect_objects_max_objects_limit(mocker, sample_frame):
    detections = [
        {"bbox": [0, 0, 50, 50], "confidence": 0.95, "class_id": 43, "class_name": "knife"},
        {"bbox": [60, 60, 120, 120], "confidence": 0.94, "class_id": 24, "class_name": "backpack"},
        {"bbox": [130, 130, 190, 190], "confidence": 0.93, "class_id": 25, "class_name": "umbrella"},
    ]
    mocker.patch.object(ObjectDetectorService, "_run_yolo_detection", return_value=detections)

    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()
    detector.max_objects_per_frame = 2

    result, error = detector.detect_objects(sample_frame)

    assert error is None
    assert len(result["objects"]) == 2


def test_calculate_iou_high_overlap():
    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()

    bbox1 = [10, 10, 110, 110]
    bbox2 = [20, 20, 100, 100]
    assert detector._calculate_iou(bbox1, bbox2) > 0.5


def test_calculate_iou_no_overlap():
    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()

    bbox1 = [10, 10, 50, 50]
    bbox2 = [100, 100, 150, 150]
    assert detector._calculate_iou(bbox1, bbox2) == 0.0


def test_calculate_iou_partial_overlap():
    detector = ObjectDetectorService()
    detector._models_loaded = True
    detector.yolo_model = object()

    bbox1 = [10, 10, 100, 100]
    bbox2 = [80, 80, 160, 160]
    iou = detector._calculate_iou(bbox1, bbox2)
    assert 0.1 < iou < 0.5


def test_detect_object_person_relationships_holding():
    detector = ObjectDetectorService()
    obj = {"object_id": "obj1", "bbox": [100, 100, 180, 180]}
    person = {"person_id": "p1", "bbox": [90, 90, 190, 190]}

    relationships = detector._detect_object_person_relationships([obj], [person])
    assert len(relationships) == 1
    assert relationships[0]["relationship"] == "holding"
    assert relationships[0]["spatial_proximity"] == "high"


def test_detect_object_person_relationships_near():
    detector = ObjectDetectorService()
    detector.person_iou_threshold = 0.05
    obj = {"object_id": "obj1", "bbox": [100, 100, 160, 160]}
    person = {"person_id": "p1", "bbox": [120, 120, 220, 220]}

    relationships = detector._detect_object_person_relationships([obj], [person])
    assert len(relationships) == 1
    assert relationships[0]["relationship"] == "near"
    assert relationships[0]["spatial_proximity"] == "medium"


def test_detect_object_person_relationships_no_relationship():
    detector = ObjectDetectorService()
    obj = {"object_id": "obj1", "bbox": [10, 10, 50, 50]}
    person = {"person_id": "p1", "bbox": [200, 200, 240, 240]}

    relationships = detector._detect_object_person_relationships([obj], [person])
    assert relationships == []


def test_calculate_threat_summary():
    detector = ObjectDetectorService()
    objects = [
        {"threat_level": ThreatLevel.HIGH},
        {"threat_level": ThreatLevel.HIGH},
        {"threat_level": ThreatLevel.MEDIUM},
        {"threat_level": ThreatLevel.MEDIUM},
        {"threat_level": ThreatLevel.MEDIUM},
        {"threat_level": ThreatLevel.LOW},
    ]
    summary = detector._calculate_threat_summary(objects)

    assert summary["max_threat_level"] == ThreatLevel.HIGH
    assert summary["high_threat_count"] == 2
    assert summary["medium_threat_count"] == 3
    assert summary["low_threat_count"] == 1
    assert summary["total_objects"] == 6


def test_classify_object_threat_weapon():
    detector = ObjectDetectorService()
    level, category = detector._classify_object_threat(43, "knife")

    assert level == ThreatLevel.HIGH
    assert category == ObjectCategory.WEAPON


def test_classify_object_threat_bag():
    detector = ObjectDetectorService()
    level, category = detector._classify_object_threat(24, "backpack")

    assert level == ThreatLevel.MEDIUM
    assert category == ObjectCategory.BAG


def test_classify_object_threat_common_object():
    detector = ObjectDetectorService()
    level, category = detector._classify_object_threat(62, "chair")

    assert level == ThreatLevel.NONE
    assert category == ObjectCategory.COMMON_OBJECT


def test_build_threat_mappings():
    detector = ObjectDetectorService()
    mappings = detector._build_threat_mappings()

    assert mappings[43]["threat_level"] == ThreatLevel.HIGH
    assert mappings[24]["threat_level"] == ThreatLevel.MEDIUM
    assert mappings[39]["threat_level"] == ThreatLevel.LOW
    assert mappings[43]["category"] == ObjectCategory.WEAPON
    assert mappings[24]["category"] == ObjectCategory.BAG
    assert mappings[39]["category"] == ObjectCategory.CONTAINER

