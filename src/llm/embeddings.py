"""
Embedding generator — thin Python wrapper for producing vector embeddings.

Supports multiple backends:
  1. Local: simple hash-based embeddings (zero dependencies, offline-first)
  2. Sentence-Transformers: real neural embeddings (optional dependency)
  3. OpenAI: API-based embeddings (optional, requires API key)

The default is local hash-based — works offline, no GPU, no downloads.
When a real model is available, it auto-upgrades.
"""

import hashlib
import math
import os
from typing import List, Optional

DEFAULT_DIM = 64


class EmbeddingEngine:
    """Produces vector embeddings from text strings."""

    def __init__(self, dim: int = DEFAULT_DIM, backend: Optional[str] = None):
        self.dim = dim
        self._backend_name = backend or os.environ.get("MCP_EMBED_BACKEND", "local")
        self._model = None
        self._init_backend()

    def _init_backend(self):
        """Try to initialize the requested backend, fall back to local."""
        if self._backend_name == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer
                model_name = os.environ.get(
                    "MCP_EMBED_MODEL", "all-MiniLM-L6-v2"
                )
                self._model = SentenceTransformer(model_name)
                self.dim = self._model.get_sentence_embedding_dimension()
                return
            except ImportError:
                pass
            self._backend_name = "local"

        if self._backend_name == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self._model = api_key
                self.dim = 1536  # text-embedding-ada-002
                return
            self._backend_name = "local"

        # Default: local hash-based
        self._backend_name = "local"

    def embed(self, text: str) -> List[float]:
        """Generate an embedding vector for a text string."""
        if self._backend_name == "sentence-transformers" and self._model is not None:
            return self._embed_st(text)
        if self._backend_name == "openai" and self._model is not None:
            return self._embed_openai(text)
        return self._embed_local(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if self._backend_name == "sentence-transformers" and self._model is not None:
            return self._embed_st_batch(texts)
        return [self.embed(t) for t in texts]

    @property
    def backend(self) -> str:
        """Return the active backend name."""
        return self._backend_name

    # --- Local hash-based embeddings (deterministic, zero-dep) ---

    def _embed_local(self, text: str) -> List[float]:
        """Deterministic hash-based embedding. Not semantic, but consistent."""
        # Use multiple hash rounds to fill the vector
        vec = [0.0] * self.dim
        text_lower = text.lower().strip()

        # Character n-gram hashing for basic distributional signal
        ngrams = []
        for n in (2, 3, 4):
            for i in range(len(text_lower) - n + 1):
                ngrams.append(text_lower[i:i + n])

        # Word-level hashing
        words = text_lower.split()
        ngrams.extend(words)

        for gram in ngrams:
            h = hashlib.sha256(gram.encode("utf-8")).digest()
            for i in range(min(self.dim, len(h))):
                # Map byte to [-1, 1] range
                val = (h[i] / 255.0) * 2.0 - 1.0
                vec[i % self.dim] += val

        # Normalize to unit vector
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-10:
            vec = [v / norm for v in vec]

        return vec

    # --- Sentence-Transformers backend ---

    def _embed_st(self, text: str) -> List[float]:
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embed_st_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]

    # --- OpenAI backend ---

    def _embed_openai(self, text: str) -> List[float]:
        import urllib.request
        import json

        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=json.dumps({
                "input": text,
                "model": "text-embedding-ada-002",
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._model}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        return result["data"][0]["embedding"]
