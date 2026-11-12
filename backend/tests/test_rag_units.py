import io
import zipfile

import pytest

from app.rag.chunker import chunk_text
from app.rag.cleaner import clean_text
from app.rag.extractors import ExtractionError, extract_text
from app.services.document_service import UploadError, store_upload


def test_cleaner_unwraps_lines_and_drops_page_numbers():
    raw = "Binary search is an efficient\nalgorithm for sorted arrays.\n\n12\n\nIt runs in O(log n) time."
    out = clean_text(raw)
    assert "efficient algorithm" in out and "\n12\n" not in out and "O(log n)" in out


def test_cleaner_rejoins_hyphenated_words_and_strips_control_chars():
    assert "algorithm" in clean_text("algo-\nrithm\x00 works")


def test_cleaner_keeps_bullets():
    assert "- item one\n- item two" in clean_text("- item one\n- item two")


def test_chunker_empty():
    assert chunk_text("") == [] and chunk_text("   \n ") == []


def test_chunker_respects_size_and_overlaps():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 80 for i in range(10))
    chunks = chunk_text(text, max_words=150, overlap_words=20)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 150 + 20 for c in chunks)
    tail = chunks[0].split()[-20:]
    assert chunks[1].split()[:20] == tail


def test_chunker_splits_one_giant_paragraph():
    chunks = chunk_text("word " * 1000, max_words=200, overlap_words=0)
    assert len(chunks) == 5 and all(len(c.split()) <= 200 for c in chunks)


def test_chunker_keeps_all_content():
    text = "\n\n".join(f"Unique{i} sentence here." for i in range(50))
    joined = " ".join(chunk_text(text, max_words=30, overlap_words=5))
    assert all(f"Unique{i}" in joined for i in range(50))


def test_extract_text_plain(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    assert extract_text(p, ".txt") == "hello world"


def test_extract_docx_and_pptx(tmp_path):
    from docx import Document
    from pptx import Presentation
    d = Document()
    d.add_paragraph("Stacks follow LIFO order.")
    d.save(tmp_path / "a.docx")
    assert "LIFO" in extract_text(tmp_path / "a.docx", ".docx")

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Queues"
    slide.placeholders[1].text = "Queues follow FIFO order."
    prs.save(tmp_path / "a.pptx")
    out = extract_text(tmp_path / "a.pptx", ".pptx")
    assert "FIFO" in out and "Slide 1" in out


def test_extract_pdf_with_text_and_corrupt(tmp_path):
    pdf = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
           b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
           b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 10 50 Td (Hello Graphs) Tj ET\nendstream endobj\n"
           b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\ntrailer<</Root 1 0 R/Size 6>>\n%%EOF")
    (tmp_path / "a.pdf").write_bytes(pdf)
    assert "Hello Graphs" in extract_text(tmp_path / "a.pdf", ".pdf")
    (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4 garbage")
    with pytest.raises(ExtractionError):
        extract_text(tmp_path / "bad.pdf", ".pdf")


def store(data, name, tmp_path, max_bytes=1024 * 1024):
    return store_upload(io.BytesIO(data), name, max_bytes, tmp_path)


def test_store_rejects_bad_inputs(tmp_path):
    for data, name in [(b"x", "run.exe"), (b"", "empty.txt"), (b"plain text", "fake.pdf"),
                       (b"not a zip", "fake.docx"), (b"\x00\x01\x02", "bin.txt"), (b"\xff\xfe\xfa", "latin.txt"),
                       (b"x", "old.doc"), (b"x", "old.ppt")]:
        with pytest.raises(UploadError):
            store(data, name, tmp_path)
    assert list(tmp_path.iterdir()) == []  # nothing left behind


def test_store_enforces_size_limit(tmp_path):
    with pytest.raises(UploadError, match="too large"):
        store(b"a" * 2000, "big.txt", tmp_path, max_bytes=1000)
    assert list(tmp_path.iterdir()) == []


def test_store_ignores_malicious_filename(tmp_path):
    saved = store(b"hello there", "../../etc/passwd.txt", tmp_path)
    assert (tmp_path / saved.stored_path).exists()
    assert "/" not in saved.stored_path and saved.original_filename == "passwd.txt"


def test_store_rejects_docx_without_word_document(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.txt", "hi")
    with pytest.raises(UploadError):
        store(buf.getvalue(), "x.docx", tmp_path)
