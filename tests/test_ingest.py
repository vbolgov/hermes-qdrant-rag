import sys
import types
from pathlib import Path

import fitz

from ingest import chunk_text, is_scanned_pdf, iter_files, ocr_pdf_to_text, parse_frontmatter


def test_iter_files_respects_ragignore(tmp_path: Path):
    (tmp_path / "keep.md").write_text("keep", encoding="utf-8")
    (tmp_path / "ignore.md").write_text("ignore", encoding="utf-8")
    (tmp_path / ".ragignore").write_text("ignore.md\n", encoding="utf-8")

    assert [path.name for path in iter_files(tmp_path)] == ["keep.md"]


def test_parse_frontmatter_returns_metadata_and_body():
    metadata, body = parse_frontmatter(
        "---\nsource_id: demo_001\ndomain: sleep\ntags: [sleep, recovery]\n---\n# Body\nText"
    )

    assert metadata["source_id"] == "demo_001"
    assert metadata["domain"] == "sleep"
    assert metadata["tags"] == ["sleep", "recovery"]
    assert body == "# Body\nText"


def test_chunk_text_always_advances_after_an_early_paragraph_break():
    text = "x" * 201 + "\n\n" + "y" * 2_000

    chunks = chunk_text(text)

    assert len(chunks) >= 2
    assert len(chunks[0]) > 250


def test_is_scanned_pdf_distinguishes_text_layer_from_scan(tmp_path: Path):
    text_pdf = tmp_path / "text.pdf"
    text_doc = fitz.open()
    text_doc.new_page().insert_text((72, 72), "Searchable text")
    text_doc.save(text_pdf)
    text_doc.close()

    scan_pdf = tmp_path / "scan.pdf"
    scan_doc = fitz.open()
    scan_doc.new_page()
    scan_doc.save(scan_pdf)
    scan_doc.close()

    assert is_scanned_pdf(text_pdf) is False
    assert is_scanned_pdf(scan_pdf) is True


def test_ocr_pdf_to_text_uses_paddleocr(monkeypatch, tmp_path: Path):
    scan_pdf = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(scan_pdf)
    document.close()

    class FakePaddleOCR:
        def __init__(self, *, lang: str, **_kwargs):
            assert lang == "ru"

        def predict(self, _image_path: str):
            return [types.SimpleNamespace(json={"res": {"rec_texts": ["Распознанный текст"]}})]

    monkeypatch.setitem(sys.modules, "paddleocr", types.SimpleNamespace(PaddleOCR=FakePaddleOCR))

    assert ocr_pdf_to_text(scan_pdf, "ru") == "Распознанный текст"
