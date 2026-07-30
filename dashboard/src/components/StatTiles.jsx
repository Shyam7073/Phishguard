const GOOD = "#0ca30c";
const CRITICAL = "#d03b3b";

function Tile({ label, value, dotColor }) {
  return (
    <div className="flex-1 min-w-[140px] rounded-lg border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-[#fcfcfb] dark:bg-[#1a1a19] px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        {dotColor && (
          <span
            className="inline-block w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: dotColor }}
            aria-hidden="true"
          />
        )}
        <span className="text-sm text-[#52514e] dark:text-[#c3c2b7]">{label}</span>
      </div>
      <div className="text-3xl font-semibold text-[#0b0b0b] dark:text-white">{value}</div>
    </div>
  );
}

export default function StatTiles({ total, phishingCount, legitCount }) {
  const rate = total > 0 ? ((phishingCount / total) * 100).toFixed(1) : "0.0";

  return (
    <div className="flex flex-wrap gap-3">
      <Tile label="Total scans" value={total.toLocaleString()} />
      <Tile label="Legitimate" value={legitCount.toLocaleString()} dotColor={GOOD} />
      <Tile label="Phishing" value={phishingCount.toLocaleString()} dotColor={CRITICAL} />
      <Tile label="Phishing rate" value={`${rate}%`} />
    </div>
  );
}
