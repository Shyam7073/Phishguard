# dashboard/

React + Tailwind dashboard for reviewing scan history and exporting reports.
Talks to the same FastAPI backend as the extension (`/history`, `/reports`).
Deployed on Vercel at `https://phishguard-gray.vercel.app` (scoped to this
subfolder as Vercel's project root — see root `README.md` → Deployment).

- `src/api.js` — `API_BASE_URL` (points at the deployed Render backend by
  default), `resolveClientId()` (reads `client_id` from the URL query string
  — the extension popup's "View my dashboard" link — then from a previously
  saved value in `localStorage`, and returns `null` if neither exists),
  `fetchHistory()`/`reportsUrl()` (both scoped by `client_id`), `scanUrl()`
  (the manual check), `persistClientId()`
- `src/App.jsx` — with no `client_id` there is nothing to fetch, so it skips
  the request and renders an empty history alongside the URL checker rather
  than showing a spinner, an error, or (worse) another client's data. The
  first manual check mints a `client_id` and saves it, after which the
  visitor accumulates their own history exactly as an extension user does.
- `src/components/` — `UrlChecker` (paste a URL, get a verdict without
  visiting it — `/scan` reads the URL string only), `HistoryTable`,
  `VerdictBarChart`, `StatTiles`, `ExportButton` (all `client_id`-aware
  where they call the backend; Export is disabled until there are rows)

No login system — `client_id` is identification, not authentication. This
dashboard's own deployed URL also needed a `TRUSTED_HOSTS` entry on the
backend, since free-hosting subdomains structurally resemble phishing URLs
to the model.

Populated starting in Milestone 9. `client_id` scoping and deployed-URL
wiring added in Milestone 15.
