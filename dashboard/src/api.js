export const API_BASE_URL = "https://phishguard-api-yjr8.onrender.com";

const CLIENT_ID_STORAGE_KEY = "phishguard_client_id";

// Reserved id whose history is seeded by backend/scripts/seed_demo.py.
export const DEMO_CLIENT_ID = "demo";

// The dashboard has no login -- it trusts a client_id, either passed in the
// URL (the extension popup's "View my dashboard" link) or previously saved
// from an earlier visit. Someone opening the deployed link without the
// extension installed has neither, so they fall through to the seeded demo
// history rather than an empty page.
export function resolveClient() {
  const fromUrl = new URLSearchParams(window.location.search).get("client_id");
  if (fromUrl) {
    localStorage.setItem(CLIENT_ID_STORAGE_KEY, fromUrl);
    return { clientId: fromUrl, isDemo: fromUrl === DEMO_CLIENT_ID };
  }
  const stored = localStorage.getItem(CLIENT_ID_STORAGE_KEY);
  if (stored) {
    return { clientId: stored, isDemo: stored === DEMO_CLIENT_ID };
  }
  return { clientId: DEMO_CLIENT_ID, isDemo: true };
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
