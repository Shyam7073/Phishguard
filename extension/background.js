// Background service worker (Manifest V3): scans a tab's URL every time
// navigation finishes, and caches the verdict in chrome.storage.local so
// the popup can show it instantly without re-scanning on every click.

importScripts("client-id.js");

const API_BASE = "https://phishguard-api-yjr8.onrender.com";
const TAB_KEY_PREFIX = "tab_";

function tabKey(tabId) {
  return `${TAB_KEY_PREFIX}${tabId}`;
}

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
    await chrome.storage.local.set({ [tabKey(tabId)]: result });
  } catch (error) {
    await chrome.storage.local.set({
      [tabKey(tabId)]: { url: tab.url, error: error.message },
    });
  }
});

// Cached verdicts are keyed by tab ID, so without this they accumulate for
// every tab ever opened and are never read again -- chrome.storage.local
// has a quota, and once it's hit every write above starts failing. Chrome
// also recycles tab IDs, so a leftover entry can belong to a tab that no
// longer exists (the popup's url check catches that, but only after it has
// already read the wrong record).
chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.local.remove(tabKey(tabId));
});

// Tab IDs don't survive a browser restart, so anything left from the last
// session is dead weight. Sweep it once on startup/install.
async function pruneStaleTabVerdicts() {
  const [stored, openTabs] = await Promise.all([
    chrome.storage.local.get(null),
    chrome.tabs.query({}),
  ]);
  const openKeys = new Set(openTabs.map((tab) => tabKey(tab.id)));
  const stale = Object.keys(stored).filter(
    (key) => key.startsWith(TAB_KEY_PREFIX) && !openKeys.has(key)
  );
  if (stale.length > 0) {
    await chrome.storage.local.remove(stale);
  }
}

chrome.runtime.onStartup.addListener(pruneStaleTabVerdicts);
chrome.runtime.onInstalled.addListener(pruneStaleTabVerdicts);
