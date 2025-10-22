"""Video processing service for frame extraction and audio separation."""
"""Video processing service for frame extraction and audio separation."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from typing import List
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
from PIL import Image
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.config import get_settings
from src.models.storage import FileType
from src.models.video import Video, VideoStatus
from src.repositories.video import VideoRepository
from src.services.storage_manager import StorageManager
from src.utils.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
settings = get_settings()
    """Application settings loaded from environment variables."""
    app_port: int = Field(default=8000, alias="APP_PORT")
class VideoProcessingService:
    """Service for processing videos: extract frames and audio."""
    db_password: str = Field(default="root", alias="DB_PASSWORD")
    def __init__(self, session: Optional[AsyncSession] = None):
        """Initialize video processing service."""
        self.session = session
        if session:
            self.video_repository = VideoRepository(session)
        
        # Create storage directories
        self.frames_path = Path(settings.frames_storage_path)
        self.audio_path = Path(settings.audio_storage_path)
        self.frames_path.mkdir(parents=True, exist_ok=True)
        self.audio_path.mkdir(parents=True, exist_ok=True)
        
        # Frame extraction interval in milliseconds
        self.frame_interval_ms = settings.frame_extraction_interval_ms
    redis_db: int = Field(default=0, alias="REDIS_DB")
    def _generate_processing_id(self, video_id: int, user_id: int) -> str:
        """
        Generate unique processing ID based on video, user, and timestamp.
        
        Format: v{video_id}_u{user_id}_{timestamp}
        Example: v123_u456_20240115_103045_789
        
        Args:
            video_id: Video ID
            user_id: User ID
            
        Returns:
            Unique processing ID string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        return f"v{video_id}_u{user_id}_{timestamp}"
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    def extract_frames(
        self,
        video_path: str,
        processing_id: str,
        interval_ms: Optional[int] = None,
    ) -> Dict:
        """
        Extract frames from video at specified interval.
        
        Args:
            video_path: Path to video file
            processing_id: Unique processing identifier
            interval_ms: Interval in milliseconds (uses config default if None)
            
        Returns:
            Dictionary with extraction results
        """
        if interval_ms is None:
            interval_ms = self.frame_interval_ms
    bcrypt_rounds: int = Field(default=12, alias="BCRYPT_ROUNDS")
        logger.info(f"Starting frame extraction: {video_path} with {interval_ms}ms interval")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
        # Create directory for this video's frames
        frames_dir = self.frames_path / processing_id
        frames_dir.mkdir(parents=True, exist_ok=True)
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")
        # Open video
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            raise ValueError("Could not open video file")
    audio_storage_path: str = Field(default="storage/audio", alias="AUDIO_STORAGE_PATH")
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    )
        logger.info(
            f"Video properties - FPS: {fps}, Total frames: {total_frames}, "
            f"Duration: {duration_sec:.2f}s, Resolution: {width}x{height}"
        )
        return v.lower()
        # Calculate frame interval
        interval_sec = interval_ms / 1000.0
        frame_step = int(fps * interval_sec)
        
        if frame_step < 1:
            frame_step = 1
            logger.warning(f"Frame interval too small, extracting every frame")
        return v_upper
        extracted_frames = []
        frame_count = 0
        extracted_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Extract frame at interval
            if frame_count % frame_step == 0:
                timestamp_ms = int((frame_count / fps) * 1000)
                
                # Generate frame filename
                # Format: frame_0000_0000ms.jpg
                frame_filename = f"frame_{extracted_count:04d}_{timestamp_ms:06d}ms.jpg"
                frame_path = frames_dir / frame_filename

                # Save frame as JPEG
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

                extracted_frames.append({
                    "filename": frame_filename,
                    "path": str(frame_path),
                    "timestamp_ms": timestamp_ms,
                    "frame_number": frame_count,
                    "sequence": extracted_count
                })

                extracted_count += 1

            frame_count += 1

        cap.release()

        result = {
            "processing_id": processing_id,
            "frames_directory": str(frames_dir),
            "total_frames_extracted": extracted_count,
            "extraction_interval_ms": interval_ms,
            "video_fps": fps,
            "video_duration_sec": duration_sec,
            "video_resolution": f"{width}x{height}",
            "frames": extracted_frames[:10]  # Include first 10 for reference
        }

        # Save metadata JSON
        metadata_path = frames_dir / "frames_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                **result,
                "frames": extracted_frames  # Include all frames in metadata
            }, f, indent=2)

        logger.info(
            f"Frame extraction completed: {extracted_count} frames extracted "
            f"from {total_frames} total frames"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    ) -> Dict:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to video file
            processing_id: Unique processing identifier
            
        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Starting audio extraction: {video_path}")

        # Create directory for this video's audio
        audio_dir = self.audio_path / processing_id
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Generate audio filename
        # Format: audio_{processing_id}.wav
        audio_filename = f"audio_{processing_id}.wav"
        audio_file_path = audio_dir / audio_filename

        try:
            # Load video
            video_clip = VideoFileClip(video_path)

            # Check if video has audio
            if video_clip.audio is None:
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
                logger.warning(f"Video has no audio track: {video_path}")
                video_clip.close()
                return {
                    "processing_id": processing_id,
                    "has_audio": False,
                    "message": "Video contains no audio track"
                }

            # Extract audio
            video_clip.audio.write_audiofile(
                str(audio_file_path),
                codec='pcm_s16le',  # WAV format
                verbose=False,
                logger=None
            )

            # Get audio properties
            duration = video_clip.audio.duration
            fps = video_clip.audio.fps
            nchannels = video_clip.audio.nchannels

            video_clip.close()

            # Get file size
            file_size = audio_file_path.stat().st_size

            result = {
                "processing_id": processing_id,
                "has_audio": True,
                "audio_directory": str(audio_dir),
                "audio_filename": audio_filename,
                "audio_path": str(audio_file_path),
                "duration_sec": duration,
                "sample_rate": fps,
                "channels": nchannels,
                "file_size_bytes": file_size,
                "format": "wav"
            }

            # Save metadata JSON
            metadata_path = audio_dir / "audio_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(result, f, indent=2)

            logger.info(
                f"Audio extraction completed: {duration:.2f}s, "
                f"{fps}Hz, {nchannels} channels, {file_size/1024/1024:.2f}MB"
            )

            return result

        except Exception as e:
            logger.error(f"Audio extraction failed: {str(e)}")
            raise

    def process_video(
        self,
        video_path: str,
        video_id: int,
        user_id: int,
        interval_ms: Optional[int] = None,
    ) -> Dict:
        """
        Complete video processing: extract frames and audio.
        
        Args:
            video_path: Path to video file
            video_id: Video ID
            user_id: User ID
            interval_ms: Frame extraction interval (uses config default if None)
            
        Returns:
            Dictionary with complete processing results
        """
        processing_id = self._generate_processing_id(video_id, user_id)
        
        logger.info(
            f"Starting video processing - ID: {processing_id}, "
            f"Video: {video_path}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

        start_time = datetime.now()

        try:
            # Extract frames
            logger.info("Step 1/2: Extracting frames...")
            frames_result = self.extract_frames(
                video_path=video_path,
                processing_id=processing_id,
                interval_ms=interval_ms
            )

            # Extract audio
            logger.info("Step 2/2: Extracting audio...")
            audio_result = self.extract_audio(
                video_path=video_path,
                processing_id=processing_id
            )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
    return Settings()
            result = {
                "processing_id": processing_id,
                "video_id": video_id,
                "user_id": user_id,
                "video_path": video_path,
                "status": "completed",
                "processing_time_sec": processing_time,
                "frames": frames_result,
                "audio": audio_result,
                "timestamp": datetime.now().isoformat()
            }

            # Save complete processing metadata
            processing_dir = Path(settings.video_storage_path).parent / "processing" / processing_id
            processing_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_path = processing_dir / "processing_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(result, f, indent=2)

            logger.info(
                f"Video processing completed successfully - "
                f"Processing ID: {processing_id}, "
                f"Time: {processing_time:.2f}s, "
                f"Frames: {frames_result['total_frames_extracted']}, "
                f"Audio: {audio_result.get('has_audio', False)}"
            )
        title="VigilantEYE API",
            return result

        except Exception as e:
            logger.error(f"Video processing failed: {str(e)}", exc_info=True)
            
            error_result = {
                "processing_id": processing_id,
                "video_id": video_id,
                "user_id": user_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return error_result
FRAME_EXTRACTION_INTERVAL_MS=30
    async def process_video_async(
        self,
        video: Video,
        interval_ms: Optional[int] = None,
    ) -> Dict:
        """
        Async wrapper for video processing with database updates.
        
        Args:
            video: Video model instance
            interval_ms: Frame extraction interval
            
        Returns:
            Processing results
        """
        try:
            # Update status to processing
            video.status = VideoStatus.PROCESSING
            if self.session:
                await self.session.commit()

            # Process video
            result = self.process_video(
                video_path=video.file_path,
                video_id=video.id,
                user_id=video.user_id,
                interval_ms=interval_ms
            )
            # Update video metadata
            if result["status"] == "completed":
                video.status = VideoStatus.COMPLETED
                video.duration = result["frames"]["video_duration_sec"]
                
                # Parse resolution
                resolution = result["frames"]["video_resolution"]
                if "x" in resolution:
                    width, height = map(int, resolution.split("x"))
                    video.width = width
                    video.height = height
                
                video.fps = result["frames"]["video_fps"]
                
                # Store processing results as JSON
                video.analysis_results = json.dumps(result)
            else:
                video.status = VideoStatus.FAILED
            if self.session:
                await self.session.commit()

            return result

        except Exception as e:
            logger.error(f"Async video processing failed: {str(e)}")
            
            # Update status to failed
            video.status = VideoStatus.FAILED
            if self.session:
                await self.session.commit()
            
            raise


def get_video_processor(session: Optional[AsyncSession] = None) -> VideoProcessingService:
    """
    Factory function to create video processor instance.
    
    Args:
        session: Optional database session
        
    Returns:
        VideoProcessingService instance
    """
    return VideoProcessingService(session)