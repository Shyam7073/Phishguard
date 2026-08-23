export const API_BASE_URL = "http://127.0.0.1:8000";

const CLIENT_ID_STORAGE_KEY = "phishguard_client_id";

// The dashboard has no login -- it trusts a client_id, either passed in the
// URL (the extension popup's "View my dashboard" link) or previously saved
// from an earlier visit. Without one there's no history to scope to.
export function getClientId() {
  const fromUrl = new URLSearchParams(window.location.search).get("client_id");
  if (fromUrl) {
    localStorage.setItem(CLIENT_ID_STORAGE_KEY, fromUrl);
    return fromUrl;
  }
  return localStorage.getItem(CLIENT_ID_STORAGE_KEY);
}

export async function fetchHistory(clientId, limit = 100) {
  const response = await fetch(
    `${API_BASE_URL}/history?client_id=${encodeURIComponent(clientId)}&limit=${limit}`
  );
  if (!response.ok) {
    throw new Error(`Failed to load history (${response.status})`);
  }
  return response.json();
}

export function reportsUrl(clientId) {
  return `${API_BASE_URL}/reports?client_id=${encodeURIComponent(clientId)}`;
}
