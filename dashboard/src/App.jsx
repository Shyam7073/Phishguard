import { useEffect, useState, useCallback } from "react";
import { fetchHistory } from "./api";
import StatTiles from "./components/StatTiles";
import VerdictBarChart from "./components/VerdictBarChart";
import HistoryTable from "./components/HistoryTable";
import ExportButton from "./components/ExportButton";

function App() {
  const [records, setRecords] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const loadHistory = useCallback(() => {
    setStatus("loading");
    fetchHistory(100)
      .then((data) => {
        setRecords(data);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message);
        setStatus("error");
      });
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const total = records.length;
  const phishingCount = records.filter((r) => r.is_phishing).length;
  const legitCount = total - phishingCount;

  return (
    <div className="min-h-screen bg-[#f9f9f7] dark:bg-[#0d0d0d]">
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <header className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-[#0b0b0b] dark:text-white">
              PhishGuard Dashboard
            </h1>
            <p className="text-sm text-[#52514e] dark:text-[#c3c2b7]">
              Scan history and stats from the Chrome extension
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadHistory}
              className="rounded-md border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] px-3 py-1.5 text-sm font-medium text-[#0b0b0b] dark:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              Refresh
            </button>
            <ExportButton />
          </div>
        </header>

        {status === "error" && (
          <div className="rounded-lg border border-[#d03b3b]/30 bg-[#d03b3b]/10 px-4 py-3 text-sm text-[#d03b3b]">
            Couldn't reach the PhishGuard backend at http://127.0.0.1:8000 — is
            it running? ({error})
          </div>
        )}

        {status !== "error" && (
          <>
            <StatTiles total={total} phishingCount={phishingCount} legitCount={legitCount} />
            <VerdictBarChart total={total} phishingCount={phishingCount} legitCount={legitCount} />
            <HistoryTable records={records} />
          </>
        )}
      </div>
    </div>
  );
}

export default App;
