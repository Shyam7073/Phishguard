# extension/

Chrome extension (Manifest V3).

- `manifest.json` — extension manifest. `permissions: ["storage", "tabs"]`
  (reads the URL you navigate to; no content script, no page access).
  `host_permissions` scoped to `localhost:8000`/`127.0.0.1:8000` (the
  backend) — that's what lets `fetch` calls from the extension bypass CORS
  for that origin specifically.
- `background.js` — service worker; on every completed navigation to an
  `http(s)` URL, calls `POST /scan` and caches the verdict in
  `chrome.storage.local`, keyed by tab ID.
- `popup/` — popup UI shown when you click the extension icon. Reads the
  cached verdict for the current tab if available (instant); otherwise
  scans on demand and shows "Scanning...". Shows a clear error if the
  backend isn't reachable rather than failing silently.

## Running it

1. Start the backend first (see `backend/README.md`) — the extension has
   nothing to talk to otherwise.
2. Open `chrome://extensions`, enable **Developer mode** (top right),
   click **Load unpacked**, and select this `extension/` folder.
3. Visit any `http(s)` page, then click the PhishGuard icon in the
   toolbar to see the verdict.

No build step — plain HTML/CSS/JS, loaded directly by Chrome. No custom
icon is set (Chrome falls back to a generic one); fine for local
development, worth adding one later for a polished demo/screenshot.

Populated in Milestone 7.
