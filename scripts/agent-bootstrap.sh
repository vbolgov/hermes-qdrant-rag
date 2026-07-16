#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  printf '%s\n' 'This distribution supports macOS on Apple Silicon only.' >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    printf '%s\n' 'Homebrew is required to install OrbStack automatically.' >&2
    exit 3
  fi
  brew install --cask orbstack
  open -a OrbStack
fi

for _ in $(seq 1 60); do
  docker info >/dev/null 2>&1 && break
  sleep 2
done
docker info >/dev/null

if ! command -v uv >/dev/null 2>&1; then
  brew install uv
fi
(cd "$ROOT" && uv sync --extra dev)
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

mkdir -p "$ROOT/library" "$ROOT/Context" "$HERMES_HOME/skills"
for skill in rag_search rag_update rag-deploy; do
  ln -sfn "$ROOT/skills/$skill" "$HERMES_HOME/skills/$skill"
done

# A disposable clone must never replace the user's active RAG configuration.
if [[ "$ROOT" == /tmp/* || "$ROOT" == /private/tmp/* ]]; then
  ACTIVATE_RAG=0
else
  ACTIVATE_RAG=1
fi

if [[ "$ACTIVATE_RAG" == 1 ]]; then
  "$PYTHON" - "$HERMES_HOME/.env" "$ROOT" <<'PY'
from pathlib import Path
import sys
path, root = Path(sys.argv[1]), sys.argv[2]
lines = path.read_text(encoding='utf-8', errors='ignore').splitlines() if path.exists() else []
lines = [line for line in lines if not line.startswith('RAG_PROJECT_DIR=')]
path.write_text('\n'.join([*lines, f'RAG_PROJECT_DIR={root}']) + '\n', encoding='utf-8')
PY
fi

docker compose -f "$ROOT/docker-compose.yml" up -d --wait --wait-timeout 180
"$PYTHON" "$ROOT/scripts/warm_embedding_model.py"
if [[ "$ACTIVATE_RAG" == 1 ]]; then
  printf 'y\n' | hermes mcp remove qdrant-rag >/dev/null 2>&1 || true
  printf 'y\n' | hermes mcp add qdrant-rag --command "$PYTHON" --args "$ROOT/rag_mcp.py"
  hermes mcp test qdrant-rag
else
  printf '%s\n' 'Disposable clone: active Hermes RAG configuration was not changed.'
fi
"$PYTHON" -m pytest "$ROOT/tests" -q
"$PYTHON" "$ROOT/ingest.py" --dry-run --json
printf '%s\n' 'READY: Open a new Hermes Desktop chat, then use /skill rag_update to index documents.'
