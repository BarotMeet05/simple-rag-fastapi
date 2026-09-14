# app/services/embedding_service.py
"""
Embedding Service
=================
Integrates with the Google Gemini API to generate vector embeddings for text chunks.

Vectors are arrays of floating point numbers that represent the semantic meaning
of text. Gemini's `text-embedding-004` model outputs 768-dimensional vectors.
We store these in PostgreSQL using `pgvector`.
"""

from typing import List

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.default_model = settings.embedding_model
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Embedding service will fail if called.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    async def get_embeddings(
        self,
        texts: List[str],
        model: str | None = None,
        task_type: str = "RETRIEVAL_DOCUMENT",
        dimensionality: int = 768,
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of strings using Gemini API.
        
        Args:
            texts: List of strings to embed.
            model: The Gemini embedding model to use (defaults to settings.embedding_model).
            task_type: Embedding task type (e.g. RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY).
            dimensionality: Vector dimension size (defaults to 768).
            
        Returns:
            List of embedding vectors (each vector is a list of floats).
        """
        if not self.client:
            raise ValueError("GEMINI_API_KEY is missing. Cannot generate embeddings.")
            
        if not texts:
            return []

        use_model = model or self.default_model

        try:
            logger.debug(f"Calling Gemini API to embed {len(texts)} chunks using model {use_model}")
            # Offload synchronous Gemini SDK call to a worker thread so it doesn't block the event loop
            import asyncio
            response = await asyncio.to_thread(
                self.client.models.embed_content,
                model=use_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=dimensionality,
                ),
            )
            
            # response.embeddings is a list of Embedding objects, each has a .values property
            embeddings = [emb.values for emb in response.embeddings]
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
