"""iconvert: fetch an image from a URL and return it converted to another format."""

import hashlib
import io
import os
import pathlib
import re
import tempfile
from urllib.parse import urlparse

import httpx
import pyvips
from PIL import Image as PILImage
from fastapi import FastAPI, HTTPException, Query, Response

FORMATS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "tiff": "image/tiff",
    "avif": "image/avif",
}
CACHE = pathlib.Path(os.getenv("CACHE_DIR", "/cache"))
MAX_BYTES = int(os.getenv("MAX_BYTES", 10 * 1024 * 1024))
MAX_SIZE = int(os.getenv("MAX_SIZE", 2048))
FETCH_TIMEOUT = float(os.getenv("FETCH_TIMEOUT", 10))
ALLOWED_HOSTS = {h.strip().lower() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()}
HEX_COLOR = re.compile(r"^[0-9a-fA-F]{6}$")

CACHE.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="iconvert")


async def fetch(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(400, "source must be an http(s) URL")
    if ALLOWED_HOSTS and parsed.hostname.lower() not in ALLOWED_HOSTS:
        raise HTTPException(403, "source host not allowed")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=FETCH_TIMEOUT) as client:
            async with client.stream("GET", url, headers={"User-Agent": "iconvert/1.0"}) as r:
                if r.status_code != 200:
                    raise HTTPException(502, f"upstream returned {r.status_code}")
                buf = bytearray()
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        raise HTTPException(413, "source too large")
                return bytes(buf)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"fetch failed: {e}") from e


def to_png_with_pillow(data: bytes) -> bytes:
    # Fallback for formats libvips can't read (e.g. ICO): pick the largest frame
    with PILImage.open(io.BytesIO(data)) as im:
        if getattr(im, "ico", None):
            im = im.ico.getimage(max(im.ico.sizes()))
        out = io.BytesIO()
        im.convert("RGBA").save(out, "PNG")
        return out.getvalue()


def render(data: bytes, fmt: str, size: int, bg: str | None) -> bytes:
    # thumbnail_buffer renders vector sources (SVG) directly at the target size
    try:
        img = pyvips.Image.thumbnail_buffer(data, size, height=size)
    except pyvips.Error:
        try:
            data = to_png_with_pillow(data)
        except Exception:
            raise pyvips.Error("source is not a supported image format")
        img = pyvips.Image.thumbnail_buffer(data, size, height=size)
    if img.hasalpha() and (bg or fmt == "jpg"):
        color = bg or "ffffff"
        img = img.flatten(background=[int(color[i : i + 2], 16) for i in (0, 2, 4)])
    return img.write_to_buffer(f".{fmt}")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/convert")
@app.get("/convert.{ext}")
async def convert(
    source: str,
    ext: str | None = None,
    format: str = "png",
    size: int = Query(256, ge=16),
    bg: str | None = None,
):
    fmt = (ext or format).lower().replace("jpeg", "jpg")
    if fmt not in FORMATS:
        raise HTTPException(400, f"format must be one of {', '.join(FORMATS)}")
    if size > MAX_SIZE:
        raise HTTPException(400, f"size must be <= {MAX_SIZE}")
    if bg is not None and not HEX_COLOR.match(bg):
        raise HTTPException(400, "bg must be a 6-digit hex color, e.g. ffffff")

    key = hashlib.sha256(f"{source}|{fmt}|{size}|{bg}".encode()).hexdigest()
    path = CACHE / f"{key}.{fmt}"
    if path.exists():
        out = path.read_bytes()
    else:
        data = await fetch(source)
        try:
            out = render(data, fmt, size, bg)
        except pyvips.Error as e:
            raise HTTPException(400, f"cannot convert source: {str(e).strip()}") from e
        with tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as tmp:
            tmp.write(out)
        os.replace(tmp.name, path)

    return Response(
        out,
        media_type=FORMATS[fmt],
        headers={"Cache-Control": "public, max-age=86400"},
    )
