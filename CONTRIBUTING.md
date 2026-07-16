# Contributing

Before a pull request run:

```text
.venv/bin/python -m pytest tests -q
git diff --check
```

Never add `.env`, personal library files, Qdrant data, manifests or credentials. Keep deployment behavior documented in `AGENTS.md` and covered by tests.
