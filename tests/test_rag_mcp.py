from pathlib import Path

from rag_mcp import absolute_source_path


def test_absolute_source_path_resolves_relative_paths_under_data_directory(tmp_path: Path):
    data_dir = tmp_path / "library"

    assert absolute_source_path("books/example.md", data_dir=data_dir) == str(
        (data_dir / "books/example.md").resolve()
    )
