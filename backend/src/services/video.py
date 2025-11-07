"""Video service."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.video import Video, VideoStatus
from src.repositories.video import VideoRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VideoService:
    """Service for video operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.video_repository = VideoRepository(session)
        # Use absolute path relative to backend directory
        backend_dir = Path(__file__).parent.parent.parent
        self.storage_path = backend_dir / "storage" / "videos"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def upload_video(
        self,
        file: UploadFile,
        user_id: int,
        content: bytes,
    ) -> Video:
        """
        Upload and save video file.
        
        Args:
            file: Uploaded file
            user_id: User ID
            content: File content bytes
            
        Returns:
            Created video instance
        """
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create video record first to get video_id
        video = await self.video_repository.create(
            user_id=user_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path="",  # Will be updated after we know the video_id
            file_size=len(content),
            mime_type=file.content_type,
        )
        
        await self.session.flush()  # Flush to get video.id
        await self.session.refresh(video)  # Refresh to get the ID
        
        # Create video-specific directory: storage/{video_id}/
        video_dir = self.storage_path / str(video.id)
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Full file path: storage/{video_id}/{filename}
        file_path = video_dir / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Update video record with correct file path
        video.file_path = str(file_path)
        await self.session.commit()
        
        logger.info(f"Video uploaded: ID={video.id}, Path={file_path}")
        
        return video

    async def start_stream(
        self,
        user_id: int,
        metadata: Optional[dict] = None,
    ) -> Video:
        """
        Start a camera stream.
        
        Args:
            user_id: User ID
            metadata: Optional stream metadata
            
        Returns:
            Created video instance for stream
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"stream_{timestamp}_{uuid.uuid4()}.webm"
        
        # Create user directory
        user_dir = self.storage_path / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = user_dir / unique_filename
        
        # Create empty file
        file_path.touch()
        
        # Create video record
        video = await self.video_repository.create(
            user_id=user_id,
            filename=unique_filename,
            original_filename=f"Camera Stream {timestamp}",
            file_path=str(file_path),
            file_size=0,
            mime_type="video/webm",
            is_stream=True,
            stream_metadata=json.dumps(metadata) if metadata else None,
        )
        
        await self.session.commit()
        
        return video

    async def append_stream_chunk(
        self,
        video_id: int,
        user_id: int,
        chunk_data: bytes,
    ) -> None:
        """
        Append chunk to streaming video.
        
        Args:
            video_id: Video ID
            user_id: User ID
            chunk_data: Chunk data bytes
        """
        # Get video
        video = await self.video_repository.get_by_id(video_id)
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Check ownership
        if video.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload to this stream"
            )
        
        # Check if stream is active
        if video.status != VideoStatus.STREAMING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stream is not active"
            )
        
        # Append chunk to file
        file_path = Path(video.file_path)
        with open(file_path, 'ab') as f:
            f.write(chunk_data)
        
        # Update file size
        new_size = file_path.stat().st_size
        await self.video_repository.update_file_size(video_id, new_size)
        await self.session.commit()

    async def stop_stream(
        self,
        video_id: int,
        user_id: int,
    ) -> Video:
        """
        Stop a camera stream.
        
        Args:
            video_id: Video ID
            user_id: User ID
            
        Returns:
            Updated video instance
        """
        # Get video
        video = await self.video_repository.get_by_id(video_id)
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Check ownership
        if video.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to stop this stream"
            )
        
        # Update status
        video = await self.video_repository.update_status(
            video_id,
            VideoStatus.COMPLETED
        )
        
        # Update file size
        file_path = Path(video.file_path)
        if file_path.exists():
            file_size = file_path.stat().st_size
            await self.video_repository.update_file_size(video_id, file_size)
        
        await self.session.commit()
        
        # TODO: Extract video metadata in background task
        
        return video

    async def get_user_videos(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Video], int]:
        """
        Get videos for a user.
        
        Args:
            user_id: User ID
            skip: Number to skip
            limit: Maximum number to return
            
        Returns:
            Tuple of (videos list, total count)
        """
        return await self.video_repository.get_by_user(user_id, skip, limit)

    async def get_video(
        self,
        video_id: int,
        user_id: int,
    ) -> Optional[Video]:
        """
        Get video by ID.
        
        Args:
            video_id: Video ID
            user_id: User ID (for authorization)
            
        Returns:
            Video instance or None
        """
        video = await self.video_repository.get_by_id(video_id)
        
        if video and video.user_id != user_id:
            # User doesn't own this video
            return None
        
        return video

    async def delete_video(
        self,
        video_id: int,
        user_id: int,
    ) -> None:
        """
        Delete video and its file.
        
        Args:
            video_id: Video ID
            user_id: User ID (for authorization)
        """
        video = await self.video_repository.get_by_id(video_id)
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        if video.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this video"
            )
        
        # Delete video file
        file_path = Path(video.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted video file: {file_path}")
        
        # Delete analysis outputs (frames and audio folders)
        video_dir = self.storage_path / str(video_id)
        if video_dir.exists():
            import shutil
            try:
                shutil.rmtree(video_dir)
                logger.info(f"Deleted video directory and analysis outputs: {video_dir}")
            except Exception as e:
                logger.error(f"Failed to delete video directory {video_dir}: {e}")
        
        # Delete database record
        await self.video_repository.delete(video_id)
        await self.session.commit()
        
        logger.info(f"Video {video_id} and all associated files deleted successfully")
