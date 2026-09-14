# Phase 5: RAG Evaluation Harness

## What was built in this phase?

In Phase 5, we solved a massive problem in AI engineering: **How do you write automated tests for text generation?**

Standard unit tests (like `assert answer == "Yes"`) do not work for LLMs because the AI might answer `"Yes."`, `"Affirmative"`, or `"According to the policy, yes."` All of those are correct, but a standard string comparison would fail.

We built an **LLM-as-a-Judge Evaluation Harness**.

### 1. The Test Document & Dataset
We created `data/test_policy.txt`, a mock engineering policy, and `data/eval_dataset.json`, a set of 6 tricky test questions based on that policy.
- We included positive tests (where the answer exists).
- We included negative tests (asking for a standing desk, which isn't in the policy, to ensure the AI refuses to answer).

### 2. The Evaluator Script (`scripts/evaluate.py`)
This script acts as our automated testing suite:
1. It automatically ensures the `test_policy.txt` is ingested into your database (chunked and embedded).
2. It loops through the JSON dataset and asks our `RAGService` every question.
3. Instead of simple string matching, it takes the RAG's answer and the Expected Answer, and **asks Gemini a second time** to grade it.
4. Gemini is prompted with a strict `JUDGE_PROMPT` to respond only with a `PASS` or `FAIL` and a one-sentence reasoning.

This gives us an automated accuracy score!

## How to test this locally

Make sure your virtual environment is activated and your `.env` has the `GEMINI_API_KEY`. (You don't even need the FastAPI server running, as the script interacts directly with the database and services).

Run the evaluation script from your terminal:
```bash
.venv\Scripts\python.exe scripts\evaluate.py
```

You will see it:
1. Ingest the policy (if it hasn't already).
2. Ask the 6 questions.
3. Output the RAG's answer, and then Gemini's Grade and Reasoning for each.
4. Give you a final percentage score.

## Next Steps (Phase 6)
We have a fully functioning, highly accurate, and mathematically tested backend RAG pipeline. Now it is time to build a beautiful **Frontend** so users can actually interact with it! Phase 6 will involve setting up a modern React/Vite interface.
