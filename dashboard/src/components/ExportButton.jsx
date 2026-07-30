import { reportsUrl } from "../api";

export default function ExportButton() {
  return (
    <a
      href={reportsUrl}
      download="phishguard_report.csv"
      className="inline-flex items-center gap-2 rounded-md bg-[#2a78d6] dark:bg-[#3987e5] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 transition-opacity"
    >
      Export CSV
    </a>
  );
}
