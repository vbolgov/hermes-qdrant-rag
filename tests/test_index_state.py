from pathlib import Path

from index_state import DocumentState, build_sync_plan, relative_source_path


def state(path: str, digest: str) -> DocumentState:
    return DocumentState(
        source_path=path,
        sha256=digest,
        modified_ns=1,
        size=10,
        indexed_at="2026-07-14T00:00:00Z",
        point_count=2,
    )


def test_sync_plan_separates_new_changed_unchanged_and_removed_documents():
    previous = {
        "same.md": state("same.md", "a"),
        "changed.md": state("changed.md", "old"),
        "removed.md": state("removed.md", "gone"),
    }
    current = {
        "same.md": state("same.md", "a"),
        "changed.md": state("changed.md", "new"),
        "new.md": state("new.md", "fresh"),
    }

    plan = build_sync_plan(previous, current, rebuild=False)

    assert plan.to_index == ("changed.md", "new.md")
    assert plan.unchanged == ("same.md",)
    assert plan.to_delete == ("removed.md",)


def test_rebuild_reindexes_every_current_document_and_removes_no_live_source():
    previous = {"same.md": state("same.md", "a")}
    current = {"same.md": state("same.md", "a"), "new.md": state("new.md", "b")}

    plan = build_sync_plan(previous, current, rebuild=True)

    assert plan.to_index == ("new.md", "same.md")
    assert plan.unchanged == ()
    assert plan.to_delete == ()


def test_source_paths_are_relative_and_portable(tmp_path: Path):
    root = tmp_path / "library"
    document = root / "articles" / "note.md"
    document.parent.mkdir(parents=True)
    document.write_text("text", encoding="utf-8")

    assert relative_source_path(document, root) == "articles/note.md"
