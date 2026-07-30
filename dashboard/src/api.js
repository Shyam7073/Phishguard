export const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchHistory(limit = 100) {
  const response = await fetch(`${API_BASE_URL}/history?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to load history (${response.status})`);
  }
  return response.json();
}

export const reportsUrl = `${API_BASE_URL}/reports`;
