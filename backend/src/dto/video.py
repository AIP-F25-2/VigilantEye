"""Video DTOs."""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.models.video import VideoStatus
from .base import BaseDTO


class VideoUploadResponse(BaseDTO):
    """Video upload response schema."""

    id: int
    filename: str
    original_filename: str
    file_size: int
    duration: Optional[float] = None
    status: VideoStatus
    message: str


class VideoResponse(BaseDTO):
    """Video response schema."""

    id: int
    user_id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    status: VideoStatus
    thumbnail_path: Optional[str] = None
    is_stream: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        use_enum_values = True


class VideoListResponse(BaseDTO):
    """Video list response schema."""

    videos: List[VideoResponse]
    total: int
    skip: int
    limit: int


class VideoStreamStartRequest(BaseDTO):
    """Request to start video stream."""

    metadata: Optional[dict] = Field(
        default=None,
        description="Optional metadata for the stream"
    )
