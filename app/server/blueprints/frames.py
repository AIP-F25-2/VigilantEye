import os, zipfile
from datetime import datetime
from flask import Blueprint, request, send_file
from ..responses import ok, err
from ..config import FRAMES_DIR
from ..index import load_index
from ..utils import human_bytes
from ..ffmpeg import run_ffmpeg

bp = Blueprint("frames", __name__)

@bp.route("/frames/snapshot", methods=["POST"])
def frames_snapshot():
    video_id = request.form.get("video_id")
    offset = max(0.0, float(request.form.get("offset_sec", "0")))
    idx = load_index(); v = idx.get(video_id or "")
    if not v: return err("Video not found", 404)
    src = v["stored_path"]
    if not os.path.exists(src): return err("File missing", 404)

    out_dir = os.path.join(FRAMES_DIR, video_id); os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_name = f"snap_{int(offset*1000)}_{ts}.jpg"
    out_path = os.path.join(out_dir, out_name)

    cmd = ["ffmpeg","-y","-ss", f"{offset:.3f}","-i", src,"-frames:v","1","-q:v","2","-vf","scale=iw:ih", out_path]
    try: run_ffmpeg(cmd)
    except RuntimeError as e: return err("FFmpeg failed: " + str(e), 500)

    return ok(image={"file": out_name, "size": human_bytes(os.path.getsize(out_path)),
                     "url": f"/api/frames/{video_id}/{out_name}"})

@bp.route("/frames/batch", methods=["POST"])
def frames_batch():
    want_json = request.args.get("json") == "1" or "application/json" in (request.headers.get("Accept") or "")
    video_id = request.form.get("video_id")
    every = max(1, int(request.form.get("every_sec", "5")))
    start_sec = max(0.0, float(request.form.get("start_sec", "0")))
    end_raw = request.form.get("end_sec", None)
    end_sec = float(end_raw) if end_raw else None
    max_frames = int(request.form.get("max_frames", "0")) or None

    idx = load_index(); v = idx.get(video_id or "")
    if not v: return err("Video not found", 404)
    src = v["stored_path"]
    if not os.path.exists(src): return err("File missing", 404)

    batch_dir_name = datetime.utcnow().strftime("batch_%Y%m%d_%H%M%S")
    out_dir = os.path.join(FRAMES_DIR, video_id, batch_dir_name); os.makedirs(out_dir, exist_ok=True)

    cmd = ["ffmpeg","-y"]
    if start_sec: cmd += ["-ss", f"{start_sec:.3f}"]
    cmd += ["-i", src, "-vf", f"fps=1/{every}", "-q:v","2"]
    if end_sec and end_sec > start_sec:
        duration = end_sec - start_sec
        cmd += ["-t", f"{duration:.3f}"]
    out_pattern = os.path.join(out_dir, "frame_%04d.jpg"); cmd += [out_pattern]

    try: run_ffmpeg(cmd)
    except RuntimeError as e: return err("FFmpeg failed: " + str(e), 500)

    files = sorted([f for f in os.listdir(out_dir) if f.lower().endswith(".jpg")])
    if max_frames and len(files) > max_frames:
        for f in files[max_frames:]:
            try: os.remove(os.path.join(out_dir, f))
            except Exception: pass
        files = files[:max_frames]

    zip_name = f"{batch_dir_name}.zip"
    zip_path = os.path.join(out_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(os.path.join(out_dir, f), arcname=f)

    if want_json:
        return ok(batch={"folder": batch_dir_name, "count": len(files),
                         "zip_download": f"/api/frames/batch/zip/{video_id}/{batch_dir_name}"})
    return send_file(zip_path, as_attachment=True, download_name=zip_name)

@bp.route("/frames/<video_id>/<filename>", methods=["GET"])
def frames_open(video_id, filename):
    path = os.path.join(FRAMES_DIR, video_id, filename)
    if not os.path.exists(path): return err("Not found", 404)
    return send_file(path, as_attachment=False, download_name=filename, mimetype="image/jpeg")

@bp.route("/videos/<video_id>/frames", methods=["GET"])
def list_frames(video_id):
    base = os.path.join(FRAMES_DIR, video_id)
    if not os.path.isdir(base): return ok(images=[], auto_runs=[])
    singles = sorted([f for f in os.listdir(base) if f.lower().endswith(".jpg")])
    images = [{"file": f, "url": f"/api/frames/{video_id}/{f}"} for f in singles]
    runs = []
    for name in sorted([d for d in os.listdir(base) if d.startswith("batch_") or d.startswith("auto_")]):
        folder = os.path.join(base, name)
        if os.path.isdir(folder):
            count = len([f for f in os.listdir(folder) if f.lower().endswith(".jpg")])
            runs.append({"folder": name, "count": count,
                         "zip_download": f"/api/frames/batch/zip/{video_id}/{name}"})
    return ok(images=images, auto_runs=runs)

@bp.route("/frames/batch/zip/<video_id>/<folder>", methods=["GET"])
def frames_batch_zip(video_id, folder):
    base = os.path.join(FRAMES_DIR, video_id, folder)
    if not os.path.isdir(base): return err("Not found", 404)
    zip_path = os.path.join(base, f"{folder}.zip")
    if not os.path.exists(zip_path):
        files = sorted([f for f in os.listdir(base) if f.lower().endswith(".jpg")])
        if not files: return err("No images", 404)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files: z.write(os.path.join(base, f), arcname=f)
    return send_file(zip_path, as_attachment=True, download_name=f"{folder}.zip")
