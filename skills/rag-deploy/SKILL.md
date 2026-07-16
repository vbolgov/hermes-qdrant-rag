---
name: rag-deploy
description: Use when a user gives a public Hermes Qdrant RAG repository and wants Hermes to deploy it locally without manual shell steps.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rag, deploy, qdrant, mlx, orbstack]
    related_skills: [rag_search, rag_update]
---

# Deploy Hermes Qdrant RAG

## Procedure

1. Read the cloned repository `AGENTS.md` and verify the host is macOS Apple Silicon.
2. Run `scripts/agent-bootstrap.sh` from repository root. It owns prerequisite setup, OrbStack/Docker readiness, Python dependencies, MLX model warm-up, skills installation and MCP registration.
3. Verify bootstrap output: Qdrant available, MLX vector generated, tests green, and `ingest.py --dry-run --json` valid.
4. Do not index documents. Tell the user to open a new Hermes Desktop chat, then invoke `rag_update` for an approved first sync.

## Completion check

Report the registered MCP name, effective embedding backend/model, Qdrant readiness, and that no source documents were indexed automatically.
