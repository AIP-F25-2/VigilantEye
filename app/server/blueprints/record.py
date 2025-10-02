import os, time, threading
from datetime import datetime
from flask import Blueprint, request
from ..responses import ok, err
from ..config import TMP_DIR, LOGS_DIR, FFMPEG_BIN, VIDEOS_DIR
from ..index import load_index, save_index
from ..ffmpeg import run_ffmpeg

bp = Blueprint("record", __name__)

_rec_lock = threading.Lock()
_rec_proc = None
_rec_file = None
_rec_started_at = None
_rec_source = None
_rec_mode = None

def recorder_status():
    with _rec_lock:
        running = _rec_proc is not None and _rec_proc.poll() is None
        return {"running": running, "mode": _rec_mode, "source": _rec_source,
                "file": _rec_file, "started_at": _rec_started_at,
                "uptime_sec": (time.time() - _rec_started_at) if running and _rec_started_at else 0}

def _start_record(cmd, out_path, mode, source, max_sec=None):
    import subprocess
    global _rec_proc, _rec_file, _rec_started_at, _rec_source, _rec_mode
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with _rec_lock:
        if _rec_proc and _rec_proc.poll() is None:
            raise RuntimeError("Already recording")
        if cmd and os.path.basename(cmd[0]).lower() in ("ffmpeg","ffmpeg.exe"):
            cmd = [FFMPEG_BIN] + cmd[1:]
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(LOGS_DIR, f"rec_{mode}_{ts}.log")
        log_f = open(log_path, "w", buffering=1, encoding="utf-8", errors="ignore")
        _rec_proc = subprocess.Popen(cmd, stdout=log_f, stderr=log_f, text=True)
        _rec_file = out_path; _rec_started_at = time.time(); _rec_source = source; _rec_mode = mode
    if max_sec and str(max_sec).strip().isdigit() and int(max_sec) > 0:
        def _timer_stop():
            time.sleep(int(max_sec))
            try: stop_recording()
            except Exception: pass
        threading.Thread(target=_timer_stop, daemon=True).start()
    return True

def stop_recording():
    import shutil
    global _rec_proc, _rec_file, _rec_started_at, _rec_source, _rec_mode
    with _rec_lock:
        proc = _rec_proc; out_path = _rec_file; mode = _rec_mode; src  = _rec_source
    if not out_path: return None
    if proc and proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception:
            try: proc.kill()
            except Exception: pass
    for _ in range(10):
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0: break
        time.sleep(0.2)
    with _rec_lock:
        _rec_proc = None; _rec_file = None; _rec_started_at = None; _rec_source = None; _rec_mode = None
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0: return None

    from uuid import uuid4
    vid = uuid4().hex
    orig_name = os.path.basename(out_path)
    stored_name = f"{vid}__{orig_name}"
    stored_path = os.path.join(VIDEOS_DIR, stored_name)
    try: os.replace(out_path, stored_path)
    except Exception:
        import shutil
        shutil.copy2(out_path, stored_path)
        try: os.remove(out_path)
        except Exception: pass

    import mimetypes, hashlib
    size = os.path.getsize(stored_path); checksum = hashlib.sha256(open(stored_path,"rb").read()).hexdigest()
    created_at = datetime.utcnow().isoformat() + "Z"
    mime = mimetypes.guess_type(stored_path)[0] or "application/octet-stream"
    idx = load_index()
    idx[vid] = {"video_id": vid, "filename": orig_name, "stored_name": stored_name, "stored_path": stored_path,
                "size_bytes": size, "size_human": f"{size/1024/1024:.1f} MB", "checksum": checksum,
                "created_at": created_at, "mimetype": mime, "recording": {"mode": mode, "source": src}}
    save_index(idx)
    return {k:v for k,v in idx[vid].items() if k!="stored_path"}

@bp.route("/record/start", methods=["POST"])
def record_start():
    mode = (request.form.get("mode") or "screen").lower()
    source = (request.form.get("source") or "").strip()
    fps = int(request.form.get("fps", 30))
    max_sec = request.form.get("max_sec") or None

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = {"screen": f"record_screen_{ts}.mp4", "rtsp": f"record_rtsp_{ts}.mp4",
                 "webcam": f"record_webcam_{ts}.mp4"}.get(mode, f"record_{mode}_{ts}.mp4")
    out_path = os.path.join(TMP_DIR, base_name)

    if mode == "screen":
        cmd = ["ffmpeg","-y","-f","gdigrab","-framerate", str(max(5,min(60,fps))), "-i","desktop",
               "-pix_fmt","yuv420p","-c:v","libx264","-preset","veryfast","-crf","23","-movflags","+faststart", out_path]
    elif mode == "rtsp":
        if not source.lower().startswith("rtsp://"): return err("RTSP requires rtsp:// URL", 400)
        cmd = ["ffmpeg","-y","-rtsp_transport","tcp","-i", source,
               "-c:v","libx264","-preset","veryfast","-profile:v","main",
               "-c:a","aac","-ar","48000","-ac","2","-b:a","128k","-movflags","+faststart", out_path]
    elif mode == "webcam":
        dev = source or "video=Integrated Camera"
        cmd = ["ffmpeg","-y","-f","dshow","-framerate", str(max(5,min(60,fps))), "-i", dev,
               "-pix_fmt","yuv420p","-c:v","libx264","-preset","veryfast","-crf","23","-movflags","+faststart", out_path]
    else:
        return err("Unsupported mode. Use screen|rtsp|webcam.", 400)

    try: _start_record(cmd, out_path, mode, source, max_sec=max_sec)
    except RuntimeError as e: return err(str(e), 409)
    return ok(status=recorder_status())

@bp.route("/record/file/start", methods=["POST"])
def record_file_start():
    video_id = request.form.get("video_id")
    offset = max(0, int(float(request.form.get("offset_sec", 0))))
    max_sec = request.form.get("max_sec") or None
    crf = request.form.get("crf") or "23"

    from ..index import load_index
    idx = load_index(); v = idx.get(video_id or "")
    if not v: return err("Video not found", 404)
    src_path = v["stored_path"]
    if not os.path.exists(src_path): return err("File missing on disk", 404)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(TMP_DIR, f"record_from_file_{video_id}_{ts}.mp4")

    cmd = ["ffmpeg","-y","-ss", str(offset), "-i", src_path,
           "-c:v","libx264","-preset","veryfast","-crf", str(crf),
           "-c:a","aac","-ar","48000","-ac","2","-b:a","128k","-movflags","+faststart"]
    if max_sec and str(max_sec).strip().isdigit(): cmd += ["-t", str(int(max_sec))]
    cmd += [out_path]

    try: _start_record(cmd, out_path, mode="file", source=f"{video_id}@{offset}s", max_sec=max_sec)
    except RuntimeError as e: return err(str(e), 409)
    return ok(status=recorder_status())

@bp.route("/record/stop", methods=["POST"])
def record_stop():
    meta = stop_recording()
    if not meta: return err("No active recording or failed to finalize.", 400)
    return ok(video=meta)

@bp.route("/record/status", methods=["GET"])
def record_status():
    return ok(**recorder_status())

@bp.route("/record/devices", methods=["GET"])
def record_devices():
    # Only works on Windows with DirectShow; adjust for other OS
    import subprocess
    try:
        p = subprocess.run([FFMPEG_BIN, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                           capture_output=True, text=True)
        text = p.stderr
    except Exception as e:
        return err(f"Failed to query devices: {e}", 500)
    return ok(raw=text)
