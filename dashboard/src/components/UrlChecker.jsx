import { useEffect, useState } from "react";
import { VerdictBadge, UrlhausBadge, DomainAgeBadge } from "./Badges";

const SCHEME_RE = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//;

// The API sits on a free tier that spins down when idle, so a check made
// after a quiet spell waits on a cold start rather than on the scan. Past
// this long, say so instead of leaving the button spinning in silence.
const COLD_START_HINT_MS = 4000;

// Lets someone paste a suspicious URL without opening it in a tab -- /scan
// only ever inspects the URL string (no page fetch), so this is exactly as
// safe as the extension's own automatic scan, just triggered manually.
function normalizeUrl(input) {
  const trimmed = input.trim();
  if (!trimmed || SCHEME_RE.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

export default function UrlChecker({ onCheck }) {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("idle"); // idle | checking | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (status !== "checking") {
      setSlow(false);
      return undefined;
    }
    const timer = setTimeout(() => setSlow(true), COLD_START_HINT_MS);
    return () => clearTimeout(timer);
  }, [status]);

  async function handleSubmit(event) {
    event.preventDefault();
    const url = normalizeUrl(input);
    if (!url) {
      setStatus("error");
      setError("Enter a URL first.");
      return;
    }

    setStatus("checking");
    setError(null);
    setResult(null);
    try {
      const verdict = await onCheck(url);
      setResult(verdict);
      setStatus("done");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  return (
    <div className="rounded-lg border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-[#fcfcfb] dark:bg-[#1a1a19] px-4 py-4 space-y-3">
      <h2 className="text-sm font-medium text-[#52514e] dark:text-[#c3c2b7]">
        Check a URL
      </h2>
      <p className="text-xs text-[#898781]">
        Paste a link you don't want to open — it's checked by URL string only, never visited.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="e.g. paypal.com.security-verify-login.tk/account"
          className="flex-1 min-w-[240px] rounded-md border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-white dark:bg-[#111110] px-3 py-1.5 text-sm text-[#0b0b0b] dark:text-white placeholder:text-[#898781] focus:outline-none focus:ring-2 focus:ring-[#2a78d6]/40"
        />
        <button
          type="submit"
          disabled={status === "checking"}
          className="inline-flex items-center rounded-md bg-[#2a78d6] dark:bg-[#3987e5] px-4 py-1.5 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {status === "checking" ? "Checking…" : "Check URL"}
        </button>
      </form>

      {status === "checking" && slow && (
        <p className="text-xs text-[#898781]">
          Still working — the API sleeps when it is idle, so the first check
          after a while can take up to a minute.
        </p>
      )}

      {status === "error" && (
        <div className="rounded-md border border-[#d03b3b]/30 bg-[#d03b3b]/10 px-3 py-2 text-sm text-[#d03b3b]">
          {error}
        </div>
      )}

      {status === "done" && result && (
        <div className="rounded-md border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] px-3 py-3 space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <VerdictBadge isPhishing={result.is_phishing} />
            <span className="text-sm text-[#0b0b0b] dark:text-white">
              {(result.confidence * 100).toFixed(1)}% confidence
            </span>
          </div>
          <p className="text-sm text-[#52514e] dark:text-[#c3c2b7]">{result.verdict_reason}</p>
          <div className="flex flex-wrap gap-4">
            <UrlhausBadge status={result.urlhaus_status} />
            <DomainAgeBadge status={result.domain_age_status} days={result.domain_age_days} />
          </div>
        </div>
      )}
    </div>
  );
}
