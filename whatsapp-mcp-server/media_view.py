"""Olaz-style media viewer: thumbnails for images, sampled frames for video, text for small files."""
import json, os, subprocess, tempfile
from mcp.server.fastmcp import Image

MAX_EDGE = 1024
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".log", ".xml", ".html", ".yaml", ".yml"}
TEXT_LIMIT = 20_000


def _thumb(src: str, out: str, edge: int = MAX_EDGE) -> str:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                    f"scale='min({edge},iw)':'min({edge},ih)':force_original_aspect_ratio=decrease",
                    "-frames:v", "1", "-q:v", "4", out], check=True)
    return out


def _duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def view(path: str, media_type: str, frames: int = 4):
    """Return a list of MCP content items (text + Image) describing the media file."""
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)
    head = {"path": path, "media_type": media_type, "bytes": size}
    tmp = tempfile.mkdtemp(prefix="wa-view-")

    if media_type == "image" or ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}:
        out = _thumb(path, os.path.join(tmp, "thumb.jpg"))
        return [json.dumps(head, ensure_ascii=False), Image(path=out)]

    if media_type == "video":
        dur = _duration(path)
        n = max(1, min(int(frames or 4), 8))
        items = [json.dumps({**head, "duration_s": round(dur, 1), "frames": n}, ensure_ascii=False)]
        for i in range(n):
            t = dur * (i + 0.5) / n if dur else 0
            out = os.path.join(tmp, f"f{i}.jpg")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                            "-vf", "scale='min(768,iw)':-2", "-q:v", "5", out], check=False)
            if os.path.exists(out):
                items += [f"frame {i + 1}/{n} @ {t:.1f}s", Image(path=out)]
        return items

    if media_type == "audio":
        return [json.dumps({**head, "duration_s": round(_duration(path), 1),
                            "note": "Audio: chưa có transcript; nghe file tại path."}, ensure_ascii=False)]

    # documents
    if ext in TEXT_EXT and size <= TEXT_LIMIT:
        with open(path, "r", errors="replace") as f:
            return [json.dumps(head, ensure_ascii=False), f.read()]
    if ext == ".pdf":
        out = os.path.join(tmp, "p1.jpg")
        r = subprocess.run(["sips", "-s", "format", "jpeg", "-Z", str(MAX_EDGE), path, "--out", out],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(out):
            return [json.dumps({**head, "note": "Trang 1 của PDF; đọc đầy đủ bằng file tại path."},
                               ensure_ascii=False), Image(path=out)]
    return [json.dumps({**head, "note": "Đã lưu file cục bộ; mở bằng path."}, ensure_ascii=False)]
