from pathlib import Path
import inspect
from types import SimpleNamespace

from rag_mcp import _format_hit, absolute_source_path, search_documents


def test_absolute_source_path_resolves_relative_paths_under_data_directory(tmp_path: Path):
    data_dir = tmp_path / "library"

    assert absolute_source_path("books/example.md", data_dir=data_dir) == str(
        (data_dir / "books/example.md").resolve()
    )


def test_formatted_hit_includes_clickable_file_url(tmp_path: Path):
    path = (tmp_path / "library" / "books" / "example.md").resolve()
    hit = SimpleNamespace(score=1.0, payload={"source_path": "books/example.md"})

    assert _format_hit(hit, data_dir=path.parents[1])["source_url"] == path.as_uri()


def test_search_documents_defaults_to_detailed_retrieval():
    assert inspect.signature(search_documents).parameters["top_k"].default == 15
