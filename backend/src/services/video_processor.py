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
from src.config import get_settings
from src.models.storage import FileType
from src.models.video import Video, VideoStatus
from src.repositories.video import VideoRepository
from src.services.storage_manager import StorageManager
from src.utils.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
settings = get_settings()


class VideoProcessingService:
    """Service for processing videos: extract frames and audio."""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """Initialize video processing service."""
        self.session = session
        if session:
            self.video_repository = VideoRepository(session)
        
        # Use absolute path relative to backend directory
        backend_dir = Path(__file__).parent.parent.parent
        
        # Create storage directories
        self.frames_path = backend_dir / "storage" / "frames"
        self.audio_path = backend_dir / "storage" / "audio"
        self.video_storage_path = backend_dir / "storage" / "videos"
        self.frames_path.mkdir(parents=True, exist_ok=True)
        self.audio_path.mkdir(parents=True, exist_ok=True)
        self.video_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Frame extraction interval in milliseconds
        self.frame_interval_ms = settings.frame_extraction_interval_ms

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

    def extract_frames(
        self,
        video_path: str,
        video_id: int,
        interval_ms: Optional[int] = None,
    ) -> Dict:
        """
        Extract frames from video at specified interval.
        
        Args:
            video_path: Path to video file
            video_id: Video ID (used for storage directory)
            interval_ms: Interval in milliseconds (uses config default if None)
            
        Returns:
            Dictionary with extraction results
        """
        if interval_ms is None:
            interval_ms = self.frame_interval_ms
        
        logger.info(f"Starting frame extraction: {video_path} with {interval_ms}ms interval")
        
        # Create directory for this video's frames: storage/videos/{video_id}/frames/
        video_dir = self.video_storage_path / str(video_id)
        frames_dir = video_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            raise ValueError("Could not open video file")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(
            f"Video properties - FPS: {fps}, Total frames: {total_frames}, "
            f"Duration: {duration_sec:.2f}s, Resolution: {width}x{height}"
        )
        
        # Calculate frame interval
        interval_sec = interval_ms / 1000.0
        frame_step = int(fps * interval_sec)
        
        if frame_step < 1:
            frame_step = 1
            logger.warning(f"Frame interval too small, extracting every frame")
        
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
            "video_id": video_id,
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
            f"from {total_frames} total frames for video {video_id}"
        )
        
        return result

    def extract_audio(
        self,
        video_path: str,
        video_id: int,
    ) -> Dict:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to video file
            video_id: Video ID (used for storage directory)
            
        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Starting audio extraction: {video_path}")

        # Create directory for this video's audio: storage/videos/{video_id}/audio/
        video_dir = self.video_storage_path / str(video_id)
        audio_dir = video_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Generate audio filename
        audio_filename = f"audio.wav"
        audio_file_path = audio_dir / audio_filename

        try:
            # Load video
            video_clip = VideoFileClip(video_path)

            # Check if video has audio
            if video_clip.audio is None:
                logger.warning(f"Video has no audio track: {video_path}")
                video_clip.close()
                return {
                    "video_id": video_id,
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
                "video_id": video_id,
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
            f"Starting video processing - Video ID: {video_id}, "
            f"Path: {video_path}"
        )

        start_time = datetime.now()

        try:
            # Extract frames
            logger.info("Step 1/2: Extracting frames...")
            frames_result = self.extract_frames(
                video_path=video_path,
                video_id=video_id,
                interval_ms=interval_ms
            )

            # Extract audio
            logger.info("Step 2/2: Extracting audio...")
            audio_result = self.extract_audio(
                video_path=video_path,
                video_id=video_id
            )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
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

            # Save complete processing metadata in video directory
            video_dir = self.video_storage_path / str(video_id)
            metadata_path = video_dir / "processing_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(result, f, indent=2)

            logger.info(
                f"Video processing completed successfully - "
                f"Video ID: {video_id}, "
                f"Time: {processing_time:.2f}s, "
                f"Frames: {frames_result['total_frames_extracted']}, "
                f"Audio: {audio_result.get('has_audio', False)}"
            )
            
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
