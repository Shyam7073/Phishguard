import { useEffect, useState, useCallback } from "react";
import { API_BASE_URL, fetchHistory, persistClientId, resolveClient, scanUrl } from "./api";
import demoData from "./demoData.json";
import StatTiles from "./components/StatTiles";
import VerdictBarChart from "./components/VerdictBarChart";
import HistoryTable from "./components/HistoryTable";
import ExportButton from "./components/ExportButton";
import UrlChecker from "./components/UrlChecker";

function App() {
  const [client, setClient] = useState(resolveClient);
  const { clientId, isDemo } = client;
  // The demo history is a fixed, checked-in fixture (demoData.json) rather
  // than a live query: it renders on first paint with no backend involved,
  // which matters because the API sits on a free tier that spins down when
  // idle and a cold start takes far longer than anyone opening this link
  // will wait. If the demo id ever does get seeded server-side, those rows
  // replace the fixture when they arrive.
  const [records, setRecords] = useState(isDemo ? demoData : []);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const loadHistory = useCallback(() => {
    setStatus("loading");
    fetchHistory(clientId, 100)
      .then((data) => {
        // An empty demo response means the seed hasn't been run against
        // this database -- keep the snapshot rather than blanking the page.
        if (data.length > 0 || !isDemo) {
          setRecords(data);
        }
        setError(null);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message);
        // Only a real client_id gets the error state; the demo keeps
        // rendering its snapshot if the API is down or still waking up.
        setStatus(isDemo ? "ready" : "error");
      });
  }, [clientId, isDemo]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // A demo visitor has no client_id of their own ("demo" is reserved and
  // /scan refuses to write under it) -- their first manual check mints a
  // real one and graduates them out of demo mode, same as installing the
  // extension would. The scan itself only ever inspects the URL string, so
  // nothing here ever opens or fetches the pasted page.
  const handleCheckUrl = useCallback(
    async (url) => {
      const targetClientId = isDemo ? crypto.randomUUID() : clientId;
      const verdict = await scanUrl(url, targetClientId);
      if (isDemo) {
        persistClientId(targetClientId);
        setClient({ clientId: targetClientId, isDemo: false });
      }
      fetchHistory(targetClientId, 100)
        .then(setRecords)
        .catch(() => {}); // best-effort refresh -- the inline result already rendered
      return verdict;
    },
    [clientId, isDemo]
  );

  const total = records.length;
  const phishingCount = records.filter((r) => r.is_phishing).length;
  const legitCount = total - phishingCount;

  return (
    <div className="min-h-screen bg-[#f9f9f7] dark:bg-[#0d0d0d]">
      <div className="px-4 sm:px-6 lg:px-8 py-8 space-y-6">
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
            <ExportButton clientId={clientId} records={records} isDemo={isDemo} />
          </div>
        </header>

        <UrlChecker onCheck={handleCheckUrl} />

        {isDemo && (
          <div className="rounded-lg border border-[#2a78d6]/30 bg-[#2a78d6]/10 px-4 py-3 text-sm text-[#0b0b0b] dark:text-white">
            <span className="font-medium">Demo history.</span> No PhishGuard install was
            detected on this browser, so this is a fixed sample showing how PhishGuard
            scores a mix of everyday browsing and known-malicious URLs. Install the extension
            and open “View my dashboard” from its popup to scan live and see your own
            history.
            {status === "loading" && (
              <span className="text-[#52514e] dark:text-[#c3c2b7]"> Refreshing from the API…</span>
            )}
            {error && (
              <span className="text-[#52514e] dark:text-[#c3c2b7]">
                {" "}
                Showing the bundled copy — the API is asleep or unreachable ({error}).
              </span>
            )}
          </div>
        )}

        {status === "error" && (
          <div className="rounded-lg border border-[#d03b3b]/30 bg-[#d03b3b]/10 px-4 py-3 text-sm text-[#d03b3b]">
            Couldn't reach the PhishGuard backend at {API_BASE_URL} — is it
            running? ({error})
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
