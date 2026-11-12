import hashlib
import math
import re
import threading
from functools import lru_cache

from app.config import get_settings
from app.models.academic import EMBEDDING_DIM


class EmbeddingError(Exception):
    """Message is safe to show to the user."""


_STOP = set("a an the of and or to in on for with is are was were be by as at it this that from which "
            "what how why when who do does explain define describe".split())
_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    """Deterministic bag-of-words embedder (feature hashing). No downloads, keyword-level similarity only.
    Useful for tests and quick demos; use the local sentence-transformers model for real semantic search."""

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * EMBEDDING_DIM
        tokens = [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]
        grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for g in grams:
            if g.endswith("s") and len(g) > 3 and "_" not in g:
                g = g[:-1]
            h = int.from_bytes(hashlib.md5(g.encode()).digest()[:8], "big")
            v[h % EMBEDDING_DIM] += 1.0 if (h >> 40) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class LocalEmbedder:
    """sentence-transformers model, loaded lazily on first use (first run downloads ~90 MB)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer(self.model_name)
                except ImportError as exc:
                    raise EmbeddingError("The embedding model library is not installed on the server.") from exc
                except Exception as exc:
                    raise EmbeddingError("The embedding model could not be loaded.") from exc
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            vecs = self._load().encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError("Embedding generation failed.") from exc
        return [list(map(float, v)) for v in vecs]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache
def get_embedder():
    s = get_settings()
    if s.embedding_provider == "hashing":
        return HashingEmbedder()
    if s.embedding_provider == "local":
        return LocalEmbedder(s.embedding_model)
    raise EmbeddingError(f"Unknown embedding provider '{s.embedding_provider}'.")


def check_dimension(vectors: list[list[float]]) -> None:
    if vectors and len(vectors[0]) != EMBEDDING_DIM:
        raise EmbeddingError(
            f"The embedding model produces {len(vectors[0])}-dimensional vectors but the database expects {EMBEDDING_DIM}."
        )
