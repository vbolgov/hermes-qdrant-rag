from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class DocumentState:
    source_path: str
    sha256: str
    modified_ns: int
    size: int
    indexed_at: str
    point_count: int


@dataclass(frozen=True)
class SyncPlan:
    to_index: tuple[str, ...]
    unchanged: tuple[str, ...]
    to_delete: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative_source_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_document(path: Path, root: Path) -> DocumentState:
    stat = path.stat()
    return DocumentState(
        source_path=relative_source_path(path, root),
        sha256=sha256_file(path),
        modified_ns=stat.st_mtime_ns,
        size=stat.st_size,
        indexed_at="",
        point_count=0,
    )


def build_sync_plan(
    previous: Mapping[str, DocumentState],
    current: Mapping[str, DocumentState],
    rebuild: bool = False,
) -> SyncPlan:
    current_paths = set(current)
    previous_paths = set(previous)
    if rebuild:
        to_index = current_paths
        unchanged: set[str] = set()
    else:
        unchanged = {
            path
            for path in current_paths & previous_paths
            if current[path].sha256 == previous[path].sha256
        }
        to_index = current_paths - unchanged
    return SyncPlan(
        to_index=tuple(sorted(to_index)),
        unchanged=tuple(sorted(unchanged)),
        to_delete=tuple(sorted(previous_paths - current_paths)),
    )


def load_manifest(path: Path) -> dict[str, DocumentState]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {
            row["source_path"]: DocumentState(
                source_path=row["source_path"],
                sha256=row["sha256"],
                modified_ns=int(row["modified_ns"]),
                size=int(row["size"]),
                indexed_at=row["indexed_at"],
                point_count=int(row["point_count"]),
            )
            for row in csv.DictReader(handle)
        }


def save_manifest(path: Path, states: Mapping[str, DocumentState]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields = ["source_path", "sha256", "modified_ns", "size", "indexed_at", "point_count"]
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for source_path in sorted(states):
            writer.writerow(asdict(states[source_path]))
    temporary.replace(path)
