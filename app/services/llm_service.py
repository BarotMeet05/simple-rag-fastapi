# app/services/llm_service.py
"""
LLM Service
===========
Handles interaction with Google Gemini API for text generation.

This service is specifically tuned for RAG (Retrieval-Augmented Generation).
It takes a user's question and a list of relevant text chunks, constructs a
prompt that explicitly instructs the LLM to only use the provided context,
and returns the generated answer.
"""

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# A strict system prompt is critical for RAG to prevent hallucinations.
RAG_SYSTEM_PROMPT = """You are a helpful and precise assistant. 
Your task is to answer the user's question based ONLY on the provided context. 

Guidelines:
- If the answer is not contained in the context, say "I don't have enough information to answer that based on the provided documents."
- Do not use outside knowledge.
- Be concise and direct.
- Cite the source filename and page number when providing facts.
"""

class LLMService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. LLM service will fail if called.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)
            
    async def generate_answer(
        self, 
        question: str, 
        context_chunks: list[dict], 
        model: str = "gemini-3.6-flash"
    ) -> str:
        """
        Generate an answer to a question using the provided context chunks.
        
        Args:
            question: The user's query.
            context_chunks: A list of dicts containing 'text', 'filename', and 'page_number'.
            model: The Gemini model to use.
            
        Returns:
            The generated answer string.
        """
        if not self.client:
            raise ValueError("GEMINI_API_KEY is missing. Cannot generate answer.")
            
        # 1. Format the context
        context_text = ""
        for i, chunk in enumerate(context_chunks):
            context_text += f"\n--- Source [{i+1}]: {chunk['filename']} (Page {chunk['page_number']}) ---\n"
            context_text += f"{chunk['text']}\n"
            
        # 2. Construct the prompt
        user_prompt = f"Context Information:\n{context_text}\n\nUser Question: {question}\n\nAnswer:"
        
        try:
            logger.debug(f"Calling Gemini API to answer question: '{question}'")
            import asyncio
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=RAG_SYSTEM_PROMPT,
                    temperature=0.0, # 0.0 forces the model to be deterministic and grounded
                ),
            )
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise
