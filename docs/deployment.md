# Deployment and recovery

## Deployment contract

The public repository contains code and neutral fixtures only. `scripts/agent-bootstrap.sh` is run by Hermes, not by the user. It may install OrbStack through Homebrew, open OrbStack, install `uv`, create `.venv`, create `.env`, start Qdrant, warm the configured embedding model, register MCP and install local skills.

## Persistent local state

| State | Location | Git |
|---|---|---|
| user configuration | `.env` | ignored |
| source documents | `library/` | ignored except fixtures |
| sync manifest | `Context/rag-index-manifest.csv` | ignored |
| vectors | Docker volume `hermes-qdrant-data` | outside repository |
| model cache | Hugging Face cache | outside repository |

## Recovery

- If Qdrant is unavailable, rerun the bootstrap entrypoint; it preserves the Docker volume.
- If MCP tools do not reflect a configuration change, start a new Hermes Desktop chat.
- If the dry-run lists changes, use `rag_update`; do not invoke raw indexing without the skill flow.
- If the embedding backend/model changes, use the skill's confirmed rebuild path.

## Acceptance checks

A deployment is ready only when Qdrant responds, model warm-up returns a vector, tests pass, dry-run is valid JSON, and `hermes mcp test qdrant-rag` succeeds.
