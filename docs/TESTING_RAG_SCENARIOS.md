# Testing and Understanding RAG Validity

When building a Retrieval-Augmented Generation (RAG) system, one of the most important concepts to understand is **Grounding**. 

Grounding means forcing the AI to base its answer **strictly on the documents you provided**, rather than relying on its pre-trained knowledge from the internet.

## Will the AI get data from outside sources?

**It shouldn't.** In our system, we intentionally designed it to *refuse* to use outside knowledge. 

If you look at `app/services/llm_service.py`, you will see this strict System Prompt:
```text
You are a helpful and precise assistant. 
Your task is to answer the user's question based ONLY on the provided context. 

Guidelines:
- If the answer is not contained in the context, say "I don't have enough information to answer that based on the provided documents."
- Do not use outside knowledge.
```
Additionally, we set `temperature=0.0`. Temperature controls creativity. A high temperature (0.8) makes the AI creative (good for writing poems). A low temperature (0.0) makes it rigid, deterministic, and highly literal (perfect for enterprise document search).

Because of these two settings, if the answer is not in your PDF, the AI *should* reply: "I don't have enough information..." 

---

## The 4 Scenarios You Must Test

To truly validate that our RAG system is working, you need to test it against these four specific scenarios. 

### Scenario 1: The "Direct Hit" (In-Context)
**What to test:** Ask a question where the answer is explicitly stated in the document you uploaded.
* **Example:** (If you uploaded an HR policy) "How many days of paid time off do I get in my first year?"
* **Expected Result:** The AI answers correctly, and the `sources` array in the JSON response points directly to the chunk containing that rule.
* **Why test this?** Verifies the "happy path". It proves your embeddings, your database search, and your LLM integration are all working.

### Scenario 2: The "Missing Information" (Out-of-Context)
**What to test:** Ask a question related to your document, but whose answer is *not actually in the text*. 
* **Example:** (If you uploaded a company laptop policy) "What brand of monitor will the company provide for my home office?" (Assuming the policy only talks about laptops, not monitors).
* **Expected Result:** The AI should say "I don't have enough information to answer that." 
* **Why test this?** This tests **Hallucination Prevention**. The database will still return the 5 *closest* chunks about laptops, but the LLM must be smart enough to read them and realize, "This doesn't mention monitors," and refuse to answer. If it guesses "Dell", your RAG system has failed.

### Scenario 3: The "General Knowledge Trap"
**What to test:** Ask a widely known fact that is NOT in your document.
* **Example:** "What is the capital of France?" or "Who won the World Cup in 2022?"
* **Expected Result:** The AI should say "I don't have enough information based on the provided documents."
* **Why test this?** This proves that the AI is fully **grounded**. Even though Gemini 2.0 Flash absolutely knows the capital of France, it must obey your system prompt and refuse to answer because the fact isn't in the provided chunks.

### Scenario 4: The "Needle in a Haystack" (Complex Retrieval)
**What to test:** Upload 3 or 4 entirely different documents (e.g., an HR policy, a technical architecture diagram, a budget spreadsheet). Then ask a highly specific question about just one minor detail in one of the documents.
* **Example:** "According to the Q3 budget, how much was spent on AWS?"
* **Expected Result:** The database vector search successfully filters through all the irrelevant HR and architecture chunks, finds the exact budget chunk, and Gemini answers correctly.
* **Why test this?** This tests the quality of your **Embeddings and pgvector**. It proves that the mathematical similarity search actually works across varied data.

---

## Summary of Validity
A RAG answer is considered "valid" if and only if:
1. It accurately answers the user's prompt.
2. Every fact in the answer can be traced back to a specific `chunk_id` in the `sources` array.
3. It politely refuses to answer anything outside of the provided context.
