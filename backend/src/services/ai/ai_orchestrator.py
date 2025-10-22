"""AI Orchestrator - Coordinates all AI analysis tasks in parallel."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.ai_config import AIConfig
from src.models.ai_analysis import (
    AnalysisStatus,
    AudioAnalysis,
    FaceDetection,
    FaceVector,
    ImageAnalysis,
    ThreatAssessment,
)
from src.repositories.storage import StorageRepository
from src.services.ai.audio_services import process_audio_parallel
from src.services.ai.face_recognition_service import analyze_faces_in_image
from src.services.ai.image_analysis_service import analyze_image_complete
from src.services.ai.threat_detection_service import detect_threats_in_frame
from src.services.ai.clothing_recognition_service import analyze_persons_in_image
from src.services.ai.threadpool_manager import get_ai_threadpool
from src.services.ai.vector_db_manager import VectorDBManager, find_or_create_face_id
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class AIOrchestrator:
    """Orchestrate all AI analysis tasks with parallel processing."""

    def __init__(self, session: AsyncSession):
        """
        Initialize AI orchestrator.
        
        Args:
            session: Database session
        """
        self.session = session
        self.storage_repository = StorageRepository(session)
        self.threadpool = get_ai_threadpool()
        self.vector_db = VectorDBManager()
        logger.info("AI Orchestrator initialized")

    async def process_video_analysis(
        self,
        processing_id: str,
        video_id: int,
        user_id: int,
        frames_dir: Path,
        audio_path: Optional[Path] = None
    ) -> Dict:
        """
        Process complete video analysis with all AI services.
        
        This orchestrates:
        1. Audio analysis (2 parallel tasks)
        2. Frame analysis (3 parallel tasks per frame)
        3. Threat detection with evidence storage
        
        Args:
            processing_id: Processing batch ID
            video_id: Video ID
            user_id: User ID
            frames_dir: Directory containing extracted frames
            audio_path: Optional path to audio file
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting AI orchestration for: {processing_id}")
        
        results = {
            'processing_id': processing_id,
            'video_id': video_id,
            'audio_analysis': None,
            'frame_analyses': [],
            'threats_detected': 0,
            'faces_detected': 0,
            'status': 'processing'
        }
        
        try:
            # Step 1: Process Audio (if available)
            if audio_path and audio_path.exists():
                logger.info("Step 1/3: Processing audio...")
                audio_result = await self._process_audio(
                    str(audio_path),
                    video_id,
                    processing_id
                )
                results['audio_analysis'] = audio_result
            else:
                logger.info("No audio file, skipping audio analysis")
                audio_result = None
            
            # Step 2: Get all frames
            frames = list(frames_dir.glob("frame_*.jpg"))
            logger.info(f"Step 2/3: Processing {len(frames)} frames...")
            
            # Batch process frames (to avoid overwhelming the system)
            batch_size = ai_config.ai_batch_size
            frame_results = []
            
            for i in range(0, len(frames), batch_size):
                batch = frames[i:i + batch_size]
                logger.info(f"Processing frame batch {i//batch_size + 1}/{(len(frames) + batch_size - 1)//batch_size}")
                
                batch_results = await self._process_frame_batch(
                    batch,
                    video_id,
                    processing_id,
                    audio_result
                )
                frame_results.extend(batch_results)
            
            results['frame_analyses'] = frame_results
            
            # Step 3: Count threats and faces
            threats = sum(1 for r in frame_results if r.get('threat_assessment', {}).get('is_threat'))
            faces = sum(r.get('face_count', 0) for r in frame_results)
            
            results['threats_detected'] = threats
            results['faces_detected'] = faces
            results['status'] = 'completed'
            
            logger.info(
                f"AI orchestration completed: {processing_id}\n"
                f"  - Frames processed: {len(frame_results)}\n"
                f"  - Threats detected: {threats}\n"
                f"  - Faces detected: {faces}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"AI orchestration failed: {e}", exc_info=True)
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    async def _process_audio(
        self,
        audio_path: str,
        video_id: int,
        processing_id: str
    ) -> Dict:
        """Process audio with parallel classification and transcription."""
        try:
            # Run audio processing in threadpool
            result = await self.threadpool.submit_batch_async(
                process_audio_parallel,
                [audio_path]
            )
            
            audio_result = result[0] if result else {}
            
            # Save to database
            await self._save_audio_analysis(
                video_id,
                processing_id,
                audio_result
            )
            
            return audio_result
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return {'error': str(e)}

    async def _process_frame_batch(
        self,
        frames: List[Path],
        video_id: int,
        processing_id: str,
        audio_result: Optional[Dict]
    ) -> List[Dict]:
        """Process a batch of frames with parallel AI tasks."""
        
        # Parse frame timestamps
        frame_data = []
        for frame_path in frames:
            # Extract timestamp from filename: frame_0001_000030ms.jpg
            filename = frame_path.stem
            parts = filename.split('_')
            timestamp_str = parts[-1]  # "000030ms"
            timestamp_ms = int(timestamp_str.replace('ms', ''))
            
            frame_data.append({
                'path': str(frame_path),
                'timestamp_ms': timestamp_ms
            })
        
        # Prepare parallel tasks for each frame
        all_tasks = []
        
        for frame in frame_data:
            # Task 1: Face analysis
            all_tasks.append({
                'func': analyze_faces_in_image,
                'args': (frame['path'], frame['timestamp_ms']),
                'kwargs': {},
                'frame_path': frame['path'],
                'task_type': 'face'
            })
            
            # Task 2: Image analysis (objects, OCR, scene)
            all_tasks.append({
                'func': analyze_image_complete,
                'args': (frame['path'], frame['timestamp_ms']),
                'kwargs': {},
                'frame_path': frame['path'],
                'task_type': 'image'
            })
            
            # Task 3: Person/Clothing analysis
            all_tasks.append({
                'func': analyze_persons_in_image,
                'args': (frame['path'], frame['timestamp_ms']),
                'kwargs': {},
                'frame_path': frame['path'],
                'task_type': 'person'
            })
        
        # Execute all tasks in parallel
        task_list = [
            {'func': t['func'], 'args': t['args'], 'kwargs': t['kwargs']}
            for t in all_tasks
        ]
        
        raw_results = self.threadpool.parallel_process(task_list)
        
        # Organize results by frame
        frame_results_map = {}
        
        for i, task_info in enumerate(all_tasks):
            frame_path = task_info['frame_path']
            task_type = task_info['task_type']
            result = raw_results[i]
            
            if frame_path not in frame_results_map:
                frame_results_map[frame_path] = {
                    'frame_path': frame_path,
                    'timestamp_ms': next(f['timestamp_ms'] for f in frame_data if f['path'] == frame_path)
                }
            
            frame_results_map[frame_path][task_type] = result
        
        # Now run threat detection for each frame (needs all previous results)
        final_results = []
        
        for frame_path, combined_result in frame_results_map.items():
            # Task 3: Threat detection (uses results from face, image, and person analysis)
            threat_result = await self._run_threat_detection(
                frame_path,
                combined_result['timestamp_ms'],
                combined_result.get('image', {}),
                combined_result.get('face', {}),
                combined_result.get('person', {}),
                audio_result,
                processing_id
            )
            
            combined_result['threat'] = threat_result
            
            # Save to database
            await self._save_frame_analysis(
                video_id,
                processing_id,
                combined_result
            )
            
            # Prepare summary
            summary = {
                'frame_path': frame_path,
                'timestamp_ms': combined_result['timestamp_ms'],
                'face_count': combined_result.get('face', {}).get('face_count', 0),
                'person_count': combined_result.get('person', {}).get('person_count', 0),
                'object_count': combined_result.get('image', {}).get('objects', {}).get('total_objects', 0),
                'has_text': combined_result.get('image', {}).get('text', {}).get('has_text', False),
                'is_threat': threat_result.get('threat_assessment', {}).get('is_threat', False),
                'threat_level': threat_result.get('threat_assessment', {}).get('threat_level', 'SAFE'),
                'status': 'completed'
            }
            
            final_results.append(summary)
        
        return final_results

    async def _run_threat_detection(
        self,
        frame_path: str,
        timestamp_ms: int,
        image_analysis: Dict,
        face_analysis: Dict,
        person_analysis: Dict,
        audio_analysis: Optional[Dict],
        processing_id: str
    ) -> Dict:
        """Run threat detection in threadpool."""
        try:
            result = await self.threadpool.submit_batch_async(
                detect_threats_in_frame,
                [(frame_path, timestamp_ms, image_analysis, face_analysis, person_analysis, audio_analysis, processing_id)]
            )
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"Threat detection failed: {e}")
            return {'error': str(e)}

    async def _save_audio_analysis(
        self,
        video_id: int,
        processing_id: str,
        audio_result: Dict
    ) -> None:
        """Save audio analysis to database."""
        try:
            # Get storage file ID for audio
            storage_files = await self.storage_repository.get_by_processing_id(processing_id)
            audio_file = next((f for f in storage_files if f.file_type.value == 'AUDIO'), None)
            
            if not audio_file:
                logger.warning("Audio storage file not found")
                return
            
            classification = audio_result.get('classification', {})
            transcription = audio_result.get('transcription', {})
            
            audio_analysis = AudioAnalysis(
                video_id=video_id,
                storage_file_id=audio_file.id,
                processing_id=processing_id,
                sound_classification=json.dumps(classification.get('all_sounds', [])),
                dominant_sounds=', '.join(classification.get('dominant_sounds', [])),
                transcription=transcription.get('transcription', ''),
                language_detected=transcription.get('language', 'unknown'),
                confidence_score=transcription.get('confidence', 0.0),
                status=AnalysisStatus.COMPLETED
            )
            
            self.session.add(audio_analysis)
            await self.session.flush()
            
            logger.debug("Audio analysis saved to database")
            
        except Exception as e:
            logger.error(f"Failed to save audio analysis: {e}")

    async def _save_frame_analysis(
        self,
        video_id: int,
        processing_id: str,
        frame_result: Dict
    ) -> None:
        """Save frame analysis results to database."""
        try:
            frame_path = frame_result['frame_path']
            timestamp_ms = frame_result['timestamp_ms']
            
            # Get storage file for this frame
            storage_files = await self.storage_repository.get_by_processing_id(processing_id)
            frame_file = next(
                (f for f in storage_files if f.file_path == frame_path),
                None
            )
            
            if not frame_file:
                logger.warning(f"Frame storage file not found: {frame_path}")
                return
            
            # Save image analysis
            await self._save_image_analysis_record(
                video_id,
                frame_file.id,
                processing_id,
                timestamp_ms,
                frame_result.get('image', {})
            )
            
            # Save face detections
            await self._save_face_detections(
                video_id,
                frame_file.id,
                processing_id,
                timestamp_ms,
                frame_result.get('face', {})
            )
            
            # Save threat assessment
            await self._save_threat_assessment(
                video_id,
                frame_file.id,
                processing_id,
                timestamp_ms,
                frame_result.get('threat', {}),
                frame_result.get('image', {})
            )
            
        except Exception as e:
            logger.error(f"Failed to save frame analysis: {e}")

    async def _save_image_analysis_record(
        self,
        video_id: int,
        frame_storage_id: int,
        processing_id: str,
        timestamp_ms: int,
        image_result: Dict
    ) -> None:
        """Save image analysis record."""
        try:
            objects = image_result.get('objects', {})
            text_data = image_result.get('text', {})
            scene = image_result.get('scene', {})
            
            image_analysis = ImageAnalysis(
                frame_storage_id=frame_storage_id,
                video_id=video_id,
                processing_id=processing_id,
                frame_timestamp_ms=timestamp_ms,
                scene_description=scene.get('location_type', ''),
                location_type=scene.get('location_type', ''),
                time_of_day=scene.get('time_of_day', ''),
                weather_conditions=scene.get('weather_conditions', ''),
                lighting_quality=scene.get('lighting_quality', ''),
                detected_text=text_data.get('full_text', ''),
                text_locations=json.dumps(text_data.get('detected_texts', [])),
                detected_objects=json.dumps(objects.get('objects', [])),
                object_count=objects.get('total_objects', 0),
                people_count=objects.get('people_count', 0),
                vehicle_count=objects.get('vehicle_count', 0),
                combined_description=image_result.get('combined_description', ''),
                status=AnalysisStatus.COMPLETED
            )
            
            self.session.add(image_analysis)
            await self.session.flush()
            
        except Exception as e:
            logger.error(f"Failed to save image analysis: {e}")

    async def _save_face_detections(
        self,
        video_id: int,
        frame_storage_id: int,
        processing_id: str,
        timestamp_ms: int,
        face_result: Dict
    ) -> None:
        """Save face detections and update vector DB."""
        try:
            faces = face_result.get('faces', [])
            
            for face_data in faces:
                embedding = face_data.get('embedding')
                
                # Find or create face ID in vector DB
                if embedding:
                    embedding_array = np.array(embedding)
                    face_match = find_or_create_face_id(
                        embedding_array,
                        {
                            'age': face_data.get('estimated_age'),
                            'gender': face_data.get('gender'),
                            'emotion': face_data.get('emotion')
                        },
                        self.vector_db
                    )
                    face_id = face_match['face_id']
                    vector_id = face_match['vector_id']
                else:
                    face_id = face_data.get('face_id', f"face_{timestamp_ms}")
                    vector_id = None
                
                # Save face detection
                face_detection = FaceDetection(
                    frame_storage_id=frame_storage_id,
                    video_id=video_id,
                    processing_id=processing_id,
                    face_id=face_id,
                    bounding_box=json.dumps(face_data.get('bounding_box', {})),
                    confidence=face_data.get('confidence', 0.0),
                    estimated_age=face_data.get('estimated_age'),
                    age_range=face_data.get('age_range'),
                    gender=face_data.get('gender'),
                    gender_confidence=face_data.get('gender_confidence'),
                    skin_tone=face_data.get('ethnicity'),
                    facial_expression=face_data.get('emotion'),
                    emotion_confidence=face_data.get('emotion_confidence'),
                    vector_id=vector_id,
                    frame_timestamp_ms=timestamp_ms
                )
                
                self.session.add(face_detection)
            
            await self.session.flush()
            
        except Exception as e:
            logger.error(f"Failed to save face detections: {e}")

    async def _save_threat_assessment(
        self,
        video_id: int,
        frame_storage_id: int,
        processing_id: str,
        timestamp_ms: int,
        threat_result: Dict,
        image_result: Dict
    ) -> None:
        """Save threat assessment."""
        try:
            assessment = threat_result.get('threat_assessment', {})
            evidence_info = threat_result.get('evidence_info', {})
            
            threat_record = ThreatAssessment(
                frame_storage_id=frame_storage_id,
                video_id=video_id,
                processing_id=processing_id,
                frame_timestamp_ms=timestamp_ms,
                is_threat=assessment.get('is_threat', False),
                threat_level=assessment.get('threat_level', 'SAFE'),
                threat_confidence=assessment.get('threat_confidence', 0.0),
                threat_types=', '.join(assessment.get('threat_types', [])),
                threat_description=assessment.get('threat_description', ''),
                is_emergency=assessment.get('is_emergency', False),
                emergency_type=assessment.get('emergency_type'),
                evidence_stored=evidence_info.get('evidence_stored', False),
                evidence_path=evidence_info.get('evidence_path'),
                recommended_action=assessment.get('recommended_action'),
                priority_level=assessment.get('priority_level', 0)
            )
            
            self.session.add(threat_record)
            await self.session.flush()
            
        except Exception as e:
            logger.error(f"Failed to save threat assessment: {e}")


import numpy as np  # Add this import at the top
