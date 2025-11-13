from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

import librosa
import numpy as np
import torch

from src.config.settings import get_config
from src.utils.model_manager import ModelManager

logger = logging.getLogger(__name__)


class SpeechToTextError(Exception):
    """Raised when speech-to-text processing fails."""


class SpeechToTextService:
    """Service responsible for speech-to-text transcription using OpenAI Whisper."""

    _instance: Optional["SpeechToTextService"] = None

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

        self.whisper_model_size = getattr(self.config, "WHISPER_MODEL_SIZE", "base")
        self.transcription_confidence_threshold = getattr(
            self.config, "TRANSCRIPTION_CONFIDENCE_THRESHOLD", 0.7
        )
        self.enable_noise_reduction = getattr(self.config, "ENABLE_NOISE_REDUCTION", True)
        self.threat_keywords = getattr(
            self.config,
            "THREAT_KEYWORDS",
            ["gun", "shoot", "kill", "bomb", "help", "fire", "weapon", "attack", "knife", "threat"],
        )
        self.profanity_keywords = getattr(self.config, "PROFANITY_KEYWORDS", [])
        self.enable_speaker_diarization = getattr(self.config, "ENABLE_SPEAKER_DIARIZATION", True)

        self.model_manager = ModelManager(config=self.config)
        self.whisper_model = None

        self._models_loaded = False
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Model management
    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        if self._models_loaded:
            return

        start_time = time.time()
        logger.info(
            "Loading Whisper model for speech-to-text",
            extra={"context": {"model_size": self.whisper_model_size, "device": self.device}},
        )

        try:
            whisper_path, error = self.model_manager.download_whisper_model(self.whisper_model_size)
            if error:
                logger.warning(
                    "Whisper model download failed",
                    extra={"context": {"error": str(error), "model_size": self.whisper_model_size}},
                )
                self.whisper_model = None
            else:
                import whisper  # type: ignore
                from pathlib import Path

                self.whisper_model = whisper.load_model(
                    self.whisper_model_size, device=self.device, download_root=str(Path(whisper_path).parent)
                )
                elapsed = (time.time() - start_time) * 1000
                logger.info(
                    "Whisper model loaded",
                    extra={
                        "context": {
                            "model_size": self.whisper_model_size,
                            "device": self.device,
                            "load_time_ms": round(elapsed, 2),
                        }
                    },
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to load Whisper model",
                extra={"context": {"error": str(exc), "model_size": self.whisper_model_size}},
            )
            self.whisper_model = None

        self._models_loaded = True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def transcribe_audio(self, audio_path: str) -> Tuple[Dict, Optional[Exception]]:
        """Transcribe audio file to text using Whisper.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (transcription_dict, error)
        """
        try:
            if not self._models_loaded:
                self._load_models()

            if self.whisper_model is None:
                logger.warning("Whisper model unavailable, using fallback transcription")
                return self._fallback_transcription(), None

            # Load audio file
            try:
                audio, sr = librosa.load(audio_path, sr=16000)  # Whisper expects 16kHz
            except Exception as exc:
                logger.exception(
                    "Failed to load audio file",
                    extra={"context": {"audio_path": audio_path, "error": str(exc)}},
                )
                return {}, SpeechToTextError(f"Failed to load audio file: {exc}")

            # Apply noise reduction if enabled
            if self.enable_noise_reduction:
                audio = self._reduce_noise(audio, sr)

            # Transcribe with Whisper
            try:
                result = self.whisper_model.transcribe(
                    audio, language=None, task="transcribe", word_timestamps=True
                )
            except Exception as exc:
                logger.exception(
                    "Whisper transcription failed",
                    extra={"context": {"audio_path": audio_path, "error": str(exc)}},
                )
                return {}, SpeechToTextError(f"Transcription failed: {exc}")

            # Extract segments with timestamps, filtering by confidence threshold
            segments = []
            for seg in result.get("segments", []):
                # Calculate segment confidence (1 - no_speech_prob)
                no_speech_prob = seg.get("no_speech_prob", 1.0)
                segment_confidence = 1.0 - no_speech_prob
                
                # Filter out low-confidence segments if threshold is set
                if segment_confidence < self.transcription_confidence_threshold:
                    continue
                
                segments.append(
                    {
                        "text": seg.get("text", "").strip(),
                        "start": seg.get("start", 0.0),
                        "end": seg.get("end", 0.0),
                        "confidence": float(segment_confidence),
                    }
                )

            # Detect speaker changes (simple energy-based) if enabled
            if self.enable_speaker_diarization:
                segments_with_speakers = self._detect_speaker_changes(audio, sr, segments)
            else:
                segments_with_speakers = [{**seg, "speaker_id": 1} for seg in segments]

            # Detect threat keywords
            full_text = result.get("text", "")
            threat_keywords = self._detect_keywords(full_text, self.threat_keywords)

            # Detect profanity
            profanity_keywords = self._detect_keywords(full_text, self.profanity_keywords)
            profanity_detected = len(profanity_keywords) > 0

            # Calculate overall confidence (average of segment confidences if available)
            confidence = result.get("language_prob", 0.0)
            if segments:
                segment_confidences = [seg.get("no_speech_prob", 0.0) for seg in result.get("segments", [])]
                if segment_confidences:
                    avg_no_speech = np.mean(segment_confidences)
                    confidence = 1.0 - avg_no_speech  # Invert: lower no_speech_prob = higher confidence

            # Build result dict
            result_dict = {
                "transcription": full_text,
                "language": result.get("language", "unknown"),
                "language_confidence": result.get("language_prob", 0.0),
                "segments": segments_with_speakers,
                "threat_keywords": threat_keywords,
                "profanity_detected": profanity_detected,
                "profanity_keywords": profanity_keywords,
                "confidence": float(confidence),
            }

            return result_dict, None

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Speech-to-text processing failed",
                extra={"context": {"audio_path": audio_path, "error": str(exc)}},
            )
            return {}, SpeechToTextError(f"Speech-to-text processing failed: {exc}")

    # ------------------------------------------------------------------ #
    # Private helper methods
    # ------------------------------------------------------------------ #
    def _reduce_noise(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply noise reduction preprocessing to audio.

        Args:
            audio: Audio array
            sr: Sample rate

        Returns:
            Processed audio array
        """
        try:
            # High-pass filter using preemphasis
            audio = librosa.effects.preemphasis(audio, coef=0.97)

            # Trim silence from beginning and end
            audio, _ = librosa.effects.trim(audio, top_db=20)

            # Normalize audio amplitude
            audio = librosa.util.normalize(audio)

            return audio
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Noise reduction failed, using original audio",
                extra={"context": {"error": str(exc)}},
            )
            return audio

    def _detect_speaker_changes(
        self, audio: np.ndarray, sr: int, segments: List[Dict]
    ) -> List[Dict]:
        """Detect speaker changes using simple energy-based approach.

        Args:
            audio: Audio array
            sr: Sample rate
            segments: List of transcription segments

        Returns:
            Segments with speaker_id field added
        """
        try:
            # Detect silence gaps
            intervals = librosa.effects.split(audio, top_db=20)

            # Assign speaker IDs based on silence boundaries
            # Simple heuristic: assume speaker changes at silence gaps
            speaker_id = 1
            segments_with_speakers = []

            for seg in segments:
                seg_start = int(seg["start"] * sr)
                seg_end = int(seg["end"] * sr)

                # Check if this segment starts after a significant silence gap
                for interval_start, interval_end in intervals:
                    if seg_start > interval_end and (seg_start - interval_end) > (sr * 0.5):  # 0.5s gap
                        speaker_id += 1
                        break

                seg_copy = seg.copy()
                seg_copy["speaker_id"] = speaker_id
                segments_with_speakers.append(seg_copy)

            return segments_with_speakers
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Speaker change detection failed, using default speaker",
                extra={"context": {"error": str(exc)}},
            )
            # Fallback: assign all segments to speaker 1
            return [{**seg, "speaker_id": 1} for seg in segments]

    def _detect_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Detect keywords in text using case-insensitive whole-word matching.

        Args:
            text: Text to search
            keywords: List of keywords to find

        Returns:
            List of matched keywords
        """
        if not text or not keywords:
            return []

        text_lower = text.lower()
        matched_keywords = []

        for keyword in keywords:
            if not keyword:
                continue
            # Whole word matching using regex
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched_keywords.append(keyword)

        return matched_keywords

    def _fallback_transcription(self) -> Dict:
        """Return empty transcription when Whisper unavailable.

        Returns:
            Empty transcription dict
        """
        logger.warning("Using fallback transcription (Whisper unavailable)")
        return {
            "transcription": "",
            "language": "unknown",
            "language_confidence": 0.0,
            "segments": [],
            "threat_keywords": [],
            "profanity_detected": False,
            "profanity_keywords": [],
            "confidence": 0.0,
        }

