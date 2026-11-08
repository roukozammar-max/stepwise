/**
 * Talking to the verifier API, and matching its answers back to board lines.
 *
 * A step's verdict depends on two lines: the previous non-empty line and the
 * line itself. Each verdict is stored with a "key" made of those two lines,
 * so a verdict is only shown while both lines are unchanged. That makes stale
 * or out-of-order answers harmless: they simply don't match the key anymore.
 */
import type { Line } from "./board";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);
export const REQUEST_TIMEOUT_MS = 90_000;

export type StepStatus = "start" | "correct" | "incorrect" | "unknown";

/** One entry of the API's response (StepResult in verifier/verifier.py). */
export type StepResult = {
  line: number;
  status: StepStatus;
  method: string;
  message: string;
  counterexample: { at: Record<string, string>; previous: string; this: string } | null;
};

export type Verdict = {
  key: string;
  status: Exclude<StepStatus, "start">;
  message: string;
};

/** A non-empty line, with the line it is compared against. */
export type CheckableLine = { id: string; latex: string; key: string; isStart: boolean };

export function stepKey(previous: string | null, current: string): string {
  return `${previous ?? ""}\u0000${current}`;
}

/** The lines that get sent to the API: non-empty ones, in order. The first
 * of them is the starting point and never gets a verdict. */
export function checkableLines(lines: Line[]): CheckableLine[] {
  const out: CheckableLine[] = [];
  let previous: string | null = null;
  for (const line of lines) {
    const latex = line.latex.trim();
    if (!latex) continue;
    out.push({ id: line.id, latex, key: stepKey(previous, latex), isStart: previous === null });
    previous = latex;
  }
  return out;
}

/** Lines whose current step has no up-to-date verdict yet. */
export function linesNeedingCheck(
  items: CheckableLine[],
  verdicts: Record<string, Verdict>,
): CheckableLine[] {
  return items.filter((item) => !item.isStart && verdicts[item.id]?.key !== item.key);
}

/** Turn the API's answer into verdicts, matched to lines by position. */
export function mapResults(sent: CheckableLine[], steps: StepResult[]): Record<string, Verdict> {
  const verdicts: Record<string, Verdict> = {};
  sent.forEach((item, i) => {
    const step = steps[i];
    if (!step || item.isStart || step.status === "start") return;
    verdicts[item.id] = { key: item.key, status: step.status, message: step.message };
  });
  return verdicts;
}

export class CheckerError extends Error {}

export async function requestVerification(latexLines: string[]): Promise<StepResult[]> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lines: latexLines }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    throw new CheckerError(
      error instanceof DOMException && error.name === "TimeoutError"
        ? "The checker took too long to answer."
        : "The checker can't be reached.",
    );
  }
  if (!response.ok) {
    throw new CheckerError(`The checker answered with an error (${response.status}).`);
  }
  const data = (await response.json()) as { steps?: StepResult[] };
  if (!Array.isArray(data.steps)) throw new CheckerError("The checker sent an unexpected answer.");
  return data.steps;
}
