from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename


def safe_upload_name(filename, allowed_extensions):
    original = secure_filename(filename or "")
    if not original or "." not in original:
        raise ValueError("A file with an allowed extension is required")
    ext = original.rsplit(".", 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type: {ext}")
    return f"{uuid4().hex}.{ext}", ext


def save_upload(file_storage, upload_folder, allowed_extensions):
    filename, ext = safe_upload_name(file_storage.filename, allowed_extensions)
    folder = Path(upload_folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    file_storage.save(target)
    return target, filename, ext


def xss_safe_text(value):
    return str(value or "").replace("\x00", "").strip()
