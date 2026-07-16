from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from vectorize import embed_text


class Embedder(Protocol):
    mode: str
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class HashEmbedder:
    mode: str = "hash"
    model: str = "stable-hash-1024"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [embed_text(text) for text in texts]


class OpenAIEmbedder:
    mode = "openai"

    def __init__(self, model: str, base_url: str | None = None) -> None:
        from openai import OpenAI

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for EMBEDDING_BACKEND=openai")
        self.model = model
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=base_url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


class LocalEmbedder:
    mode = "local"

    def __init__(self, model: str) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as error:
            raise RuntimeError(
                "fastembed is required for EMBEDDING_BACKEND=local; run ./bootstrap.sh"
            ) from error
        self.model = model
        self._model = TextEmbedding(model_name=model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]


class MlxEmbedder:
    mode = "mlx"

    def __init__(self, model: str) -> None:
        try:
            from mlx_embeddings import generate, load
        except ImportError as error:
            raise RuntimeError(
                "mlx-embeddings is required for EMBEDDING_BACKEND=mlx; install project dependencies first"
            ) from error
        self.model = model
        self._generate = generate
        self._model, self._processor = load(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        output = self._generate(self._model, self._processor, texts=texts, max_length=512)
        vectors = getattr(output, "text_embeds", output)
        return vectors.tolist()


def create_embedder(
    backend: str,
    *,
    local_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    mlx_model: str = "mlx-community/multilingual-e5-small-mlx",
    openai_model: str = "text-embedding-3-small",
    openai_base_url: str | None = None,
) -> Embedder:
    normalized = backend.strip().lower()
    if normalized == "hash":
        return HashEmbedder()
    if normalized == "local":
        return LocalEmbedder(local_model)
    if normalized == "mlx":
        return MlxEmbedder(mlx_model)
    if normalized == "openai":
        return OpenAIEmbedder(openai_model, base_url=openai_base_url)
    raise ValueError(f"Unsupported embedding backend: {backend}")
