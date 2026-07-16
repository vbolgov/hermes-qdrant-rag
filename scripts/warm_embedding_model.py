from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from embeddings import create_embedder
for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

backend = os.getenv("EMBEDDING_BACKEND", "mlx")
embedder = create_embedder(
    backend,
    local_model=os.getenv("LOCAL_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
    mlx_model=os.getenv("MLX_EMBED_MODEL", "mlx-community/multilingual-e5-small-mlx"),
    openai_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
    openai_base_url=os.getenv("OPENAI_BASE_URL"),
)
vector = embedder.embed(["Hermes RAG readiness check"])[0]
print({"embedding_mode": embedder.mode, "embedding_model": embedder.model, "vector_size": len(vector)})
