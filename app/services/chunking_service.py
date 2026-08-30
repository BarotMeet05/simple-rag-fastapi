# app/services/chunking_service.py
"""
Chunking Service
================
Splits extracted document text into smaller, overlapping chunks.

Why chunking?
-------------
LLMs have a context window limit. We cannot feed an entire 100-page PDF into
a prompt. Instead, we split the document into pieces, convert each piece to
a vector, and search for the most relevant pieces.

Chunking strategies:
--------------------
1. Fixed-size (character count) — Simple, fast, but can cut words/sentences in half.
2. Recursive Character (Langchain style) — Tries to split on paragraphs, then sentences, then words.
3. Semantic — Uses an LLM to split by topic change.

For Phase 3, we implement a simple Recursive Character strategy.
It tries to split by double newline, single newline, space, then falls back to character limits.
Overlap ensures context isn't lost if a concept spans a chunk boundary.
"""

import re
from dataclasses import dataclass
from typing import List

from app.services.parser_service import ParsedPage


@dataclass
class TextChunk:
    text: str
    page_number: int
    chunk_index: int


def chunk_document(
    pages: List[ParsedPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[TextChunk]:
    """
    Splits a list of parsed pages into overlapping chunks.
    
    This is a simplified RecursiveCharacterTextSplitter.
    It attempts to split the text on natural boundaries (paragraphs, then spaces)
    to keep chunks within the chunk_size limit.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    chunks: List[TextChunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text
        # Naive split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk_text = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If a single paragraph is too large, we would ideally split it by sentences.
            # For simplicity, we just forcefully chunk it by character length if it exceeds limit.
            
            # Can we fit this paragraph into the current chunk?
            if len(current_chunk_text) + len(para) + 2 <= chunk_size:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
            else:
                # If current_chunk_text has content, yield it
                if current_chunk_text:
                    chunks.append(
                        TextChunk(
                            text=current_chunk_text,
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1
                    
                    # Create overlap string from the end of the current chunk
                    # Roughly take the last `chunk_overlap` characters, trying to start at a word boundary
                    overlap_text = current_chunk_text[-chunk_overlap:] if chunk_overlap > 0 else ""
                    if overlap_text and " " in overlap_text:
                        # trim to first space to avoid partial words
                        overlap_text = overlap_text[overlap_text.find(" ") + 1:]
                    
                    current_chunk_text = overlap_text + "\n\n" + para if overlap_text else para
                    
                    # If even the new paragraph with overlap is too big, we just truncate it for now
                    # (A real implementation would recursively split here)
                    if len(current_chunk_text) > chunk_size:
                        # Hard split
                        while len(current_chunk_text) > chunk_size:
                            part = current_chunk_text[:chunk_size]
                            chunks.append(
                                TextChunk(
                                    text=part,
                                    page_number=page.page_number,
                                    chunk_index=chunk_index,
                                )
                            )
                            chunk_index += 1
                            
                            overlap_text = part[-chunk_overlap:] if chunk_overlap > 0 else ""
                            if overlap_text and " " in overlap_text:
                                overlap_text = overlap_text[overlap_text.find(" ") + 1:]
                                
                            current_chunk_text = overlap_text + current_chunk_text[chunk_size:]
                else:
                    # current_chunk_text is empty, meaning the paragraph itself is larger than chunk_size
                    current_chunk_text = para
                    while len(current_chunk_text) > chunk_size:
                        part = current_chunk_text[:chunk_size]
                        chunks.append(
                            TextChunk(
                                text=part,
                                page_number=page.page_number,
                                chunk_index=chunk_index,
                            )
                        )
                        chunk_index += 1
                        
                        overlap_text = part[-chunk_overlap:] if chunk_overlap > 0 else ""
                        if overlap_text and " " in overlap_text:
                            overlap_text = overlap_text[overlap_text.find(" ") + 1:]
                            
                        current_chunk_text = overlap_text + current_chunk_text[chunk_size:]

        # Yield the final piece for this page
        if current_chunk_text:
            chunks.append(
                TextChunk(
                    text=current_chunk_text,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks
