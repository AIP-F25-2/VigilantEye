import os, mimetypes
from flask import Blueprint, request, send_file
from ..responses import ok, err
from ..config import AUDIO_DIR
from ..index import load_index
from ..ffmpeg import run_ffmpeg
from ..utils import stream_bytes

bp = Blueprint("audio", __name__)

@bp.route("/audio/<video_id>", methods=["GET"])
def audio_stream(video_id):
    """
    Streams (with Range support) an audio-only file extracted from the video.
    First request extracts & caches to data/audio/<video_id>.m4a
    """
    idx = load_index(); v = idx.get(video_id or "")
    if not v: return err("Video not found", 404)
    src = v["stored_path"]
    if not os.path.exists(src): return err("File missing", 404)

    out_path = os.path.join(AUDIO_DIR, f"{video_id}.m4a")
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        # Extract default/first audio track; if none exists, ffmpeg will fail
        try:
            run_ffmpeg([
                "ffmpeg","-y","-i", src,
                "-vn", "-map", "a:0",  # pick first audio track
                "-ac", "2", "-ar", "48000",
                "-c:a", "aac", "-b:a", "160k",
                out_path
            ])
        except RuntimeError as e:
            return err("No audio track or extraction failed.", 404)

    # Byte-range streaming (like /api/stream/<video_id>)
    mime = "audio/mp4"  # .m4a
    rng = request.headers.get("Range")
    if not rng:
        return send_file(out_path, mimetype=mime, as_attachment=False, conditional=True)
    try:
        units, spec = rng.split("=")
        if units != "bytes": raise ValueError
        start_s, end_s = (spec.split("-") + [""])[:2]
        start = int(start_s) if start_s else None
        end   = int(end_s) if end_s else None
    except Exception:
        return send_file(out_path, mimetype=mime, as_attachment=False, conditional=True)
    return stream_bytes(out_path, start, end, mime)
