import { VerdictBadge, UrlhausBadge, DomainAgeBadge } from "./Badges";

function formatTimestamp(value) {
  return new Date(value).toLocaleString();
}

export default function HistoryTable({ records }) {
  if (records.length === 0) {
    return (
      <div className="rounded-lg border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-[#fcfcfb] dark:bg-[#1a1a19] px-4 py-8 text-center text-sm text-[#898781]">
        No scans yet — check a URL above, or install the PhishGuard extension
        to have every site you visit scanned automatically.
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
              <td
                className="px-4 py-2 max-w-md xl:max-w-xl 2xl:max-w-3xl truncate text-[#0b0b0b] dark:text-white"
                title={record.url}
              >
                {record.url}
              </td>
              <td className="px-4 py-2">
                <VerdictBadge isPhishing={record.is_phishing} />
              </td>
              <td
                className="px-4 py-2 max-w-md xl:max-w-lg 2xl:max-w-2xl truncate text-[#52514e] dark:text-[#c3c2b7]"
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
