import logging
import os
from pathlib import Path
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.config import DEFAULT_MODEL_DIR

logger = logging.getLogger("anyrag.embedder")

class LocalEmbedder:
    _instance = None

    def __init__(self, model_path: Union[str, Path] = DEFAULT_MODEL_DIR):
        self.model_path = Path(model_path)
        if self.model_path.exists() and (self.model_path / "model.safetensors").exists():
            logger.info(f"Loading local embedding model from: {self.model_path}")
            self.model = SentenceTransformer(str(self.model_path))
        else:
            logger.info(f"Model folder {self.model_path} not found. Fallback to all-MiniLM-L6-v2 identifier.")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")

        if hasattr(self.model, "get_embedding_dimension"):
            self.dimension = self.model.get_embedding_dimension()
        elif hasattr(self.model, "get_sentence_embedding_dimension"):
            self.dimension = self.model.get_sentence_embedding_dimension()
        else:
            self.dimension = 384

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate normalized embeddings for a list of text strings."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate normalized embedding for a single search query."""
        vec = self.embed_texts([query])[0]
        return vec

# Singleton accessor for fast reuse across sessions
_cached_embedder = None

def get_embedder(model_path: Union[str, Path] = DEFAULT_MODEL_DIR) -> LocalEmbedder:
    global _cached_embedder
    if _cached_embedder is None:
        _cached_embedder = LocalEmbedder(model_path)
    return _cached_embedder
