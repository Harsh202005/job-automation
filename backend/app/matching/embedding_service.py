"""
Embedding Service
=================
Provides sentence embeddings using the `all-MiniLM-L6-v2` model from
sentence-transformers. The model is loaded once (singleton) at the module
level on first use, not at import time, keeping startup fast.

Model stats:
  - Parameters : ~22 M
  - Embedding dim: 384
  - Avg encode time: ~5 ms per sentence on CPU
  - Disk size : ~90 MB (downloaded from HuggingFace Hub on first use)
"""
from __future__ import annotations

import logging
import math
import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

from pathlib import Path

_MODEL_NAME = "all-MiniLM-L6-v2"
_LOCAL_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "all-MiniLM-L6-v2"

# ── Singleton state ────────────────────────────────────────────────────────────
_model: "SentenceTransformer | None" = None
_model_lock = threading.Lock()


def _load_model() -> "SentenceTransformer":
    """
    Load (or return cached) the SentenceTransformer model.
    Checks local models directory first, then HuggingFace Hub identifier.
    Thread-safe double-checked locking — safe under both sync and async callers.
    """
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:  # second check after acquiring lock
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
    """
    Return a 384-dimensional embedding vector for *text*.

    Parameters
    ----------
    text : str
        Input text. Truncated to 512 word-pieces internally by the model.

    Returns
    -------
    list[float]
        Plain Python list of floats (JSON-serialisable).
    """
    if not text or not text.strip():
        # Return a zero vector for empty input so callers don't crash
        return [0.0] * 384

    model = _load_model()
    # encode() returns a numpy ndarray of shape (384,)
    vector: np.ndarray = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
    return vector.tolist()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two embedding vectors.

    Returns a float in [0, 1] (clamped from [-1, 1] since embeddings from
    MiniLM are non-negative in practice, but we clamp defensively).

    Parameters
    ----------
    vec_a, vec_b : list[float]
        Embedding vectors of equal length.

    Returns
    -------
    float
        Similarity score in [0.0, 1.0].
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        # One or both vectors are zero — undefined similarity, return 0
        return 0.0

    raw = float(np.dot(a, b) / (norm_a * norm_b))
    # Clamp to [0, 1] — cosine can be slightly outside due to float32 precision
    return max(0.0, min(1.0, raw))
