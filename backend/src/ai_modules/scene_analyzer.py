from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image

from src.config.constants import (
    CrowdDensity,
    LightingCondition,
    SceneType,
    WeatherCondition,
)
from src.config.settings import get_config
from src.utils.model_manager import ModelManager

logger = logging.getLogger(__name__)


class SceneAnalysisError(Exception):
    """Raised when scene analysis fails."""


class SceneAnalyzerService:
    """Service responsible for scene understanding using BLIP-2."""

    _instance: Optional["SceneAnalyzerService"] = None

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

        self.scene_confidence_threshold = getattr(self.config, "SCENE_CONFIDENCE_THRESHOLD", 0.7)
        self.blip2_model_name = getattr(self.config, "BLIP2_MODEL_NAME", "Salesforce/blip2-opt-2.7b")
        self.max_caption_length = getattr(self.config, "BLIP2_MAX_LENGTH", 100)
        self.blip2_prompt = getattr(
            self.config,
            "BLIP2_PROMPT",
            "Describe the scene in one sentence highlighting environment, lighting, weather, and crowd.",
        )
        self.use_fallback = getattr(self.config, "USE_SCENE_FALLBACK", True)

        self.model_manager = ModelManager(config=self.config)

        self.blip2_processor = None
        self.blip2_model = None

        self._models_loaded = False
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Model management
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        if self._models_loaded:
            return

        logger.info("Loading BLIP-2 models for scene analysis")
        start_time = perf_counter()

        try:
            blip2_path, error = self.model_manager.download_blip2_model(model_name=self.blip2_model_name)
            if error:
                logger.warning(
                    "BLIP-2 download failed; falling back to rule-based scene analysis",
                    extra={"context": {"error": str(error)}},
                )
                self.blip2_processor = None
                self.blip2_model = None
            elif blip2_path is not None:
                cache_dir = str(Path(blip2_path).parent)
                from transformers import (  # type: ignore
                    Blip2ForConditionalGeneration,
                    Blip2Processor,
                )

                self.blip2_processor = Blip2Processor.from_pretrained(
                    self.blip2_model_name,
                    cache_dir=cache_dir,
                )
                self.blip2_model = (
                    Blip2ForConditionalGeneration.from_pretrained(
                        self.blip2_model_name,
                        cache_dir=cache_dir,
                    )
                    .to(self.device)
                    .eval()
                )
                for param in self.blip2_model.parameters():
                    param.requires_grad = False
                logger.info(
                    "BLIP-2 models loaded for scene analysis",
                    extra={"context": {"device": self.device}},
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to load BLIP-2 models; enabling fallback mode",
                extra={"context": {"error": str(exc)}},
            )
            self.blip2_processor = None
            self.blip2_model = None
        finally:
            duration = perf_counter() - start_time
            logger.debug(
                "Scene analyzer model loading completed",
                extra={"context": {"duration_seconds": round(duration, 2)}},
            )
            self._models_loaded = True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze_scene(self, frame: np.ndarray) -> Tuple[Dict, Optional[Exception]]:
        if frame is None or frame.size == 0:
            return {}, SceneAnalysisError("Empty frame provided for scene analysis")

        try:
            if not self._models_loaded:
                self._load_models()

            if self.blip2_model is None or self.blip2_processor is None:
                if self.use_fallback:
                    logger.debug("Using fallback scene analysis due to unavailable BLIP-2 model")
                    return self._fallback_scene_analysis(frame), None
                raise SceneAnalysisError("BLIP-2 model unavailable for scene analysis")

            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            inputs = self.blip2_processor(
                images=image,
                text=self.blip2_prompt,
                return_tensors="pt",
            )
            inputs = {key: value.to(self.device) for key, value in inputs.items()}

            with torch.no_grad():
                generated_ids = self.blip2_model.generate(
                    **inputs,
                    max_length=int(self.max_caption_length),
                )

            caption = self.blip2_processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0].strip()

            parsed = self._parse_scene_description(caption, frame)
            confidence = max(self.scene_confidence_threshold, parsed.get("confidence", 0.85))

            result = {
                "scene_type": parsed["scene_type"],
                "lighting": parsed["lighting"],
                "weather": parsed["weather"],
                "crowd_density": parsed["crowd_density"],
                "description": caption,
                "environment_details": {
                    "location_type": parsed["location_type"],
                    "time_of_day": parsed["time_of_day"],
                    "visibility": parsed["visibility"],
                },
                "confidence": float(min(max(confidence, 0.0), 1.0)),
            }

            logger.debug(
                "Scene analysis completed",
                extra={
                    "context": {
                        "scene_type": result["scene_type"],
                        "lighting": result["lighting"],
                        "crowd_density": result["crowd_density"],
                        "confidence": result["confidence"],
                    }
                },
            )

            return result, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Scene analysis failed", extra={"context": {"error": str(exc)}})
            if self.use_fallback:
                return self._fallback_scene_analysis(frame), exc
            return {}, exc

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _parse_scene_description(self, caption: str, frame: np.ndarray) -> Dict:
        caption_lower = caption.lower()
        brightness = self._calculate_frame_brightness(frame)

        scene_type = self._determine_scene_type(caption_lower, brightness)
        lighting = self._determine_lighting(caption_lower, brightness)
        weather = self._determine_weather(caption_lower)
        crowd_density = self._determine_crowd_density(caption_lower)
        location_type = self._classify_location_type(caption_lower)
        time_of_day = self._estimate_time_of_day(frame, caption_lower)
        visibility = self._determine_visibility(lighting, weather)

        confidence = 0.9 if self.blip2_model is not None else 0.5

        return {
            "scene_type": scene_type,
            "lighting": lighting,
            "weather": weather,
            "crowd_density": crowd_density,
            "location_type": location_type,
            "time_of_day": time_of_day,
            "visibility": visibility,
            "confidence": confidence,
        }

    def _fallback_scene_analysis(self, frame: np.ndarray) -> Dict:
        brightness = self._calculate_frame_brightness(frame)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_frame, 100, 200)
        edge_density = float(np.mean(edges > 0))
        scene_type = SceneType.OUTDOOR if edge_density > 0.05 else SceneType.INDOOR

        if brightness > 0.6:
            lighting = LightingCondition.BRIGHT
        elif brightness > 0.3:
            lighting = LightingCondition.DIM
        else:
            lighting = LightingCondition.DARK

        fallback_result = {
            "scene_type": scene_type,
            "lighting": lighting,
            "weather": WeatherCondition.UNKNOWN,
            "crowd_density": CrowdDensity.SPARSE,
            "description": "Fallback scene analysis based on basic frame heuristics.",
            "environment_details": {
                "location_type": "unknown",
                "time_of_day": self._estimate_time_of_day(frame, ""),
                "visibility": "poor"
                if lighting in (LightingCondition.DARK, LightingCondition.NIGHT)
                else "good",
            },
            "confidence": 0.5,
        }
        return fallback_result

    def _determine_scene_type(self, caption_lower: str, brightness: float) -> str:
        indoor_keywords = ("indoor", "inside", "room", "office", "building", "hallway")
        outdoor_keywords = ("outdoor", "outside", "street", "parking", "park", "road", "alley", "sidewalk")

        if any(keyword in caption_lower for keyword in indoor_keywords):
            return SceneType.INDOOR
        if any(keyword in caption_lower for keyword in outdoor_keywords):
            return SceneType.OUTDOOR
        return SceneType.OUTDOOR if brightness > 0.55 else SceneType.UNKNOWN

    def _determine_lighting(self, caption_lower: str, brightness: float) -> str:
        if "night" in caption_lower or "dark" in caption_lower:
            return LightingCondition.NIGHT
        if "bright" in caption_lower or brightness >= 0.6:
            return LightingCondition.BRIGHT
        if "dim" in caption_lower or "low light" in caption_lower or 0.3 <= brightness < 0.6:
            return LightingCondition.DIM
        return LightingCondition.DARK if brightness < 0.3 else LightingCondition.BRIGHT

    def _determine_weather(self, caption_lower: str) -> str:
        if any(keyword in caption_lower for keyword in ("rain", "rainy", "drizzle", "storm")):
            return WeatherCondition.RAINY
        if any(keyword in caption_lower for keyword in ("fog", "foggy", "mist", "haze")):
            return WeatherCondition.FOGGY
        if any(keyword in caption_lower for keyword in ("snow", "snowy", "blizzard")):
            return WeatherCondition.SNOWY
        if any(keyword in caption_lower for keyword in ("sunny", "clear skies", "clear sky")):
            return WeatherCondition.CLEAR
        return WeatherCondition.UNKNOWN

    def _determine_crowd_density(self, caption_lower: str) -> str:
        if any(keyword in caption_lower for keyword in ("crowd", "crowded", "many people", "busy street", "packed")):
            return CrowdDensity.CROWDED
        if any(keyword in caption_lower for keyword in ("several people", "group of people", "people walking")):
            return CrowdDensity.MODERATE
        if any(keyword in caption_lower for keyword in ("few people", "some people", "couple of people", "sparse")):
            return CrowdDensity.SPARSE
        if any(keyword in caption_lower for keyword in ("no people", "empty", "nobody", "deserted")):
            return CrowdDensity.EMPTY
        return CrowdDensity.SPARSE

    def _determine_visibility(self, lighting: str, weather: str) -> str:
        if weather in (WeatherCondition.RAINY, WeatherCondition.FOGGY, WeatherCondition.SNOWY):
            return "very_poor"
        if lighting in (LightingCondition.NIGHT, LightingCondition.DARK):
            return "poor"
        if lighting == LightingCondition.DIM:
            return "poor"
        return "good"

    def _calculate_frame_brightness(self, frame: np.ndarray) -> float:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray) / 255.0)

    def _classify_location_type(self, caption_lower: str) -> str:
        if any(keyword in caption_lower for keyword in ("parking lot", "garage", "parking")):
            return "parking_lot"
        if any(keyword in caption_lower for keyword in ("street", "road", "sidewalk", "intersection")):
            return "street"
        if any(keyword in caption_lower for keyword in ("building", "office", "lobby", "conference")):
            return "building"
        if any(keyword in caption_lower for keyword in ("park", "garden", "field", "playground")):
            return "park"
        return "unknown"

    def _estimate_time_of_day(self, frame: np.ndarray, caption_lower: str) -> str:
        brightness = self._calculate_frame_brightness(frame)
        if "night" in caption_lower or brightness < 0.2:
            return "night"
        if any(keyword in caption_lower for keyword in ("dawn", "dusk", "sunset", "sunrise")) or brightness < 0.35:
            return "dusk"
        if any(keyword in caption_lower for keyword in ("day", "daytime", "sunny")) or brightness > 0.6:
            return "day"
        return "unknown"

