"""Video controller for upload and streaming."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.session import get_db
from src.dto.video import (
    VideoResponse,
    VideoUploadResponse,
    VideoListResponse,
    VideoStreamStartRequest,
)
from src.services.video import VideoService
from src.utils.logger import get_logger

from .dependencies import CurrentUser

router = APIRouter(prefix="/video", tags=["Video"])
logger = get_logger(__name__)
settings = get_settings()


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload video file",
    description="Upload a video file for analysis"
)
async def upload_video(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload video file endpoint.
    
    Accepts video files and stores them for processing.
    Returns video metadata and storage information.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only video files are allowed"
        )
    
    # Validate file size (max 500MB)
    max_size = 500 * 1024 * 1024  # 500MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 500MB limit"
        )
    
    await file.seek(0)  # Reset file pointer
    
    video_service = VideoService(db)
    
    try:
        video = await video_service.upload_video(
            file=file,
            user_id=current_user.id,
            content=content
        )
        
        logger.info(f"Video uploaded successfully: {video.id} by user {current_user.id}")
        
        return VideoUploadResponse(
            id=video.id,
            filename=video.filename,
            original_filename=video.original_filename,
            file_size=video.file_size,
            duration=video.duration,
            status=video.status,
            message="Video uploaded successfully"
        )
    
    except Exception as e:
        logger.error(f"Video upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )


@router.post(
    "/stream/start",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start camera stream",
    description="Initiate camera stream and save recording"
)
async def start_stream(
    request: VideoStreamStartRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Start camera stream endpoint.
    
    Creates a new video record for camera stream.
    Returns stream ID and storage information.
    """
    video_service = VideoService(db)
    
    try:
        video = await video_service.start_stream(
            user_id=current_user.id,
            metadata=request.metadata
        )
        
        logger.info(f"Stream started: {video.id} by user {current_user.id}")
        
        return VideoUploadResponse(
            id=video.id,
            filename=video.filename,
            original_filename=video.original_filename,
            file_size=0,
            duration=0,
            status=video.status,
            message="Stream started successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to start stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream: {str(e)}"
        )


@router.post(
    "/stream/{video_id}/chunk",
    status_code=status.HTTP_200_OK,
    summary="Upload stream chunk",
    description="Upload video chunk from camera stream"
)
async def upload_stream_chunk(
    video_id: int,
    chunk: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload stream chunk endpoint.
    
    Accepts video chunks from camera stream.
    Appends chunks to the video file.
    """
    video_service = VideoService(db)
    
    try:
        # Read chunk data
        chunk_data = await chunk.read()
        
        # Append chunk to video file
        await video_service.append_stream_chunk(
            video_id=video_id,
            user_id=current_user.id,
            chunk_data=chunk_data
        )
        
        return {"message": "Chunk uploaded successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload chunk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {str(e)}"
        )


@router.post(
    "/stream/{video_id}/stop",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop camera stream",
    description="Stop camera stream and finalize video"
)
async def stop_stream(
    video_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Stop camera stream endpoint.
    
    Finalizes the video file and updates status.
    """
    video_service = VideoService(db)
    
    try:
        video = await video_service.stop_stream(
            video_id=video_id,
            user_id=current_user.id
        )
        
        logger.info(f"Stream stopped: {video.id} by user {current_user.id}")
        
        return VideoUploadResponse(
            id=video.id,
            filename=video.filename,
            original_filename=video.original_filename,
            file_size=video.file_size,
            duration=video.duration,
            status=video.status,
            message="Stream stopped successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop stream: {str(e)}"
        )


@router.get(
    "/list",
    response_model=VideoListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user videos",
    description="Get list of videos uploaded by current user"
)
async def list_videos(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """
    List videos endpoint.
    
    Returns paginated list of user's videos.
    """
    video_service = VideoService(db)
    
    try:
        videos, total = await video_service.get_user_videos(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        return VideoListResponse(
            videos=[VideoResponse.model_validate(v) for v in videos],
            total=total,
            skip=skip,
            limit=limit
        )
    
    except Exception as e:
        logger.error(f"Failed to list videos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list videos: {str(e)}"
        )


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get video details",
    description="Get detailed information about a specific video"
)
async def get_video(
    video_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get video details endpoint.
    
    Returns detailed information about a specific video.
    """
    video_service = VideoService(db)
    
    try:
        video = await video_service.get_video(
            video_id=video_id,
            user_id=current_user.id
        )
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        return VideoResponse.model_validate(video)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video: {str(e)}"
        )


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete video",
    description="Delete a video and its associated files"
)
async def delete_video(
    video_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete video endpoint.
    
    Deletes video record and associated files.
    """
    video_service = VideoService(db)
    
    try:
        await video_service.delete_video(
            video_id=video_id,
            user_id=current_user.id
        )
        
        logger.info(f"Video deleted: {video_id} by user {current_user.id}")
        
        return {"message": "Video deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete video: {str(e)}"
        )


@router.get(
    "/{video_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download video",
    description="Download the video file"
)
async def download_video(
    video_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Download video endpoint.
    
    Returns the video file for download.
    """
    video_service = VideoService(db)
    
    try:
        video = await video_service.get_video(
            video_id=video_id,
            user_id=current_user.id
        )
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        file_path = Path(video.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video file not found on disk"
            )
        
        return FileResponse(
            path=str(file_path),
            media_type=video.mime_type or 'video/mp4',
            filename=video.original_filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download video: {str(e)}"
        )
