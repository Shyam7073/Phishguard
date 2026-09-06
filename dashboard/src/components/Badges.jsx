export const GOOD = "#0ca30c";
export const CRITICAL = "#d03b3b";
export const NEUTRAL = "#898781";

export function VerdictBadge({ isPhishing }) {
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

export function UrlhausBadge({ status }) {
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

export function DomainAgeBadge({ status, days }) {
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
