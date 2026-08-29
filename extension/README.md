# extension/

Chrome extension (Manifest V3).

- `manifest.json` — extension manifest. `permissions: ["storage", "tabs"]`
  (reads the URL you navigate to; no content script, no page access).
  `host_permissions` includes the deployed Render backend plus
  `localhost:8000`/`127.0.0.1:8000` for local dev — that's what lets
  `fetch` calls from the extension bypass CORS for those origins
  specifically.
- `client-id.js` — generates a random `client_id` (`crypto.randomUUID()`)
  on first run and persists it in `chrome.storage.local`; every install
  gets its own ID, sent with every scan so the backend can keep each
  friend's history separate. Shared into `background.js` via `importScripts()` and into `popup.html`
  via a `<script>` tag — not a login, just identification; reinstalling or
  clearing extension storage generates a new ID and orphans the old
  history.
- `background.js` — service worker; on every completed navigation to an
  `http(s)` URL, calls `POST /scan` (with `client_id`) and caches the
  verdict in `chrome.storage.local`, keyed by tab ID.
- `popup/` — popup UI shown when you click the extension icon. Reads the
  cached verdict for the current tab if available (instant); otherwise
  scans on demand and shows "Scanning...". Shows a clear error if the
  backend isn't reachable rather than failing silently. Also has a "View
  my dashboard" link that deep-links to the dashboard with `?client_id=...`
  so it can show that install's history without a login.

## Running it

1. Start the backend first (see `backend/README.md`) — the extension has
   nothing to talk to otherwise. `API_BASE`/`DASHBOARD_URL` in
   `background.js`/`popup.js` point at the deployed Render/Vercel URLs by
   default; switch them to `http://127.0.0.1:8000`/the local Vite dev
   server URL for local-only testing.
2. Open `chrome://extensions`, enable **Developer mode** (top right),
   click **Load unpacked**, and select this `extension/` folder.
3. Visit any `http(s)` page, then click the PhishGuard icon in the
   toolbar to see the verdict.

No build step — plain HTML/CSS/JS, loaded directly by Chrome. No custom
icon is set (Chrome falls back to a generic one); fine for local
development, worth adding one later for a polished demo/screenshot.

**Sharing with others**: not published to the Chrome Web Store. Zip just
this `extension/` folder (not the whole repo) and send it — each recipient
loads it unpacked the same way, and gets their own isolated `client_id`/
history against the same shared deployed backend.

Populated in Milestone 7. Multi-tenant `client_id` + deployed-URL wiring
added in Milestone 15.
