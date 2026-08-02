// Popup: shows the verdict for the current tab. Prefers the result the
// background service worker already cached for this tab (instant); falls
// back to scanning on-demand if nothing's cached yet (e.g. the page loaded
// before the extension did, or the background scan hasn't finished).

const API_BASE = "http://127.0.0.1:8000";

const statusEl = document.getElementById("status");
const reasonEl = document.getElementById("reason");
const confidenceEl = document.getElementById("confidence");
const blocklistEl = document.getElementById("blocklist");
const domainAgeEl = document.getElementById("domain-age");

const BLOCKLIST_LABELS = {
  listed: { text: "🚫 On URLhaus blocklist", className: "danger" },
  not_listed: { text: "✓ Not on any blocklist", className: "safe" },
  unknown: { text: "Blocklist check unavailable", className: "unknown" },
};

const DOMAIN_AGE_LABELS = {
  new: { className: "danger" },
  moderate: { className: "unknown" },
  established: { className: "safe" },
  unknown: { text: "Domain age unavailable", className: "unknown" },
};

function render(result) {
  if (result.error) {
    statusEl.textContent = "Scan failed";
    statusEl.className = "unknown";
    reasonEl.textContent = result.error;
    confidenceEl.textContent = "";
    blocklistEl.textContent = "";
    blocklistEl.className = "badge";
    domainAgeEl.textContent = "";
    domainAgeEl.className = "badge";
    return;
  }

  if (result.is_phishing) {
    statusEl.textContent = "⚠ Likely phishing";
    statusEl.className = "danger";
  } else {
    statusEl.textContent = "✓ Looks safe";
    statusEl.className = "safe";
  }

  // Fall back gracefully for verdicts cached before these fields existed.
  reasonEl.textContent =
    result.verdict_reason || (result.is_phishing ? "Flagged by ML model" : "Looks safe");
  confidenceEl.textContent = `Confidence: ${(result.confidence * 100).toFixed(1)}%`;

  const blocklist = BLOCKLIST_LABELS[result.urlhaus_status] || BLOCKLIST_LABELS.unknown;
  blocklistEl.textContent = blocklist.text;
  blocklistEl.className = `badge ${blocklist.className}`;

  // Fall back gracefully for verdicts cached before domain age existed.
  const domainAge = DOMAIN_AGE_LABELS[result.domain_age_status] || DOMAIN_AGE_LABELS.unknown;
  domainAgeEl.textContent =
    domainAge.text ||
    (result.domain_age_days != null
      ? `Domain age: ${result.domain_age_days} days`
      : "Domain age unavailable");
  domainAgeEl.className = `badge ${domainAge.className}`;
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
