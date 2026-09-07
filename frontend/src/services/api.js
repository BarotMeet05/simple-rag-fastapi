// frontend/src/services/api.js
/**
 * API Service — communicates with the FastAPI backend.
 *
 * In dev, Vite's proxy forwards /api/* to localhost:8000.
 * In production, VITE_API_URL points to the Render backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

async function handleResponse(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    // Our backend returns { error: { message: "..." } }
    const message = body?.error?.message || body?.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return response.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/v1/documents`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse(response);
}

export async function fetchDocuments() {
  const response = await fetch(`${API_BASE}/api/v1/documents`);
  return handleResponse(response);
}

export async function sendChatMessage(question, topK = 5) {
  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  return handleResponse(response);
}
