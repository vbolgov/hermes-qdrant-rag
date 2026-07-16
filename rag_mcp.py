from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient

from embeddings import create_embedder

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_COLLECTION = "consulting_kb"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_LOCAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MLX_MODEL = "mlx-community/multilingual-e5-small-mlx"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


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


load_env()
QDRANT_URL = os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL)
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION)
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "local")
LOCAL_EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", DEFAULT_LOCAL_MODEL)
MLX_EMBED_MODEL = os.getenv("MLX_EMBED_MODEL", DEFAULT_MLX_MODEL)
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", DEFAULT_OPENAI_MODEL)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
RAG_DATA_DIR = os.getenv("RAG_DATA_DIR", str(PROJECT_ROOT / "library"))

mcp = FastMCP("hermes-qdrant-rag")
client = QdrantClient(url=QDRANT_URL)
embedder = create_embedder(
    EMBEDDING_BACKEND,
    local_model=LOCAL_EMBED_MODEL,
    mlx_model=MLX_EMBED_MODEL,
    openai_model=OPENAI_EMBED_MODEL,
    openai_base_url=OPENAI_BASE_URL,
)


def absolute_source_path(source_path: str | None, *, data_dir: str | Path = RAG_DATA_DIR) -> str | None:
    if source_path is None:
        return None
    source = Path(source_path).expanduser()
    if source.is_absolute():
        return str(source.resolve())
    root = Path(data_dir).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    return str((root.resolve() / source).resolve())


def _format_hit(hit, *, data_dir: str | Path = RAG_DATA_DIR) -> dict:
    payload = hit.payload or {}
    source_path = absolute_source_path(payload.get("source_path"), data_dir=data_dir)
    return {
        "score": round(float(hit.score or 0), 4),
        "source_id": payload.get("source_id"),
        "source_path": source_path,
        "source_url": Path(source_path).as_uri() if source_path else None,
        "reveal_url": f"https://hermes.local/reveal-file?path={quote(source_path, safe='')}" if source_path else None,
        "title": payload.get("title"),
        "chunk_id": payload.get("chunk_id"),
        "chunk_index": payload.get("chunk_index"),
        "text": payload.get("text", ""),
    }


@mcp.tool()
def collection_stats() -> dict:
    """Show local Qdrant collection and effective embedding status."""
    exists = client.collection_exists(collection_name=QDRANT_COLLECTION)
    count = client.count(QDRANT_COLLECTION, exact=True).count if exists else 0
    return {
        "qdrant_url": QDRANT_URL,
        "collection": QDRANT_COLLECTION,
        "exists": exists,
        "point_count": count,
        "embedding_mode": embedder.mode,
        "embedding_model": embedder.model,
        "data_dir": RAG_DATA_DIR,
    }


@mcp.tool()
def reveal_source_in_finder(source_path: str, *, data_dir: str | Path = RAG_DATA_DIR) -> dict:
    """Reveal a RAG source file in macOS Finder without opening its contents."""
    root = Path(data_dir).expanduser().resolve()
    candidate = Path(source_path).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return {"revealed": False, "error": "Source path is outside the configured RAG library."}
    if not candidate.is_file():
        return {"revealed": False, "error": "Source file does not exist.", "source_path": str(candidate)}
    subprocess.run(["open", "-R", str(candidate)], check=True)
    return {"revealed": True, "source_path": str(candidate)}


@mcp.tool()
def search_documents(query: str, top_k: int = 15) -> dict:
    """Search the local Qdrant archive and return traceable source fragments."""
    if not client.collection_exists(collection_name=QDRANT_COLLECTION):
        return {"query": query, "embedding_mode": embedder.mode, "results": []}
    vector = embedder.embed([query])[0]
    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        limit=max(1, min(top_k, 50)),
        with_payload=True,
    )
    hits = response.points if hasattr(response, "points") else response
    return {
        "query": query,
        "embedding_mode": embedder.mode,
        "embedding_model": embedder.model,
        "results": [_format_hit(hit) for hit in hits],
    }


if __name__ == "__main__":
    mcp.run()
