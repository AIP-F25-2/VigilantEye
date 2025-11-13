from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from PIL import Image

from src.app import db
from src.config.settings import get_config
from src.models.person import Person
from src.services.storage_service import StorageError
from src.utils.chromadb_manager import ChromaDBManager
from src.utils.model_manager import ModelManager

logger = logging.getLogger(__name__)


class PersonDetectionError(Exception):
    """Raised when person detection fails."""


class PersonDetectorService:
    """Main service responsible for person detection and re-identification."""

    _instance: Optional["PersonDetectorService"] = None

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

        self.person_confidence = getattr(self.config, "PERSON_DETECTION_CONFIDENCE", 0.5)
        self.face_confidence = getattr(self.config, "FACE_DETECTION_CONFIDENCE", 0.9)
        self.reid_similarity_threshold = getattr(self.config, "REID_SIMILARITY_THRESHOLD", 0.8)
        self.max_persons_per_frame = getattr(self.config, "MAX_PERSONS_PER_FRAME", 50)
        self.person_min_size = getattr(self.config, "PERSON_MIN_SIZE", 50)
        self.save_thumbnails = getattr(self.config, "SAVE_PERSON_THUMBNAILS", True)

        self.models_cache_path = Path(getattr(self.config, "MODELS_CACHE_PATH", "./models_cache"))
        self.storage_base_path = Path(getattr(self.config, "STORAGE_BASE_PATH", "./storage"))

        self.model_manager = ModelManager(config=self.config)
        self.chromadb_manager = ChromaDBManager(config=self.config)

        self.yolo_model = None
        self.mtcnn_detector = None
        self.arcface_model: Optional[nn.Module] = None
        self.osnet_extractor = None
        self.mivolo_model = None
        self.mivolo_processor = None
        self.demographics_backend: Optional[str] = None
        self.deepface = None
        self.deepface_models: Dict[str, object] = {}

        self._models_loaded = False
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Model management
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        if self._models_loaded:
            return

        logger.info("Loading AI models for person detection")
        loading_errors: List[str] = []

        try:
            yolov8_path, error = self.model_manager.download_yolov8_model()
            if error:
                loading_errors.append(f"YOLOv8: {error}")
            else:
                from ultralytics import YOLO  # type: ignore

                self.yolo_model = YOLO(yolov8_path)
        except Exception as exc:  # pylint: disable=broad-except
            loading_errors.append(f"YOLOv8: {exc}")

        try:
            _, error = self.model_manager.download_mtcnn_weights()
            if error:
                loading_errors.append(f"MTCNN: {error}")
            else:
                from facenet_pytorch import MTCNN  # type: ignore

                self.mtcnn_detector = MTCNN(keep_all=True, device=self.device)
        except Exception as exc:  # pylint: disable=broad-except
            loading_errors.append(f"MTCNN: {exc}")

        try:
            arcface_path, error = self.model_manager.download_arcface_model()
            if error:
                loading_errors.append(f"ArcFace: {error}")
            else:
                from facenet_pytorch import InceptionResnetV1  # type: ignore

                self.arcface_model = (
                    InceptionResnetV1(pretrained="vggface2")
                    .eval()
                    .to(self.device)
                )
                for param in self.arcface_model.parameters():
                    param.requires_grad = False
        except Exception as exc:  # pylint: disable=broad-except
            loading_errors.append(f"ArcFace: {exc}")

        try:
            osnet_path, error = self.model_manager.download_osnet_model()
            if error:
                loading_errors.append(f"OSNet: {error}")
            else:
                from torchreid.utils import FeatureExtractor  # type: ignore

                self.osnet_extractor = FeatureExtractor(
                    model_name="osnet_x1_0",
                    device=self.device,
                )
        except Exception as exc:  # pylint: disable=broad-except
            loading_errors.append(f"OSNet: {exc}")

        try:
            mivolo_path, error = self.model_manager.download_mivolo_model()
            if error:
                loading_errors.append(f"MiVOLO: {error}")
            else:
                from transformers import (  # type: ignore
                    AutoImageProcessor,
                    AutoModelForImageClassification,
                )

                cache_dir = str(Path(mivolo_path).parent)
                self.mivolo_processor = AutoImageProcessor.from_pretrained(
                    "iitolstykh/mivolo_v2",
                    cache_dir=cache_dir,
                )
                self.mivolo_model = (
                    AutoModelForImageClassification.from_pretrained(
                        "iitolstykh/mivolo_v2",
                        cache_dir=cache_dir,
                    )
                    .to(self.device)
                    .eval()
                )
                self.demographics_backend = "mivolo"
        except Exception as exc:  # pylint: disable=broad-except
            loading_errors.append(f"MiVOLO: {exc}")
            self.mivolo_model = None
            self.mivolo_processor = None

        if self.demographics_backend != "mivolo":
            try:
                from deepface import DeepFace  # type: ignore

                self.deepface = DeepFace
                self.deepface_models = {
                    "age": DeepFace.build_model("Age"),  # type: ignore[attr-defined]
                    "gender": DeepFace.build_model("Gender"),  # type: ignore[attr-defined]
                    "race": DeepFace.build_model("Race"),  # type: ignore[attr-defined]
                }
                self.demographics_backend = "deepface"
            except Exception as exc:  # pylint: disable=broad-except
                loading_errors.append(f"Demographics: {exc}")
                self.deepface = None
                self.deepface_models = {}

        if loading_errors:
            logger.warning("Model loading completed with issues", extra={"context": {"errors": loading_errors}})
        else:
            logger.info("All person detection models loaded successfully")

        self._models_loaded = True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def detect_persons(
        self,
        frame: np.ndarray,
        video_id: str,
        timestamp: datetime,
        frame_number: int,
    ) -> Tuple[List[Dict], Optional[Exception]]:
        if frame is None or frame.size == 0:
            return [], PersonDetectionError("Empty frame supplied")

        try:
            if not self._models_loaded:
                self._load_models()

            if self.yolo_model is None:
                raise PersonDetectionError("YOLOv8 model unavailable")

            detections = self._run_yolo_detection(frame)
            if not detections:
                return [], None

            frame_height, frame_width = frame.shape[:2]
            processed_persons: List[Dict] = []

            for index, detection in enumerate(detections[: self.max_persons_per_frame]):
                bbox = detection["bbox"]
                confidence = detection["confidence"]

                if confidence < self.person_confidence:
                    continue

                x1, y1, x2, y2 = self._clip_bbox(bbox, frame_width, frame_height)
                if (x2 - x1) < self.person_min_size or (y2 - y1) < self.person_min_size:
                    continue

                person_crop = frame[y1:y2, x1:x2]
                if person_crop.size == 0:
                    continue

                body_embedding = self._extract_body_embedding(person_crop)
                person_tracking_id = f"person_{uuid.uuid4()}"
                reid_metadata = {
                    "video_id": video_id,
                    "frame_number": frame_number,
                    "first_seen": int(timestamp.timestamp()),
                    "confidence": confidence,
                }

                if body_embedding is not None:
                    similar_bodies, _ = self.chromadb_manager.search_similar_bodies(
                        body_embedding,
                        n_results=5,
                        time_window_hours=2,
                    )
                    if similar_bodies:
                        best_match = similar_bodies[0]
                        if best_match["similarity"] >= self.reid_similarity_threshold:
                            person_tracking_id = best_match["person_id"]

                (
                    face_embedding,
                    demographics,
                ) = self._process_face(person_crop)

                clothing_description = self._describe_clothing(person_crop)
                body_features = self._extract_body_features(person_crop)

                detection_data = {
                    "bbox": [x1, y1, x2, y2],
                    "confidence": confidence,
                    "age": demographics.get("age"),
                    "gender": demographics.get("gender"),
                    "ethnicity": demographics.get("ethnicity"),
                    "demographics_details": demographics,
                    "clothing_description": clothing_description,
                    "body_features": body_features,
                }

                person_record, db_error = self._create_or_update_person(
                    person_tracking_id=person_tracking_id,
                    video_id=video_id,
                    timestamp=timestamp,
                    detection_data=detection_data,
                    frame=frame,
                )
                if db_error:
                    logger.error("Failed to persist person record", extra={"context": {"error": str(db_error)}})
                    continue

                metadata = {
                    "video_id": video_id,
                    "frame_number": frame_number,
                    "first_seen": int(timestamp.timestamp()),
                    "confidence": confidence,
                }

                body_vector = body_embedding.tolist() if body_embedding is not None else None
                face_vector = face_embedding.tolist() if face_embedding is not None else None

                if body_embedding is not None:
                    success, error = self.chromadb_manager.add_body_embedding(
                        person_tracking_id,
                        body_embedding,
                        metadata,
                    )
                    if error or not success:
                        logger.warning(
                            "Failed to store body embedding",
                            extra={"context": {"person_id": person_tracking_id, "error": str(error)}},
                        )

                if face_embedding is not None:
                    success, error = self.chromadb_manager.add_face_embedding(
                        person_tracking_id,
                        face_embedding,
                        metadata,
                    )
                    if error or not success:
                        logger.warning(
                            "Failed to store face embedding",
                            extra={"context": {"person_id": person_tracking_id, "error": str(error)}},
                        )

                demographics_payload = {
                    "age": {
                        "value": demographics.get("age"),
                        "confidence": demographics.get("age_confidence"),
                    },
                    "gender": {
                        "value": demographics.get("gender", "unknown"),
                        "confidence": demographics.get("gender_confidence"),
                    },
                    "ethnicity": {
                        "value": demographics.get("ethnicity", "unknown"),
                        "confidence": demographics.get("ethnicity_confidence"),
                    },
                    "overall_confidence": demographics.get("confidence", 0.0),
                }

                details_payload = {
                    "clothing_description": clothing_description,
                    "body_features": body_features,
                    "embeddings": {
                        "face": face_vector or [],
                        "body": body_vector or [],
                    },
                    "demographics_raw": demographics,
                    "first_seen": person_record.first_seen.isoformat() if person_record else None,
                    "last_seen": person_record.last_seen.isoformat() if person_record else None,
                    "total_appearances": person_record.total_appearances if person_record else 0,
                }

                processed_persons.append(
                    {
                        "person_id": person_tracking_id,
                        "db_id": person_record.id if person_record else None,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": confidence,
                        "demographics": demographics_payload,
                        "details": details_payload,
                    }
                )

            return processed_persons, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Person detection failed", extra={"context": {"error": str(exc)}})
            return [], exc

    def find_similar_persons(
        self,
        person_id: str,
        time_window_hours: int = 2,
        top_k: int = 10,
    ) -> Tuple[List[Dict], Optional[Exception]]:
        try:
            person = Person.query.filter_by(id=person_id).first()
            if person is None:
                return [], PersonDetectionError("Person not found")

            face_embedding = self._get_embedding_from_chroma(
                person.person_tracking_id,
                embedding_type="face",
            )
            body_embedding = self._get_embedding_from_chroma(
                person.person_tracking_id,
                embedding_type="body",
            )

            combined_results: Dict[str, Dict] = {}

            if face_embedding is not None:
                face_matches, _ = self.chromadb_manager.search_similar_faces(
                    face_embedding,
                    n_results=top_k,
                    time_window_hours=time_window_hours,
                )
                self._merge_similarity_results(combined_results, face_matches, weight=0.6)

            if body_embedding is not None:
                body_matches, _ = self.chromadb_manager.search_similar_bodies(
                    body_embedding,
                    n_results=top_k,
                    time_window_hours=time_window_hours,
                )
                self._merge_similarity_results(combined_results, body_matches, weight=0.4)

            sorted_matches = sorted(
                combined_results.values(),
                key=lambda item: item["score"],
                reverse=True,
            )[:top_k]

            for match in sorted_matches:
                related_person = Person.query.filter_by(
                    person_tracking_id=match["person_tracking_id"]
                ).first()
                if related_person:
                    match["person"] = related_person.to_dict()

            return sorted_matches, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to find similar persons", extra={"context": {"error": str(exc)}})
            return [], exc

    def get_person_details(self, person_id: str) -> Tuple[Optional[Dict], Optional[Exception]]:
        try:
            person = Person.query.filter_by(id=person_id).first()
            if person is None:
                return None, PersonDetectionError("Person not found")

            person_data = person.to_dict()
            person_data["embeddings"] = {"face": [], "body": []}

            face_embedding = self._get_embedding_from_chroma(
                person.person_tracking_id,
                embedding_type="face",
            )
            body_embedding = self._get_embedding_from_chroma(
                person.person_tracking_id,
                embedding_type="body",
            )

            if face_embedding is not None:
                person_data["embeddings"]["face"] = face_embedding.tolist()

            if body_embedding is not None:
                person_data["embeddings"]["body"] = body_embedding.tolist()

            return person_data, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to retrieve person details", extra={"context": {"error": str(exc)}})
            return None, exc

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _run_yolo_detection(self, frame: np.ndarray) -> List[Dict]:
        detections: List[Dict] = []

        if hasattr(self.yolo_model, "predict"):
            results = self.yolo_model.predict(frame, classes=[0])  # type: ignore[attr-defined]
        else:
            results = self.yolo_model(frame, classes=[0])  # type: ignore[operator]

        if not results:
            return detections

        first_result = results[0]

        boxes = getattr(first_result, "boxes", None)
        if boxes is None and hasattr(first_result, "pred"):
            boxes = first_result.pred[0]

        if boxes is None:
            return detections

        if hasattr(boxes, "xyxy"):
            for bbox, score in zip(boxes.xyxy, boxes.conf):
                detections.append(
                    {
                        "bbox": bbox.tolist(),
                        "confidence": float(score),
                    }
                )
        else:
            for row in boxes:
                if len(row) >= 6:
                    x1, y1, x2, y2, conf, cls = row[:6]
                    if int(cls) != 0:
                        continue
                    detections.append(
                        {
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "confidence": float(conf),
                        }
                    )

        detections.sort(key=lambda item: item["confidence"], reverse=True)
        return detections

    @staticmethod
    def _clip_bbox(bbox: List[float], width: int, height: int) -> Tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(int(x1), width - 1))
        y1 = max(0, min(int(y1), height - 1))
        x2 = max(0, min(int(x2), width - 1))
        y2 = max(0, min(int(y2), height - 1))
        if x2 <= x1:
            x2 = min(width - 1, x1 + 1)
        if y2 <= y1:
            y2 = min(height - 1, y1 + 1)
        return x1, y1, x2, y2

    def _extract_body_embedding(self, person_crop: np.ndarray) -> Optional[np.ndarray]:
        if self.osnet_extractor is None:
            return None

        try:
            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            embeddings = self.osnet_extractor([rgb_crop])  # type: ignore[operator]
            if isinstance(embeddings, torch.Tensor):
                embedding_tensor = embeddings[0]
            else:
                embedding_tensor = embeddings[0]
            normalized = torch.nn.functional.normalize(
                embedding_tensor,
                p=2,
                dim=0,
            )
            return normalized.detach().cpu().numpy()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to compute body embedding: %s", exc)
            return None

    @staticmethod
    def _default_demographics() -> Dict:
        return {
            "age": None,
            "age_confidence": None,
            "gender": "unknown",
            "gender_confidence": 0.0,
            "ethnicity": "unknown",
            "ethnicity_confidence": 0.0,
            "confidence": 0.0,
        }

    def _process_face(self, person_crop: np.ndarray) -> Tuple[Optional[np.ndarray], Dict]:
        if self.mtcnn_detector is None or self.arcface_model is None:
            return None, self._default_demographics()

        try:
            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            detections = self.mtcnn_detector.detect(rgb_crop)
            if detections is None:
                return None, self._default_demographics()

            boxes, probs = detections
            if boxes is None or probs is None or len(boxes) == 0:
                return None, self._default_demographics()

            best_index = int(np.argmax(probs))
            if probs[best_index] < self.face_confidence:
                demographics = self._default_demographics()
                demographics["confidence"] = float(probs[best_index])
                return None, demographics

            x1, y1, x2, y2 = boxes[best_index].astype(int)
            h, w = rgb_crop.shape[:2]
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w - 1))
            y2 = max(0, min(y2, h - 1))
            face_image = rgb_crop[y1:y2, x1:x2]
            if face_image.size == 0:
                demographics = self._default_demographics()
                demographics["confidence"] = float(probs[best_index])
                return None, demographics

            face_tensor = self._prepare_face_tensor(face_image)
            with torch.no_grad():
                embedding = (
                    self.arcface_model(face_tensor.to(self.device))
                    .detach()
                    .cpu()
                    .numpy()
                    .reshape(-1)
                )

            demographics = self._detect_demographics(face_image)
            return embedding, demographics
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Face processing failed: %s", exc)
            return None, self._default_demographics()

    def _prepare_face_tensor(self, face_image: np.ndarray) -> torch.Tensor:
        resized = cv2.resize(face_image, (160, 160))
        tensor = torch.from_numpy(resized).float() / 255.0
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        return tensor

    def _detect_demographics(self, face_crop: np.ndarray) -> Dict:
        try:
            if (
                self.demographics_backend == "mivolo"
                and self.mivolo_model is not None
                and self.mivolo_processor is not None
            ):
                demographics = self._detect_demographics_mivolo(face_crop)
                if demographics:
                    return demographics
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("MiVOLO inference failed: %s", exc)

        try:
            if self.deepface is not None:
                return self._detect_demographics_deepface(face_crop)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("DeepFace inference failed: %s", exc)

        return self._default_demographics()

    def _detect_demographics_mivolo(self, face_crop: np.ndarray) -> Optional[Dict]:
        if self.mivolo_processor is None or self.mivolo_model is None:
            return None

        image = Image.fromarray(face_crop)
        inputs = self.mivolo_processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self.mivolo_model(**inputs)

        parsed = self._parse_mivolo_outputs(outputs)
        if parsed is None:
            return None

        parsed.setdefault("confidence", max(parsed.get("gender_confidence", 0.0), parsed.get("ethnicity_confidence", 0.0)))
        return parsed

    def _detect_demographics_deepface(self, face_crop: np.ndarray) -> Dict:
        if self.deepface is None:
            return self._default_demographics()

        bgr_face = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
        models = self.deepface_models if self.deepface_models else None
        analysis = self.deepface.analyze(  # type: ignore[attr-defined]
            bgr_face,
            actions=("age", "gender", "race"),
            enforce_detection=False,
            detector_backend="skip",
            models=models,
        )

        if isinstance(analysis, list):
            analysis = analysis[0] if analysis else {}

        demographics = self._default_demographics()

        if not isinstance(analysis, dict):
            return demographics

        age_value = analysis.get("age")
        if isinstance(age_value, (int, float)):
            demographics["age"] = int(max(0, min(120, round(age_value))))

        gender_label = analysis.get("dominant_gender")
        gender_scores = analysis.get("gender", {})
        gender_confidence = 0.0
        if isinstance(gender_scores, dict) and gender_label in gender_scores:
            try:
                gender_confidence = float(gender_scores[gender_label]) / 100.0
            except (TypeError, ValueError):
                gender_confidence = 0.0
        demographics["gender_confidence"] = min(max(gender_confidence, 0.0), 1.0)
        if isinstance(gender_label, str):
            demographics["gender"] = gender_label.lower()

        ethnicity_label = analysis.get("dominant_race")
        race_scores = analysis.get("race", {})
        ethnicity_confidence = 0.0
        if isinstance(race_scores, dict) and ethnicity_label in race_scores:
            try:
                ethnicity_confidence = float(race_scores[ethnicity_label]) / 100.0
            except (TypeError, ValueError):
                ethnicity_confidence = 0.0
        demographics["ethnicity_confidence"] = min(max(ethnicity_confidence, 0.0), 1.0)
        if isinstance(ethnicity_label, str):
            demographics["ethnicity"] = ethnicity_label.lower()

        demographics["confidence"] = max(
            demographics.get("gender_confidence", 0.0),
            demographics.get("ethnicity_confidence", 0.0),
        )
        return demographics

    def _parse_mivolo_outputs(self, outputs) -> Optional[Dict]:
        if outputs is None:
            return None

        if isinstance(outputs, dict):
            output_dict = outputs
        else:
            try:
                output_dict = dict(outputs)
            except Exception:  # pylint: disable=broad-except
                output_dict = getattr(outputs, "__dict__", {})

        gender_tensor = self._extract_tensor(output_dict, ["logits_gender", "gender_logits", "gender"])
        ethnicity_tensor = self._extract_tensor(
            output_dict,
            ["logits_ethnicity", "logits_race", "ethnicity_logits", "race_logits"],
        )
        age_tensor = self._extract_tensor(output_dict, ["logits_age", "age", "age_logits"])

        demographics = self._default_demographics()

        if age_tensor is not None:
            age_array = age_tensor.detach().cpu().float().flatten()
            if age_array.numel() > 0:
                age_value = float(age_array.mean().item())
                demographics["age"] = int(max(0, min(120, round(age_value))))

        if gender_tensor is not None:
            gender_probs = F.softmax(gender_tensor.squeeze(), dim=-1)
            gender_idx = int(torch.argmax(gender_probs).item())
            label_map = self._resolve_label_map(
                getattr(self.mivolo_model, "config", None),
                ["gender_id2label", "gender_labels"],
                fallback=["female", "male"],
            )
            demographics["gender"] = label_map.get(gender_idx, "unknown").lower()
            demographics["gender_confidence"] = float(gender_probs[gender_idx].item())

        if ethnicity_tensor is not None:
            ethnicity_probs = F.softmax(ethnicity_tensor.squeeze(), dim=-1)
            ethnicity_idx = int(torch.argmax(ethnicity_probs).item())
            label_map = self._resolve_label_map(
                getattr(self.mivolo_model, "config", None),
                ["ethnicity_id2label", "race_id2label", "ethnicity_labels", "race_labels"],
                fallback=["asian", "black", "hispanic", "indian", "middle eastern", "white", "other"],
            )
            demographics["ethnicity"] = label_map.get(ethnicity_idx, "unknown").lower()
            demographics["ethnicity_confidence"] = float(ethnicity_probs[ethnicity_idx].item())

        if demographics == self._default_demographics():
            return None

        demographics["confidence"] = max(
            demographics.get("gender_confidence", 0.0),
            demographics.get("ethnicity_confidence", 0.0),
        )
        return demographics

    @staticmethod
    def _extract_tensor(output_dict: Dict, keys: List[str]) -> Optional[torch.Tensor]:
        for key in keys:
            if key not in output_dict:
                continue
            value = output_dict[key]
            if isinstance(value, (list, tuple)) and value:
                value = value[0]
            if isinstance(value, torch.Tensor):
                return value
        return None

    @staticmethod
    def _resolve_label_map(config, keys: List[str], fallback: Optional[List[str]] = None) -> Dict[int, str]:
        if config is not None:
            for key in keys:
                label_map = getattr(config, key, None)
                if not label_map:
                    continue
                if isinstance(label_map, dict):
                    return {int(k): str(v) for k, v in label_map.items()}
                if isinstance(label_map, list):
                    return {idx: str(value) for idx, value in enumerate(label_map)}
        if fallback:
            return {idx: str(value) for idx, value in enumerate(fallback)}
        return {}

    def _describe_clothing(self, person_crop: np.ndarray) -> str:
        if person_crop.size == 0:
            return "Unknown clothing"

        try:
            resized = cv2.resize(person_crop, (64, 128))
            data = resized.reshape(-1, 3)
            data = np.float32(data)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(data, 3, None, criteria, 3, cv2.KMEANS_RANDOM_CENTERS)
            counts = np.bincount(labels.flatten())
            dominant = centers[np.argmax(counts)].astype(int)
            r, g, b = dominant
            brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            tone = "Light" if brightness > 0.6 else "Dark" if brightness < 0.3 else "Neutral"
            return f"{tone} clothing"
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Clothing description fallback: %s", exc)
            return "Unknown clothing"

    def _extract_body_features(self, person_crop: np.ndarray) -> Dict[str, float | str]:
        height, width = person_crop.shape[:2]
        height_ratio = round(height / max(width, 1), 2)
        aspect_ratio = round(width / max(height, 1), 2)
        position = "center"
        return {
            "height_ratio": height_ratio,
            "aspect_ratio": aspect_ratio,
            "position": position,
        }

    def _create_or_update_person(
        self,
        person_tracking_id: str,
        video_id: str,
        timestamp: datetime,
        detection_data: Dict,
        frame: np.ndarray,
    ) -> Tuple[Optional[Person], Optional[Exception]]:
        try:
            person = Person.query.filter_by(
                person_tracking_id=person_tracking_id,
                video_id=video_id,
            ).first()

            if person is None:
                person = Person(
                    video_id=video_id,
                    person_tracking_id=person_tracking_id,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    total_appearances=1,
                    age_estimate=detection_data.get("age"),
                    gender=detection_data.get("gender"),
                    ethnicity=detection_data.get("ethnicity"),
                    confidence_score=detection_data.get("confidence"),
                    clothing_description=detection_data.get("clothing_description"),
                    body_features=detection_data.get("body_features"),
                )
                person.set_person_ttl()
                if self.save_thumbnails:
                    thumbnail_path = self._save_person_thumbnail(
                        frame,
                        detection_data["bbox"],
                        person_tracking_id,
                    )
                    person.thumbnail_path = thumbnail_path
                db.session.add(person)
            else:
                person.update_last_seen(timestamp)
                if detection_data.get("confidence"):
                    person.confidence_score = max(
                        person.confidence_score or 0.0,
                        detection_data.get("confidence") or 0.0,
                    )
                if detection_data.get("age") is not None:
                    person.age_estimate = detection_data.get("age")
                if detection_data.get("gender"):
                    person.gender = detection_data.get("gender")
                if detection_data.get("ethnicity"):
                    person.ethnicity = detection_data.get("ethnicity")
                person.clothing_description = detection_data.get("clothing_description")
                person.body_features = detection_data.get("body_features")

            db.session.commit()
            return person, None
        except StorageError as exc:
            db.session.rollback()
            logger.error("Failed to save person thumbnail: %s", exc)
            return None, exc
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            logger.exception("Failed to persist person", extra={"context": {"error": str(exc)}})
            return None, exc

    def _save_person_thumbnail(
        self,
        frame: np.ndarray,
        bbox: List[int],
        person_tracking_id: str,
    ) -> Optional[str]:
        if not self.save_thumbnails:
            return None

        x1, y1, x2, y2 = bbox
        cropped = frame[y1:y2, x1:x2]
        if cropped.size == 0:
            return None

        persons_dir = self.storage_base_path / "persons"
        persons_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_path = persons_dir / f"{person_tracking_id}_thumb.jpg"
        cv2.imwrite(str(thumbnail_path), cropped)
        return str(thumbnail_path.relative_to(self.storage_base_path.parent))

    def _get_embedding_from_chroma(
        self,
        person_tracking_id: str,
        embedding_type: str,
    ) -> Optional[np.ndarray]:
        collection = None
        if embedding_type == "face":
            collection = getattr(self.chromadb_manager, "face_collection", None)
        elif embedding_type == "body":
            collection = getattr(self.chromadb_manager, "body_collection", None)

        if collection is None:
            return None

        records = collection.get(ids=[person_tracking_id], include=["embeddings"])
        if not records or not records.get("embeddings"):
            return None
        embeddings = records["embeddings"][0]
        if not embeddings:
            return None
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            embeddings = embeddings[0]
        array = np.asarray(embeddings, dtype=np.float32).reshape(-1)
        if array.shape[0] != 512:
            logger.warning(
                "Unexpected embedding dimensionality from ChromaDB",
                extra={"context": {"person_tracking_id": person_tracking_id, "dim": array.shape[0]}},
            )
            return None
        return array

    @staticmethod
    def _merge_similarity_results(
        accumulator: Dict[str, Dict],
        matches: List[Dict],
        weight: float,
    ) -> None:
        for match in matches:
            tracking_id = match["person_id"]
            score = match.get("similarity", 0.0) * weight
            if tracking_id not in accumulator:
                accumulator[tracking_id] = {
                    "person_tracking_id": tracking_id,
                    "score": 0.0,
                }
            accumulator[tracking_id]["score"] += score

