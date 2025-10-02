import os, subprocess
from .config import FFMPEG_BIN

def run_ffmpeg(cmd):
    if cmd and os.path.basename(cmd[0]).lower() in ("ffmpeg", "ffmpeg.exe"):
        cmd = [FFMPEG_BIN] + cmd[1:]
    try:
        p = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return p
    except FileNotFoundError:
        raise RuntimeError(f"FFmpeg not found. Tried: {cmd[0]}. Check FFMPEG_BIN.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr)
