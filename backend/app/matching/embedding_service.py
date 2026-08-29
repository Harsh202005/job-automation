"""
Embedding Service
=================
Provides high-performance sentence embeddings using the `all-MiniLM-L6-v2` model from
sentence-transformers. Features batch vectorization and singleton model caching.

Model stats:
  - Parameters : ~22 M
  - Embedding dim: 384
  - Avg encode time: ~2 ms per sentence in batch mode on CPU
  - Disk size : ~90 MB (downloaded from HuggingFace Hub on first use)
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_LOCAL_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "all-MiniLM-L6-v2"

# ── Singleton state ────────────────────────────────────────────────────────────
_model: "SentenceTransformer | None" = None
_model_lock = threading.Lock()


def _load_model() -> "SentenceTransformer":
    """
    Load (or return cached) the SentenceTransformer model.
    Checks local models directory first, then HuggingFace Hub identifier.
    Thread-safe double-checked locking.
    """
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        model_target = str(_LOCAL_MODEL_PATH) if (_LOCAL_MODEL_PATH / "model.safetensors").exists() else _MODEL_NAME
        logger.info("Loading sentence-transformers model from '%s'...", model_target)
        _model = SentenceTransformer(model_target)
        logger.info("Model '%s' loaded and cached.", model_target)
        return _model


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """Return a 384-dimensional normalized embedding vector for text."""
    if not text or not text.strip():
        return [0.0] * 384

    model = _load_model()
    vector: np.ndarray = model.encode(
        text,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vector.tolist()


def get_embeddings_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Batch vectorization for multiple texts.
    Orders of magnitude faster than individual encode calls on CPU.
    """
    if not texts:
        return []

    clean_texts = [t if (t and t.strip()) else " " for t in texts]
    model = _load_model()
    vectors: np.ndarray = model.encode(
        clean_texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    raw = float(np.dot(a, b) / (norm_a * norm_b))
    return max(0.0, min(1.0, raw))
