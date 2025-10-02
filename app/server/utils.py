import os
from flask import Response

def human_bytes(n: int) -> str:
    units = ["B","KB","MB","GB","TB"]
    for u in units:
        if n < 1024.0:
            return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} PB"

def stream_bytes(path: str, start: int, end: int, mime: str):
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
