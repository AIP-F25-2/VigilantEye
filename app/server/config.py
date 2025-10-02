import os, json

# Paths
BASE_DIR   = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")
SEGS_DIR   = os.path.join(DATA_DIR, "segments")
CLIPS_DIR  = os.path.join(DATA_DIR, "clips")
FRAMES_DIR = os.path.join(DATA_DIR, "frames")
LOGS_DIR   = os.path.join(DATA_DIR, "logs")
TMP_DIR    = os.path.join(DATA_DIR, "tmp")
INDEX_PATH = os.path.join(DATA_DIR, "index.json")
AUDIO_DIR  = os.path.join(DATA_DIR, "audio") 
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024 * 20  # 20 GB
ALLOWED_EXTS = {".mp4", ".mov", ".mkv", ".avi"}

FFMPEG_BIN = os.environ.get(
    "FFMPEG_BIN",
    r"C:\Users\Sukjit Singh\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
)

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    for d in (VIDEOS_DIR, SEGS_DIR, CLIPS_DIR, FRAMES_DIR, LOGS_DIR, TMP_DIR,AUDIO_DIR):
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "w") as f: json.dump({}, f)

class Config:
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
