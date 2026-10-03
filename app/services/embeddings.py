import asyncio
from typing import List, Optional
import logging
import torch
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDINGS_MODEL
        # Auto-detect CUDA availability
        self._device = device or ("cuda" if (torch.cuda.is_available() and getattr(settings, "USE_CUDA", True)) else "cpu")
        self._model = None
        self._load_model()

    def _load_model(self):
        if self._model is not None:
            return
        try:
            logger.info("Loading embedding model '%s' on device '%s'...", self.model_name, self._device)
            self._model = SentenceTransformer(self.model_name, device=self._device)
            logger.info("Embedding model loaded.")
        except Exception as e:
            logger.exception("Failed to load embedding model: %s", e)
            raise

    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model

    # Sync helper
    def encode(self, text: str, normalize: bool = True) -> List[float]:
        emb = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=normalize)
        return emb.tolist()

    # Async wrapper (Renamed to match vector_manager.py)
    async def embed_text_async(self, text: str) -> List[float]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.encode(text))

# ---------------------------------------------------------
# INSTANCE EXPORT
# ---------------------------------------------------------
embedding_service = EmbeddingService()