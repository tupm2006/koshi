import os
import secrets
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status

ALLOWED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}

def get_upload_dir() -> Path:
    if os.path.exists("/app/data"):
        d = Path("/app/data/uploads")
    elif os.path.exists("./data"):
        d = Path("./data/uploads")
    elif os.path.exists("./app/data"):
        d = Path("./app/data/uploads")
    else:
        d = Path("./data/uploads")
    d.mkdir(parents=True, exist_ok=True)
    return d.resolve()

def get_upload_path(filename: str) -> Path:
    clean_name = os.path.basename(filename)
    if clean_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    upload_dir = get_upload_dir()
    full_path = (upload_dir / clean_name).resolve()
    if not str(full_path).startswith(str(upload_dir)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal detected")
    return full_path

def delete_upload(filename: Optional[str]) -> bool:
    if not filename:
        return False
    try:
        path = get_upload_path(filename)
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        pass
    return False

async def save_upload(file: UploadFile, max_bytes: int = 2 * 1024 * 1024) -> Tuple[str, str, int]:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported media type. Allowed types: image/png, image/jpeg, image/webp"
        )

    # Read initial bytes to verify magic numbers
    header = await file.read(16)
    if len(header) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too small to be a valid image."
        )

    is_valid_magic = False
    if content_type == "image/png":
        is_valid_magic = header.startswith(b"\x89PNG\r\n\x1a\n")
    elif content_type in ("image/jpeg", "image/jpg"):
        is_valid_magic = header.startswith(b"\xff\xd8\xff")
    elif content_type == "image/webp":
        is_valid_magic = header.startswith(b"RIFF") and header[8:12] == b"WEBP"

    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File contents do not match the expected image signature."
        )

    ext = ALLOWED_MIME_TYPES[content_type]
    stored_name = f"{secrets.token_hex(16)}{ext}"
    dest_path = get_upload_dir() / stored_name

    size_bytes = 0
    try:
        with open(dest_path, "wb") as f:
            size_bytes += len(header)
            if size_bytes > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size exceeds maximum limit of {max_bytes} bytes"
                )
            f.write(header)

            chunk_size = 64 * 1024
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File size exceeds maximum limit of {max_bytes} bytes"
                    )
                f.write(chunk)
    except Exception:
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
        raise
    finally:
        await file.close()

    return stored_name, content_type, size_bytes
