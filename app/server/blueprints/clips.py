import os
from flask import Blueprint, request, send_file
from ..responses import ok, err
from ..config import CLIPS_DIR
from ..index import load_index
from ..utils import human_bytes
from ..ffmpeg import run_ffmpeg

bp = Blueprint("clips", __name__)

def escape_drawtext_text(s: str) -> str:
    s = s.replace("\\", "\\\\").replace(":", "\\:")
    s = s.replace('"', r'\"').replace("'", r"\'")
    return s

def make_drawtext_filter(text: str) -> str:
    t = escape_drawtext_text(text)
    return (f'drawtext=font="Arial":text="{t}":x=w-tw-20:y=20:fontsize=24:'
            f'fontcolor=white:box=1:boxcolor=black@0.4')

@bp.route("/clips", methods=["POST"])
def create_clip():
    video_id = request.form.get("video_id")
    start_sec = float(request.form.get("start_sec", 0))
    end_sec   = float(request.form.get("end_sec", 0))
    watermark = (request.form.get("watermark") or "").strip()
    if not video_id: return err("video_id required")
    if end_sec <= start_sec: return err("end_sec must be > start_sec")

    idx = load_index(); v = idx.get(video_id)
    if not v: return err("not found", 404)

    out_dir = os.path.join(CLIPS_DIR, video_id); os.makedirs(out_dir, exist_ok=True)
    clip_name = f"clip_{int(start_sec*1000)}_{int(end_sec*1000)}.mp4"
    out_path  = os.path.join(out_dir, clip_name)

    cmd = ["ffmpeg","-y","-ss", str(start_sec), "-to", str(end_sec), "-i", v["stored_path"],
           "-c:v","libx264","-preset","veryfast","-profile:v","main",
           "-c:a","aac","-ar","48000","-ac","2","-b:a","128k"]
    if watermark:
        cmd += ["-vf", make_drawtext_filter(watermark)]
    cmd.append(out_path)

    try: run_ffmpeg(cmd)
    except RuntimeError as e: return err("FFmpeg failed: " + str(e), 500)

    return ok(clip={"file": clip_name, "size": human_bytes(os.path.getsize(out_path)),
                    "download": f"/api/clips/{video_id}/{clip_name}"})

@bp.route("/videos/<video_id>/clips", methods=["GET"])
def list_clips(video_id):
    out_dir = os.path.join(CLIPS_DIR, video_id)
    if not os.path.isdir(out_dir): return ok(clips=[])
    files = sorted([f for f in os.listdir(out_dir) if f.endswith(".mp4")])
    items = [{"file": f, "size": human_bytes(os.path.getsize(os.path.join(out_dir,f))),
              "download": f"/api/clips/{video_id}/{f}"} for f in files]
    return ok(clips=items)

@bp.route("/clips/<video_id>/<filename>", methods=["GET"])
def download_clip(video_id, filename):
    clip_dir = os.path.join(CLIPS_DIR, video_id)
    path = os.path.join(clip_dir, filename)
    if not os.path.exists(path): return err("not found", 404)
    return send_file(path, as_attachment=True, download_name=filename)
