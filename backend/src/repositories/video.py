"""Video repository."""

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.video import Video, VideoStatus


class VideoRepository:
    """Repository for Video model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        user_id: int,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: int = 0,
        mime_type: Optional[str] = None,
        is_stream: bool = False,
        stream_metadata: Optional[str] = None,
    ) -> Video:
        """
        Create a new video record.
        
        Args:
            user_id: User ID
            filename: Unique filename
            original_filename: Original filename
            file_path: Path to video file
            file_size: File size in bytes
            mime_type: MIME type
            is_stream: Whether this is a stream
            stream_metadata: Stream metadata JSON
            
        Returns:
            Created video instance
        """
        video = Video(
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            is_stream=is_stream,
            stream_metadata=stream_metadata,
            status=VideoStatus.STREAMING if is_stream else VideoStatus.UPLOADED,
        )
        self.session.add(video)
        await self.session.flush()
        await self.session.refresh(video)
        return video

    async def get_by_id(self, video_id: int) -> Optional[Video]:
        """
        Get video by ID.
        
        Args:
            video_id: Video ID
            
        Returns:
            Video instance or None
        """
        result = await self.session.execute(
            select(Video).where(Video.id == video_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Video], int]:
        """
        Get videos by user ID.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            Tuple of (videos list, total count)
        """
        # Get videos
        result = await self.session.execute(
            select(Video)
            .where(Video.user_id == user_id)
            .order_by(Video.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        videos = list(result.scalars().all())
        
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(Video).where(Video.user_id == user_id)
        )
        total = count_result.scalar_one()
        
        return videos, total

    async def update_status(
        self,
        video_id: int,
        status: VideoStatus
    ) -> Optional[Video]:
        """
        Update video status.
        
        Args:
            video_id: Video ID
            status: New status
            
        Returns:
            Updated video instance
        """
        video = await self.get_by_id(video_id)
        if video:
            video.status = status
            await self.session.flush()
            await self.session.refresh(video)
        return video

    async def update_file_size(
        self,
        video_id: int,
        file_size: int
    ) -> Optional[Video]:
        """
        Update video file size.
        
        Args:
            video_id: Video ID
            file_size: File size in bytes
            
        Returns:
            Updated video instance
        """
        video = await self.get_by_id(video_id)
        if video:
            video.file_size = file_size
            await self.session.flush()
            await self.session.refresh(video)
        return video

    async def update_metadata(
        self,
        video_id: int,
        duration: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        codec: Optional[str] = None,
    ) -> Optional[Video]:
        """
        Update video metadata.
        
        Args:
            video_id: Video ID
            duration: Video duration
            width: Video width
            height: Video height
            fps: Frames per second
            codec: Video codec
            
        Returns:
            Updated video instance
        """
        video = await self.get_by_id(video_id)
        if video:
            if duration is not None:
                video.duration = duration
            if width is not None:
                video.width = width
            if height is not None:
                video.height = height
            if fps is not None:
                video.fps = fps
            if codec is not None:
                video.codec = codec
            await self.session.flush()
            await self.session.refresh(video)
        return video

    async def delete(self, video_id: int) -> bool:
        """
        Delete video by ID.
        
        Args:
            video_id: Video ID
            
        Returns:
            True if deleted, False if not found
        """
        video = await self.get_by_id(video_id)
        if video:
            await self.session.delete(video)
            await self.session.flush()
            return True
        return False
