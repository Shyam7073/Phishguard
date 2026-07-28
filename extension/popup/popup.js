// Popup: shows the verdict for the current tab. Prefers the result the
// background service worker already cached for this tab (instant); falls
// back to scanning on-demand if nothing's cached yet (e.g. the page loaded
// before the extension did, or the background scan hasn't finished).

const API_BASE = "http://127.0.0.1:8000";

const statusEl = document.getElementById("status");
const detailsEl = document.getElementById("details");

function render(result) {
  if (result.error) {
    statusEl.textContent = "Scan failed";
    statusEl.className = "unknown";
    detailsEl.textContent = result.error;
    return;
  }

  if (result.is_phishing) {
    statusEl.textContent = "⚠ Likely phishing";
    statusEl.className = "danger";
  } else {
    statusEl.textContent = "✓ Looks safe";
    statusEl.className = "safe";
  }
  detailsEl.textContent = `Confidence: ${(result.confidence * 100).toFixed(1)}%`;
}

async function scanUrl(url) {
  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`);
  }
  return response.json();
}

async function main() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab || !tab.url || !/^https?:\/\//.test(tab.url)) {
    statusEl.textContent = "Not applicable to this page";
    statusEl.className = "unknown";
    return;
  }

  const key = `tab_${tab.id}`;
  const stored = await chrome.storage.local.get(key);
  const cached = stored[key];

  if (cached && cached.url === tab.url) {
    render(cached);
    return;
  }

  statusEl.textContent = "Scanning...";
  try {
    const result = await scanUrl(tab.url);
    render(result);
    await chrome.storage.local.set({ [key]: result });
  } catch (error) {
    render({
      url: tab.url,
      error: "Could not reach the PhishGuard backend. Is it running on localhost:8000?",
    });
  }
}

main();
