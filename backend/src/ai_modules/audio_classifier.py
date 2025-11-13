from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple

import librosa
import numpy as np
import soundfile

from src.config.constants import AudioCategory, UrgencyLevel
from src.config.settings import get_config
from src.utils.model_manager import ModelManager

logger = logging.getLogger(__name__)


class AudioClassificationError(Exception):
    """Raised when audio classification fails."""


class AudioClassifierService:
    """Service responsible for audio event classification using YAMNet."""

    _instance: Optional["AudioClassifierService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[object] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.config = config or get_config()

        self.audio_confidence_threshold = getattr(self.config, "AUDIO_CLASSIFICATION_CONFIDENCE", 0.5)
        self.max_sounds_per_segment = getattr(self.config, "MAX_SOUNDS_PER_SEGMENT", 5)

        self.model_manager = ModelManager(config=self.config)
        self.yamnet_model = None
        self.yamnet_class_names = None

        self.urgency_mappings = self._build_urgency_mappings()

        self._models_loaded = False
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Model management
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        if self._models_loaded:
            return

        start_time = time.time()
        logger.info("Loading YAMNet model for audio classification")

        try:
            yamnet_path, error = self.model_manager.download_yamnet_model()
            if error:
                logger.warning(
                    "YAMNet model download failed",
                    extra={"context": {"error": str(error)}},
                )
                self.yamnet_model = None
            else:
                import tensorflow_hub as hub  # type: ignore

                yamnet_model_url = getattr(self.config, "YAMNET_MODEL_URL", "https://tfhub.dev/google/yamnet/1")
                self.yamnet_model = hub.load(yamnet_model_url)

                # Load class names from YAMNet using built-in class_names attribute
                try:
                    # YAMNet model has a class_names method/attribute
                    if hasattr(self.yamnet_model, "class_names"):
                        self.yamnet_class_names = self.yamnet_model.class_names
                    elif callable(getattr(self.yamnet_model, "class_names", None)):
                        self.yamnet_class_names = self.yamnet_model.class_names()
                    else:
                        # Try to get class names from the model's assets
                        resolved_path = hub.resolve(yamnet_model_url)
                        class_map_path = str(resolved_path) + "/yamnet_class_map.csv"
                        try:
                            # Try reading CSV directly without pandas
                            import csv
                            with open(class_map_path, "r", encoding="utf-8") as f:
                                reader = csv.DictReader(f)
                                # Extract display_name column
                                self.yamnet_class_names = [row.get("display_name", "").strip() for row in reader]
                                # Ensure we have 521 classes
                                if len(self.yamnet_class_names) < 521:
                                    self.yamnet_class_names.extend([f"class_{i}" for i in range(len(self.yamnet_class_names), 521)])
                        except Exception:  # pylint: disable=broad-except
                            # Fallback: use index-based names
                            self.yamnet_class_names = [f"class_{i}" for i in range(521)]
                            logger.warning("Could not load YAMNet class names, using index-based names")
                except Exception:  # pylint: disable=broad-except
                    # Fallback: use index-based names if class names not available
                    self.yamnet_class_names = [f"class_{i}" for i in range(521)]
                    logger.warning("Could not load YAMNet class names, using index-based names")

                elapsed = (time.time() - start_time) * 1000
                logger.info(
                    "YAMNet model loaded",
                    extra={"context": {"load_time_ms": round(elapsed, 2)}},
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to load YAMNet model",
                extra={"context": {"error": str(exc)}},
            )
            self.yamnet_model = None
            self.yamnet_class_names = None

        self._models_loaded = True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def classify_audio(self, audio_path: str) -> Tuple[Dict, Optional[Exception]]:
        """Classify audio events using YAMNet.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (classification_dict, error)
        """
        try:
            if not self._models_loaded:
                self._load_models()

            if self.yamnet_model is None:
                logger.warning("YAMNet model unavailable, using fallback classification")
                return self._fallback_classification(), None

            # Load audio file
            try:
                audio, sr = soundfile.read(audio_path)
            except Exception as exc:
                logger.exception(
                    "Failed to load audio file",
                    extra={"context": {"audio_path": audio_path, "error": str(exc)}},
                )
                return {}, AudioClassificationError(f"Failed to load audio file: {exc}")

            # Convert to mono if stereo
            # soundfile.read returns (n_samples, n_channels) shape for multi-channel audio
            if audio.ndim == 2:
                # Audio is (n_samples, n_channels), average across channels
                audio = audio.mean(axis=1)
            elif audio.ndim > 2:
                # For other multi-dimensional audio, use librosa
                audio = librosa.to_mono(audio)

            # Resample to 16kHz (YAMNet requirement)
            if sr != 16000:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

            # Run YAMNet inference
            try:
                scores, embeddings, spectrogram = self.yamnet_model(audio)
                scores = scores.numpy()  # Convert TensorFlow tensor to numpy
            except Exception as exc:
                logger.exception(
                    "YAMNet inference failed",
                    extra={"context": {"audio_path": audio_path, "error": str(exc)}},
                )
                return {}, AudioClassificationError(f"YAMNet inference failed: {exc}")

            # Process each segment (0.96s windows)
            detected_sounds: List[Dict] = []
            num_segments = scores.shape[0]

            for i in range(num_segments):
                segment_scores = scores[i]

                # Get top-k classes
                top_indices = np.argsort(segment_scores)[-self.max_sounds_per_segment :][::-1]

                for class_idx in top_indices:
                    confidence = float(segment_scores[class_idx])

                    # Filter by confidence threshold
                    if confidence < self.audio_confidence_threshold:
                        continue

                    # Get class name
                    if self.yamnet_class_names and class_idx < len(self.yamnet_class_names):
                        class_name = self.yamnet_class_names[class_idx]
                    else:
                        class_name = f"class_{class_idx}"

                    # Map class to urgency level
                    urgency_level, category = self._map_class_to_urgency(class_name)

                    # Calculate timestamp
                    timestamp = i * 0.96  # YAMNet uses 0.96s segments

                    # Create sound dict
                    sound_dict = {
                        "sound_id": f"sound_{uuid.uuid4()}",
                        "class_name": class_name,
                        "category": category,
                        "urgency_level": urgency_level,
                        "confidence": confidence,
                        "timestamp": timestamp,
                        "duration": 0.96,
                    }

                    detected_sounds.append(sound_dict)

            # Calculate urgency summary
            urgency_summary = self._calculate_urgency_summary(detected_sounds)

            # Estimate ambient noise level
            ambient_level = self._estimate_ambient_noise(audio, 16000)

            # Calculate overall confidence (average of detected sound confidences)
            confidence = 0.0
            if detected_sounds:
                confidence = np.mean([sound["confidence"] for sound in detected_sounds])

            # Build result dict
            result_dict = {
                "detected_sounds": detected_sounds,
                "urgency_summary": urgency_summary,
                "ambient_noise_level": ambient_level,
                "confidence": float(confidence),
            }

            return result_dict, None

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Audio classification processing failed",
                extra={"context": {"audio_path": audio_path, "error": str(exc)}},
            )
            return {}, AudioClassificationError(f"Audio classification processing failed: {exc}")

    # ------------------------------------------------------------------ #
    # Private helper methods
    # ------------------------------------------------------------------ #
    def _build_urgency_mappings(self) -> Dict[str, Dict]:
        """Build static mapping of YAMNet class names to urgency levels.

        Returns:
            Dict mapping class name patterns to urgency and category
        """
        return {
            # Critical urgency
            "Gunshot, gunfire": {"urgency": UrgencyLevel.CRITICAL, "category": AudioCategory.VIOLENCE},
            "Gunshot": {"urgency": UrgencyLevel.CRITICAL, "category": AudioCategory.VIOLENCE},
            "Explosion": {"urgency": UrgencyLevel.CRITICAL, "category": AudioCategory.VIOLENCE},
            # High urgency
            "Screaming": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.DISTRESS},
            "Scream": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.DISTRESS},
            # Medium urgency
            "Alarm": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.ALERT},
            "Fire alarm": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.ALERT},
            # High urgency (other alerts)
            "Siren": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.ALERT},
            "Glass": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.BREAKING},
            "Yell": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.DISTRESS},
            "Yelling": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.DISTRESS},
            "Shouting": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.DISTRESS},
            "Crash": {"urgency": UrgencyLevel.HIGH, "category": AudioCategory.BREAKING},
            # Medium urgency
            "Dog": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.ANIMAL},
            "Car horn": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.VEHICLE},
            "Door": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.IMPACT},
            "Footsteps": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.MOVEMENT},
            "Running": {"urgency": UrgencyLevel.MEDIUM, "category": AudioCategory.MOVEMENT},
            # Low urgency
            "Music": {"urgency": UrgencyLevel.LOW, "category": AudioCategory.AMBIENT},
            "Speech": {"urgency": UrgencyLevel.LOW, "category": AudioCategory.COMMUNICATION},
            "Vehicle": {"urgency": UrgencyLevel.LOW, "category": AudioCategory.AMBIENT},
            "Ambient": {"urgency": UrgencyLevel.LOW, "category": AudioCategory.AMBIENT},
        }

    def _map_class_to_urgency(self, class_name: str) -> Tuple[str, str]:
        """Map YAMNet class name to urgency level and category.

        Args:
            class_name: YAMNet class name

        Returns:
            Tuple of (urgency_level, category)
        """
        class_name_lower = class_name.lower()

        # Check for exact or partial matches
        for mapping_key, mapping_value in self.urgency_mappings.items():
            if mapping_key.lower() in class_name_lower or class_name_lower in mapping_key.lower():
                return mapping_value["urgency"], mapping_value["category"]

        # Default: low urgency, ambient category
        return UrgencyLevel.LOW, AudioCategory.AMBIENT

    def _calculate_urgency_summary(self, detected_sounds: List[Dict]) -> Dict:
        """Calculate urgency summary from detected sounds.

        Args:
            detected_sounds: List of detected sound dicts

        Returns:
            Urgency summary dict
        """
        critical_count = len([s for s in detected_sounds if s["urgency_level"] == UrgencyLevel.CRITICAL])
        high_count = len([s for s in detected_sounds if s["urgency_level"] == UrgencyLevel.HIGH])
        medium_count = len([s for s in detected_sounds if s["urgency_level"] == UrgencyLevel.MEDIUM])
        low_count = len([s for s in detected_sounds if s["urgency_level"] == UrgencyLevel.LOW])

        # Determine max urgency
        max_urgency = UrgencyLevel.LOW
        if critical_count > 0:
            max_urgency = UrgencyLevel.CRITICAL
        elif high_count > 0:
            max_urgency = UrgencyLevel.HIGH
        elif medium_count > 0:
            max_urgency = UrgencyLevel.MEDIUM

        return {
            "max_urgency": max_urgency,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "total_sounds": len(detected_sounds),
        }

    def _estimate_ambient_noise(self, audio: np.ndarray, sr: int) -> str:
        """Estimate ambient noise level from audio.

        Args:
            audio: Audio array
            sr: Sample rate

        Returns:
            Noise level string (high|moderate|low|very_low)
        """
        try:
            # Calculate RMS energy
            rms = librosa.feature.rms(y=audio)
            mean_rms = float(np.mean(rms))

            # Classify noise level
            if mean_rms > 0.1:
                return "high"
            elif mean_rms > 0.05:
                return "moderate"
            elif mean_rms > 0.01:
                return "low"
            else:
                return "very_low"
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Ambient noise estimation failed",
                extra={"context": {"error": str(exc)}},
            )
            return "unknown"

    def _fallback_classification(self) -> Dict:
        """Return empty classification when YAMNet unavailable.

        Returns:
            Empty classification dict
        """
        logger.warning("Using fallback classification (YAMNet unavailable)")
        return {
            "detected_sounds": [],
            "urgency_summary": {
                "max_urgency": UrgencyLevel.LOW,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "total_sounds": 0,
            },
            "ambient_noise_level": "unknown",
            "confidence": 0.0,
        }

