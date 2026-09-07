import asyncio
from sqlalchemy import select
from app.db.database import get_session_factory
from app.db.models import DocumentModel, DocumentChunkModel

async def verify_chunks():
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 1. Get the most recently uploaded document
        result = await session.execute(
            select(DocumentModel).order_by(DocumentModel.uploaded_at.desc()).limit(1)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            print("No documents found in the database. Please upload one first!")
            return
            
        print(f"\n--- Checking Document: {doc.filename} (ID: {doc.document_id}) ---")
        print(f"Status: {doc.processing_status}")
        print(f"Total Chunks generated: {doc.chunk_count}")
        
        if doc.chunk_count == 0:
            print("No chunks were generated. Did you add your GEMINI_API_KEY to .env?")
            return
            
        # 2. Fetch the chunks for this document
        chunk_result = await session.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == doc.document_id)
            .order_by(DocumentChunkModel.chunk_index)
        )
        chunks = list(chunk_result.scalars().all())
        
        print("\n--- Chunk Details ---")
        for chunk in chunks[:3]:  # Print first 3 chunks to avoid massive terminal output
            print(f"\n[Chunk Index {chunk.chunk_index} | Page {chunk.page_number}]")
            print(f"Text Preview: {chunk.text_content[:150]}...")
            
            if chunk.embedding is not None:
                # The embedding is a list of floats. We just check its length.
                print(f"Vector Embedding Dimension: {len(chunk.embedding)} (Should be 768 for Gemini)")
                print(f"Vector Sample: {chunk.embedding[:3]} ...")
            else:
                print("Vector Embedding: None (Failed to embed)")
                
        if len(chunks) > 3:
            print(f"\n... and {len(chunks) - 3} more chunks.")

if __name__ == "__main__":
    asyncio.run(verify_chunks())
