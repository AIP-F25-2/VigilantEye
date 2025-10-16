import tempfile
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from app.config import settings
from app.services.storage import save_bytes
from app.logger import logger
import os

def extract_from_video_bytes(video_bytes: bytes):
    """Save temp video, extract audio (wav bytes) and frames at period, store them via storage.save_bytes.
    Returns dict: {'audio_artifact_id': ..., 'frames': [{'artifact_id', 'timestamp'} ...]}"""
    tmp_dir = tempfile.mkdtemp()
    try:
        video_path = os.path.join(tmp_dir, "upload.mp4")
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        clip = VideoFileClip(video_path)
        # audio
        audio_path = os.path.join(tmp_dir, "audio.wav")
        try:
            clip.audio.write_audiofile(audio_path, logger=None)
        except Exception as e:
            logger.exception(f"Failed to write audiofile: {e}")
            audio_path = None

        audio_artifact_id = None
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_artifact_id = save_bytes(audio_bytes, "audio", ".wav")

        frames = []
        period = settings.IMAGE_PERIOD_SEC
        duration = int(clip.duration or 0)
        for t in range(0, max(duration, 1), max(1, period)):
            try:
                frame = clip.get_frame(t)  # RGB
                # convert to BGR for cv2 then encode JPG
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ret, buf = cv2.imencode(".jpg", frame_bgr)
                if not ret:
                    continue
                jpg_bytes = buf.tobytes()
                aid = save_bytes(jpg_bytes, "images", ".jpg")
                frames.append({"artifact_id": aid, "timestamp": t})
            except Exception as e:
                logger.exception(f"Failed to extract frame at {t}: {e}")

        return {"audio_artifact_id": audio_artifact_id, "frames": frames}
    finally:
        try:
            clip.close()
        except Exception:
            pass
        # cleanup tmp dir
        try:
            import shutil
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
