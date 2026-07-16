---
name: rag_update
description: Use when the user approved an update of the local Hermes Qdrant RAG index. Show the synchronization plan and require confirmation before destructive actions or OCR.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rag, qdrant, indexing, ocr]
    related_skills: [rag_search]
---

# RAG update

## Procedure

1. Resolve `RAG_PROJECT_DIR`; if it is absent, report that RAG is not configured and do not guess a path.
2. Run `"$RAG_PROJECT_DIR/.venv/bin/python" "$RAG_PROJECT_DIR/ingest.py" --dry-run --json` first.
3. Show exact `to_index`, `to_delete`, and `ocr_required` lists.
4. Require explicit current confirmation before deleting vectors, using `--ocr`, or using `--rebuild`.
5. Start Qdrant: `docker compose -f "$RAG_PROJECT_DIR/docker-compose.yml" up -d`.
6. Run the confirmed `ingest.py` mode, then verify with MCP `collection_stats`.
7. Report added/updated/deleted documents, chunks, OCR status, and readiness.

## Safety

Do not modify source files in `library/`. Do not reveal API keys. Do not perform a destructive operation without current confirmation.

## Completion check

Manifest update and Qdrant collection state are verified.
