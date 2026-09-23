"""Storage for field-evidence photos."""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def save_photo(session_id: str, upload: UploadFile) -> str:
    """Persist an evidence photo and return a relative URL.

    EXIF metadata is stripped to remove embedded GPS or device info
    before saving.
    """
    settings = get_settings()
    if upload.content_type not in ALLOWED_TYPES:
        raise ValueError(f"unsupported upload type: {upload.content_type}")

    data = upload.file.read()
    if len(data) > MAX_BYTES:
        raise ValueError("photo exceeds 10 MB limit")

    try:
        image = Image.open(_BytesReader(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise ValueError("uploaded file is not a recognised image") from exc

    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[upload.content_type]
    filename = f"{secrets.token_hex(12)}{suffix}"
    target_dir: Path = settings.upload_dir / session_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename

    # Re-save without EXIF.
    stripped = Image.new(image.mode, image.size)
    stripped.putdata(list(image.getdata()))
    fmt = {".jpg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[suffix]
    stripped.save(target, format=fmt, quality=85)

    return f"/uploads/{session_id}/{filename}"


class _BytesReader:
    """Tiny adapter so PIL can read from a bytes buffer with .read/.seek."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    def seek(self, pos: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = pos
        elif whence == 1:
            self._pos += pos
        elif whence == 2:
            self._pos = len(self._data) + pos
        return self._pos

    def tell(self) -> int:
        return self._pos
