import logging
import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from src.app import db
from src.config.settings import get_config
from src.models.video import Video


logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Raised when a video processing operation fails."""


class StreamError(Exception):
    """Raised when stream management encounters an error."""


class VideoProcessorService:
    """Service responsible for video processing and stream management."""

    def __init__(self, config: Optional[object] = None) -> None:
        self.config = config or get_config()
        self.frame_interval_seconds = self.config.FRAME_EXTRACTION_INTERVAL
        self.motion_threshold = self.config.MOTION_DETECTION_THRESHOLD
        self.max_concurrent_streams = self.config.MAX_CONCURRENT_STREAMS
        self.storage_base_path = Path(self.config.STORAGE_BASE_PATH)
        self.thumbnail_size = (
            int(getattr(self.config, "THUMBNAIL_WIDTH", 320)),
            int(getattr(self.config, "THUMBNAIL_HEIGHT", 240)),
        )
        self.max_resolution_width = getattr(self.config, "MAX_RESOLUTION_WIDTH", 3840)
        self.max_resolution_height = getattr(
            self.config, "MAX_RESOLUTION_HEIGHT", 2160
        )
        self.max_video_size_mb = getattr(self.config, "MAX_VIDEO_SIZE_MB", 500)
        self.frame_buffer_size = getattr(self.config, "FRAME_BUFFER_SIZE", 100)
        self.ffmpeg_path = getattr(self.config, "FFMPEG_PATH", "ffmpeg")
        self.ffprobe_path = getattr(self.config, "FFPROBE_PATH", None)

        self.active_streams: Dict[str, Dict[str, object]] = {}
        self.streams_lock = threading.Lock()

        if self.ffmpeg_path:
            AudioSegment.converter = self.ffmpeg_path
            AudioSegment.ffmpeg = self.ffmpeg_path
            os.environ.setdefault("FFMPEG_BINARY", self.ffmpeg_path)

        if self.ffprobe_path:
            AudioSegment.ffprobe = self.ffprobe_path
            os.environ.setdefault("FFPROBE_BINARY", self.ffprobe_path)

        self.ffmpeg_available = self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> bool:
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("FFmpeg binary not available: %s", exc)
            return False

    def extract_metadata(
        self, video_path: str
    ) -> Tuple[Optional[Dict[str, object]], Optional[Exception]]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Unable to open video for metadata extraction: %s", video_path)
            return None, VideoProcessingError("Unable to open video file")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration = float(frame_count / fps) if fps > 0 else 0.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            resolution = f"{width}x{height}" if width and height else ""
            metadata = {
                "duration": duration,
                "fps": fps,
                "resolution": resolution,
                "width": width,
                "height": height,
                "frame_count": frame_count,
            }
            return metadata, None
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Failed extracting metadata for %s", video_path)
            return None, exc
        finally:
            cap.release()

    def generate_thumbnail(
        self, video_path: str, output_path: str, size: Tuple[int, int] | None = None
    ) -> Tuple[bool, Optional[Exception]]:
        target_size = size or self.thumbnail_size
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Unable to open video for thumbnail generation: %s", video_path)
            return False, VideoProcessingError("Unable to open video file")

        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.error("No frames available for thumbnail from %s", video_path)
                return False, VideoProcessingError("Unable to read frame for thumbnail")

            thumbnail = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(output_path, thumbnail)
            return True, None
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Failed generating thumbnail for %s", video_path)
            return False, exc
        finally:
            cap.release()

    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        interval: float | None = None,
        use_motion_detection: bool = True,
    ) -> Tuple[List[str], Optional[Exception]]:
        frame_interval_seconds = interval or self.frame_interval_seconds
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            logger.error("Unable to open video for frame extraction: %s", video_path)
            return [], VideoProcessingError("Unable to open video file")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            if fps <= 0:
                fps = 30.0
            frame_interval = max(int(fps * frame_interval_seconds), 1)

            extracted_frames: List[str] = []
            prev_frame: Optional[np.ndarray] = None
            frame_number = 0
            saved_index = 0

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_number % frame_interval != 0:
                    frame_number += 1
                    continue

                save_frame = True

                if use_motion_detection:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.GaussianBlur(gray, (21, 21), 0)

                    if prev_frame is not None:
                        frame_delta = cv2.absdiff(prev_frame, gray)
                        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                        motion_score = 0.0
                        non_zero = cv2.countNonZero(thresh)
                        if thresh.size > 0:
                            motion_score = float(non_zero) / float(thresh.size)
                        if motion_score < self.motion_threshold:
                            save_frame = False
                    prev_frame = gray.copy()

                if save_frame:
                    frame_path = os.path.join(
                        output_dir, f"frame_{saved_index:06d}.jpg"
                    )
                    cv2.imwrite(frame_path, frame)
                    extracted_frames.append(frame_path)
                    saved_index += 1

                frame_number += 1

            return extracted_frames, None
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Failed extracting frames from %s", video_path)
            return [], exc
        finally:
            cap.release()

    def extract_audio(
        self, video_path: str, output_path: str
    ) -> Tuple[bool, Optional[Exception]]:
        if not self.ffmpeg_available:
            error = VideoProcessingError("FFmpeg is not available for audio extraction")
            logger.error(str(error))
            return False, error

        try:
            audio = AudioSegment.from_file(video_path)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            audio.export(output_path, format="wav")
            return True, None
        except CouldntDecodeError:
            logger.warning("Video has no decodable audio track: %s", video_path)
            return False, None
        except FileNotFoundError as exc:
            logger.error("FFmpeg binary not found when extracting audio: %s", exc)
            return False, exc
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Failed extracting audio from %s", video_path)
            return False, exc

    def validate_video(self, video_path: str) -> Tuple[bool, Optional[str]]:
        if not os.path.exists(video_path):
            logger.error("Video file not found: %s", video_path)
            return False, "Video file does not exist"

        file_size = os.path.getsize(video_path)
        if file_size > self.max_video_size_mb * 1024 * 1024:
            logger.error("Video file exceeds maximum size: %s", video_path)
            return False, "Video file exceeds maximum allowed size"

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Video file cannot be opened for validation: %s", video_path)
            return False, "Video file cannot be opened"

        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.error("Video file contains no readable frames: %s", video_path)
                return False, "Video file contains no frames"

            height, width = frame.shape[:2]
            if width > self.max_resolution_width or height > self.max_resolution_height:
                logger.error("Video resolution exceeds limits: %s", video_path)
                return False, "Video resolution exceeds allowed limits"
        finally:
            cap.release()

        return True, None

    def process_uploaded_video(
        self, video: Video
    ) -> Tuple[Optional[Video], Optional[Exception]]:
        video_path = video.get_storage_path()
        logger.info("Starting processing for uploaded video %s", video.id)

        try:
            video.mark_processing()
            db.session.commit()

            metadata, error = self.extract_metadata(video_path)
            if error:
                raise VideoProcessingError(str(error))

            if metadata:
                video.duration = metadata.get("duration")
                video.fps = metadata.get("fps")
                video.resolution = metadata.get("resolution")
                db.session.commit()

            thumbnail_path = self._build_thumbnail_path(video_path)
            success, thumb_error = self.generate_thumbnail(
                video_path, thumbnail_path, self.thumbnail_size
            )
            if not success and thumb_error:
                logger.warning(
                    "Thumbnail generation failed for %s: %s", video.id, thumb_error
                )

            video.mark_ready()
            db.session.commit()
            logger.info("Video processing completed successfully for %s", video.id)
            return video, None
        except Exception as exc:
            logger.exception("Video processing failed for %s", video.id)
            db.session.rollback()
            try:
                video.mark_error(str(exc))
                db.session.commit()
            except Exception:
                db.session.rollback()
            return None, exc

    def start_stream(
        self,
        camera_id: str,
        stream_url: str,
        frame_callback: Optional[Callable[[str, np.ndarray], None]] = None,
    ) -> Tuple[bool, Optional[Exception]]:
        with self.streams_lock:
            if len(self.active_streams) >= self.max_concurrent_streams:
                error = StreamError("Maximum concurrent streams reached")
                logger.error(str(error))
                return False, error

            if camera_id in self.active_streams:
                error = StreamError("Stream already active for this camera")
                logger.error(str(error))
                return False, error

            stop_event = threading.Event()
            frame_buffer: deque[np.ndarray] = deque(maxlen=self.frame_buffer_size)

            thread = threading.Thread(
                target=self._stream_worker,
                args=(camera_id, stream_url, stop_event, frame_buffer, frame_callback),
                daemon=True,
            )

            self.active_streams[camera_id] = {
                "thread": thread,
                "stop_event": stop_event,
                "frame_buffer": frame_buffer,
                "stream_url": stream_url,
                "started_at": datetime.utcnow(),
                "capture": None,
            }

        thread.start()
        logger.info("Started stream for camera %s", camera_id)
        return True, None

    def stop_stream(self, camera_id: str) -> Tuple[bool, Optional[Exception]]:
        capture_to_release: Optional[cv2.VideoCapture] = None
        with self.streams_lock:
            stream_info = self.active_streams.get(camera_id)
            if not stream_info:
                logger.info("Stop requested for camera %s but no active stream found", camera_id)
                return True, None

            stop_event: threading.Event = stream_info["stop_event"]  # type: ignore[assignment]
            thread: threading.Thread = stream_info["thread"]  # type: ignore[assignment]
            capture_to_release = stream_info.get("capture")  # type: ignore[assignment]
            if capture_to_release is not None:
                stream_info["capture"] = None

        stop_event.set()
        if capture_to_release is not None:
            try:
                capture_to_release.release()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to release capture for camera %s: %s",
                    camera_id,
                    exc,
                )
        thread.join(timeout=5.0)

        with self.streams_lock:
            stream_info = self.active_streams.pop(camera_id, None)
            remaining_capture = None if not stream_info else stream_info.get("capture")

        if thread.is_alive():
            logger.warning("Stream worker thread did not terminate within timeout for %s", camera_id)

        if remaining_capture is not None:
            try:
                remaining_capture.release()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to release capture after stop for camera %s: %s",
                    camera_id,
                    exc,
                )

        logger.info("Stopped stream for camera %s", camera_id)
        return True, None

    def get_stream_frame(
        self, camera_id: str
    ) -> Tuple[Optional[np.ndarray], Optional[Exception]]:
        with self.streams_lock:
            stream_info = self.active_streams.get(camera_id)
            if not stream_info:
                error = StreamError("Stream not found for the specified camera")
                logger.error(str(error))
                return None, error

            frame_buffer: deque[np.ndarray] = stream_info["frame_buffer"]  # type: ignore[assignment]

            if not frame_buffer:
                return None, None

            return frame_buffer[-1], None

    def _stream_worker(
        self,
        camera_id: str,
        stream_url: str,
        stop_event: threading.Event,
        frame_buffer: deque,
        frame_callback: Optional[Callable[[str, np.ndarray], None]],
    ) -> None:
        retry_count = 0
        max_retries = 3

        while not stop_event.is_set():
            cap = cv2.VideoCapture(stream_url)
            with self.streams_lock:
                stream_info = self.active_streams.get(camera_id)
                if stream_info is not None:
                    stream_info["capture"] = cap

            if not cap.isOpened():
                with self.streams_lock:
                    stream_info = self.active_streams.get(camera_id)
                    if stream_info and stream_info.get("capture") is cap:
                        stream_info["capture"] = None
                cap.release()
                retry_delay = min(2 ** retry_count, 30)
                logger.warning(
                    "Failed to open stream for camera %s. Retrying in %s seconds",
                    camera_id,
                    retry_delay,
                )
                time.sleep(retry_delay)
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(
                        "Exceeded maximum retries for camera %s stream; stopping",
                        camera_id,
                    )
                    with self.streams_lock:
                        removed = self.active_streams.pop(camera_id, None)
                        if removed is not None:
                            logger.info(
                                "Stream for camera %s removed from registry after retry exhaustion",
                                camera_id,
                            )
                    break
                continue

            retry_count = 0
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            if fps <= 0:
                fps = 30.0
            frame_delay = 1.0 / fps

            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning(
                        "Stream read failed for camera %s; attempting reconnection",
                        camera_id,
                    )
                    break

                with self.streams_lock:
                    buffer = self.active_streams.get(camera_id, {}).get("frame_buffer")
                    if buffer is not None:
                        buffer.append(frame)

                if frame_callback:
                    try:
                        frame_callback(camera_id, frame)
                    except Exception as exc:  # pragma: no cover - callback safety net
                        logger.exception("Frame callback failed for camera %s", camera_id)

                time.sleep(frame_delay)

            cap.release()
            with self.streams_lock:
                stream_info = self.active_streams.get(camera_id)
                if stream_info and stream_info.get("capture") is cap:
                    stream_info["capture"] = None

        with self.streams_lock:
            if camera_id in self.active_streams:
                logger.info("Stream worker exiting for camera %s", camera_id)
            else:
                logger.debug(
                    "Stream worker exit for camera %s with registry already cleared",
                    camera_id,
                )

    def _build_thumbnail_path(self, video_path: str) -> str:
        path = Path(video_path)
        return str(path.with_name(f"{path.stem}-thumb.jpg"))
