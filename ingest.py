from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import fitz
import yaml
from bs4 import BeautifulSoup
from docx import Document
from ebooklib import ITEM_DOCUMENT, epub
from qdrant_client import QdrantClient
from qdrant_client.http import models

from embeddings import create_embedder
from index_state import (
    DocumentState,
    build_sync_plan,
    inspect_document,
    load_manifest,
    save_manifest,
    utc_now,
)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_COLLECTION = "consulting_kb"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_DATA_DIR = PROJECT_ROOT / "library"
DEFAULT_MANIFEST = PROJECT_ROOT / "Context" / "rag-index-manifest.csv"
DEFAULT_LOCAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MLX_MODEL = "mlx-community/multilingual-e5-small-mlx"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".epub", ".fb2"}


@dataclass(frozen=True)
class Chunk:
    text: str
    source_path: str
    source_id: str
    title: str
    chunk_index: int
    source_sha256: str
    metadata: dict[str, object]


def load_env() -> None:
    for env_path in (PROJECT_ROOT / ".env", Path.home() / ".hermes" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def clean_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    out = "\n".join(line for line in lines if line.strip())
    return "\n".join(part.strip() for part in out.split("\n\n") if part.strip())


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    closing = text.find("\n---\n", 4)
    if closing < 0:
        return {}, text
    raw = text[4:closing]
    parsed = yaml.safe_load(raw) or {}
    if not isinstance(parsed, dict):
        return {}, text
    return parsed, text[closing + 5 :]


def payload_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [payload_value(item) for item in value]
    return str(value)


def chunk_text(text: str, max_chars: int = 1800, overlap_chars: int = 250) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            cut = text.rfind("\n\n", start, end)
            if cut <= start + overlap_chars:
                cut = text.rfind("\n", start, end)
            if cut > start + overlap_chars:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end if end >= len(text) else max(end - overlap_chars, start + 1)
    return chunks


def iter_files(root: Path) -> Iterable[Path]:
    ignore_file = root / ".ragignore"
    ignore_patterns = []
    if ignore_file.exists():
        ignore_patterns = [
            line.strip()
            for line in ignore_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if path.name.startswith(".") or any(part.startswith(".") for part in relative.parts):
            continue
        if any(relative.match(pattern) for pattern in ignore_patterns):
            continue
        if path.suffix.lower() in ALLOWED_EXTENSIONS:
            yield path


def is_scanned_pdf(path: Path) -> bool:
    """Return True when a PDF has no usable text layer and needs OCR."""
    doc = fitz.open(path)
    try:
        return not any(str(page.get_text("text")).strip() for page in doc)
    finally:
        doc.close()


def ocr_pdf_to_text(path: Path, language: str) -> str:
    """Extract text locally with PaddleOCR without modifying the source PDF."""
    try:
        from paddleocr import PaddleOCR
    except ImportError as error:
        raise RuntimeError("PaddleOCR is required for OCR. Install project dependencies and retry with --ocr.") from error

    engine = PaddleOCR(
        lang=language,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    doc = fitz.open(path)
    try:
        pages: list[str] = []
        for page in doc:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png") as image:
                image.write(pixmap.tobytes("png"))
                image.flush()
                results = engine.predict(image.name)
            for result in results:
                payload = result.json.get("res", {})
                texts = [str(text).strip() for text in payload.get("rec_texts", []) if str(text).strip()]
                if texts:
                    pages.append("\n".join(texts))
        return "\n\n".join(pages)
    finally:
        doc.close()


def extract_text(path: Path, *, ocr: bool = False, ocr_language: str = "ru") -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        doc = fitz.open(path)
        try:
            text = "\n\n".join(str(page.get_text("text")) for page in doc)
        finally:
            doc.close()
        if text.strip() or not ocr:
            return text
        return ocr_pdf_to_text(path, ocr_language)
    if suffix == ".docx":
        return "\n".join(paragraph.text for paragraph in Document(path).paragraphs)
    if suffix == ".epub":
        book = epub.read_epub(str(path))
        parts: list[str] = []
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            text = BeautifulSoup(item.get_body_content(), "html.parser").get_text("\n", strip=True)
            if text:
                parts.append(text)
        return "\n\n".join(parts)
    if suffix == ".fb2":
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="ignore"))
        return "\n".join(text.strip() for text in root.itertext() if text and text.strip())
    raise ValueError(f"unsupported file type: {suffix}")


def make_id(source_path: str, chunk_index: int, text: str) -> str:
    text_hash = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_path}|{chunk_index}|{text_hash}"))


def delete_source(client: QdrantClient, collection: str, source_path: str) -> None:
    if not client.collection_exists(collection_name=collection):
        return
    client.delete(
        collection_name=collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="source_path", match=models.MatchValue(value=source_path))]
            )
        ),
        wait=True,
    )


def ensure_collection(client: QdrantClient, collection: str, vector_size: int) -> None:
    if not client.collection_exists(collection_name=collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        return
    info = client.get_collection(collection_name=collection)
    vectors = info.config.params.vectors
    existing_size = getattr(vectors, "size", None)
    if existing_size is not None and existing_size != vector_size:
        raise RuntimeError(
            f"Collection vector size is {existing_size}, embedder returns {vector_size}. "
            "Run ingest.py --rebuild after changing the embedding backend."
        )


def index_path(
    root: Path,
    collection: str,
    qdrant_url: str,
    manifest_path: Path,
    backend: str,
    local_model: str,
    mlx_model: str,
    openai_model: str,
    openai_base_url: str,
    *,
    rebuild: bool = False,
    dry_run: bool = False,
    ocr: bool = False,
    ocr_language: str = "ru",
) -> dict[str, object]:
    files = {state.source_path: (path, state) for path in iter_files(root) if (state := inspect_document(path, root))}
    current = {source: state for source, (_, state) in files.items()}
    previous = load_manifest(manifest_path)
    plan = build_sync_plan(previous, current, rebuild=rebuild)
    ocr_required = [
        source_path
        for source_path in plan.to_index
        if files[source_path][0].suffix.lower() == ".pdf" and is_scanned_pdf(files[source_path][0])
    ]

    if dry_run:
        return {
            "embedding_mode": backend,
            "to_index": list(plan.to_index),
            "unchanged": list(plan.unchanged),
            "to_delete": list(plan.to_delete),
            "ocr_required": ocr_required,
            "indexed_chunks": 0,
        }

    client = QdrantClient(url=qdrant_url)
    if rebuild and client.collection_exists(collection_name=collection):
        client.delete_collection(collection_name=collection)

    for source_path in plan.to_delete:
        delete_source(client, collection, source_path)
        print(f"removed vectors for {source_path}")

    embedder = create_embedder(
        backend,
        local_model=local_model,
        mlx_model=mlx_model,
        openai_model=openai_model,
        openai_base_url=openai_base_url,
    )
    next_manifest: dict[str, DocumentState] = {
        source_path: previous[source_path] for source_path in plan.unchanged
    }
    indexed_chunks = 0

    for source_path in plan.to_index:
        path, state = files[source_path]
        if source_path in ocr_required and not ocr:
            print(f"OCR required; skipped {source_path}. Re-run with --ocr after confirmation.")
            continue
        delete_source(client, collection, source_path)
        metadata, document_body = parse_frontmatter(extract_text(path, ocr=ocr, ocr_language=ocr_language))
        source_id = str(metadata.get("source_id") or state.sha256)
        title = str(metadata.get("title") or path.stem)
        payload_metadata = {
            key: payload_value(value)
            for key, value in metadata.items()
            if key in {"source_type", "domain", "reliability", "date_added", "tags", "marker"}
        }
        chunks = [
            Chunk(
                text=text,
                source_path=source_path,
                source_id=source_id,
                title=title,
                chunk_index=index,
                source_sha256=state.sha256,
                metadata=payload_metadata,
            )
            for index, text in enumerate(chunk_text(document_body))
        ]
        if chunks:
            # FastEmbed can exceed its practical memory limit when a long document
            # is embedded as one large batch. Keep the indexer streaming-friendly.
            vectors: list[list[float]] = []
            batch_size = 16
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                vectors.extend(embedder.embed([chunk.text for chunk in batch]))
            ensure_collection(client, collection, len(vectors[0]))
            points = [
                models.PointStruct(
                    id=make_id(chunk.source_path, chunk.chunk_index, chunk.text),
                    vector=vector,
                    payload={
                        **chunk.metadata,
                        "source_id": chunk.source_id,
                        "source_path": chunk.source_path,
                        "title": chunk.title,
                        "chunk_id": f"{chunk.source_path}#{chunk.chunk_index}",
                        "chunk_index": chunk.chunk_index,
                        "source_sha256": chunk.source_sha256,
                        "embedding_mode": embedder.mode,
                        "embedding_model": embedder.model,
                        "text": chunk.text,
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            client.upsert(collection_name=collection, points=points, wait=True)
        next_manifest[source_path] = replace(
            state,
            indexed_at=utc_now(),
            point_count=len(chunks),
        )
        indexed_chunks += len(chunks)
        print(f"indexed {len(chunks):4d} chunks from {source_path}")

    save_manifest(manifest_path, next_manifest)
    return {
        "embedding_mode": embedder.mode,
        "to_index": len(plan.to_index),
        "unchanged": len(plan.unchanged),
        "to_delete": len(plan.to_delete),
        "ocr_required": ocr_required,
        "indexed_chunks": indexed_chunks,
    }


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Synchronize local documents with Qdrant")
    parser.add_argument("--path", default=os.getenv("RAG_DATA_DIR", str(DEFAULT_DATA_DIR)))
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION))
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL))
    parser.add_argument("--manifest", default=os.getenv("RAG_MANIFEST", str(DEFAULT_MANIFEST)))
    parser.add_argument("--backend", choices=["local", "mlx", "openai", "hash"], default=os.getenv("EMBEDDING_BACKEND", "local"))
    parser.add_argument("--local-model", default=os.getenv("LOCAL_EMBED_MODEL", DEFAULT_LOCAL_MODEL))
    parser.add_argument("--mlx-model", default=os.getenv("MLX_EMBED_MODEL", DEFAULT_MLX_MODEL))
    parser.add_argument("--openai-model", default=os.getenv("OPENAI_EMBED_MODEL", DEFAULT_OPENAI_MODEL))
    parser.add_argument("--openai-base-url", default=os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL))
    parser.add_argument("--rebuild", action="store_true", help="Delete and rebuild the collection")
    parser.add_argument("--dry-run", action="store_true", help="Show synchronization plan without Qdrant writes")
    parser.add_argument("--ocr", action="store_true", help="Run local OCR for detected scanned PDFs")
    parser.add_argument("--ocr-language", default=os.getenv("OCR_LANGUAGE", "ru"))
    parser.add_argument("--json", action="store_true", help="Print a machine-readable result")
    args = parser.parse_args()

    root = Path(args.path).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    root = root.resolve()
    if not root.exists():
        raise SystemExit(f"missing folder: {root}")

    manifest_path = Path(args.manifest).expanduser()
    if not manifest_path.is_absolute():
        manifest_path = PROJECT_ROOT / manifest_path

    result = index_path(
        root=root,
        collection=args.collection,
        qdrant_url=args.qdrant_url,
        manifest_path=manifest_path.resolve(),
        backend=args.backend,
        local_model=args.local_model,
        mlx_model=args.mlx_model,
        openai_model=args.openai_model,
        openai_base_url=args.openai_base_url,
        rebuild=args.rebuild,
        dry_run=args.dry_run,
        ocr=args.ocr,
        ocr_language=args.ocr_language,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print("done:", result)


if __name__ == "__main__":
    main()
