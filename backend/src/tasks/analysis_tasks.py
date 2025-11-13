import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np
from celery import chain, chord, group
from celery.utils.log import get_task_logger

from src.app import db
from src.celery_app import create_celery_app
from src.config import get_config
from src.config.constants import AnalysisResult
from src.models.ai_performance_metrics import AIPerformanceMetrics
from src.models.audit_log import AuditLog
from src.models.video import Video
from src.services.ai_orchestrator import AIOrchestrator
from src.utils.websocket_utils import (
    emit_ai_processing_started,
    emit_analysis_complete,
    emit_analysis_error,
    emit_analysis_started,
    emit_frames_extracted,
    emit_llm_analysis_complete,
)

config = get_config()
celery_app = create_celery_app()
logger = get_task_logger(__name__)


@celery_app.task(
    name="src.tasks.analysis_tasks.analyze_video_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def analyze_video_task(self, video_id: str) -> Dict:
    """Entry point task that chains the entire analysis pipeline."""
    try:
        # Query video
        video = Video.query.get(video_id)
        if not video:
            error_msg = f"Video not found: {video_id}"
            logger.error(error_msg)
            emit_analysis_error(video_id, error_msg)
            raise ValueError(error_msg)

        # Update video status
        video.mark_analyzing()
        db.session.commit()

        # Emit WebSocket event
        emit_analysis_started(video_id)

        # Chain tasks with parallel AI analysis using chord
        # First extract frames, then run AI tasks in parallel, then aggregate and handle
        task_chain = (
            extract_frames_task.s(video_id)
            | prepare_ai_chord_task.s()
            | handle_suspicious_result_task.s()
        )
        result = task_chain.apply_async()

        logger.info(f"Analysis pipeline started for video {video_id}, task_id: {result.id}")

        return {"video_id": video_id, "task_id": result.id, "status": "started"}

    except Exception as exc:
        logger.exception(f"Failed to start analysis for video {video_id}")
        try:
            video = Video.query.get(video_id)
            if video:
                video.mark_error(str(exc))
                db.session.commit()
        except Exception:
            pass
        emit_analysis_error(video_id, str(exc))
        raise


@celery_app.task(name="src.tasks.analysis_tasks.extract_frames_task", bind=True)
def extract_frames_task(self, video_id: str) -> Dict:
    """Extract frames and audio from video."""
    try:
        orchestrator = AIOrchestrator()

        # Get video
        video = Video.query.get(video_id)
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        video_path = video.get_storage_path()
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create output directories
        frames_dir = f"storage/frames/temp_{video_id}"
        audio_dir = f"storage/audio/temp_{video_id}"
        Path(frames_dir).mkdir(parents=True, exist_ok=True)
        Path(audio_dir).mkdir(parents=True, exist_ok=True)

        # Extract frames
        start_time = time.time()
        frames, error = orchestrator.video_processor.extract_frames(
            video_path,
            frames_dir,
            interval=config.FRAME_EXTRACTION_INTERVAL,
            use_motion_detection=True,
        )
        frame_duration_ms = int((time.time() - start_time) * 1000)
        orchestrator._track_performance(
            "frame_extraction",
            "ffmpeg",
            frame_duration_ms,
            video_id,
            "success" if not error else "failure",
            str(error) if error else None,
        )

        if error:
            logger.error(f"Frame extraction failed for video {video_id}: {error}")
            raise error

        # Extract audio
        audio_path = f"{audio_dir}/audio.wav"
        start_time = time.time()
        audio_extracted, error = orchestrator.video_processor.extract_audio(video_path, audio_path)
        audio_duration_ms = int((time.time() - start_time) * 1000)
        orchestrator._track_performance(
            "audio_extraction",
            "ffmpeg",
            audio_duration_ms,
            video_id,
            "success" if audio_extracted else "failure",
            str(error) if error else None,
        )

        if not audio_extracted:
            audio_path = None  # Continue without audio
            logger.warning(f"Audio extraction failed for video {video_id}, continuing without audio")

        # Emit WebSocket event
        emit_frames_extracted(video_id, len(frames))

        return {"video_id": video_id, "frames": frames, "audio_path": audio_path}

    except Exception as exc:
        logger.exception(f"Frame extraction task failed for video {video_id}")
        try:
            video = Video.query.get(video_id)
            if video:
                video.mark_error(str(exc))
                db.session.commit()
        except Exception:
            pass
        emit_analysis_error(video_id, str(exc))
        raise


@celery_app.task(name="src.tasks.analysis_tasks.prepare_ai_chord_task", bind=True)
def prepare_ai_chord_task(self, extraction_result: Dict) -> Dict:
    """Prepare and execute parallel AI tasks using chord, then aggregate results."""
    try:
        video_id = extraction_result.get("video_id") if isinstance(extraction_result, dict) else None
        frames = extraction_result.get("frames", []) if isinstance(extraction_result, dict) else []
        audio_path = extraction_result.get("audio_path") if isinstance(extraction_result, dict) else None

        if not video_id:
            raise ValueError("video_id missing from extraction_result")

        if not frames:
            logger.warning(f"No frames extracted for video {video_id}")
            # Return empty results
            return {
                "video_id": video_id,
                "llm_result": {"is_suspicious": False, "confidence": 0.0},
                "ai_results": {"scene": None, "persons": [], "objects": None, "transcription": None, "audio_events": None, "errors": []},
                "frames": [],
                "audio_path": audio_path,
            }

        orchestrator = AIOrchestrator()
        
        # Select frame(s) based on config
        if config.AI_ORCHESTRATOR_ANALYZE_ALL_FRAMES:
            # Analyze all frames or a sampled subset
            frame_paths = frames
            if len(frames) > 10:  # Sample if too many frames
                step = len(frames) // 10
                frame_paths = frames[::step]
            frame_info_list = []
            for idx, frame_path in enumerate(frame_paths):
                frame_info_list.append((frame_path, idx))
        else:
            # Select representative frame
            frame_path, _, frame_number = orchestrator._select_representative_frame(frames)
            frame_info_list = [(frame_path, frame_number)]
        
        # Build parallel AI tasks
        ai_tasks = []
        
        # For each frame, create vision tasks
        for frame_path, frame_number in frame_info_list:
            # Person detection
            ai_tasks.append(run_person_detection_task.s(video_id, frame_path, frame_number))
            # Scene analysis
            ai_tasks.append(run_scene_analysis_task.s(video_id, frame_path))
            # Object detection (will need persons from person detection, so we'll handle this in aggregation)
            ai_tasks.append(run_object_detection_task.s(video_id, frame_path, []))
        
        # Audio tasks (only once)
        ai_tasks.append(run_speech_to_text_task.s(video_id, audio_path))
        ai_tasks.append(run_audio_classification_task.s(video_id, audio_path))
        
        # Create group and chord
        ai_group = group(ai_tasks)
        chord_callback = aggregate_ai_results_task.s(extraction_result)
        chord_result = chord(ai_group)(chord_callback)
        
        # Execute chord and wait for result
        return chord_result.get()

    except Exception as exc:
        video_id = extraction_result.get("video_id") if isinstance(extraction_result, dict) else None
        video_id = video_id or "<unknown>"
        logger.exception(f"Prepare AI chord task failed for video {video_id}")
        emit_analysis_error(video_id, str(exc))
        raise


@celery_app.task(name="src.tasks.analysis_tasks.run_person_detection_task", bind=True)
def run_person_detection_task(self, video_id: str, frame_path: str, frame_number: int) -> Dict:
    """Run person detection on a frame."""
    try:
        orchestrator = AIOrchestrator()
        frame_array = cv2.imread(frame_path)
        if frame_array is None:
            raise ValueError(f"Failed to load frame: {frame_path}")
        
        timestamp = datetime.utcnow()
        persons, error = orchestrator._run_person_detection(video_id, frame_array, timestamp, frame_number)
        
        if error:
            return {"module": "person_detection", "result": [], "error": str(error)}
        return {"module": "person_detection", "result": persons if persons else [], "error": None}
    except Exception as exc:
        logger.exception(f"Person detection task failed for video {video_id}")
        return {"module": "person_detection", "result": [], "error": str(exc)}


@celery_app.task(name="src.tasks.analysis_tasks.run_scene_analysis_task", bind=True)
def run_scene_analysis_task(self, video_id: str, frame_path: str) -> Dict:
    """Run scene analysis on a frame."""
    try:
        orchestrator = AIOrchestrator()
        frame_array = cv2.imread(frame_path)
        if frame_array is None:
            raise ValueError(f"Failed to load frame: {frame_path}")
        
        scene, error = orchestrator._run_scene_analysis(frame_array, video_id)
        
        if error:
            scene = {"scene_type": "unknown", "lighting": "unknown", "description": "Analysis unavailable"}
            return {"module": "scene_analysis", "result": scene, "error": str(error)}
        return {"module": "scene_analysis", "result": scene, "error": None}
    except Exception as exc:
        logger.exception(f"Scene analysis task failed for video {video_id}")
        scene = {"scene_type": "unknown", "lighting": "unknown", "description": "Analysis unavailable"}
        return {"module": "scene_analysis", "result": scene, "error": str(exc)}


@celery_app.task(name="src.tasks.analysis_tasks.run_object_detection_task", bind=True)
def run_object_detection_task(self, video_id: str, frame_path: str, persons: list) -> Dict:
    """Run object detection on a frame."""
    try:
        orchestrator = AIOrchestrator()
        frame_array = cv2.imread(frame_path)
        if frame_array is None:
            raise ValueError(f"Failed to load frame: {frame_path}")
        
        objects, error = orchestrator._run_object_detection(frame_array, persons, video_id)
        
        if error:
            objects = {"objects": [], "relationships": [], "threat_summary": {}}
            return {"module": "object_detection", "result": objects, "error": str(error)}
        return {"module": "object_detection", "result": objects, "error": None}
    except Exception as exc:
        logger.exception(f"Object detection task failed for video {video_id}")
        objects = {"objects": [], "relationships": [], "threat_summary": {}}
        return {"module": "object_detection", "result": objects, "error": str(exc)}


@celery_app.task(name="src.tasks.analysis_tasks.run_speech_to_text_task", bind=True)
def run_speech_to_text_task(self, video_id: str, audio_path: Optional[str]) -> Dict:
    """Run speech-to-text on audio."""
    try:
        if not audio_path or not os.path.exists(audio_path):
            transcription = {"transcription": "", "language": "unknown", "confidence": 0.0}
            return {"module": "speech_to_text", "result": transcription, "error": None}
        
        orchestrator = AIOrchestrator()
        transcription, error = orchestrator._run_speech_to_text(audio_path, video_id)
        
        if error:
            transcription = {"transcription": "", "language": "unknown", "confidence": 0.0}
            return {"module": "speech_to_text", "result": transcription, "error": str(error)}
        return {"module": "speech_to_text", "result": transcription, "error": None}
    except Exception as exc:
        logger.exception(f"Speech-to-text task failed for video {video_id}")
        transcription = {"transcription": "", "language": "unknown", "confidence": 0.0}
        return {"module": "speech_to_text", "result": transcription, "error": str(exc)}


@celery_app.task(name="src.tasks.analysis_tasks.run_audio_classification_task", bind=True)
def run_audio_classification_task(self, video_id: str, audio_path: Optional[str]) -> Dict:
    """Run audio classification on audio."""
    try:
        if not audio_path or not os.path.exists(audio_path):
            audio_events = {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}
            return {"module": "audio_classification", "result": audio_events, "error": None}
        
        orchestrator = AIOrchestrator()
        audio_events, error = orchestrator._run_audio_classification(audio_path, video_id)
        
        if error:
            audio_events = {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}
            return {"module": "audio_classification", "result": audio_events, "error": str(error)}
        return {"module": "audio_classification", "result": audio_events, "error": None}
    except Exception as exc:
        logger.exception(f"Audio classification task failed for video {video_id}")
        audio_events = {"detected_sounds": [], "urgency_summary": {}, "confidence": 0.0}
        return {"module": "audio_classification", "result": audio_events, "error": str(exc)}


@celery_app.task(name="src.tasks.analysis_tasks.aggregate_ai_results_task", bind=True)
def aggregate_ai_results_task(self, extraction_result: Dict, ai_task_results: list) -> Dict:
    """Aggregate AI task results, run LLM analysis, and return combined result."""
    try:
        video_id = extraction_result.get("video_id") if isinstance(extraction_result, dict) else None
        frames = extraction_result.get("frames", []) if isinstance(extraction_result, dict) else []
        audio_path = extraction_result.get("audio_path") if isinstance(extraction_result, dict) else None

        if not video_id:
            raise ValueError("video_id missing from extraction_result")

        orchestrator = AIOrchestrator()

        # Emit WebSocket event
        emit_ai_processing_started(video_id)

        # Aggregate results from parallel AI tasks
        ai_results = {
            "scene": None,
            "persons": [],
            "objects": None,
            "transcription": None,
            "audio_events": None,
            "errors": [],
        }

        # Process results from parallel tasks (graceful degradation)
        # Collect all results per module (for multi-frame analysis)
        person_results = []
        scene_results = []
        object_results = []
        
        for task_result in ai_task_results:
            if not isinstance(task_result, dict):
                continue
            
            module = task_result.get("module")
            result = task_result.get("result")
            error = task_result.get("error")
            
            if error:
                ai_results["errors"].append(f"{module}: {error}")
            
            if module == "person_detection":
                if result:
                    person_results.append(result)
            elif module == "scene_analysis":
                if result:
                    scene_results.append(result)
            elif module == "object_detection":
                if result:
                    object_results.append(result)
            elif module == "speech_to_text":
                # Audio tasks only run once
                ai_results["transcription"] = result
            elif module == "audio_classification":
                # Audio tasks only run once
                ai_results["audio_events"] = result
        
        # Merge results across frames
        if person_results:
            # Flatten person lists
            all_persons = []
            for person_list in person_results:
                if isinstance(person_list, list):
                    all_persons.extend(person_list)
            ai_results["persons"] = all_persons
        
        if scene_results:
            # Use scene with highest confidence or most detailed
            ai_results["scene"] = max(
                scene_results,
                key=lambda s: s.get("confidence", 0.0) if isinstance(s, dict) else 0.0
            ) if scene_results else None
        
        if object_results:
            # Merge object detections (union of objects, max confidence summaries)
            merged_objects = {"objects": [], "relationships": [], "threat_summary": {}}
            for obj_result in object_results:
                if isinstance(obj_result, dict):
                    merged_objects["objects"].extend(obj_result.get("objects", []))
                    merged_objects["relationships"].extend(obj_result.get("relationships", []))
                    # Merge threat summaries (take max counts)
                    threat_summary = obj_result.get("threat_summary", {})
                    if isinstance(threat_summary, dict):
                        for key, value in threat_summary.items():
                            if isinstance(value, (int, float)):
                                merged_objects["threat_summary"][key] = max(
                                    merged_objects["threat_summary"].get(key, 0), value
                                )
            ai_results["objects"] = merged_objects

        # Run LLM analysis
        video = Video.query.get(video_id)
        location = video.camera.name if video and video.camera else "Unknown"
        timestamp = datetime.utcnow()

        start_time = time.time()
        llm_result, error = orchestrator.llm_analyzer.analyze_situation(ai_results, timestamp, location)
        llm_duration_ms = int((time.time() - start_time) * 1000)

        if error:
            logger.warning(f"LLM analysis failed for video {video_id}, using fallback: {error}")
            llm_result = orchestrator._fallback_analysis(ai_results)
            orchestrator._track_performance(
                "llm_analysis", "fallback", llm_duration_ms, video_id, "partial", str(error)
            )
        else:
            orchestrator._track_performance("llm_analysis", "llama3.2:1b", llm_duration_ms, video_id, "success")

        # Emit WebSocket event
        emit_llm_analysis_complete(video_id, llm_result.get("is_suspicious", False))

        return {
            "video_id": video_id,
            "llm_result": llm_result,
            "ai_results": ai_results,
            "frames": frames,
            "audio_path": audio_path,
        }

    except Exception as exc:
        video_id = extraction_result.get("video_id") if isinstance(extraction_result, dict) else None
        video_id = video_id or "<unknown>"
        logger.exception(f"AI aggregation task failed for video {video_id}")
        emit_analysis_error(video_id, str(exc))
        raise


@celery_app.task(name="src.tasks.analysis_tasks.handle_suspicious_result_task", bind=True)
def handle_suspicious_result_task(self, analysis_result: Dict) -> Dict:
    """Handle analysis result: create ticket, store evidence, send alert if suspicious."""
    try:
        video_id = analysis_result.get("video_id") if isinstance(analysis_result, dict) else None
        llm_result = analysis_result.get("llm_result", {}) if isinstance(analysis_result, dict) else {}
        ai_results = analysis_result.get("ai_results", {}) if isinstance(analysis_result, dict) else {}
        frames = analysis_result.get("frames", []) if isinstance(analysis_result, dict) else []
        audio_path = analysis_result.get("audio_path") if isinstance(analysis_result, dict) else None

        if not video_id:
            raise ValueError("video_id missing from analysis_result")

        orchestrator = AIOrchestrator()

        # Handle result (domain actions only - no status/event emission)
        orchestrator._handle_analysis_result(video_id, llm_result, ai_results, frames, audio_path)

        # Update video status
        video = Video.query.get(video_id)
        if video:
            result_type = (
                AnalysisResult.SUSPICIOUS if llm_result.get("is_suspicious", False) else AnalysisResult.CLEAN
            )
            video.mark_analyzed(result_type)
            db.session.commit()

        # Cleanup temporary files
        frames_dir = f"storage/frames/temp_{video_id}"
        audio_dir = f"storage/audio/temp_{video_id}"

        if os.path.exists(frames_dir) and not config.AI_ORCHESTRATOR_SAVE_TEMP_FILES:
            try:
                shutil.rmtree(frames_dir)
            except Exception as exc:
                logger.warning(f"Failed to cleanup frames directory: {exc}")

        if os.path.exists(audio_dir) and not config.AI_ORCHESTRATOR_SAVE_TEMP_FILES:
            try:
                shutil.rmtree(audio_dir)
            except Exception as exc:
                logger.warning(f"Failed to cleanup audio directory: {exc}")

        # Get ticket ID if suspicious
        ticket_id = None
        if llm_result.get("is_suspicious", False):
            from src.models.ticket import Ticket

            ticket = Ticket.query.filter_by(video_id=video_id).order_by(Ticket.created_at.desc()).first()
            if ticket:
                ticket_id = ticket.id

        # Emit WebSocket event (single source of emission)
        emit_analysis_complete(
            video_id,
            "suspicious" if llm_result.get("is_suspicious", False) else "clean",
            ticket_id,
            llm_result.get("threat_level"),
        )

        return {
            "video_id": video_id,
            "is_suspicious": llm_result.get("is_suspicious", False),
            "ticket_id": ticket_id,
        }

    except Exception as exc:
        video_id = analysis_result.get("video_id") if isinstance(analysis_result, dict) else None
        video_id = video_id or "<unknown>"
        logger.exception(f"Handle result task failed for video {video_id}")
        try:
            if video_id and video_id != "<unknown>":
                video = Video.query.get(video_id)
                if video:
                    video.mark_error(str(exc))
                    db.session.commit()
        except Exception:
            pass
        emit_analysis_error(video_id, str(exc))
        raise

