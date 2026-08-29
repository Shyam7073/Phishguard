import { reportsUrl } from "../api";

// Mirrors the column order of the backend's /reports CSV exactly, so the
// demo export and a real one open identically in a spreadsheet.
const COLUMNS = [
  "id",
  "client_id",
  "url",
  "is_phishing",
  "confidence",
  "ml_score",
  "urlhaus_status",
  "domain_age_days",
  "domain_age_status",
  "verdict_reason",
  "scanned_at",
];

function escapeCell(value) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(records, clientId) {
  const rows = records.map((record) =>
    COLUMNS.map((column) =>
      escapeCell(column === "client_id" ? clientId : record[column])
    ).join(",")
  );
  return [COLUMNS.join(","), ...rows].join("\n");
}

export default function ExportButton({ clientId, records = [], isDemo = false }) {
  const className =
    "inline-flex items-center gap-2 rounded-md bg-[#2a78d6] dark:bg-[#3987e5] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 transition-opacity";

  // The demo history is a fixed client-side fixture, so its export is built
  // in the browser from the same rows on screen -- otherwise this button
  // would hit /reports for a client_id the database has never heard of and
  // hand back an empty file.
  if (isDemo) {
    const handleExport = () => {
      const blob = new Blob([toCsv(records, clientId)], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "phishguard_report.csv";
      link.click();
      URL.revokeObjectURL(url);
    };

    return (
      <button type="button" onClick={handleExport} className={className}>
        Export CSV
      </button>
    );
  }

  return (
    <a href={reportsUrl(clientId)} download="phishguard_report.csv" className={className}>
      Export CSV
    </a>
  );
}
