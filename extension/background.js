// Background service worker (Manifest V3): scans a tab's URL every time
// navigation finishes, and caches the verdict in chrome.storage.local so
// the popup can show it instantly without re-scanning on every click.

importScripts("client-id.js");

const API_BASE = "https://phishguard-api-yjr8.onrender.com";

function isScannable(url) {
  return Boolean(url) && (url.startsWith("http://") || url.startsWith("https://"));
}

async function scanUrl(url) {
  const clientId = await getOrCreateClientId();
  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, client_id: clientId }),
  });
  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`);
  }
  return response.json();
}

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete" || !isScannable(tab.url)) {
    return;
  }

  try {
    const result = await scanUrl(tab.url);
    await chrome.storage.local.set({ [`tab_${tabId}`]: result });
  } catch (error) {
    await chrome.storage.local.set({
      [`tab_${tabId}`]: { url: tab.url, error: error.message },
    });
  }
});
