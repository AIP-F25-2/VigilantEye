"""Video processing controller."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.dto.video import VideoProcessingResponse, VideoProcessingRequest
from src.repositories.video import VideoRepository
from src.services.video_processor import VideoProcessingService
from src.utils.logger import get_logger

from .dependencies import CurrentUser

router = APIRouter(prefix="/video/process", tags=["Video Processing"])
logger = get_logger(__name__)


@router.post(
    "/{video_id}",
    response_model=VideoProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process video",
    description="Extract frames and audio from video"
)
async def process_video(
    video_id: int,
    request: VideoProcessingRequest = None,
    background_tasks: BackgroundTasks = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Start video processing.
    
    This will:
    1. Extract frames at specified interval (default 30ms)
    2. Extract audio track
    3. Store frames in organized directory structure
    4. Store audio as WAV file
    5. Generate metadata files
    """
    video_repository = VideoRepository(db)
    
    # Get video
    video = await video_repository.get_by_id(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to process this video"
        )
    
    # Create processor
    processor = VideoProcessingService(db)
    
    # Get interval from request or use default
    interval_ms = request.interval_ms if request else None
    
    # Process in background
    if background_tasks:
        background_tasks.add_task(
            processor.process_video_async,
            video=video,
            interval_ms=interval_ms
        )
        
        message = "Video processing started in background"
    else:
        # Process synchronously (for testing)
        result = await processor.process_video_async(video, interval_ms)
        message = "Video processing completed"
        
        return VideoProcessingResponse(
            video_id=video_id,
            status="completed",
            processing_id=result["processing_id"],
            message=message,
            frames_extracted=result["frames"]["total_frames_extracted"],
            audio_extracted=result["audio"].get("has_audio", False),
            processing_time_sec=result.get("processing_time_sec")
        )
    
    return VideoProcessingResponse(
        video_id=video_id,
        status="processing",
        processing_id=f"v{video_id}_u{current_user.id}",
        message=message
    )


@router.get(
    "/{video_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Get processing status",
    description="Check video processing status"
)
async def get_processing_status(
    video_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get video processing status.
    
    Returns current processing status and results if available.
    """
    video_repository = VideoRepository(db)
    
    # Get video
    video = await video_repository.get_by_id(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this video"
        )
    
    return {
        "video_id": video_id,
        "status": video.status.value,
        "has_results": video.analysis_results is not None,
        "duration": video.duration,
        "resolution": f"{video.width}x{video.height}" if video.width and video.height else None,
        "fps": video.fps,
    }
