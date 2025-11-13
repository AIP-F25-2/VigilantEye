from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from src.config.constants import ObjectCategory, ThreatLevel
from src.config.settings import get_config
from src.utils.model_manager import ModelManager

logger = logging.getLogger(__name__)


class ObjectDetectionError(Exception):
    """Raised when object detection fails."""


class ObjectDetectorService:
    """Service responsible for object detection and threat classification."""

    _instance: Optional["ObjectDetectorService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[object] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.config = config or get_config()
        self.device = (
            "cuda"
            if getattr(self.config, "USE_GPU_INFERENCE", True) and torch.cuda.is_available()
            else "cpu"
        )

        self.object_confidence_threshold = getattr(self.config, "OBJECT_DETECTION_CONFIDENCE", 0.5)
        self.object_min_size = getattr(self.config, "OBJECT_MIN_SIZE", 30)
        self.max_objects_per_frame = getattr(self.config, "MAX_OBJECTS_PER_FRAME", 100)
        self.person_iou_threshold = getattr(self.config, "OBJECT_PERSON_IOU_THRESHOLD", 0.1)
        self.detect_all_objects = getattr(self.config, "DETECT_ALL_OBJECTS", False)
        self.person_max_distance = getattr(self.config, "OBJECT_PERSON_MAX_DISTANCE", 100)

        self.model_manager = ModelManager(config=self.config)
        self.yolo_model = None

        self.threat_mappings = self._build_threat_mappings()

        self._models_loaded = False
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Model management
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        if self._models_loaded:
            return

        try:
            yolov8_path, error = self.model_manager.download_yolov8_model()
            if error:
                logger.warning(
                    "YOLOv8 download failed for object detection",
                    extra={"context": {"error": str(error)}},
                )
                self.yolo_model = None
            else:
                from ultralytics import YOLO  # type: ignore

                self.yolo_model = YOLO(yolov8_path)
                if hasattr(self.yolo_model, "to"):
                    self.yolo_model.to(self.device)  # type: ignore[attr-defined]
                logger.info(
                    "YOLOv8 model loaded for object detection",
                    extra={"context": {"device": self.device}},
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to load YOLOv8 model for object detection", extra={"context": {"error": str(exc)}})
            self.yolo_model = None
        finally:
            self._models_loaded = True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def detect_objects(
        self,
        frame: np.ndarray,
        person_detections: Optional[List[Dict]] = None,
    ) -> Tuple[Dict, Optional[Exception]]:
        if frame is None or frame.size == 0:
            return {}, ObjectDetectionError("Empty frame supplied for object detection")

        try:
            if not self._models_loaded:
                self._load_models()

            if self.yolo_model is None:
                raise ObjectDetectionError("YOLOv8 model unavailable")

            detections = self._run_yolo_detection(frame)
            if not detections:
                empty_result = {
                    "objects": [],
                    "relationships": [],
                    "threat_summary": {
                        "max_threat_level": ThreatLevel.NONE,
                        "high_threat_count": 0,
                        "medium_threat_count": 0,
                        "low_threat_count": 0,
                        "total_objects": 0,
                    },
                }
                return empty_result, None

            selected_objects: List[Dict] = []
            for detection in detections:
                if detection["confidence"] < self.object_confidence_threshold:
                    continue

                normalized_bbox = self._normalize_and_clip_bbox(detection["bbox"], frame.shape)
                if normalized_bbox is None:
                    continue

                if not self._is_valid_bbox(normalized_bbox):
                    continue

                class_id = detection["class_id"]
                class_name = detection["class_name"]
                threat_level, category = self._classify_object_threat(class_id, class_name)

                if not self.detect_all_objects and threat_level == ThreatLevel.NONE:
                    continue

                object_payload = {
                    "object_id": f"obj_{uuid.uuid4()}",
                    "class_id": class_id,
                    "class_name": class_name,
                    "bbox": normalized_bbox,
                    "confidence": detection["confidence"],
                    "threat_level": threat_level,
                    "category": category,
                }
                selected_objects.append(object_payload)

                if len(selected_objects) >= self.max_objects_per_frame:
                    logger.warning(
                        "Maximum objects per frame limit reached",
                        extra={"context": {"limit": self.max_objects_per_frame}},
                    )
                    break

            relationships: List[Dict] = []
            if person_detections:
                relationships = self._detect_object_person_relationships(selected_objects, person_detections)

            threat_summary = self._calculate_threat_summary(selected_objects)

            result = {
                "objects": selected_objects,
                "relationships": relationships,
                "threat_summary": threat_summary,
            }

            logger.debug(
                "Object detection completed",
                extra={
                    "context": {
                        "object_count": len(selected_objects),
                        "max_threat": threat_summary["max_threat_level"],
                    }
                },
            )

            return result, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Object detection failed", extra={"context": {"error": str(exc)}})
            return {}, exc

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _run_yolo_detection(self, frame: np.ndarray) -> List[Dict]:
        detections: List[Dict] = []

        if hasattr(self.yolo_model, "predict"):
            results = self.yolo_model.predict(frame)  # type: ignore[attr-defined]
        else:
            results = self.yolo_model(frame)  # type: ignore[operator]

        if not results:
            return detections

        first_result = results[0]
        boxes = getattr(first_result, "boxes", None)
        names_attr = getattr(self.yolo_model, "names", {})

        class_name_map: Dict[int, str] = {}
        if isinstance(names_attr, dict):
            class_name_map = {int(k): str(v) for k, v in names_attr.items()}
        elif isinstance(names_attr, list):
            class_name_map = {idx: str(value) for idx, value in enumerate(names_attr)}

        if boxes is None and hasattr(first_result, "pred"):
            boxes = first_result.pred[0]

        if boxes is None:
            return detections

        if hasattr(boxes, "xyxy"):
            for bbox, score, cls_id in zip(boxes.xyxy, boxes.conf, boxes.cls):
                class_id = int(cls_id)
                detections.append(
                    {
                        "bbox": bbox.tolist(),
                        "confidence": float(score),
                        "class_id": class_id,
                        "class_name": class_name_map.get(class_id, str(class_id)),
                    }
                )
        else:
            for row in boxes:
                if len(row) >= 6:
                    x1, y1, x2, y2, conf, cls = row[:6]
                    class_id = int(cls)
                    detections.append(
                        {
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "confidence": float(conf),
                            "class_id": class_id,
                            "class_name": class_name_map.get(class_id, str(class_id)),
                        }
                    )

        detections.sort(key=lambda item: item["confidence"], reverse=True)
        return detections

    def _is_valid_bbox(self, bbox: List[float]) -> bool:
        if len(bbox) != 4:
            return False
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        return width >= self.object_min_size and height >= self.object_min_size

    @staticmethod
    def _normalize_and_clip_bbox(bbox: List[float], frame_shape: Tuple[int, int, int]) -> Optional[List[float]]:
        if len(bbox) != 4:
            return None

        height, width = frame_shape[0], frame_shape[1]
        x1, y1, x2, y2 = bbox

        x_min = float(min(x1, x2))
        x_max = float(max(x1, x2))
        y_min = float(min(y1, y2))
        y_max = float(max(y1, y2))

        x_min = max(0.0, min(x_min, float(width - 1)))
        x_max = max(0.0, min(x_max, float(width - 1)))
        y_min = max(0.0, min(y_min, float(height - 1)))
        y_max = max(0.0, min(y_max, float(height - 1)))

        if x_max <= x_min or y_max <= y_min:
            return None

        return [x_min, y_min, x_max, y_max]

    def _detect_object_person_relationships(
        self,
        objects: List[Dict],
        persons: List[Dict],
    ) -> List[Dict]:
        relationships: List[Dict] = []

        for obj in objects:
            obj_bbox = obj.get("bbox")
            if not obj_bbox:
                continue

            for person in persons:
                person_bbox = person.get("bbox")
                if not person_bbox:
                    continue

                iou = self._calculate_iou(obj_bbox, person_bbox)
                relationship = None
                spatial_proximity = None
                confidence = max(iou, 0.0)

                if iou >= 0.3:
                    relationship = "holding"
                    spatial_proximity = "high"
                elif iou >= self.person_iou_threshold:
                    relationship = "near"
                    spatial_proximity = "medium"
                else:
                    distance = self._calculate_bbox_distance(obj_bbox, person_bbox)
                    if distance <= self.person_max_distance:
                        relationship = "in_vicinity"
                        spatial_proximity = "low"
                        confidence = max(confidence, 0.05)

                if relationship is None:
                    continue

                relationships.append(
                    {
                        "person_id": person.get("person_id"),
                        "object_id": obj["object_id"],
                        "relationship": relationship,
                        "confidence": float(min(max(confidence, 0.0), 1.0)),
                        "spatial_proximity": spatial_proximity,
                    }
                )

        return relationships

    @staticmethod
    def _calculate_iou(bbox1: List[float], bbox2: List[float]) -> float:
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)

        inter_width = max(0.0, inter_x_max - inter_x_min)
        inter_height = max(0.0, inter_y_max - inter_y_min)
        intersection = inter_width * inter_height

        area1 = max(0.0, (x1_max - x1_min)) * max(0.0, (y1_max - y1_min))
        area2 = max(0.0, (x2_max - x2_min)) * max(0.0, (y2_max - y2_min))
        union = area1 + area2 - intersection

        if union <= 0:
            return 0.0
        return float(intersection / union)

    @staticmethod
    def _calculate_bbox_distance(bbox1: List[float], bbox2: List[float]) -> float:
        x1_center = (bbox1[0] + bbox1[2]) / 2.0
        y1_center = (bbox1[1] + bbox1[3]) / 2.0
        x2_center = (bbox2[0] + bbox2[2]) / 2.0
        y2_center = (bbox2[1] + bbox2[3]) / 2.0
        return float(np.hypot(x1_center - x2_center, y1_center - y2_center))

    def _calculate_threat_summary(self, objects: List[Dict]) -> Dict:
        high_count = sum(1 for obj in objects if obj["threat_level"] == ThreatLevel.HIGH)
        medium_count = sum(1 for obj in objects if obj["threat_level"] == ThreatLevel.MEDIUM)
        low_count = sum(1 for obj in objects if obj["threat_level"] == ThreatLevel.LOW)
        total = len(objects)

        if high_count > 0:
            max_threat = ThreatLevel.HIGH
        elif medium_count > 0:
            max_threat = ThreatLevel.MEDIUM
        elif low_count > 0:
            max_threat = ThreatLevel.LOW
        else:
            max_threat = ThreatLevel.NONE

        return {
            "max_threat_level": max_threat,
            "high_threat_count": high_count,
            "medium_threat_count": medium_count,
            "low_threat_count": low_count,
            "total_objects": total,
        }

    def _classify_object_threat(self, class_id: int, class_name: str) -> Tuple[str, str]:
        mapping = self.threat_mappings.get(class_id)
        if mapping:
            return mapping["threat_level"], mapping["category"]
        return ThreatLevel.NONE, ObjectCategory.COMMON_OBJECT

    def _build_threat_mappings(self) -> Dict[int, Dict[str, str]]:
        return {
            43: {"name": "knife", "category": ObjectCategory.WEAPON, "threat_level": ThreatLevel.HIGH},
            76: {"name": "scissors", "category": ObjectCategory.SHARP_OBJECT, "threat_level": ThreatLevel.HIGH},
            37: {"name": "baseball_bat", "category": ObjectCategory.BLUNT_WEAPON, "threat_level": ThreatLevel.HIGH},
            24: {"name": "backpack", "category": ObjectCategory.BAG, "threat_level": ThreatLevel.MEDIUM},
            26: {"name": "handbag", "category": ObjectCategory.BAG, "threat_level": ThreatLevel.MEDIUM},
            28: {"name": "suitcase", "category": ObjectCategory.BAG, "threat_level": ThreatLevel.MEDIUM},
            25: {"name": "umbrella", "category": ObjectCategory.TOOL, "threat_level": ThreatLevel.MEDIUM},
            39: {"name": "bottle", "category": ObjectCategory.CONTAINER, "threat_level": ThreatLevel.LOW},
            67: {"name": "cell_phone", "category": ObjectCategory.ELECTRONICS, "threat_level": ThreatLevel.LOW},
            63: {"name": "laptop", "category": ObjectCategory.ELECTRONICS, "threat_level": ThreatLevel.LOW},
            2: {"name": "car", "category": ObjectCategory.VEHICLE, "threat_level": ThreatLevel.LOW},
            3: {"name": "motorcycle", "category": ObjectCategory.VEHICLE, "threat_level": ThreatLevel.LOW},
            5: {"name": "bus", "category": ObjectCategory.VEHICLE, "threat_level": ThreatLevel.LOW},
            7: {"name": "truck", "category": ObjectCategory.VEHICLE, "threat_level": ThreatLevel.LOW},
        }

