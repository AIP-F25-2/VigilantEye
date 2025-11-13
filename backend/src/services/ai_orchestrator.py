import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.ai_modules.audio_classifier import AudioClassifierService
from src.ai_modules.llm_analyzer import LLMAnalyzerService
from src.ai_modules.object_detector import ObjectDetectorService
from src.ai_modules.person_detector import PersonDetectorService
from src.ai_modules.scene_analyzer import SceneAnalyzerService
from src.ai_modules.speech_to_text import SpeechToTextService
from src.app import db
from src.config.constants import AnalysisResult
from src.config.settings import get_config
from src.models.ai_performance_metrics import AIPerformanceMetrics
from src.models.audit_log import AuditLog
from src.models.video import Video
from src.services.messenger_service import MessengerService
from src.services.storage_service import StorageService
from src.services.ticket_service import TicketService
from src.services.video_processor import VideoProcessorService

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Base exception for analysis operations."""

    pass


class AIOrchestrator:
    """Service that coordinates the complete AI analysis pipeline."""

    _instance: Optional["AIOrchestrator"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[object] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.config = config or get_config()
        self.frame_interval = getattr(self.config, "FRAME_EXTRACTION_INTERVAL", 1.0)
        self.use_motion_detection = True
        self.confidence_threshold = getattr(self.config, "LLM_CONFIDENCE_THRESHOLD", 0.7)

        # Initialize AI services (singleton instances)
        self.person_detector = PersonDetectorService(config=self.config)
        self.scene_analyzer = SceneAnalyzerService(config=self.config)
        self.object_detector = ObjectDetectorService(config=self.config)
        self.speech_to_text = SpeechToTextService(config=self.config)
        self.audio_classifier = AudioClassifierService(config=self.config)
        self.llm_analyzer = LLMAnalyzerService(config=self.config)

        # Initialize supporting services
        self.video_processor = VideoProcessorService(config=self.config)
        self.storage_service = StorageService(config=self.config)
        self.ticket_service = TicketService(config=self.config)
        self.messenger_service = MessengerService(config=self.config)

        self._initialized = True

    def analyze_video(self, video_id: str) -> Tuple[Dict, Optional[Exception]]:
        """Main orchestration method for video analysis."""
        try:
            # Query video
            video = Video.query.get(video_id)
            if not video:
                return None, AnalysisError(f"Video not found: {video_id}")

            # Update video status
            video.mark_analyzing()
            db.session.commit()

            # Get video path
            video_path = video.get_storage_path()
            if not os.path.exists(video_path):
                error = AnalysisError(f"Video file not found: {video_path}")
                video.mark_error(str(error))
                db.session.commit()
                return None, error

            # Create output directories
            frames_dir = f"storage/frames/temp_{video_id}"
            audio_dir = f"storage/audio/temp_{video_id}"
            Path(frames_dir).mkdir(parents=True, exist_ok=True)
            Path(audio_dir).mkdir(parents=True, exist_ok=True)

            # Extract frames
            start_time = time.time()
            frames, error = self.video_processor.extract_frames(
                video_path, frames_dir, interval=self.frame_interval, use_motion_detection=self.use_motion_detection
            )
            frame_duration_ms = int((time.time() - start_time) * 1000)
            self._track_performance("frame_extraction", "ffmpeg", frame_duration_ms, video_id, "success" if not error else "failure", str(error) if error else None)

            if error:
                logger.error(f"Frame extraction failed for video {video_id}: {error}")
                video.mark_error(f"Frame extraction failed: {str(error)}")
                db.session.commit()
                return None, error

            # Extract audio
            audio_path = f"{audio_dir}/audio.wav"
            start_time = time.time()
            audio_extracted, error = self.video_processor.extract_audio(video_path, audio_path)
            audio_duration_ms = int((time.time() - start_time) * 1000)
            self._track_performance("audio_extraction", "ffmpeg", audio_duration_ms, video_id, "success" if audio_extracted else "failure", str(error) if error else None)

            if not audio_extracted:
                audio_path = None  # Continue without audio
                logger.warning(f"Audio extraction failed for video {video_id}, continuing without audio")

            # Run AI analysis
            ai_results = self._run_parallel_ai_analysis(video_id, frames, audio_path)

            # Run LLM aggregation
            location = video.camera.name if video.camera else "Unknown"
            timestamp = datetime.utcnow()
            llm_result, error = self.llm_analyzer.analyze_situation(ai_results, timestamp, location)

            if error:
                logger.warning(f"LLM analysis failed for video {video_id}, using fallback: {error}")
                # Use fallback analysis
                llm_result = self._fallback_analysis(ai_results)

            # Handle result
            self._handle_analysis_result(video_id, llm_result, ai_results, frames, audio_path)

            # Update video status
            result_type = AnalysisResult.SUSPICIOUS if llm_result.get("is_suspicious", False) else AnalysisResult.CLEAN
            video.mark_analyzed(result_type)
            db.session.commit()

            return llm_result, None

        except Exception as exc:
            logger.exception(f"Analysis failed for video {video_id}")
            try:
                video = Video.query.get(video_id)
                if video:
                    video.mark_error(str(exc))
                    db.session.commit()
            except Exception:
                pass
            return None, exc

    def _run_parallel_ai_analysis(self, video_id: str, frames: List[str], audio_path: Optional[str]) -> Dict:
        """Run all 5 AI modules in parallel and aggregate results."""
        ai_results = {
            "scene": None,
            "persons": [],
            "objects": None,
            "transcription": None,
            "audio_events": None,
            "errors": [],
        }

        if not frames:
            logger.warning(f"No frames extracted for video {video_id}")
            return ai_results

        # Select frame(s) based on config
        if self.config.AI_ORCHESTRATOR_ANALYZE_ALL_FRAMES:
            # Analyze all frames or a sampled subset
            frame_paths = frames
            if len(frames) > 10:  # Sample if too many frames
                step = len(frames) // 10
                frame_paths = frames[::step]
            
            # Aggregate results across frames
            all_persons = []
            all_objects = []
            scenes = []
            
            for frame_path in frame_paths:
                frame_array = cv2.imread(frame_path)
                if frame_array is None:
                    continue
                
                frame_number = frames.index(frame_path) if frame_path in frames else 0
                timestamp = datetime.utcnow()
                
                # Person Detection
                try:
                    start_time = time.time()
                    persons, error = self.person_detector.detect_persons(frame_array, video_id, timestamp, frame_number)
                    duration_ms = int((time.time() - start_time) * 1000)
                    model_name = "yolov8n"
                    if error:
                        logger.warning(f"Person detection failed for video {video_id}: {error}")
                        ai_results["errors"].append(f"person_detection: {str(error)}")
                        self._track_performance("person_detection", model_name, duration_ms, video_id, "failure", str(error))
                    else:
                        if persons:
                            all_persons.extend(persons)
                        self._track_performance("person_detection", model_name, duration_ms, video_id, "success")
                except Exception as exc:
                    logger.exception(f"Person detection exception for video {video_id}")
                    ai_results["errors"].append(f"person_detection: {str(exc)}")
                
                # Scene Analysis
                try:
                    start_time = time.time()
                    scene, error = self.scene_analyzer.analyze_scene(frame_array)
                    duration_ms = int((time.time() - start_time) * 1000)
                    model_name = "blip2-opt-2.7b"
                    if error:
                        logger.warning(f"Scene analysis failed for video {video_id}: {error}")
                        ai_results["errors"].append(f"scene_analysis: {str(error)}")
                        self._track_performance("scene_analysis", model_name, duration_ms, video_id, "failure", str(error))
                    else:
                        scenes.append(scene)
                        self._track_performance("scene_analysis", model_name, duration_ms, video_id, "success")
                except Exception as exc:
                    logger.exception(f"Scene analysis exception for video {video_id}")
                    ai_results["errors"].append(f"scene_analysis: {str(exc)}")
                
                # Object Detection
                try:
                    start_time = time.time()
                    objects, error = self.object_detector.detect_objects(frame_array, all_persons if all_persons else [])
                    duration_ms = int((time.time() - start_time) * 1000)
                    model_name = "yolov8n"
                    if error:
                        logger.warning(f"Object detection failed for video {video_id}: {error}")
                        ai_results["errors"].append(f"object_detection: {str(error)}")
                        self._track_performance("object_detection", model_name, duration_ms, video_id, "failure", str(error))
                    else:
                        if objects and isinstance(objects, dict):
                            all_objects.append(objects)
                        self._track_performance("object_detection", model_name, duration_ms, video_id, "success")
                except Exception as exc:
                    logger.exception(f"Object detection exception for video {video_id}")
                    ai_results["errors"].append(f"object_detection: {str(exc)}")
            
            # Merge results across frames
            ai_results["persons"] = all_persons
            if scenes:
                # Use the scene with highest confidence or most detailed description
                ai_results["scene"] = max(scenes, key=lambda s: s.get("confidence", 0.0) if isinstance(s, dict) else 0.0) if scenes else None
            if all_objects:
                # Merge object detections (union of objects, max confidence summaries)
                merged_objects = {"objects": [], "relationships": [], "threat_summary": {}}
                for obj_result in all_objects:
                    if isinstance(obj_result, dict):
                        merged_objects["objects"].extend(obj_result.get("objects", []))
                        merged_objects["relationships"].extend(obj_result.get("relationships", []))
                        # Merge threat summaries (take max counts)
                        threat_summary = obj_result.get("threat_summary", {})
                        if isinstance(threat_summary, dict):
                            for key, value in threat_summary.items():
                                if isinstance(value, (int, float)):
                                    merged_objects["threat_summary"][key] = max(merged_objects["threat_summary"].get(key, 0), value)
                ai_results["objects"] = merged_objects
            
            # Continue with audio processing below
        else:
            # Select representative frame (original behavior)
            frame_path, frame_array, frame_number = self._select_representative_frame(frames)
            timestamp = datetime.utcnow()

            # Run vision AI on representative frame
            # Person Detection
            try:
                start_time = time.time()
                persons, error = self.person_detector.detect_persons(frame_array, video_id, timestamp, frame_number)
                duration_ms = int((time.time() - start_time) * 1000)
                model_name = "yolov8n"  # Default model name
                if error:
                    logger.warning(f"Person detection failed for video {video_id}: {error}")
                    ai_results["errors"].append(f"person_detection: {str(error)}")
                    persons = []
                    self._track_performance("person_detection", model_name, duration_ms, video_id, "failure", str(error))
                else:
                    ai_results["persons"] = persons if persons else []
                    self._track_performance("person_detection", model_name, duration_ms, video_id, "success")
            except Exception as exc:
                logger.exception(f"Person detection exception for video {video_id}")
                ai_results["errors"].append(f"person_detection: {str(exc)}")
                persons = []

            # Scene Analysis
            try:
                start_time = time.time()
                scene, error = self.scene_analyzer.analyze_scene(frame_array)
                duration_ms = int((time.time() - start_time) * 1000)
                model_name = "blip2-opt-2.7b"  # Default model name
                if error:
                    logger.warning(f"Scene analysis failed for video {video_id}: {error}")
                    ai_results["errors"].append(f"scene_analysis: {str(error)}")
                    # Use fallback scene data
                    scene = {"scene_type": "unknown", "lighting": "unknown", "description": "Analysis unavailable"}
                    self._track_performance("scene_analysis", model_name, duration_ms, video_id, "failure", str(error))
                else:
                    ai_results["scene"] = scene
                    self._track_performance("scene_analysis", model_name, duration_ms, video_id, "success")
            except Exception as exc:
                logger.exception(f"Scene analysis exception for video {video_id}")
                ai_results["errors"].append(f"scene_analysis: {str(exc)}")
                scene = {"scene_type": "unknown", "lighting": "unknown", "description": "Analysis unavailable"}

            # Object Detection
            try:
                start_time = time.time()
                objects, error = self.object_detector.detect_objects(frame_array, persons if persons else [])
                duration_ms = int((time.time() - start_time) * 1000)
                model_name = "yolov8n"  # Default model name
                if error:
                    logger.warning(f"Object detection failed for video {video_id}: {error}")
                    ai_results["errors"].append(f"object_detection: {str(error)}")
                    objects = {"objects": [], "relationships": [], "threat_summary": {}}
                    self._track_performance("object_detection", model_name, duration_ms, video_id, "failure", str(error))
                else:
                    ai_results["objects"] = objects
                    self._track_performance("object_detection", model_name, duration_ms, video_id, "success")
            except Exception as exc:
                logger.exception(f"Object detection exception for video {video_id}")
                ai_results["errors"].append(f"object_detection: {str(exc)}")
                objects = {"objects": [], "relationships": [], "threat_summary": {}}

        # Run audio AI (if audio_path exists)
        if audio_path and os.path.exists(audio_path):
            # Speech-to-Text
            try:
                start_time = time.time()
                transcription, error = self.speech_to_text.transcribe_audio(audio_path)
                duration_ms = int((time.time() - start_time) * 1000)
                model_name = "whisper-base"  # Default model name
                if error:
                    logger.warning(f"Speech-to-text failed for video {video_id}: {error}")
                    ai_results["errors"].append(f"speech_to_text: {str(error)}")
                    transcription = {"transcription": "", "language": "unknown", "confidence": 0.0}
                    self._track_performance("speech_to_text", model_name, duration_ms, video_id, "failure", str(error))
                else:
                    ai_results["transcription"] = transcription
                    self._track_performance("speech_to_text", model_name, duration_ms, video_id, "success")
            except Exception as exc:
                logger.exception(f"Speech-to-text exception for video {video_id}")
                ai_results["errors"].append(f"speech_to_text: {str(exc)}")
                transcription = {"transcription": "", "language": "unknown", "confidence": 0.0}

            # Audio Classification
            try:
                start_time = time.time()
                audio_events, error = self.audio_classifier.classify_audio(audio_path)
                duration_ms = int((time.time() - start_time) * 1000)
                model_name = "yamnet"  # Default model name
                if error:
                    logger.warning(f"Audio classification failed for video {video_id}: {error}")
                    ai_results["errors"].append(f"audio_classification: {str(error)}")
                    audio_events = {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}
                    self._track_performance("audio_classification", model_name, duration_ms, video_id, "failure", str(error))
                else:
                    ai_results["audio_events"] = audio_events
                    self._track_performance("audio_classification", model_name, duration_ms, video_id, "success")
            except Exception as exc:
                logger.exception(f"Audio classification exception for video {video_id}")
                ai_results["errors"].append(f"audio_classification: {str(exc)}")
                audio_events = {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}
        else:
            # No audio available
            ai_results["transcription"] = {"transcription": "", "language": "unknown", "confidence": 0.0}
            ai_results["audio_events"] = {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}

        # Log summary
        logger.info(
            "AI analysis completed",
            extra={
                "context": {
                    "video_id": video_id,
                    "persons_detected": len(ai_results.get("persons", [])),
                    "objects_detected": len(ai_results.get("objects", {}).get("objects", [])),
                    "errors": len(ai_results.get("errors", [])),
                }
            },
        )

        return ai_results

    def _handle_analysis_result(
        self, video_id: str, llm_result: Dict, ai_results: Dict, frames: List[str], audio_path: Optional[str]
    ) -> None:
        """Handle analysis result: create ticket, store evidence, send alert if suspicious."""
        is_suspicious = llm_result.get("is_suspicious", False)
        confidence = llm_result.get("confidence", 0.0)

        # Check if suspicious AND confidence >= threshold
        if is_suspicious and confidence >= self.confidence_threshold:
            # Collect person IDs from AI results
            person_ids = []
            for person_data in ai_results.get("persons", []):
                if isinstance(person_data, dict) and "person_id" in person_data:
                    person_ids.append(person_data["person_id"])

            # Create ticket
            ticket, error = self.ticket_service.create_ticket(
                video_id, llm_result, evidence_ids=[], person_ids=person_ids
            )
            if error:
                logger.error(f"Failed to create ticket for video {video_id}: {error}")
                return

            # Store evidence
            if frames:
                frame_path, frame_array, frame_number = self._select_representative_frame(frames)
                timestamp = datetime.utcnow()
                try:
                    # Read frame data
                    with open(frame_path, "rb") as f:
                        frame_data = f.read()
                    evidence_frame, error = self.storage_service.save_frame(
                        frame_data, ticket.id, video_id, timestamp, frame_number, description=llm_result.get("reasoning", "")
                    )
                    if error:
                        logger.warning(f"Failed to save evidence frame: {error}")
                except Exception as exc:
                    logger.warning(f"Failed to read frame for evidence: {exc}")

            if audio_path and os.path.exists(audio_path):
                timestamp = datetime.utcnow()
                try:
                    with open(audio_path, "rb") as f:
                        audio_data = f.read()
                    evidence_audio, error = self.storage_service.save_audio(
                        audio_data, ticket.id, video_id, timestamp
                    )
                    if error:
                        logger.warning(f"Failed to save evidence audio: {error}")
                except Exception as exc:
                    logger.warning(f"Failed to read audio for evidence: {exc}")

            # Send alert
            image_path = None
            if frames:
                frame_path, _, _ = self._select_representative_frame(frames)
                image_path = frame_path

            success, error = self.messenger_service.send_alert(ticket, image_path=image_path)
            if error:
                logger.warning(f"Failed to send alert for ticket {ticket.id}: {error}")

            # Store AI analysis in evidence
            try:
                from src.models.evidence import Evidence
                evidence = Evidence.query.filter_by(ticket_id=ticket.id).first()
                if evidence:
                    evidence.ai_analysis = ai_results
                    db.session.commit()
            except Exception as exc:
                logger.warning(f"Failed to store AI analysis in evidence: {exc}")

        # Note: WebSocket event emission is handled by handle_suspicious_result_task

        logger.info(
            "Analysis result handled",
            extra={
                "context": {
                    "video_id": video_id,
                    "is_suspicious": is_suspicious,
                    "confidence": confidence,
                }
            },
        )

    def _track_performance(
        self, task_name: str, model_name: str, duration_ms: int, video_id: str = None, status: str = "success", error_message: str = None
    ) -> None:
        """Track AI performance metrics."""
        try:
            metric = AIPerformanceMetrics(
                video_id=video_id,
                task_name=task_name,
                model_name=model_name,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message,
            )
            db.session.add(metric)
            db.session.commit()
            logger.debug(
                "Performance metric recorded",
                extra={"context": {"task_name": task_name, "duration_ms": duration_ms}},
            )
        except Exception as exc:
            logger.warning(f"Failed to record performance metric: {exc}")
            # Don't fail analysis if metrics fail

    def _run_person_detection(self, video_id: str, frame_array: np.ndarray, timestamp: datetime, frame_number: int) -> Tuple[List, Optional[Exception]]:
        """Helper method for person detection task."""
        try:
            start_time = time.time()
            persons, error = self.person_detector.detect_persons(frame_array, video_id, timestamp, frame_number)
            duration_ms = int((time.time() - start_time) * 1000)
            model_name = "yolov8n"
            if error:
                self._track_performance("person_detection", model_name, duration_ms, video_id, "failure", str(error))
            else:
                self._track_performance("person_detection", model_name, duration_ms, video_id, "success")
            return persons if persons else [], error
        except Exception as exc:
            logger.exception(f"Person detection exception for video {video_id}")
            return [], exc

    def _run_scene_analysis(self, frame_array: np.ndarray, video_id: Optional[str] = None) -> Tuple[Dict, Optional[Exception]]:
        """Helper method for scene analysis task."""
        try:
            start_time = time.time()
            scene, error = self.scene_analyzer.analyze_scene(frame_array)
            duration_ms = int((time.time() - start_time) * 1000)
            model_name = "blip2-opt-2.7b"
            if error:
                self._track_performance("scene_analysis", model_name, duration_ms, video_id, "failure", str(error))
            else:
                self._track_performance("scene_analysis", model_name, duration_ms, video_id, "success")
            return scene, error
        except Exception as exc:
            logger.exception(f"Scene analysis exception for video {video_id or 'unknown'}")
            return {"scene_type": "unknown", "lighting": "unknown", "description": "Analysis unavailable"}, exc

    def _run_object_detection(self, frame_array: np.ndarray, persons: List, video_id: Optional[str] = None) -> Tuple[Dict, Optional[Exception]]:
        """Helper method for object detection task."""
        try:
            start_time = time.time()
            objects, error = self.object_detector.detect_objects(frame_array, persons if persons else [])
            duration_ms = int((time.time() - start_time) * 1000)
            model_name = "yolov8n"
            if error:
                self._track_performance("object_detection", model_name, duration_ms, video_id, "failure", str(error))
            else:
                self._track_performance("object_detection", model_name, duration_ms, video_id, "success")
            return objects, error
        except Exception as exc:
            logger.exception(f"Object detection exception for video {video_id or 'unknown'}")
            return {"objects": [], "relationships": [], "threat_summary": {}}, exc

    def _run_speech_to_text(self, audio_path: str, video_id: Optional[str] = None) -> Tuple[Dict, Optional[Exception]]:
        """Helper method for speech-to-text task."""
        try:
            start_time = time.time()
            transcription, error = self.speech_to_text.transcribe_audio(audio_path)
            duration_ms = int((time.time() - start_time) * 1000)
            model_name = "whisper-base"
            if error:
                self._track_performance("speech_to_text", model_name, duration_ms, video_id, "failure", str(error))
            else:
                self._track_performance("speech_to_text", model_name, duration_ms, video_id, "success")
            return transcription, error
        except Exception as exc:
            logger.exception(f"Speech-to-text exception for video {video_id or 'unknown'}")
            return {"transcription": "", "language": "unknown", "confidence": 0.0}, exc

    def _run_audio_classification(self, audio_path: str, video_id: Optional[str] = None) -> Tuple[Dict, Optional[Exception]]:
        """Helper method for audio classification task."""
        try:
            start_time = time.time()
            audio_events, error = self.audio_classifier.classify_audio(audio_path)
            duration_ms = int((time.time() - start_time) * 1000)
            model_name = "yamnet"
            if error:
                self._track_performance("audio_classification", model_name, duration_ms, video_id, "failure", str(error))
            else:
                self._track_performance("audio_classification", model_name, duration_ms, video_id, "success")
            return audio_events, error
        except Exception as exc:
            logger.exception(f"Audio classification exception for video {video_id or 'unknown'}")
            return {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}, exc

    def _select_representative_frame(self, frames: List[str]) -> Tuple[str, np.ndarray, int]:
        """Select representative frame (middle frame or frame with most motion)."""
        if not frames:
            raise ValueError("No frames provided")

        # Select middle frame
        middle_idx = len(frames) // 2
        frame_path = frames[middle_idx]
        frame_array = cv2.imread(frame_path)
        if frame_array is None:
            raise ValueError(f"Failed to load frame: {frame_path}")

        frame_number = middle_idx
        return frame_path, frame_array, frame_number

    def _fallback_analysis(self, ai_results: Dict) -> Dict:
        """Fallback rule-based analysis if LLM fails."""
        # Simple rule-based threat assessment
        threat_indicators = 0

        # Check for high-threat objects
        objects = ai_results.get("objects", {})
        if isinstance(objects, dict):
            threat_summary = objects.get("threat_summary", {})
            if isinstance(threat_summary, dict):
                if threat_summary.get("high_threat_count", 0) > 0:
                    threat_indicators += 2

        # Check for critical audio events
        audio_events = ai_results.get("audio_events", {})
        if isinstance(audio_events, dict):
            urgency_summary = audio_events.get("urgency_summary", {})
            if isinstance(urgency_summary, dict):
                if urgency_summary.get("critical", 0) > 0:
                    threat_indicators += 2

        # Determine result
        is_suspicious = threat_indicators >= 2
        confidence = 0.6 if is_suspicious else 0.4  # Lower confidence for fallback

        return {
            "is_suspicious": is_suspicious,
            "confidence": confidence,
            "threat_level": "high" if threat_indicators >= 3 else "medium" if threat_indicators >= 2 else "low",
            "reasoning": "Rule-based fallback analysis (LLM unavailable)",
            "recommended_action": "alert" if is_suspicious else "monitor",
            "key_factors": ["fallback_analysis"],
        }

