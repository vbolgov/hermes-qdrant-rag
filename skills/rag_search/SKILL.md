---
name: rag_search
description: Use when the user asks to find facts, quotes, or mentions in the local Hermes RAG archive. Check index freshness first and never start indexing without confirmation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rag, qdrant, search, citations]
    related_skills: [rag_update]
---

# RAG search

## Procedure

1. Resolve `RAG_PROJECT_DIR` from the current profile file `${HERMES_HOME:-$HOME/.hermes}/.env` at the start of every invocation; do not trust an inherited shell/session value. If it is absent, report that RAG is not configured and do not guess a path.
2. Run `"$RAG_PROJECT_DIR/.venv/bin/python" "$RAG_PROJECT_DIR/ingest.py" --dry-run --json`.
3. If `to_index`, `to_delete`, or `ocr_required` is non-empty, show exact lists and ask whether to invoke `rag_update`. Do not index, OCR, delete, or rebuild from this skill.
4. If the index is current, use MCP `qdrant-rag.search_documents` with `top_k=15` by default; use `top_k=20` for an explicitly detailed request.
5. Write a rich, natural analytical answer: state the direct answer, then explain relationships, mechanisms, implications, comparisons, and tensions that are actually supported by the retrieved fragments. Make reasoned conclusions explicit when multiple sources justify them, clearly distinguishing them from direct quotes; never invent missing evidence or fill gaps with generic advice. Use light headings or bullets only when useful, never a rigid template. Put each evidence block immediately beside the claim it supports: a short quote followed on the next line by `— [<full absolute source_path>](<MCP reveal_url>) · confidence: high|medium|low`. Do not collect citations into a separate source section or replace the answer with citations.

## Completion check

Return traceable evidence or an explicit update plan awaiting user approval.
