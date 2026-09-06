// `npm run dev` talks to a backend running locally (see backend/README.md),
// so local UI work never writes scans into the deployed Neon database;
// `npm run build` (what Vercel deploys) keeps pointing at the Render API.
// Set VITE_API_BASE_URL to override either -- e.g. to point the dev server
// at the deployed API on purpose.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "https://phishguard-api-yjr8.onrender.com");

const CLIENT_ID_STORAGE_KEY = "phishguard_client_id";

// The dashboard has no login -- it trusts a client_id, either passed in the
// URL (the extension popup's "View my dashboard" link) or previously saved
// from an earlier visit. Someone opening the deployed link without the
// extension has neither and gets null: an empty history plus the URL
// checker, which mints them an id on their first check.
export function resolveClientId() {
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

// Manual, paste-a-URL check from the dashboard -- same /scan endpoint the
// extension calls on every navigation, so a pasted URL never needs to be
// opened in a tab to get a verdict.
export async function scanUrl(url, clientId) {
  const response = await fetch(`${API_BASE_URL}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, client_id: clientId }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = typeof body?.detail === "string" ? body.detail : `Scan failed (${response.status})`;
    throw new Error(message);
  }
  return response.json();
}

// Persists a client_id the same way resolveClientId() reads one back, used
// when a first-time visitor's manual check mints one for them (still
// anonymous -- identification, not authentication).
export function persistClientId(clientId) {
  localStorage.setItem(CLIENT_ID_STORAGE_KEY, clientId);
}
