# app.py
import os, json, mimetypes, hashlib, shutil, subprocess, signal, time, threading, zipfile
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_file, redirect, url_for

# ----------------------------
# Minimal config & folders
# ----------------------------
BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")
SEGS_DIR   = os.path.join(DATA_DIR, "segments")
CLIPS_DIR  = os.path.join(DATA_DIR, "clips")
FRAMES_DIR = os.path.join(DATA_DIR, "frames")
LOGS_DIR   = os.path.join(DATA_DIR, "logs")
TMP_DIR    = os.path.join(DATA_DIR, "tmp")
INDEX_PATH = os.path.join(DATA_DIR, "index.json")

MAX_CONTENT_LENGTH = 1024 * 1024 * 1024 * 20  # 20 GB
ALLOWED_EXTS = {".mp4", ".mov", ".mkv", ".avi"}

for d in (DATA_DIR, VIDEOS_DIR, SEGS_DIR, CLIPS_DIR, FRAMES_DIR, LOGS_DIR, TMP_DIR):
    os.makedirs(d, exist_ok=True)
if not os.path.exists(INDEX_PATH):
    with open(INDEX_PATH, "w") as f: json.dump({}, f)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Absolute path to ffmpeg (set yours if different)
FFMPEG_BIN = os.environ.get(
    "FFMPEG_BIN",
    r"C:\Users\Sukjit Singh\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
)
print("Using ffmpeg at:", FFMPEG_BIN)

# ----------------------------
# Helpers
# ----------------------------
def load_index():
    with open(INDEX_PATH, "r") as f: return json.load(f)

def save_index(idx):
    tmp = INDEX_PATH + ".tmp"
    with open(tmp, "w") as f: json.dump(idx, f, indent=2)
    os.replace(tmp, INDEX_PATH)

def sha256sum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def human_bytes(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024.0: return f"{n:.1f} {u}"
        n /= 1024.0
        # continue
    return f"{n:.1f} PB"

def allowed_file(fn): return os.path.splitext(fn)[1].lower() in ALLOWED_EXTS

def stream_bytes(path, start, end, mime):
    size = os.path.getsize(path)
    start = 0 if start is None else int(start)
    end = size - 1 if end is None else int(end)
    if start > end or start >= size:
        return Response(status=416, headers={"Content-Range": f"bytes */{size}"})
    length = end - start + 1
    def gen():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            chunk = 1024 * 1024
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data: break
                remaining -= len(data)
                yield data
    headers = {
        "Content-Range": f"bytes {start}-{end}/{size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": mime or "application/octet-stream",
        "Cache-Control": "private, max-age=0, must-revalidate",
    }
    return Response(gen(), status=206, headers=headers)

def run_ffmpeg(cmd):
    # Ensure absolute ffmpeg; tolerate spaces in path
    if cmd and os.path.basename(cmd[0]).lower() in ("ffmpeg", "ffmpeg.exe"):
        cmd = [FFMPEG_BIN] + cmd[1:]
    try:
        p = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return p
    except FileNotFoundError:
        raise RuntimeError(f"FFmpeg not found. Tried: {cmd[0]}. Check FFMPEG_BIN.")
    except subprocess.CalledProcessError as e:
        # Return full stderr to see real error from drawtext/inputs
        raise RuntimeError(e.stderr)

# ---------- drawtext helpers (for clip watermark) ----------
def escape_drawtext_text(s: str) -> str:
    s = s.replace("\\", "\\\\").replace(":", "\\:")
    s = s.replace('"', r'\"').replace("'", r"\'")
    return s

def make_drawtext_filter(text: str) -> str:
    # Prefer fontconfig family name to avoid Windows path headaches
    t = escape_drawtext_text(text)
    return (
        f'drawtext=font="Arial":'
        f'text="{t}":x=w-tw-20:y=20:fontsize=24:'
        f'fontcolor=white:box=1:boxcolor=black@0.4'
    )

# ----------------------------
# Frontend (simple HTML)
# ----------------------------
STYLE = """
:root{color-scheme:dark}
body{margin:0;background:#0b0b0f;color:#e8e8ea;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
.card{background:#14141a;border:1px solid #222229;border-radius:16px;padding:16px}
h1{font-size:22px;margin:0 0 8px 0}
h3{margin:0 0 8px 0}
.muted{color:#9aa0a6}
.btn{background:#5b6cff;border:0;color:white;padding:8px 12px;border-radius:10px;cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{background:#6b7bff}
.btn.gray{background:#23232b;color:#e8e8ea}.btn.gray:hover{background:#2b2b35}
.btn.red{background:#e24a4a}.btn.red:hover{background:#f05a5a}
.row{display:flex;gap:16px;flex-wrap:wrap}
.col{flex:1 1 320px;min-width:300px}
input[type=file], input[type=number], input[type=text]{color:#e8e8ea;background:#1a1a22;border:1px solid #2a2a32;border-radius:8px;padding:8px;width:100%}
label{font-size:12px;color:#c8c8cc}
video{width:100%;max-height:60vh;background:#000}
ul{list-style:none;margin:0;padding:0}
.item{padding:12px 0;border-top:1px solid #1e1e26}
.item:first-child{border-top:0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{border-bottom:1px solid #1e1e26;padding:6px 4px;text-align:left}
code{background:#111116;padding:2px 6px;border-radius:6px}
"""

@app.route("/", methods=["GET"])
def home():
    idx = load_index()
    items = sorted(idx.values(), key=lambda x: x["created_at"], reverse=True)
    li = "".join(f"""
      <li class="item">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
          <div style="min-width:0">
            <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{v['filename']}</div>
            <div class="muted" style="font-size:12px">{v['size_human']} · {datetime.fromisoformat(v['created_at'].replace('Z','')).strftime('%Y-%m-%d %H:%M:%S')}</div>
          </div>
          <div style="display:flex;gap:8px">
            <a class="btn gray" href="/video/{v['video_id']}">Open</a>
            <a class="btn gray" href="/download/{v['video_id']}">Download</a>
            <a class="btn red"  href="/videos/{v['video_id']}/delete" onclick="return confirm('Delete this video?')">Delete</a>
          </div>
        </div>
      </li>
    """ for v in items)

    return Response(f"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VigilantEye · CCTV (No AI)</title>
<style>{STYLE}</style></head><body>
<div class="wrap">
  <h1>VigilantEye · CCTV (No AI)</h1>
  <p class="muted">Upload, manage, stream, segment, clip — record (screen/RTSP/webcam or from file) — and extract frames.</p>

  <div class="row">
    <div class="col">
      <div class="card">
        <h3>Upload</h3>
        <form action="/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="file" accept="video/*" required>
          <div style="height:8px"></div>
          <button class="btn" type="submit">Upload</button>
        </form>
        <p class="muted" style="font-size:12px;margin-top:6px">Allowed: {", ".join(sorted(ALLOWED_EXTS))}. Keeps original file.</p>
      </div>

      <div style="height:16px"></div>

      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h3>Library</h3>
          <a class="btn gray" href="/">Refresh</a>
        </div>
        <ul>{li or '<li class="muted" style="padding:12px 0">No videos yet.</li>'}</ul>
      </div>
    </div>

    <div class="col">
      <div class="card">
        <h3>Record (Screen / RTSP / Webcam)</h3>
        <form action="/record/start" method="post">
          <label>Mode</label>
          <select name="mode" style="width:100%;background:#1a1a22;border:1px solid #2a2a32;border-radius:8px;color:#e8e8ea;padding:8px">
            <option value="screen">Screen (Windows desktop)</option>
            <option value="rtsp">RTSP URL</option>
            <option value="webcam">Webcam (DirectShow)</option>
          </select>
          <div style="height:6px"></div>
          <label>Source (RTSP: rtsp://... | Webcam: video=Integrated Camera)</label>
          <input type="text" name="source" placeholder="Leave blank for screen">
          <div class="grid" style="margin-top:6px">
            <div>
              <label>Frame rate</label>
              <input type="number" name="fps" value="30" min="5" max="60">
            </div>
            <div>
              <label>Max duration (seconds, optional)</label>
              <input type="number" name="max_sec" value="">
            </div>
          </div>
          <div style="height:8px"></div>
          <button class="btn" type="submit">Start recording</button>
          <a class="btn red" href="/record/stop" style="margin-left:8px" onclick="return confirm('Stop recording?')">Stop</a>
          <a class="btn gray" href="/record" style="margin-left:8px">Status</a>
        </form>
        <p class="muted" style="font-size:12px;margin-top:6px">Webcam device listing: <a class="btn gray" href="/record/devices">/record/devices</a></p>
      </div>
    </div>
  </div>
</div>
</body></html>
""", mimetype="text/html")

# ----- Video detail page (endpoint fixed explicitly) -----
@app.route("/video/<video_id>", methods=["GET"], endpoint="video_page")
def video_page(video_id):
    idx = load_index()
    v = idx.get(video_id)
    if not v: return Response("Not found", 404)

    # list segments & clips
    seg_dir = os.path.join(SEGS_DIR, video_id)
    seg_rows = []
    if os.path.isdir(seg_dir):
        for name in sorted([f for f in os.listdir(seg_dir) if f.endswith(".mp4")]):
            p = os.path.join(seg_dir, name)
            seg_rows.append(f"<tr><td>{name}</td><td>{human_bytes(os.path.getsize(p))}</td><td><a class='btn gray' href='/segments/{video_id}/{name}'>Download</a></td></tr>")
    clip_dir = os.path.join(CLIPS_DIR, video_id)
    clip_rows = []
    if os.path.isdir(clip_dir):
        for name in sorted([f for f in os.listdir(clip_dir) if f.endswith('.mp4')]):
            p = os.path.join(clip_dir, name)
            clip_rows.append(f"<tr><td>{name}</td><td>{human_bytes(os.path.getsize(p))}</td><td><a class='btn gray' href='/clips/{video_id}/{name}'>Download</a></td></tr>")

    # frames (snapshots) list (top-level jpgs)
    frames_dir = os.path.join(FRAMES_DIR, video_id)
    frame_rows = []
    if os.path.isdir(frames_dir):
        for name in sorted([f for f in os.listdir(frames_dir) if f.lower().endswith(".jpg")]):
            p = os.path.join(frames_dir, name)
            frame_rows.append(
                f"<tr><td>{name}</td><td>{human_bytes(os.path.getsize(p))}</td>"
                f"<td><a class='btn gray' href='/frames/{video_id}/{name}'>Open</a></td></tr>"
            )

    body = f"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video {video_id}</title>
<style>{STYLE}</style></head><body>
<div class="wrap">
  <a class="btn gray" href="/">← Back</a>
  <div style="height:10px"></div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
      <div>
        <h3 style="margin:0">{v['filename']}</h3>
        <div class="muted" style="font-size:12px">ID: {video_id}</div>
      </div>
      <div style="display:flex;gap:8px">
        <a class="btn gray" href="/download/{video_id}">Download original</a>
        <a class="btn red"  href="/videos/{video_id}/delete" onclick="return confirm('Delete this video?')">Delete</a>
      </div>
    </div>
    <div class="grid" style="margin-top:8px">
      <div><span class="muted">Size:</span> {v['size_human']}</div>
      <div><span class="muted">Created:</span> {datetime.fromisoformat(v['created_at'].replace('Z','')).strftime('%Y-%m-%d %H:%M:%S')}</div>
      <div style="grid-column:1/3"><span class="muted">Checksum:</span> <code>{v['checksum']}</code></div>
    </div>
    <div style="margin-top:10px">
      <video id="player" controls src="/stream/{video_id}"></video>
      <div class="muted" style="font-size:12px;margin-top:6px">Streaming original via <code>/stream/{video_id}</code> (no transcoding).</div>
    </div>
  </div>

  <div style="height:16px"></div>

  <div class="row">
    <div class="col">
      <div class="card">
        <h3>Segment</h3>
        <form action="/videos/{video_id}/segment" method="post">
          <label>Segment length (seconds)</label>
          <input type="number" name="segment_seconds" min="2" step="1" value="30" required>
          <div style="height:8px"></div>
          <button class="btn" type="submit">Create segments</button>
        </form>
        <div style="height:10px"></div>
        <h4 style="margin:0 0 6px 0">Segments</h4>
        <table>
          <thead><tr><th>File</th><th>Size</th><th>Action</th></tr></thead>
          <tbody>{''.join(seg_rows) or '<tr><td colspan=3 class="muted">No segments yet.</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <div class="col">
      <div class="card">
        <h3>Create Clip</h3>
        <form action="/clips" method="post">
          <input type="hidden" name="video_id" value="{video_id}">
          <div class="grid">
            <div>
              <label>Start (sec)</label>
              <input type="number" name="start_sec" min="0" step="0.1" value="0" required>
            </div>
            <div>
              <label>End (sec)</label>
              <input type="number" name="end_sec" min="0" step="0.1" value="10" required>
            </div>
          </div>
          <div style="height:6px"></div>
          <label>Watermark text (optional)</label>
          <input type="text" name="watermark" placeholder="e.g. Case-123">
          <div style="height:8px"></div>
          <button class="btn" type="submit">Create clip</button>
        </form>
        <div style="height:10px"></div>
        <h4 style="margin:0 0 6px 0">Clips</h4>
        <table>
          <thead><tr><th>File</th><th>Size</th><th>Action</th></tr></thead>
          <tbody>{''.join(clip_rows) or '<tr><td colspan=3 class="muted">No clips yet.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  </div>

  <div style="height:16px"></div>

  <div class="row">
    <div class="col">
      <div class="card">
        <h3>Snapshot (image) at current time</h3>
        <form id="snapForm" action="/frames/snapshot" method="post">
          <input type="hidden" name="video_id" value="{video_id}">
          <input type="hidden" id="snap_offset" name="offset_sec" value="0">
          <button class="btn" type="button" id="snapBtn">Take snapshot</button>
        </form>
        <p class="muted" style="font-size:12px;margin-top:6px">
          Captures a single JPEG at the HTML5 player's current position.
        </p>
        <div style="height:10px"></div>
        <h4 style="margin:0 0 6px 0">Snapshots</h4>
        <table>
          <thead><tr><th>File</th><th>Size</th><th>Action</th></tr></thead>
          <tbody>{''.join(frame_rows) or '<tr><td colspan=3 class="muted">No snapshots yet.</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <div class="col">
      <div class="card">
        <h3>Batch extract (every N seconds)</h3>
        <form action="/frames/batch" method="post">
          <input type="hidden" name="video_id" value="{video_id}">
          <div class="grid">
            <div>
              <label>Start (sec)</label>
              <input type="number" name="start_sec" min="0" step="0.1" value="0">
            </div>
            <div>
              <label>End (sec, optional)</label>
              <input type="number" name="end_sec" min="0" step="0.1">
            </div>
          </div>
          <div class="grid" style="margin-top:6px">
            <div>
              <label>Every (sec)</label>
              <input type="number" name="every_sec" min="1" step="1" value="5" required>
            </div>
            <div>
              <label>Max frames (optional)</label>
              <input type="number" name="max_frames" min="1" step="1">
            </div>
          </div>
          <div style="height:8px"></div>
          <button class="btn" type="submit">Extract & download ZIP</button>
        </form>
        <p class="muted" style="font-size:12px;margin-top:6px">
          Generates multiple JPEGs and returns a ZIP.
        </p>
      </div>
    </div>
  </div>

  <div style="height:16px"></div>

  <div class="card">
    <h3>Record THIS video from current time</h3>
    <form id="recordFileForm" action="/record_file/start" method="post">
      <input type="hidden" name="video_id" value="{video_id}">
      <input type="hidden" id="offset_sec" name="offset_sec" value="0">
      <div class="grid">
        <div>
          <label>Max duration (seconds, optional)</label>
          <input type="number" id="rf_max" name="max_sec" min="1" placeholder="e.g. 60">
        </div>
        <div>
          <label>Re-encode quality (CRF 18-28)</label>
          <input type="number" name="crf" min="18" max="28" value="23">
        </div>
      </div>
      <div style="height:8px"></div>
      <button class="btn" type="button" id="recordFromHereBtn">Record from current time</button>
      <a class="btn red" href="/record/stop" style="margin-left:8px" onclick="return confirm('Stop recording?')">Stop</a>
      <a class="btn gray" href="/record" style="margin-left:8px">Status</a>
    </form>
    <p class="muted" style="font-size:12px;margin-top:6px">Starts FFmpeg on the server reading this file from the current player time.</p>
  </div>
</div>

<script>
  // Snapshot uses the current HTML5 player time
  const snapBtn = document.getElementById('snapBtn');
  snapBtn?.addEventListener('click', () => {{
    const v = document.getElementById('player');
    const off = v ? Math.max(0, v.currentTime) : 0;
    document.getElementById('snap_offset').value = off.toFixed(3);
    document.getElementById('snapForm').submit();
  }});

  // Record-from-file uses current time too
  const rfBtn = document.getElementById('recordFromHereBtn');
  rfBtn?.addEventListener('click', () => {{
    const v = document.getElementById('player');
    const off = v ? Math.max(0, Math.floor(v.currentTime)) : 0;
    document.getElementById('offset_sec').value = off;
    document.getElementById('recordFileForm').submit();
  }});
</script>

</body></html>
"""
    return Response(body, mimetype="text/html")

# ----------------------------
# API — Task 1 (Upload/List/Meta/Delete) & Task 3 (Stream)
# ----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files: return Response("No file", 400)
    file = request.files["file"]
    if not file.filename: return Response("Empty filename", 400)
    if not allowed_file(file.filename):
        return Response(f"Unsupported extension. Allowed: {sorted(ALLOWED_EXTS)}", 415)

    vid = uuid4().hex
    stored_name = f"{vid}__{file.filename}"
    stored_path = os.path.join(VIDEOS_DIR, stored_name)
    file.save(stored_path)

    size = os.path.getsize(stored_path)
    checksum = sha256sum(stored_path)
    created_at = datetime.utcnow().isoformat() + "Z"
    mime = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    idx = load_index()
    idx[vid] = {
        "video_id": vid,
        "filename": file.filename,
        "stored_name": stored_name,
        "stored_path": stored_path,
        "size_bytes": size,
        "size_human": human_bytes(size),
        "checksum": checksum,
        "created_at": created_at,
        "mimetype": mime,
    }
    save_index(idx)
    return redirect(url_for("video_page", video_id=vid))

@app.route("/videos", methods=["GET"])
def list_videos():
    idx = load_index()
    items = sorted(idx.values(), key=lambda x: x["created_at"], reverse=True)
    out = [ {k:v for k,v in it.items() if k!="stored_path"} for it in items ]
    return jsonify({"videos": out})

@app.route("/videos/<video_id>", methods=["GET"])
def get_video(video_id):
    idx = load_index()
    v = idx.get(video_id)
    if not v: return jsonify({"error":"not found"}), 404
    return jsonify({k:v for k,v in v.items() if k!="stored_path"})

@app.route("/stream/<video_id>", methods=["GET"])
def stream(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return jsonify({"error":"not found"}), 404
    path = v["stored_path"]
    if not os.path.exists(path): return jsonify({"error":"file missing"}), 404
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

@app.route("/download/<video_id>", methods=["GET"])
def download(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return jsonify({"error":"not found"}), 404
    path = v["stored_path"]
    if not os.path.exists(path): return jsonify({"error":"file missing"}), 404
    return send_file(path, as_attachment=True, download_name=v["filename"])

@app.route("/videos/<video_id>/delete", methods=["GET"])
def delete_video(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return Response("Not found", 404)
    try:
        if os.path.exists(v["stored_path"]): os.remove(v["stored_path"])
    except Exception: pass
    shutil.rmtree(os.path.join(SEGS_DIR, video_id), ignore_errors=True)
    shutil.rmtree(os.path.join(CLIPS_DIR, video_id), ignore_errors=True)
    shutil.rmtree(os.path.join(FRAMES_DIR, video_id), ignore_errors=True)
    idx.pop(video_id, None); save_index(idx)
    return redirect(url_for("home"))

# ----------------------------
# API — Task 2 (Segmentation & Clipping)
# ----------------------------
@app.route("/videos/<video_id>/segment", methods=["POST"])
def segment_video(video_id):
    idx = load_index(); v = idx.get(video_id)
    if not v: return Response("Not found", 404)
    try:
        seg_sec = int(request.form.get("segment_seconds", 60))
        seg_sec = max(2, seg_sec)
    except Exception:
        seg_sec = 60

    out_dir = os.path.join(SEGS_DIR, video_id)
    os.makedirs(out_dir, exist_ok=True)

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
    try:
        run_ffmpeg(cmd)
    except RuntimeError as e:
        return Response("FFmpeg failed: " + str(e), 500)

    return redirect(url_for("video_page", video_id=video_id))

@app.route("/segments/<video_id>/<filename>", methods=["GET"])
def download_segment(video_id, filename):
    seg_dir = os.path.join(SEGS_DIR, video_id)
    path = os.path.join(seg_dir, filename)
    if not os.path.exists(path): return Response("Not found", 404)
    return send_file(path, as_attachment=True, download_name=filename)

@app.route("/clips", methods=["POST"])
def create_clip():
    video_id = request.form.get("video_id")
    start_sec = float(request.form.get("start_sec", 0))
    end_sec   = float(request.form.get("end_sec", 0))
    watermark = (request.form.get("watermark") or "").strip()

    if not video_id: return Response("video_id required", 400)
    if end_sec <= start_sec: return Response("end_sec must be > start_sec", 400)

    idx = load_index(); v = idx.get(video_id)
    if not v: return Response("Not found", 404)

    out_dir = os.path.join(CLIPS_DIR, video_id)
    os.makedirs(out_dir, exist_ok=True)
    clip_name = f"clip_{int(start_sec*1000)}_{int(end_sec*1000)}.mp4"
    out_path  = os.path.join(out_dir, clip_name)

    cmd = ["ffmpeg","-y","-ss", str(start_sec), "-to", str(end_sec), "-i", v["stored_path"],
           "-c:v","libx264","-preset","veryfast","-profile:v","main",
           "-c:a","aac","-ar","48000","-ac","2","-b:a","128k"]
    if watermark:
        draw = make_drawtext_filter(watermark)
        cmd += ["-vf", draw]
    cmd.append(out_path)

    try:
        run_ffmpeg(cmd)
    except RuntimeError as e:
        return Response("FFmpeg failed: " + str(e), 500)

    return redirect(url_for("video_page", video_id=video_id))

@app.route("/clips/<video_id>/<filename>", methods=["GET"])
def download_clip(video_id, filename):
    clip_dir = os.path.join(CLIPS_DIR, video_id)
    path = os.path.join(clip_dir, filename)
    if not os.path.exists(path): return Response("Not found", 404)
    return send_file(path, as_attachment=True, download_name=filename)

# ----------------------------
# NEW: Frames (images) — snapshot & batch
# ----------------------------
@app.route("/frames/snapshot", methods=["POST"])
def frames_snapshot():
    """
    Extract a single JPEG from an uploaded video at an offset (seconds).
    Saves to data/frames/<video_id>/snap_<timestamp>.jpg and redirects back.
    """
    video_id = request.form.get("video_id")
    try:
        offset = float(request.form.get("offset_sec", "0"))
        offset = max(0.0, offset)
    except Exception:
        offset = 0.0

    idx = load_index()
    v = idx.get(video_id or "")
    if not v:
        return Response("Video not found", 404)
    src = v["stored_path"]
    if not os.path.exists(src):
        return Response("File missing", 404)

    out_dir = os.path.join(FRAMES_DIR, video_id)
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_name = f"snap_{int(offset*1000)}_{ts}.jpg"
    out_path = os.path.join(out_dir, out_name)

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{offset:.3f}",
        "-i", src,
        "-frames:v", "1",
        "-q:v", "2",
        "-vf", "scale=iw:ih",
        out_path
    ]
    try:
        run_ffmpeg(cmd)
    except RuntimeError as e:
        return Response("FFmpeg failed: " + str(e), 500)

    return redirect(url_for("video_page", video_id=video_id))

@app.route("/frames/batch", methods=["POST"])
def frames_batch():
    """
    Extract multiple frames every N seconds in [start_sec, end_sec].
    Writes JPGs to data/frames/<video_id>/batch_* and returns a ZIP.
    """
    video_id = request.form.get("video_id")
    try:
        every = max(1, int(request.form.get("every_sec", "5")))
    except Exception:
        every = 5
    try:
        start_sec = max(0.0, float(request.form.get("start_sec", "0")))
    except Exception:
        start_sec = 0.0
    try:
        end_sec = float(request.form.get("end_sec", "0"))
        if end_sec <= 0:
            end_sec = None
    except Exception:
        end_sec = None
    try:
        max_frames = int(request.form.get("max_frames", "0")) or None
    except Exception:
        max_frames = None

    idx = load_index()
    v = idx.get(video_id or "")
    if not v:
        return Response("Video not found", 404)
    src = v["stored_path"]
    if not os.path.exists(src):
        return Response("File missing", 404)

    batch_dir_name = datetime.utcnow().strftime("batch_%Y%m%d_%H%M%S")
    out_dir = os.path.join(FRAMES_DIR, video_id, batch_dir_name)
    os.makedirs(out_dir, exist_ok=True)

    cmd = ["ffmpeg", "-y"]
    if start_sec:
        cmd += ["-ss", f"{start_sec:.3f}"]
    cmd += ["-i", src, "-vf", f"fps=1/{every}", "-q:v", "2"]
    if end_sec and end_sec > start_sec:
        duration = end_sec - start_sec
        cmd += ["-t", f"{duration:.3f}"]
    out_pattern = os.path.join(out_dir, "frame_%04d.jpg")
    cmd += [out_pattern]

    try:
        run_ffmpeg(cmd)
    except RuntimeError as e:
        return Response("FFmpeg failed: " + str(e), 500)

    files = sorted([f for f in os.listdir(out_dir) if f.lower().endswith(".jpg")])
    if max_frames and len(files) > max_frames:
        for f in files[max_frames:]:
            try: os.remove(os.path.join(out_dir, f))
            except Exception: pass
        files = files[:max_frames]

    zip_name = f"{batch_dir_name}.zip"
    zip_path = os.path.join(out_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(out_dir, f), arcname=f)

    return send_file(zip_path, as_attachment=True, download_name=zip_name)

@app.route("/frames/<video_id>/<filename>", methods=["GET"])
def frames_download(video_id, filename):
    folder = os.path.join(FRAMES_DIR, video_id)
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return Response("Not found", 404)
    # Inline display for JPGs
    return send_file(path, as_attachment=False, download_name=filename, mimetype="image/jpeg")

# ----------------------------
# Recording subsystem (start/stop/status) + record from file
# ----------------------------
_rec_lock = threading.Lock()
_rec_proc = None
_rec_file = None
_rec_started_at = None
_rec_source = None
_rec_mode = None

def recorder_status():
    with _rec_lock:
        running = _rec_proc is not None and _rec_proc.poll() is None
        return {
            "running": running,
            "mode": _rec_mode,
            "source": _rec_source,
            "file": _rec_file,
            "started_at": _rec_started_at,
            "uptime_sec": (time.time() - _rec_started_at) if running and _rec_started_at else 0
        }

def _start_record(cmd, out_path, mode, source, max_sec=None):
    """
    Launch ffmpeg in background. Logs go to data/logs/ to avoid PIPE blocking.
    """
    global _rec_proc, _rec_file, _rec_started_at, _rec_source, _rec_mode

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with _rec_lock:
        if _rec_proc and _rec_proc.poll() is None:
            raise RuntimeError("Already recording")
        if cmd and os.path.basename(cmd[0]).lower() in ("ffmpeg", "ffmpeg.exe"):
            cmd = [FFMPEG_BIN] + cmd[1:]
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(LOGS_DIR, f"rec_{mode}_{ts}.log")
        log_f = open(log_path, "w", buffering=1, encoding="utf-8", errors="ignore")
        _rec_proc = subprocess.Popen(cmd, stdout=log_f, stderr=log_f, text=True)
        _rec_file = out_path
        _rec_started_at = time.time()
        _rec_source = source
        _rec_mode = mode

    if max_sec and str(max_sec).strip().isdigit() and int(max_sec) > 0:
        def _timer_stop():
            time.sleep(int(max_sec))
            try: stop_recording()
            except Exception: pass
        threading.Thread(target=_timer_stop, daemon=True).start()
    return True

def stop_recording():
    """
    Stop ffmpeg if running. Finalize by moving the file into the library and
    registering it. Returns new video_id or None.
    """
    global _rec_proc, _rec_file, _rec_started_at, _rec_source, _rec_mode

    with _rec_lock:
        proc = _rec_proc
        out_path = _rec_file
        mode = _rec_mode
        src  = _rec_source

    if not out_path:
        return None  # nothing to finalize

    if proc and proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: pass

    # Wait a bit for filesystem to flush
    for _ in range(10):
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            break
        time.sleep(0.2)

    with _rec_lock:
        _rec_proc = None
        _rec_file = None
        _rec_started_at = None
        _rec_source = None
        _rec_mode = None

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None

    vid = uuid4().hex
    orig_name = os.path.basename(out_path)
    stored_name = f"{vid}__{orig_name}"
    stored_path = os.path.join(VIDEOS_DIR, stored_name)
    try:
        os.replace(out_path, stored_path)
    except Exception:
        shutil.copy2(out_path, stored_path)
        try: os.remove(out_path)
        except Exception: pass

    size = os.path.getsize(stored_path)
    checksum = sha256sum(stored_path)
    created_at = datetime.utcnow().isoformat() + "Z"
    mime = mimetypes.guess_type(stored_path)[0] or "application/octet-stream"

    idx = load_index()
    idx[vid] = {
        "video_id": vid,
        "filename": orig_name,
        "stored_name": stored_name,
        "stored_path": stored_path,
        "size_bytes": size,
        "size_human": human_bytes(size),
        "checksum": checksum,
        "created_at": created_at,
        "mimetype": mime,
        "recording": {"mode": mode, "source": src}
    }
    save_index(idx)
    return vid

@app.route("/record", methods=["GET"])
def record_page():
    st = recorder_status()
    body = f"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recording status</title>
<style>{STYLE}</style></head><body>
<div class="wrap">
  <a class="btn gray" href="/">← Back</a>
  <div style="height:10px"></div>
  <div class="card">
    <h3>Status</h3>
    <pre class="muted" style="white-space:pre-wrap">{json.dumps(st, indent=2)}</pre>
    <div style="height:8px"></div>
    <a class="btn red" href="/record/stop" onclick="return confirm('Stop recording?')">Stop recording</a>
    <a class="btn gray" href="/record/logs" style="margin-left:8px">View last log</a>
  </div>
</div>
</body></html>
"""
    return Response(body, mimetype="text/html")

@app.route("/record/logs", methods=["GET"])
def record_logs():
    files = sorted([f for f in os.listdir(LOGS_DIR) if f.endswith(".log")])
    last = files[-1] if files else None
    if not last:
        return Response("No logs yet.", 200)
    with open(os.path.join(LOGS_DIR, last), "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()[-20000:]
    return Response("<pre>" + text.replace("&","&amp;").replace("<","&lt;") + "</pre>", mimetype="text/html")

# Start generic recording (screen/rtsp/webcam)
@app.route("/record/start", methods=["POST"])
def record_start():
    mode = (request.form.get("mode") or "screen").lower()
    source = (request.form.get("source") or "").strip()
    fps = int(request.form.get("fps", 30))
    max_sec = request.form.get("max_sec") or None

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = {
        "screen": f"record_screen_{ts}.mp4",
        "rtsp":   f"record_rtsp_{ts}.mp4",
        "webcam": f"record_webcam_{ts}.mp4"
    }.get(mode, f"record_{mode}_{ts}.mp4")
    out_path = os.path.join(TMP_DIR, base_name)

    if mode == "screen":
        cmd = [
            "ffmpeg","-y",
            "-f","gdigrab",
            "-framerate", str(max(5,min(60,fps))),
            "-i","desktop",
            "-pix_fmt","yuv420p",
            "-c:v","libx264","-preset","veryfast","-crf","23",
            "-movflags","+faststart",
            out_path
        ]
    elif mode == "rtsp":
        if not source.lower().startswith("rtsp://"):
            return Response("RTSP mode requires a valid rtsp:// URL in Source.", 400)
        cmd = [
            "ffmpeg","-y",
            "-rtsp_transport","tcp",
            "-i", source,
            "-c:v","libx264","-preset","veryfast","-profile:v","main",
            "-c:a","aac","-ar","48000","-ac","2","-b:a","128k",
            "-movflags","+faststart",
            out_path
        ]
    elif mode == "webcam":
        dev = source or "video=Integrated Camera"
        cmd = [
            "ffmpeg","-y",
            "-f","dshow",
            "-framerate", str(max(5,min(60,fps))),
            "-i", dev,
            "-pix_fmt","yuv420p",
            "-c:v","libx264","-preset","veryfast","-crf","23",
            "-movflags","+faststart",
            out_path
        ]
    else:
        return Response("Unsupported mode. Use screen | rtsp | webcam.", 400)

    try:
        _start_record(cmd, out_path, mode, source, max_sec=max_sec)
    except RuntimeError as e:
        return Response(str(e), 409)

    return redirect(url_for("record_page"))

# NEW: Start recording from an uploaded FILE at offset (current time)
@app.route("/record_file/start", methods=["POST"])
def record_file_start():
    video_id = request.form.get("video_id")
    try:
        offset = int(float(request.form.get("offset_sec", 0)))
        offset = max(0, offset)
    except Exception:
        offset = 0
    max_sec = request.form.get("max_sec") or None
    crf = request.form.get("crf") or "23"

    idx = load_index()
    v = idx.get(video_id or "")
    if not v: return Response("Video not found", 404)
    src_path = v["stored_path"]
    if not os.path.exists(src_path): return Response("File missing on disk", 404)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(TMP_DIR, f"record_from_file_{video_id}_{ts}.mp4")

    cmd = ["ffmpeg","-y","-ss", str(offset), "-i", src_path,
           "-c:v","libx264","-preset","veryfast","-crf", str(crf),
           "-c:a","aac","-ar","48000","-ac","2","-b:a","128k",
           "-movflags","+faststart"]
    if max_sec and str(max_sec).strip().isdigit():
        cmd += ["-t", str(int(max_sec))]
    cmd += [out_path]

    try:
        _start_record(cmd, out_path, mode="file", source=f"{video_id}@{offset}s", max_sec=max_sec)
    except RuntimeError as e:
        return Response(str(e), 409)

    return redirect(url_for("record_page"))

@app.route("/record/stop", methods=["GET"])
def record_stop():
    vid = stop_recording()
    if not vid:
        return Response("No active recording or failed to finalize.", 400)
    return redirect(url_for("video_page", video_id=vid))

@app.route("/record/status", methods=["GET"])
def record_status():
    return jsonify(recorder_status())

@app.route("/record/devices", methods=["GET"])
def record_devices():
    try:
        p = subprocess.run(
            [FFMPEG_BIN, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True
        )
        text = p.stderr
    except Exception as e:
        text = f"Failed to query devices: {e}"
    body = f"""<!doctype html><html><head><meta charset="utf-8"><style>{STYLE}</style></head>
<body><div class="wrap"><a class="btn gray" href="/">← Back</a>
<div style="height:10px"></div>
<div class="card"><h3>DirectShow devices</h3>
<pre style="white-space:pre-wrap">{text}</pre></div></div></body></html>"""
    return Response(body, mimetype="text/html")

# # ----------------------------
# # Run
# # ----------------------------
# if __name__ == "__main__":
#     if not os.path.exists(FFMPEG_BIN):
#         print("WARNING: ffmpeg path not found:", FFMPEG_BIN)
#     app.run(debug=True, port=5000)
