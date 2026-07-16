# Hermes Qdrant RAG — Agent Contract

## Goal

Turn a fresh public clone into a working local RAG for the current Hermes profile. The user must not run shell, Docker, SSH or Python commands manually.

## First-run procedure

1. Confirm macOS Apple Silicon. Stop and report an unsupported host.
2. Run `scripts/agent-bootstrap.sh` from repository root.
3. Do not edit or print `.env` secrets.
4. Confirm bootstrap completed: Qdrant is running, MLX warm-up returned a vector, tests passed, and dry-run returned JSON.
5. Tell the user to open a new Hermes Desktop chat so MCP and installed skills are loaded.
6. Do not index any documents unless the user explicitly asks to run `rag_update` or approves its displayed plan.

## Runtime rules

- `library/` is read-only for the pipeline.
- Use `rag_search` for questions; it must dry-run before search.
- Use `rag_update` for synchronization; require current confirmation before OCR, vector deletion, or `--rebuild`.
- Keep source citations as full absolute local paths in search results.
- Do not add personal documents, `.env`, manifests, model caches or Qdrant data to Git.

## Public-repository checks

Before every commit run:

```text
.venv/bin/python -m pytest tests -q
git diff --check
git check-ignore library/books/* library/articles/*
```

The only supported deployment entrypoint is `scripts/agent-bootstrap.sh`.
