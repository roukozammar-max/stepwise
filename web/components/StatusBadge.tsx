/** The small status mark at the end of each line. */

export type LineState = "checking" | "correct" | "incorrect" | "unknown" | "offline";

const LABELS: Record<LineState, string> = {
  checking: "Checking",
  correct: "Correct step",
  incorrect: "Incorrect step",
  unknown: "Couldn't decide",
  offline: "Not checked",
};

export function StatusBadge({ state }: { state: LineState }) {
  const label = LABELS[state];
  if (state === "checking") {
    return (
      <span role="img" aria-label={label} title={label} className="status-badge text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      </span>
    );
  }
  const style = {
    correct: "bg-ok-soft text-ok",
    incorrect: "bg-bad-soft text-bad",
    unknown: "bg-warn-soft text-warn",
    offline: "bg-warn-soft text-warn",
  }[state];
  const symbol = { correct: "✓", incorrect: "✗", unknown: "?", offline: "?" }[state];
  return (
    <span role="img" aria-label={label} title={label} className={`status-badge ${style}`}>
      {symbol}
    </span>
  );
}
