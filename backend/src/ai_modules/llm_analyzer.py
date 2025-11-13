"""LLM Analyzer service for threat assessment using Ollama."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import ValidationError

from src.config.settings import get_config
from src.schemas.llm_schemas import SuspicionAnalysis
from src.utils.model_manager import ModelManager
from src.utils.prompt_templates import (
    CHAIN_OF_THOUGHT_INSTRUCTION,
    FEW_SHOT_EXAMPLES,
    SITUATION_TEMPLATE,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMAnalysisError(Exception):
    """Raised when LLM analysis fails."""


class LLMAnalyzerService:
    """Service responsible for threat assessment using local LLM via Ollama."""

    _instance: Optional["LLMAnalyzerService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[object] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.config = config or get_config()

        self.ollama_host = getattr(self.config, "OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = getattr(self.config, "OLLAMA_MODEL", "llama3.2:1b")
        self.confidence_threshold = getattr(self.config, "LLM_CONFIDENCE_THRESHOLD", 0.7)
        self.max_tokens = getattr(self.config, "LLM_MAX_TOKENS", 500)
        self.temperature = getattr(self.config, "LLM_TEMPERATURE", 0.3)
        self.timeout = getattr(self.config, "LLM_TIMEOUT_SECONDS", 30)
        self.max_retries = getattr(self.config, "LLM_MAX_RETRIES", 2)
        self.use_chain_of_thought = getattr(self.config, "USE_CHAIN_OF_THOUGHT", True)
        self.use_few_shot = getattr(self.config, "USE_FEW_SHOT_EXAMPLES", True)
        self.enable_fallback = getattr(self.config, "ENABLE_RULE_BASED_FALLBACK", True)

        self.model_manager = ModelManager(config=self.config)
        self.ollama_client = None

        self._models_loaded = False
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Model management
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        """Load Ollama model for LLM inference."""
        if self._models_loaded:
            # Allow reattempt if client is None (previous load failed)
            if self.ollama_client is not None:
                return
            # Reset flag to allow retry
            self._models_loaded = False

        start_time = time.time()
        logger.info("Loading Ollama model for LLM analysis")

        try:
            success, error = self.model_manager.download_ollama_model(self.ollama_model, self.ollama_host)
            if error:
                logger.warning(
                    "Ollama model download failed",
                    extra={"context": {"error": str(error), "model": self.ollama_model}},
                )
                self.ollama_client = None
                # Don't set _models_loaded=True on failure to allow retry
                return

            import ollama  # type: ignore

            self.ollama_client = ollama.Client(host=self.ollama_host)

            # Verify connection
            try:
                self.ollama_client.list()
                elapsed = (time.time() - start_time) * 1000
                logger.info(
                    "Ollama model loaded and verified",
                    extra={"context": {"model": self.ollama_model, "load_time_ms": round(elapsed, 2)}},
                )
                # Only set _models_loaded=True after successful client initialization
                self._models_loaded = True
            except Exception as verify_exc:  # pylint: disable=broad-except
                logger.warning(
                    "Ollama connection verification failed",
                    extra={"context": {"error": str(verify_exc)}},
                )
                self.ollama_client = None
                # Don't set _models_loaded=True on verification failure to allow retry

        except ImportError as exc:
            logger.exception(
                "Ollama library not available",
                extra={"context": {"error": str(exc)}},
            )
            self.ollama_client = None
            # Don't set _models_loaded=True on import error to allow retry
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to load Ollama model",
                extra={"context": {"error": str(exc)}},
            )
            self.ollama_client = None
            # Don't set _models_loaded=True on failure to allow retry

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze_situation(
        self, ai_outputs: Dict, timestamp: datetime, location: str = "Unknown"
    ) -> Tuple[Dict, Optional[Exception]]:
        """Analyze situation using LLM to determine if suspicious.

        Args:
            ai_outputs: Aggregated outputs from all 5 AI modules
            timestamp: Timestamp of the situation
            location: Location/camera identifier

        Returns:
            Tuple of (analysis_dict, error)
        """
        try:
            if not self._models_loaded:
                self._load_models()

            # Check if Ollama available
            if self.ollama_client is None:
                if self.enable_fallback:
                    logger.warning("Ollama unavailable, using rule-based fallback")
                    return self._fallback_analysis(ai_outputs), None
                else:
                    return {}, LLMAnalysisError("Ollama service unavailable and fallback disabled")

            # Build prompt
            prompt = self._build_prompt(ai_outputs, timestamp, location)

            # Call LLM with retries
            result = None
            for attempt in range(self.max_retries + 1):
                try:
                    # Wrap Ollama call in timeout mechanism
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            self.ollama_client.generate,
                            model=self.ollama_model,
                            prompt=prompt,
                            format="json",
                            options={"temperature": self.temperature, "num_predict": self.max_tokens},
                        )
                        try:
                            response = future.result(timeout=self.timeout)
                        except FutureTimeoutError:
                            raise LLMAnalysisError(f"LLM call timed out after {self.timeout} seconds")

                    response_text = response.get("response", "")
                    if not response_text:
                        raise LLMAnalysisError("Empty response from Ollama")

                    # Parse and validate
                    result = self._parse_and_validate_response(response_text)
                    if result is not None:
                        break

                    # If validation failed, add schema hints to prompt for retry
                    if attempt < self.max_retries:
                        logger.warning(
                            "LLM response validation failed, retrying with schema hints",
                            extra={"context": {"attempt": attempt + 1, "max_retries": self.max_retries}},
                        )
                        prompt = self._build_prompt(ai_outputs, timestamp, location, include_schema_hints=True)

                except Exception as exc:  # pylint: disable=broad-except
                    if attempt < self.max_retries:
                        logger.warning(
                            "LLM call failed, retrying",
                            extra={"context": {"attempt": attempt + 1, "error": str(exc)}},
                        )
                        continue
                    else:
                        logger.exception(
                            "LLM call failed after all retries",
                            extra={"context": {"error": str(exc)}},
                        )
                        if self.enable_fallback:
                            return self._fallback_analysis(ai_outputs), None
                        else:
                            return {}, LLMAnalysisError(f"LLM analysis failed: {exc}")

            # If all retries failed, use fallback
            if result is None:
                if self.enable_fallback:
                    logger.warning("LLM returned invalid JSON after all retries, using fallback")
                    return self._fallback_analysis(ai_outputs), None
                else:
                    return {}, LLMAnalysisError("LLM returned invalid JSON after all retries")

            # Check confidence threshold
            if result["confidence"] < self.confidence_threshold:
                logger.info(
                    "LLM confidence below threshold, overriding is_suspicious",
                    extra={
                        "context": {
                            "confidence": result["confidence"],
                            "threshold": self.confidence_threshold,
                        }
                    },
                )
                result["is_suspicious"] = False
                # Normalize recommended_action to match the override
                if result.get("recommended_action") in ["alert", "escalate"]:
                    result["recommended_action"] = "monitor"
                elif result.get("recommended_action") not in ["monitor", "ignore"]:
                    result["recommended_action"] = "monitor"
                result["reasoning"] = (
                    f"{result['reasoning']} Note: Confidence ({result['confidence']:.2f}) "
                    f"is below threshold ({self.confidence_threshold}), so situation is not flagged as suspicious."
                )

            return result, None

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to analyze situation", extra={"context": {"error": str(exc)}})
            if self.enable_fallback:
                return self._fallback_analysis(ai_outputs), None
            else:
                return {}, LLMAnalysisError(f"Analysis failed: {exc}")

    # ------------------------------------------------------------------ #
    # Prompt building
    # ------------------------------------------------------------------ #
    def _build_prompt(
        self, ai_outputs: Dict, timestamp: datetime, location: str, include_schema_hints: bool = False
    ) -> str:
        """Build prompt for LLM analysis.

        Args:
            ai_outputs: Aggregated AI outputs
            timestamp: Timestamp
            location: Location
            include_schema_hints: Whether to include detailed schema hints

        Returns:
            Complete prompt string
        """
        prompt_parts = [SYSTEM_PROMPT]

        # Add few-shot examples if enabled
        if self.use_few_shot:
            prompt_parts.append("\n## Examples:\n")
            for i, example in enumerate(self._get_few_shot_examples(), 1):
                prompt_parts.append(f"### Example {i}:\n")
                prompt_parts.append(f"Input:\n{example['input']}\n\n")
                prompt_parts.append(f"Output:\n{json.dumps(example['output'], indent=2)}\n\n")

        # Add chain-of-thought instruction if enabled
        if self.use_chain_of_thought:
            prompt_parts.append(f"\n{CHAIN_OF_THOUGHT_INSTRUCTION}\n")

        # Add current situation
        formatted_outputs = self._format_ai_outputs_for_prompt(ai_outputs)
        situation_text = SITUATION_TEMPLATE.format(
            timestamp=timestamp.isoformat(),
            location=location,
            scene_description=formatted_outputs.get("scene", "No scene data"),
            person_summary=formatted_outputs.get("persons", "No person data"),
            object_summary=formatted_outputs.get("objects", "No object data"),
            transcription_summary=formatted_outputs.get("transcription", "No transcription"),
            audio_events_summary=formatted_outputs.get("audio_events", "No audio events"),
        )

        prompt_parts.append(situation_text)

        # Add schema hints if retrying
        if include_schema_hints:
            prompt_parts.append(
                "\n\nIMPORTANT: You must respond with valid JSON matching this exact schema:\n"
            )
            prompt_parts.append(
                json.dumps(
                    {
                        "is_suspicious": True,
                        "confidence": 0.9,
                        "threat_level": "high",
                        "reasoning": "Example reasoning text",
                        "recommended_action": "alert",
                        "key_factors": ["factor1", "factor2"],
                    },
                    indent=2,
                )
            )
            prompt_parts.append(
                "\n\nValid threat_level values: low, medium, high, critical\n"
                "Valid recommended_action values: alert, monitor, escalate, ignore\n"
                "confidence must be between 0.0 and 1.0\n"
                "key_factors must be an array of 1-10 strings\n"
            )

        return "\n".join(prompt_parts)

    def _format_ai_outputs_for_prompt(self, ai_outputs: Dict) -> Dict[str, str]:
        """Format AI outputs into readable text for prompt.

        Args:
            ai_outputs: Aggregated AI outputs

        Returns:
            Dictionary of formatted strings
        """
        formatted = {}

        # Format scene
        scene = ai_outputs.get("scene", {})
        if scene:
            scene_type = scene.get("scene_type", "unknown")
            lighting = scene.get("lighting", "unknown")
            weather = scene.get("weather", "unknown")
            crowd_density = scene.get("crowd_density", "unknown")
            description = scene.get("description", "")
            formatted["scene"] = (
                f"{scene_type} environment with {lighting} lighting, {weather} weather, "
                f"{crowd_density} crowd density. {description}"
            )
        else:
            formatted["scene"] = "No scene data available"

        # Format persons
        persons = ai_outputs.get("persons", [])
        if persons:
            person_count = len(persons)
            person_details = []
            for person in persons[:5]:  # Limit to 5 persons
                # Try top-level keys first for backward compatibility
                age = person.get("age")
                gender = person.get("gender")
                clothing = person.get("clothing_description")
                
                # Fall back to nested structure if top-level not found
                if age is None:
                    demographics = person.get("demographics", {})
                    age_data = demographics.get("age", {})
                    if isinstance(age_data, dict):
                        age = age_data.get("value")
                    else:
                        age = age_data
                
                if gender is None or gender == "unknown":
                    demographics = person.get("demographics", {})
                    gender_data = demographics.get("gender", {})
                    if isinstance(gender_data, dict):
                        gender = gender_data.get("value", "unknown")
                    else:
                        gender = gender_data or "unknown"
                
                if clothing is None or clothing == "unknown clothing":
                    details = person.get("details", {})
                    clothing = details.get("clothing_description", "unknown clothing")
                
                # Default values if still None
                age = age if age is not None else "unknown"
                gender = gender if gender else "unknown"
                clothing = clothing if clothing else "unknown clothing"
                
                person_details.append(f"Person: {gender}, age {age}, {clothing}")
            formatted["persons"] = f"{person_count} person(s) detected. {'; '.join(person_details)}."
        else:
            formatted["persons"] = "No persons detected"

        # Format objects
        objects_data = ai_outputs.get("objects", {})
        if objects_data:
            objects_list = objects_data.get("objects", [])
            # Build map of object_id -> threat_level
            object_threat_map = {obj.get("object_id"): obj.get("threat_level") for obj in objects_list if obj.get("object_id")}
            
            high_threat = [obj for obj in objects_list if obj.get("threat_level") == "high"]
            relationships = objects_data.get("relationships", [])
            # Look up threat_level from object map instead of checking rel['object_threat_level']
            person_holding_weapon = any(
                rel.get("relationship") == "holding" and object_threat_map.get(rel.get("object_id")) == "high"
                for rel in relationships
            )

            object_summary = f"{len(objects_list)} objects detected."
            if high_threat:
                high_threat_names = [obj.get("class_name", "unknown") for obj in high_threat]
                object_summary += f" High threat: {', '.join(high_threat_names)}."
            if person_holding_weapon:
                object_summary += " Person holding weapon detected."
            formatted["objects"] = object_summary
        else:
            formatted["objects"] = "No objects detected"

        # Format transcription
        transcription = ai_outputs.get("transcription", {})
        if transcription:
            text = transcription.get("text", "")
            language = transcription.get("language", "unknown")
            threat_keywords = transcription.get("threat_keywords", [])
            if text:
                formatted["transcription"] = f"'{text}'. Language: {language}."
                if threat_keywords:
                    formatted["transcription"] += f" Threat keywords: {', '.join(threat_keywords)}."
            else:
                formatted["transcription"] = "No speech detected"
        else:
            formatted["transcription"] = "No transcription data"

        # Format audio events
        audio_events = ai_outputs.get("audio_events", {})
        if audio_events:
            detected_sounds = audio_events.get("detected_sounds", [])
            if detected_sounds:
                sound_names = [sound.get("class_name", "unknown") for sound in detected_sounds[:5]]
                max_urgency = max(
                    (sound.get("urgency_level", "low") for sound in detected_sounds),
                    key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(x, 0),
                    default="low",
                )
                critical_sounds = [
                    sound.get("class_name", "unknown")
                    for sound in detected_sounds
                    if sound.get("urgency_level") == "critical"
                ]
                formatted["audio_events"] = f"Detected sounds: {', '.join(sound_names)}. Max urgency: {max_urgency}."
                if critical_sounds:
                    formatted["audio_events"] += f" Critical: {', '.join(critical_sounds)}."
            else:
                formatted["audio_events"] = "No sounds detected"
        else:
            formatted["audio_events"] = "No audio events data"

        return formatted

    def _get_few_shot_examples(self) -> List[Dict]:
        """Get few-shot examples for prompt.

        Returns:
            List of example dicts with 'input' and 'output' keys
        """
        return FEW_SHOT_EXAMPLES

    # ------------------------------------------------------------------ #
    # Response parsing and validation
    # ------------------------------------------------------------------ #
    def _parse_and_validate_response(self, response_text: str) -> Optional[Dict]:
        """Parse and validate LLM response.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Validated dict or None if validation fails
        """
        try:
            # Try to extract JSON from response (may have extra text)
            response_text = response_text.strip()

            # Find JSON object in response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON object found in LLM response")
                return None

            json_text = response_text[start_idx:end_idx]
            data = json.loads(json_text)

            # Validate with Pydantic
            analysis = SuspicionAnalysis.model_validate(data)
            return analysis.model_dump()

        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in LLM response", extra={"context": {"error": str(exc)}})
            return None
        except ValidationError as exc:
            logger.warning("LLM response validation failed", extra={"context": {"error": str(exc)}})
            return None
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to parse LLM response", extra={"context": {"error": str(exc)}})
            return None

    # ------------------------------------------------------------------ #
    # Fallback analysis
    # ------------------------------------------------------------------ #
    def _fallback_analysis(self, ai_outputs: Dict) -> Dict:
        """Rule-based fallback analysis when LLM unavailable.

        Args:
            ai_outputs: Aggregated AI outputs

        Returns:
            Analysis dict matching output schema
        """
        logger.warning("Using rule-based fallback analysis")

        is_suspicious = False
        threat_level = "low"
        reasoning_parts = []
        key_factors = []

        # Check for high-threat objects
        objects_data = ai_outputs.get("objects", {})
        objects_list = objects_data.get("objects", [])
        # Build map of object_id -> threat_level
        object_threat_map = {obj.get("object_id"): obj.get("threat_level") for obj in objects_list if obj.get("object_id")}
        high_threat_objects = [obj for obj in objects_list if obj.get("threat_level") == "high"]

        if high_threat_objects:
            is_suspicious = True
            threat_level = "high"
            object_names = [obj.get("class_name", "unknown") for obj in high_threat_objects]
            reasoning_parts.append(f"High-threat objects detected: {', '.join(object_names)}")
            key_factors.extend([f"High-threat object: {name}" for name in object_names])

        # Check for person holding weapon
        relationships = objects_data.get("relationships", [])
        # Look up threat_level from object map instead of checking rel['object_threat_level']
        person_holding_weapon = any(
            rel.get("relationship") == "holding" and object_threat_map.get(rel.get("object_id")) == "high"
            for rel in relationships
        )

        if person_holding_weapon:
            is_suspicious = True
            if threat_level == "low":
                threat_level = "high"
            reasoning_parts.append("Person detected holding weapon")
            key_factors.append("Person holding weapon")

        # Check for critical audio events
        audio_events = ai_outputs.get("audio_events", {})
        detected_sounds = audio_events.get("detected_sounds", [])
        critical_sounds = [sound for sound in detected_sounds if sound.get("urgency_level") == "critical"]

        if critical_sounds:
            is_suspicious = True
            threat_level = "critical"
            sound_names = [sound.get("class_name", "unknown") for sound in critical_sounds]
            reasoning_parts.append(f"Critical audio events detected: {', '.join(sound_names)}")
            key_factors.extend([f"Critical sound: {name}" for name in sound_names])

        # Check for threat keywords in transcription
        transcription = ai_outputs.get("transcription", {})
        threat_keywords = transcription.get("threat_keywords", [])

        if threat_keywords:
            is_suspicious = True
            if threat_level == "low":
                threat_level = "medium"
            reasoning_parts.append(f"Threat keywords detected in speech: {', '.join(threat_keywords)}")
            key_factors.extend([f"Threat keyword: {kw}" for kw in threat_keywords[:3]])

        # Build reasoning
        if not reasoning_parts:
            reasoning = "No significant threat indicators detected. Normal activity."
        else:
            reasoning = "Rule-based analysis: " + "; ".join(reasoning_parts) + "."

        return {
            "is_suspicious": is_suspicious,
            "confidence": 0.6,  # Lower confidence for fallback
            "threat_level": threat_level,
            "reasoning": reasoning,
            "recommended_action": "alert" if is_suspicious else "ignore",
            "key_factors": key_factors if key_factors else ["No significant factors"],
        }

