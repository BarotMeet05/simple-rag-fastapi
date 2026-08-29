"""
Phase 1 Smoke Test Script
==========================
Run this while the server is running (uvicorn app.main:app --port 8001) to
manually verify all endpoints work correctly from the command line.

Usage:
    python scripts/smoke_test.py
"""

import httpx

BASE = "http://localhost:8001"
API = f"{BASE}/api/v1"


def check(label: str, response: httpx.Response, expected_status: int) -> dict:
    status = "PASS" if response.status_code == expected_status else "FAIL"
    print(f"\n{status} {label}")
    print(f"   Status: {response.status_code} (expected {expected_status})")
    try:
        body = response.json()
        print(f"   Body:   {body}")
    except Exception:
        print(f"   Body:   (empty)")
    return response.json() if response.status_code < 400 else {}


def main() -> None:
    print("=" * 60)
    print("Phase 1 Smoke Test")
    print("=" * 60)

    # 1. Health check
    r = httpx.get(f"{BASE}/health")
    check("GET /health", r, 200)

    # 2. Create a valid document
    r = httpx.post(f"{API}/documents", json={"filename": "policy.pdf", "file_type": "pdf"})
    doc = check("POST /documents (valid)", r, 201)
    doc_id = doc.get("document_id")

    # 3. Create a second document
    r = httpx.post(f"{API}/documents", json={"filename": "handbook.txt", "file_type": "txt"})
    check("POST /documents (second)", r, 201)

    # 4. Duplicate detection
    r = httpx.post(f"{API}/documents", json={"filename": "policy.pdf", "file_type": "pdf"})
    check("POST /documents (duplicate -> 409)", r, 409)

    # 5. Invalid file type
    r = httpx.post(f"{API}/documents", json={"filename": "virus.exe", "file_type": "exe"})
    check("POST /documents (bad file_type -> 422)", r, 422)

    # 6. Extension mismatch
    r = httpx.post(f"{API}/documents", json={"filename": "policy.txt", "file_type": "pdf"})
    check("POST /documents (extension mismatch -> 422)", r, 422)

    # 7. List documents
    r = httpx.get(f"{API}/documents")
    check("GET /documents", r, 200)

    # 8. Get by ID
    if doc_id:
        r = httpx.get(f"{API}/documents/{doc_id}")
        check(f"GET /documents/{doc_id[:8]}...", r, 200)

    # 9. Get non-existent
    r = httpx.get(f"{API}/documents/00000000-0000-0000-0000-000000000000")
    check("GET /documents/non-existent -> 404", r, 404)

    # 10. Search stub
    r = httpx.post(f"{API}/search", json={"query": "What is the coverage limit?"})
    check("POST /search (stub -> 200 empty)", r, 200)

    # 11. Chat stub
    r = httpx.post(f"{API}/chat", json={"question": "What is the deductible?"})
    check("POST /chat (stub -> 200)", r, 200)

    # 12. Delete
    if doc_id:
        r = httpx.delete(f"{API}/documents/{doc_id}")
        check(f"DELETE /documents/{doc_id[:8]}...", r, 204)

    # 13. Double delete
    if doc_id:
        r = httpx.delete(f"{API}/documents/{doc_id}")
        check("DELETE /documents (already deleted -> 404)", r, 404)

    print("\n" + "=" * 60)
    print("Smoke test complete. Open http://localhost:8001/docs for Swagger UI.")
    print("=" * 60)


if __name__ == "__main__":
    main()
