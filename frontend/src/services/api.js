// frontend/src/services/api.js
/**
 * API Service — communicates with the FastAPI backend.
 * Handles all error formatting so users never see raw stack traces.
 */

const rawBase = import.meta.env.VITE_API_URL || '';
const API_BASE = rawBase.replace(/\/+$/, '');

// Map ugly backend errors to friendly messages
function friendlyError(raw) {
  const lower = (raw || '').toLowerCase();
  if (lower.includes('429') || lower.includes('rate') || lower.includes('quota'))
    return 'The AI service is temporarily busy. Please wait a minute and try again.';
  if (lower.includes('409') || lower.includes('already exists') || lower.includes('duplicate'))
    return 'This file has already been uploaded.';
  if (lower.includes('gemini') || lower.includes('api_key') || lower.includes('missing'))
    return 'AI service is not configured. Please check the API key.';
  if (lower.includes('econnrefused') || lower.includes('failed to fetch') || lower.includes('networkerror'))
    return 'Cannot reach the server. Please check your backend connection or VITE_API_URL.';
  if (raw.length > 120) return 'Something went wrong. Please try again.';
  return raw;
}

async function handleResponse(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const raw = body?.error?.message || body?.detail || `Request failed (${response.status})`;
    throw new Error(friendlyError(raw));
  }
  return response.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await fetch(`${API_BASE}/api/v1/documents`, {
      method: 'POST',
      body: formData,
    });
    return await handleResponse(response);
  } catch (err) {
    throw new Error(friendlyError(err.message));
  }
}

export async function fetchDocuments() {
  try {
    const response = await fetch(`${API_BASE}/api/v1/documents`);
    return await handleResponse(response);
  } catch (err) {
    throw new Error(friendlyError(err.message));
  }
}

export async function sendChatMessage(question, topK = 5) {
  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });
  return handleResponse(response);
}
