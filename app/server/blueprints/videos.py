import os, mimetypes, hashlib
from flask import Blueprint, request, send_file
from ..config import VIDEOS_DIR, ALLOWED_EXTS
from ..index import load_index, save_index
from ..responses import ok, err
from ..utils import stream_bytes

bp = Blueprint("videos", __name__)

def allowed_file(fn): return os.path.splitext(fn)[1].lower() in ALLOWED_EXTS

@bp.route("/videos/upload", methods=["POST"])
def upload():
    from uuid import uuid4
    from datetime import datetime
    if "file" not in request.files: return err("No file", 400)
    file = request.files["file"]
    if not file.filename: return err("Empty filename", 400)
    if not allowed_file(file.filename):
        return err(f"Unsupported extension. Allowed: {sorted(ALLOWED_EXTS)}", 415)

    vid = uuid4().hex
    stored_name = f"{vid}__{file.filename}"
    stored_path = os.path.join(VIDEOS_DIR, stored_name)
    file.save(stored_path)

    size = os.path.getsize(stored_path)
    checksum = hashlib.sha256(open(stored_path,"rb").read()).hexdigest()
    created_at = datetime.utcnow().isoformat() + "Z"
    mime = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    idx = load_index()
    idx[vid] = {
        "video_id": vid, "filename": file.filename, "stored_name": stored_name,
        "stored_path": stored_path, "size_bytes": size,
        "size_human": f"{size/1024/1024:.1f} MB", "checksum": checksum,
        "created_at": created_at, "mimetype": mime
    }
    save_index(idx)
    return ok(video={k:v for k,v in idx[vid].items() if k!="stored_path"})

@bp.route("/videos", methods=["GET"])
def list_videos():
    idx = load_index()
    items = sorted(idx.values(), key=lambda x: x["created_at"], reverse=True)
    out = [{k:v for k,v in it.items() if k!="stored_path"} for it in items]
    return ok(videos=out)

@bp.route("/videos/<video_id>", methods=["GET"])
def get_video(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return err("not found", 404)
    return ok(video={k:v for k,v in v.items() if k!="stored_path"})

@bp.route("/videos/<video_id>/delete", methods=["DELETE"])
def delete_video(video_id):
    from ..config import SEGS_DIR, CLIPS_DIR, FRAMES_DIR
    import shutil
    idx = load_index(); v = idx.get(video_id)
    if not v: return err("not found", 404)
    try:
        if os.path.exists(v["stored_path"]): os.remove(v["stored_path"])
    except Exception: pass
    shutil.rmtree(os.path.join(SEGS_DIR, video_id), ignore_errors=True)
    shutil.rmtree(os.path.join(CLIPS_DIR, video_id), ignore_errors=True)
    shutil.rmtree(os.path.join(FRAMES_DIR, video_id), ignore_errors=True)
    idx.pop(video_id, None); save_index(idx)
    return ok(deleted=video_id)

@bp.route("/stream/<video_id>", methods=["GET"])
def stream(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return err("not found", 404)
    path = v["stored_path"]
    if not os.path.exists(path): return err("file missing", 404)
    mime = v.get("mimetype") or "application/octet-stream"
    rng = request.headers.get("Range")
    if not rng:
        return send_file(path, mimetype=mime, as_attachment=False, conditional=True)
    try:
        units, spec = rng.split("=")
        if units != "bytes": raise ValueError
        start_s, end_s = (spec.split("-") + [""])[:2]
        start = int(start_s) if start_s else None
        end   = int(end_s) if end_s else None
    except Exception:
        return send_file(path, mimetype=mime, as_attachment=False, conditional=True)
    return stream_bytes(path, start, end, mime)

@bp.route("/download/<video_id>", methods=["GET"])
def download(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return err("not found", 404)
    path = v["stored_path"]
    if not os.path.exists(path): return err("file missing", 404)
    return send_file(path, as_attachment=True, download_name=v["filename"])
