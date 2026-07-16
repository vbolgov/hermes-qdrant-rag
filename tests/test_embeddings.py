import sys
import types

import pytest

from embeddings import create_embedder


def test_hash_backend_is_available_without_external_dependencies():
    embedder = create_embedder("hash")
    vectors = embedder.embed(["alpha beta", "gamma"])
    assert embedder.mode == "hash"
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024


def test_mlx_backend_loads_a_model_and_returns_text_embeddings(monkeypatch):
    captured: dict[str, object] = {}

    class FakeArray:
        def tolist(self):
            return [[0.1, 0.2], [0.3, 0.4]]

    def fake_load(model_name: str):
        captured["model_name"] = model_name
        return "model", "processor"

    def fake_generate(model, processor, *, texts, max_length):
        captured.update({"model": model, "processor": processor, "texts": texts, "max_length": max_length})
        return types.SimpleNamespace(text_embeds=FakeArray())

    monkeypatch.setitem(sys.modules, "mlx_embeddings", types.SimpleNamespace(load=fake_load, generate=fake_generate))

    embedder = create_embedder("mlx", mlx_model="mlx-community/test-embedding")

    assert embedder.mode == "mlx"
    assert embedder.model == "mlx-community/test-embedding"
    assert embedder.embed(["alpha", "beta"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert captured == {
        "model_name": "mlx-community/test-embedding",
        "model": "model",
        "processor": "processor",
        "texts": ["alpha", "beta"],
        "max_length": 512,
    }


def test_unknown_embedding_backend_is_rejected():
    with pytest.raises(ValueError, match="Unsupported embedding backend"):
        create_embedder("unknown")


def test_openai_backend_uses_configured_compatible_base_url(monkeypatch):
    captured: dict[str, str] = {}

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str):
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    embedder = create_embedder(
        "openai",
        openai_model="test-embedding",
        openai_base_url="https://embeddings.example/v1",
    )

    assert embedder.mode == "openai"
    assert embedder.model == "test-embedding"
    assert captured == {
        "api_key": "test-key",
        "base_url": "https://embeddings.example/v1",
    }
