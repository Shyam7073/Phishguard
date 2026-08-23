# dashboard/

React + Tailwind dashboard for reviewing scan history and exporting reports.
Talks to the same FastAPI backend as the extension (`/history`, `/reports`).
Deployed on Vercel at `https://phishguard-gray.vercel.app` (scoped to this
subfolder as Vercel's project root — see root `README.md` → Deployment).

- `src/api.js` — `API_BASE_URL` (points at the deployed Render backend by
  default), `getClientId()` (reads `client_id` from the URL query string,
  the extension popup's "View my dashboard" link, or falls back to a
  previously saved value in `localStorage`), `fetchHistory()`/`reportsUrl()`
  (both scoped by `client_id`)
- `src/App.jsx` — shows an explicit "open this from the extension popup"
  message if no `client_id` is available, rather than showing nothing or
  (worse) another client's data
- `src/components/` — `HistoryTable`, `VerdictBarChart`, `StatTiles`,
  `ExportButton` (all `client_id`-aware where they call the backend)

No login system — `client_id` is identification, not authentication. See
`PROJECT_PROGRESS.md` Milestone 15 for the full rationale, including why
this dashboard's own deployed URL needed a `TRUSTED_HOSTS` entry on the
backend (free-hosting subdomains structurally resemble phishing URLs to the
model).

Populated starting in Milestone 9. `client_id` scoping and deployed-URL
wiring added in Milestone 15.
