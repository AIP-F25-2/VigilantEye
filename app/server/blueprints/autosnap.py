import os, time, threading
from datetime import datetime
from flask import Blueprint, request
from ..responses import ok, err
from ..config import FRAMES_DIR, LOGS_DIR, FFMPEG_BIN
from ..index import load_index
from ..ffmpeg import run_ffmpeg

bp = Blueprint("autosnap", __name__)

_snap_lock = threading.Lock()
_snap_proc = None
_snap_dir = None
_snap_started_at = None
_snap_vid = None
_snap_log = None

def snap_status():
    with _snap_lock:
        running = _snap_proc is not None and _snap_proc.poll() is None
        return {"running": running, "video_id": _snap_vid,
                "out_dir": _snap_dir, "started_at": _snap_started_at}

def _start_snap(cmd, out_dir, video_id):
    import subprocess
    global _snap_proc, _snap_dir, _snap_started_at, _snap_vid, _snap_log
    os.makedirs(out_dir, exist_ok=True)
    with _snap_lock:
        if _snap_proc and _snap_proc.poll() is None:
            raise RuntimeError("Auto-screenshots are already running.")
        if cmd and os.path.basename(cmd[0]).lower() in ("ffmpeg","ffmpeg.exe"):
            cmd = [FFMPEG_BIN] + cmd[1:]
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(LOGS_DIR, f"snap_{video_id}_{ts}.log")
        log_f = open(log_path, "w", buffering=1, encoding="utf-8", errors="ignore")
        _snap_proc = subprocess.Popen(cmd, stdout=log_f, stderr=log_f, text=True)
        _snap_dir = out_dir
        _snap_started_at = time.time()
        _snap_vid = video_id
        _snap_log = log_path
    return True

def stop_snapshots():
    global _snap_proc, _snap_dir, _snap_started_at, _snap_vid, _snap_log
    with _snap_lock:
        proc = _snap_proc
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            try: proc.kill()
            except Exception: pass
    with _snap_lock:
        _snap_proc = None; _snap_dir = None; _snap_started_at = None; _snap_vid = None; _snap_log = None

@bp.route("/frames/auto/start", methods=["POST"])
def auto_start():
    video_id = request.form.get("video_id")
    offset = max(0, int(float(request.form.get("offset_sec", "0"))))
    every = max(1, int(request.form.get("every_sec", "2")))
    idx = load_index(); v = idx.get(video_id or "")
    if not v: return err("Video not found", 404)
    src = v["stored_path"]
    if not os.path.exists(src): return err("File missing", 404)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(FRAMES_DIR, video_id, f"auto_{ts}")
    out_pattern = os.path.join(out_dir, "auto_%06d.jpg")
    cmd = ["ffmpeg","-y","-ss", str(offset), "-i", src, "-vf", f"fps=1/{every}", "-q:v","2", out_pattern]
    try: _start_snap(cmd, out_dir, video_id)
    except RuntimeError as e: return err(str(e), 409)
    return ok(running=True, video_id=video_id, out_dir=out_dir, every_sec=every, offset=offset)

@bp.route("/frames/auto/stop", methods=["POST"])
def auto_stop():
    st = snap_status()
    stop_snapshots()
    return ok(stopped=True, previous=st)

@bp.route("/frames/auto/status", methods=["GET"])
def auto_status():
    return ok(**snap_status())
