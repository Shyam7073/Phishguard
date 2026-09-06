import { reportsUrl } from "../api";

const BASE_CLASS =
  "inline-flex items-center gap-2 rounded-md bg-[#2a78d6] dark:bg-[#3987e5] px-3 py-1.5 text-sm font-medium text-white transition-opacity";

export default function ExportButton({ clientId, records = [] }) {
  // A first-time visitor has no client_id until their first check, and an
  // id with no rows yields a header-only file. Either way the button stays
  // in place but inert, rather than downloading nothing or building a
  // /reports URL around a null id.
  if (!clientId || records.length === 0) {
    return (
      <button
        type="button"
        disabled
        title="Nothing to export yet — check a URL first"
        className={`${BASE_CLASS} opacity-50 cursor-not-allowed`}
      >
        Export CSV
      </button>
    );
  }

  return (
    <a
      href={reportsUrl(clientId)}
      download="phishguard_report.csv"
      className={`${BASE_CLASS} hover:opacity-90`}
    >
      Export CSV
    </a>
  );
}
