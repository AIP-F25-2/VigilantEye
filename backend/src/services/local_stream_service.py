import logging
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from src.app import db, socketio
from src.config.settings import get_config
from src.models.camera import Camera
from src.models.video import Video
from src.services.video_processor import VideoProcessorService
from src.utils.websocket_utils import emit_local_stream_frame_ack, emit_local_stream_error

logger = logging.getLogger(__name__)


class LocalStreamService:
    """Service for handling local camera stream frame buffering and processing."""

    def __init__(self, config: Optional[object] = None) -> None:
        self.config = config or get_config()
        self.storage_base_path = Path(self.config.STORAGE_BASE_PATH)
        self.frame_buffer_size = getattr(self.config, "LOCAL_STREAM_BUFFER_SIZE", 300)  # ~10 seconds at 30fps
        self.segment_duration_seconds = getattr(self.config, "LOCAL_STREAM_SEGMENT_DURATION", 10)
        self.max_concurrent_local_streams = getattr(self.config, "MAX_CONCURRENT_LOCAL_STREAMS", 4)

        # Active sessions: session_id -> session_info
        self.active_sessions: Dict[str, Dict] = {}
        self.sessions_lock = threading.Lock()

        self.video_processor = VideoProcessorService(config=self.config)

    def create_session(
        self, user_id: str, camera_name: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Create a new local stream session. Returns (session_id, video_id, camera_id)."""
        with self.sessions_lock:
            if len(self.active_sessions) >= self.max_concurrent_local_streams:
                error = "Maximum concurrent local streams reached"
                logger.error(error)
                return None, None, error

            session_id = str(uuid.uuid4())
            camera_id = str(uuid.uuid4())
            video_id = str(uuid.uuid4())

            # Create camera record
            camera_name = camera_name or f"Local Camera {session_id[:8]}"
            camera = Camera(
                id=camera_id,
                name=camera_name,
                stream_url="local-stream",  # Special marker for local streams
            )
            camera.mark_active()
            db.session.add(camera)

            # Create video record
            video = Video(
                id=video_id,
                filename=f"local-stream-{session_id[:8]}.mp4",
                filepath=f"local_streams/{video_id}.mp4",
                camera_id=camera_id,
                upload_type="stream",
                user_id=user_id,
            )
            video.mark_processing()
            video.set_video_ttl()
            db.session.add(video)
            db.session.commit()

            # Create session directory
            session_dir = self.storage_base_path / "local_streams" / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            frame_buffer: deque[Tuple[np.ndarray, float]] = deque(maxlen=self.frame_buffer_size)
            stop_event = threading.Event()

            self.active_sessions[session_id] = {
                "user_id": user_id,
                "camera_id": camera_id,
                "video_id": video_id,
                "session_dir": session_dir,
                "frame_buffer": frame_buffer,
                "stop_event": stop_event,
                "started_at": datetime.utcnow(),
                "last_frame_time": None,
                "frame_count": 0,
                "segment_thread": None,
            }

            logger.info(f"Created local stream session {session_id} for user {user_id}, video {video_id}")
            return session_id, video_id, None

    def add_frame(
        self, session_id: str, frame_data: bytes, timestamp: float, width: int, height: int
    ) -> Tuple[bool, Optional[str]]:
        """Add a frame to the session buffer. Returns (success, error_message)."""
        with self.sessions_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                error = f"Session {session_id} not found"
                logger.warning(error)
                return False, error

        try:
            # Decode JPEG frame to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return False, "Failed to decode frame"

            # Resize if needed (ensure consistent size)
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))

            with self.sessions_lock:
                session = self.active_sessions.get(session_id)
                if not session:
                    return False, "Session ended"

                frame_buffer: deque = session["frame_buffer"]
                frame_buffer.append((frame, timestamp))
                session["last_frame_time"] = timestamp
                session["frame_count"] += 1

                # Start segment thread if not running
                if session["segment_thread"] is None or not session["segment_thread"].is_alive():
                    thread = threading.Thread(
                        target=self._segment_worker,
                        args=(session_id,),
                        daemon=True,
                    )
                    session["segment_thread"] = thread
                    thread.start()

            emit_local_stream_frame_ack(session_id)
            return True, None

        except Exception as exc:
            logger.exception(f"Error adding frame to session {session_id}: {exc}")
            return False, str(exc)

    def stop_session(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """Stop a local stream session and finalize video. Returns (success, error_message)."""
        with self.sessions_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return True, None  # Already stopped

            stop_event: threading.Event = session["stop_event"]
            stop_event.set()

            camera_id = session["camera_id"]
            video_id = session["video_id"]

        # Wait for segment thread to finish
        if session.get("segment_thread"):
            session["segment_thread"].join(timeout=5.0)

        # Finalize video
        try:
            video = Video.query.get(video_id)
            if video:
                video.mark_ready()
                db.session.commit()

            camera = Camera.query.get(camera_id)
            if camera:
                camera.mark_inactive()
                db.session.commit()

            # Cleanup session from active sessions
            with self.sessions_lock:
                self.active_sessions.pop(session_id, None)

            logger.info(f"Stopped local stream session {session_id}")
            return True, None

        except Exception as exc:
            logger.exception(f"Error stopping session {session_id}: {exc}")
            return False, str(exc)

    def _segment_worker(self, session_id: str) -> None:
        """Worker thread that creates video segments from buffered frames."""
        session = None
        with self.sessions_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return

            session_dir: Path = session["session_dir"]
            frame_buffer: deque = session["frame_buffer"]
            stop_event: threading.Event = session["stop_event"]

        segment_index = 0
        last_segment_time = time.time()

        while not stop_event.is_set() or frame_buffer:
            current_time = time.time()

            # Check if it's time to create a new segment
            if current_time - last_segment_time >= self.segment_duration_seconds and frame_buffer:
                try:
                    segment_path = session_dir / f"segment_{segment_index:04d}.mp4"
                    success, error = self._create_segment(session_id, segment_path, frame_buffer)

                    if success:
                        logger.debug(f"Created segment {segment_index} for session {session_id}")
                        segment_index += 1
                        last_segment_time = current_time
                    else:
                        logger.warning(f"Failed to create segment for session {session_id}: {error}")
                except Exception as exc:
                    logger.exception(f"Error creating segment for session {session_id}: {exc}")

            time.sleep(1.0)  # Check every second

        # Create final segment with remaining frames
        if frame_buffer:
            try:
                segment_path = session_dir / f"segment_{segment_index:04d}.mp4"
                self._create_segment(session_id, segment_path, frame_buffer)
            except Exception as exc:
                logger.exception(f"Error creating final segment for session {session_id}: {exc}")

    def _create_segment(
        self, session_id: str, output_path: Path, frame_buffer: deque[Tuple[np.ndarray, float]]
    ) -> Tuple[bool, Optional[str]]:
        """Create a video segment from buffered frames."""
        if not frame_buffer:
            return False, "No frames to create segment"

        try:
            frames_to_write = list(frame_buffer)
            if not frames_to_write:
                return False, "No frames available"

            # Get frame dimensions
            first_frame = frames_to_write[0][0]
            height, width = first_frame.shape[:2]
            fps = 30.0  # Default FPS

            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

            try:
                for frame, _timestamp in frames_to_write:
                    out.write(frame)
            finally:
                out.release()

            # Queue segment for analysis (similar to RTSP stream processing)
            # This would trigger AI analysis on the segment
            logger.debug(f"Created segment {output_path} with {len(frames_to_write)} frames")

            return True, None

        except Exception as exc:
            logger.exception(f"Error creating segment {output_path}: {exc}")
            return False, str(exc)

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        with self.sessions_lock:
            return self.active_sessions.get(session_id)

