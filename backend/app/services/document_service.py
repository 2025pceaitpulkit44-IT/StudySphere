import hashlib
import re
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

MATERIAL_TYPES = [
    "Lecture Notes", "Unit Notes", "Assignment", "Question Bank", "Lab Manual", "Syllabus", "Reference Material",
]

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
}
LEGACY_EXTENSIONS = {".doc", ".ppt"}
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024  # zip-bomb guard for docx/pptx
CHUNK = 1024 * 1024


class UploadError(Exception):
    """Message is safe to show to the user."""


@dataclass
class StoredFile:
    stored_path: str          # server-generated, relative to the upload root
    original_filename: str    # sanitised, for display only
    mime_type: str
    size_bytes: int
    sha256: str
    extension: str


def safe_display_name(name: str) -> str:
    base = Path((name or "").replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return (base or "upload")[:255]


def _sniff(path: Path, ext: str) -> None:
    """Check the file's real content matches its extension (the client-supplied MIME type is not trusted)."""
    if ext == ".pdf":
        with open(path, "rb") as f:
            if not f.read(5) == b"%PDF-":
                raise UploadError("This file is not a valid PDF.")
    elif ext in (".docx", ".pptx"):
        required = "word/document.xml" if ext == ".docx" else "ppt/presentation.xml"
        if not zipfile.is_zipfile(path):
            raise UploadError(f"This file is not a valid {ext} document.")
        with zipfile.ZipFile(path) as z:
            if required not in z.namelist():
                raise UploadError(f"This file is not a valid {ext} document.")
            if sum(i.file_size for i in z.infolist()) > MAX_UNCOMPRESSED_BYTES:
                raise UploadError("This file expands to an unreasonable size and was rejected.")
    else:  # .txt / .md
        data = path.read_bytes()
        if b"\x00" in data[:8192]:
            raise UploadError("This does not look like a text file.")
        try:
            data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise UploadError("Text files must be UTF-8 encoded.")


def store_upload(fileobj: BinaryIO, original_name: str, max_bytes: int, dest_dir: Path) -> StoredFile:
    ext = Path(original_name or "").suffix.lower()
    if ext in LEGACY_EXTENSIONS:
        raise UploadError(f"Legacy {ext} files are not supported. Please save as {ext}x and upload again.")
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError("Unsupported file type. Allowed: PDF, DOCX, PPTX, TXT, Markdown.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / f"{uuid.uuid4().hex}{ext}"  # name is generated here; user input never touches the path
    partial = final.with_suffix(final.suffix + ".part")
    digest, size = hashlib.sha256(), 0
    try:
        with open(partial, "wb") as out:
            while chunk := fileobj.read(CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadError(f"File is too large. The limit is {max_bytes // (1024 * 1024)} MB.")
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise UploadError("The file is empty.")
        _sniff(partial, ext)
        partial.rename(final)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return StoredFile(final.name, safe_display_name(original_name), ALLOWED_EXTENSIONS[ext], size, digest.hexdigest(), ext)


def delete_stored_file(root: Path, stored_path: str) -> None:
    """Remove a stored file, refusing anything that resolves outside the upload root."""
    target = (root / stored_path).resolve()
    if root.resolve() in target.parents:
        target.unlink(missing_ok=True)
