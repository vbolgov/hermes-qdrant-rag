from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9_]{2,}")
DEFAULT_DIMS = 1024


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def embed_text(text: str, dims: int = DEFAULT_DIMS) -> list[float]:
    counts = Counter(tokenize(text))
    vec = [0.0] * dims
    for token, count in counts.items():
        token_digest = hashlib.sha1(token.encode("utf-8")).digest()
        idx = int.from_bytes(token_digest[:8], "big") % dims
        sign = 1.0 if (token_digest[8] & 1) == 0 else -1.0
        vec[idx] += sign * float(count)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec
