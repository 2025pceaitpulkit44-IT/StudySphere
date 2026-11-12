from pathlib import Path


class ExtractionError(Exception):
    """Raised with a message that is safe to show to the user."""


def _pdf(path: Path) -> str:
    from pypdf import PdfReader
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("This PDF is password-protected. Please upload an unlocked copy.")
        pages = [(page.extract_text() or "") for page in reader.pages]
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("This PDF could not be read. It may be corrupt.") from exc
    text = "\n\n".join(pages)
    if not text.strip():
        raise ExtractionError("No selectable text found in this PDF. It may be a scan; OCR is not supported yet.")
    return text


def _docx(path: Path) -> str:
    from docx import Document
    try:
        doc = Document(str(path))
    except Exception as exc:
        raise ExtractionError("This Word file could not be read. It may be corrupt.") from exc
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n\n".join(p for p in parts if p.strip())


def _pptx(path: Path) -> str:
    from pptx import Presentation
    try:
        prs = Presentation(str(path))
    except Exception as exc:
        raise ExtractionError("This PowerPoint file could not be read. It may be corrupt.") from exc
    slides = []
    for i, slide in enumerate(prs.slides, start=1):
        texts = [f"Slide {i}"]
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    texts.append(" | ".join(c.text.strip() for c in row.cells))
        if slide.has_notes_slide:
            texts.append(slide.notes_slide.notes_text_frame.text)
        slides.append("\n".join(t for t in texts if t.strip()))
    return "\n\n".join(slides)


def _plain(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExtractionError("Text files must be UTF-8 encoded.") from exc


_EXTRACTORS = {".pdf": _pdf, ".docx": _docx, ".pptx": _pptx, ".txt": _plain, ".md": _plain}


def extract_text(path: Path, ext: str) -> str:
    fn = _EXTRACTORS.get(ext.lower())
    if fn is None:
        raise ExtractionError("This file type is not supported.")
    return fn(path)
