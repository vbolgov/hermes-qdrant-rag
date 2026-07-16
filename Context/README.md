# Index state

`rag-index-manifest.csv` is created and updated atomically by `ingest.py`.

It records the relative source path, SHA-256, modification timestamp, size, index time, and number of chunks for each indexed document. It is runtime state and is intentionally excluded from Git.
