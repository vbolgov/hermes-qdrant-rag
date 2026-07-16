from pathlib import Path
import inspect
from types import SimpleNamespace
from urllib.parse import quote

from rag_mcp import _format_hit, absolute_source_path, reveal_source_in_finder, search_documents


def test_absolute_source_path_resolves_relative_paths_under_data_directory(tmp_path: Path):
    data_dir = tmp_path / "library"

    assert absolute_source_path("books/example.md", data_dir=data_dir) == str(
        (data_dir / "books/example.md").resolve()
    )


def test_formatted_hit_includes_clickable_file_url(tmp_path: Path):
    path = (tmp_path / "library" / "books" / "example.md").resolve()
    hit = SimpleNamespace(score=1.0, payload={"source_path": "books/example.md"})

    formatted = _format_hit(hit, data_dir=path.parents[1])
    assert formatted["source_url"] == path.as_uri()
    assert formatted["reveal_url"] == f"https://hermes.local/reveal-file?path={quote(str(path), safe='')}"


def test_reveal_source_in_finder_reveals_a_library_file(tmp_path: Path, monkeypatch):
    source = tmp_path / "library" / "books" / "example.md"
    source.parent.mkdir(parents=True)
    source.write_text("example", encoding="utf-8")
    calls = []
    monkeypatch.setattr("rag_mcp.subprocess.run", lambda args, check: calls.append((args, check)))

    result = reveal_source_in_finder(str(source), data_dir=source.parents[1])

    assert result["revealed"] is True
    assert calls == [(["open", "-R", str(source)], True)]


def test_search_documents_defaults_to_detailed_retrieval():
    assert inspect.signature(search_documents).parameters["top_k"].default == 15
