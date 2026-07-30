const GOOD = "#0ca30c";
const CRITICAL = "#d03b3b";

function BarRow({ label, count, total, color }) {
  const pct = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 w-28 shrink-0">
        <span
          className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: color }}
          aria-hidden="true"
        />
        <span className="text-sm font-medium text-[#0b0b0b] dark:text-white">{label}</span>
      </div>
      <div className="flex-1 py-1.5">
        <div className="h-5 rounded-sm bg-[#e1e0d9] dark:bg-[#2c2c2a] overflow-hidden">
          <div
            className="h-5 rounded-r-[4px]"
            style={{ width: `${pct}%`, backgroundColor: color }}
          />
        </div>
      </div>
      <span className="w-12 text-right text-sm font-semibold tabular-nums text-[#0b0b0b] dark:text-white">
        {count.toLocaleString()}
      </span>
    </div>
  );
}

export default function VerdictBarChart({ total, phishingCount, legitCount }) {
  return (
    <div className="rounded-lg border border-[rgba(11,11,11,0.10)] dark:border-[rgba(255,255,255,0.10)] bg-[#fcfcfb] dark:bg-[#1a1a19] px-4 py-4">
      <h2 className="text-sm font-medium text-[#52514e] dark:text-[#c3c2b7] mb-3">
        Verdict breakdown
      </h2>
      <div className="space-y-1">
        <BarRow label="Legitimate" count={legitCount} total={total} color={GOOD} />
        <BarRow label="Phishing" count={phishingCount} total={total} color={CRITICAL} />
      </div>
    </div>
  );
}
