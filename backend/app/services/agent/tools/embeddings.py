"""Text embeddings for semantic memory recall.

Groq does not provide an embeddings API, so this module always uses the
deterministic hash-derived pseudo-embedding fallback. The pgvector HNSW
index still works structurally; similarity scores won't be semantically
meaningful but the Historian's recall code path remains fully exercisable.

To get real semantic embeddings, swap in an OpenAI-compatible embeddings
endpoint and restore the ``_real_embedding`` call in ``embed_text``.
"""

from __future__ import annotations

import hashlib
import math
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover
    pass

LOGGER = get_logger(__name__)

EMBEDDING_DIM = 768


def embed_text(text: str) -> list[float]:
    """Embed ``text`` and return a unit-normalised 768-dim vector.

    Groq does not provide an embeddings API, so this always returns the
    deterministic pseudo-embedding. Empty strings are mapped to the zero
    vector.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM
    return _deterministic_pseudo_embedding(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two same-length vectors, in [-1, 1]."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------


def _real_embedding(text: str, api_key: str, model: str) -> list[float]:
    """Not used: Groq has no embeddings API.

    Kept as a stub so diffs stay minimal when restoring a real provider.
    """
    raise NotImplementedError("Groq does not provide an embeddings API")


def _deterministic_pseudo_embedding(text: str) -> list[float]:
    """Hash-derived stand-in used for offline tests.

    SHA-256 over the text yields 32 bytes; we expand by re-hashing
    blocks until we have ``EMBEDDING_DIM`` bytes, then map to floats in
    ``[-1, 1]`` and unit-normalise. Different texts produce distinct,
    repeatable vectors — enough to validate the recall code path
    without exercising the real model.
    """
    raw = b""
    seed = text.encode("utf-8")
    counter = 0
    while len(raw) < EMBEDDING_DIM:
        raw += hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
    raw = raw[:EMBEDDING_DIM]
    floats = [(b - 127.5) / 127.5 for b in raw]
    norm = math.sqrt(sum(x * x for x in floats)) or 1.0
    return [x / norm for x in floats]


__all__ = ["EMBEDDING_DIM", "cosine_similarity", "embed_text"]
