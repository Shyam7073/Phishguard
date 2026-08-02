const GOOD = "#0ca30c";
const CRITICAL = "#d03b3b";
const NEUTRAL = "#898781";

function VerdictBadge({ isPhishing }) {
  const color = isPhishing ? CRITICAL : GOOD;
  const label = isPhishing ? "Phishing" : "Legitimate";

  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-[#0b0b0b] dark:text-white">
      <span
        className="inline-block w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

const URLHAUS_LABELS = {
  listed: { text: "Blocklisted", color: CRITICAL },
  not_listed: { text: "Clean", color: GOOD },
  unknown: { text: "Unchecked", color: NEUTRAL },
};

function UrlhausBadge({ status }) {
  const { text, color } = URLHAUS_LABELS[status] || { text: "—", color: NEUTRAL };
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-[#0b0b0b] dark:text-white">
      <span
        className="inline-block w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      {text}
    </span>
  );
}

const DOMAIN_AGE_COLORS = {
  new: CRITICAL,
  moderate: NEUTRAL,
  established: GOOD,
  unknown: NEUTRAL,
};

function DomainAgeBadge({ status, days }) {
  const color = DOMAIN_AGE_COLORS[status] || NEUTRAL;
  const label = status === "unknown" || status == null ? "—" : days != null ? `${days}d (${status})` : status;
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-[#0b0b0b] dark:text-white">
      <span
        className="inline-block w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString();
}

export default function HistoryTable({ records }) {
  if (records.length === 0) {
    return (
      <div className="rounded-lg border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-[#fcfcfb] dark:bg-[#1a1a19] px-4 py-8 text-center text-sm text-[#898781]">
        No scans yet — browse to a site with the PhishGuard extension installed.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-[#fcfcfb] dark:bg-[#1a1a19] overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#e1e0d9] dark:border-[#2c2c2a] text-left text-[#52514e] dark:text-[#c3c2b7]">
            <th className="px-4 py-2 font-medium">URL</th>
            <th className="px-4 py-2 font-medium">Verdict</th>
            <th className="px-4 py-2 font-medium">Reason</th>
            <th className="px-4 py-2 font-medium">Blocklist</th>
            <th className="px-4 py-2 font-medium">Domain age</th>
            <th className="px-4 py-2 font-medium text-right">Confidence</th>
            <th className="px-4 py-2 font-medium text-right">Scanned at</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr
              key={record.id}
              className="border-b border-[#e1e0d9] dark:border-[#2c2c2a] last:border-0"
            >
              <td className="px-4 py-2 max-w-xs truncate text-[#0b0b0b] dark:text-white" title={record.url}>
                {record.url}
              </td>
              <td className="px-4 py-2">
                <VerdictBadge isPhishing={record.is_phishing} />
              </td>
              <td
                className="px-4 py-2 max-w-xs truncate text-[#52514e] dark:text-[#c3c2b7]"
                title={record.verdict_reason || ""}
              >
                {record.verdict_reason || "—"}
              </td>
              <td className="px-4 py-2">
                <UrlhausBadge status={record.urlhaus_status} />
              </td>
              <td className="px-4 py-2">
                <DomainAgeBadge status={record.domain_age_status} days={record.domain_age_days} />
              </td>
              <td className="px-4 py-2 text-right tabular-nums text-[#0b0b0b] dark:text-white">
                {(record.confidence * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-2 text-right text-[#52514e] dark:text-[#c3c2b7] whitespace-nowrap">
                {formatTimestamp(record.scanned_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
