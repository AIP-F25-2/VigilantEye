import os
from flask import Blueprint, send_file, request
from ..responses import ok, err
from ..config import SEGS_DIR
from ..index import load_index
from ..utils import human_bytes
from ..ffmpeg import run_ffmpeg

bp = Blueprint("segments", __name__)

@bp.route("/videos/<video_id>/segment", methods=["POST"])
def segment_video(video_id):
    seg_sec = max(2, int(request.form.get("segment_seconds", 60)))
    idx = load_index(); v = idx.get(video_id)
    if not v: return err("not found", 404)
    out_dir = os.path.join(SEGS_DIR, video_id); os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.endswith(".mp4"): os.remove(os.path.join(out_dir, f))
    out_pattern = os.path.join(out_dir, "segment_%03d.mp4")
    cmd = [
        "ffmpeg","-y","-i", v["stored_path"],
        "-c:v","libx264","-preset","veryfast","-profile:v","main",
        "-c:a","aac","-ar","48000","-ac","2","-b:a","128k",
        "-force_key_frames", f"expr:gte(t,n_forced*{seg_sec})",
        "-g","60","-keyint_min","60","-sc_threshold","0",
        "-f","segment","-segment_time", str(seg_sec), "-reset_timestamps","1",
        out_pattern
    ]
    try: run_ffmpeg(cmd)
    except RuntimeError as e: return err("FFmpeg failed: " + str(e), 500)

    files = sorted([f for f in os.listdir(out_dir) if f.endswith(".mp4")])
    items = [{"file": f, "size": human_bytes(os.path.getsize(os.path.join(out_dir,f))),
              "download": f"/api/segments/{video_id}/{f}"} for f in files]
    return ok(segments=items)

@bp.route("/segments/<video_id>", methods=["GET"])
def list_segments(video_id):
    out_dir = os.path.join(SEGS_DIR, video_id)
    if not os.path.isdir(out_dir): return ok(segments=[])
    files = sorted([f for f in os.listdir(out_dir) if f.endswith(".mp4")])
    items = [{"file": f, "size": human_bytes(os.path.getsize(os.path.join(out_dir,f))),
              "download": f"/api/segments/{video_id}/{f}"} for f in files]
    return ok(segments=items)

@bp.route("/segments/<video_id>/<filename>", methods=["GET"])
def download_segment(video_id, filename):
    seg_dir = os.path.join(SEGS_DIR, video_id)
    path = os.path.join(seg_dir, filename)
    if not os.path.exists(path): return err("not found", 404)
    return send_file(path, as_attachment=True, download_name=filename)
