"use client";

/**
 * Checks the board with the verifier API:
 * - about 800 ms after typing stops, or right away on Enter / leaving a line
 * - only the newest answer counts (each request gets an increasing number)
 * - "slow" after 3 s (the free server may be waking up), "error" if it fails
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Line } from "./board";
import {
  CheckerError,
  checkableLines,
  linesNeedingCheck,
  mapResults,
  requestVerification,
  type Verdict,
} from "./verify";

export const TYPING_PAUSE_MS = 800;
export const SLOW_AFTER_MS = 3_000;

export type CheckerStatus = "idle" | "checking" | "slow" | "error";

export function useChecker(lines: Line[]) {
  const [verdicts, setVerdicts] = useState<Record<string, Verdict>>({});
  const [status, setStatus] = useState<CheckerStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const linesRef = useRef(lines);
  const verdictsRef = useRef(verdicts);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSent = useRef(0);
  const lastApplied = useRef(0);

  // Layout effects run right after React updates the page, so a check that
  // starts straight after an edit (e.g. on Enter) always sees the new lines.
  useLayoutEffect(() => {
    linesRef.current = lines;
  }, [lines]);
  useLayoutEffect(() => {
    verdictsRef.current = verdicts;
  }, [verdicts]);

  const run = useCallback(async () => {
    const items = checkableLines(linesRef.current);
    if (linesNeedingCheck(items, verdictsRef.current).length === 0) {
      setStatus((s) => (s === "error" ? s : "idle"));
      return;
    }
    const seq = ++lastSent.current;
    setStatus("checking");
    const slowTimer = setTimeout(() => {
      if (seq === lastSent.current) setStatus("slow");
    }, SLOW_AFTER_MS);
    try {
      const steps = await requestVerification(items.map((item) => item.latex));
      if (seq > lastApplied.current) {
        lastApplied.current = seq;
        const fresh = mapResults(items, steps);
        setVerdicts((old) => ({ ...old, ...fresh }));
      }
      if (seq === lastSent.current) {
        setStatus("idle");
        setErrorMessage("");
      }
    } catch (error) {
      if (seq === lastSent.current) {
        setStatus("error");
        setErrorMessage(
          error instanceof CheckerError ? error.message : "Something went wrong while checking.",
        );
      }
    } finally {
      clearTimeout(slowTimer);
    }
  }, []);

  /** Check after the typing pause (or after `delay` ms). */
  const schedule = useCallback(
    (delay: number = TYPING_PAUSE_MS) => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        timer.current = null;
        void run();
      }, delay);
    },
    [run],
  );

  /** Check right away (Enter, leaving a line, Retry). */
  const checkNow = useCallback(() => schedule(0), [schedule]);

  // Whenever a step changes, check it after the typing pause.
  const signature = checkableLines(lines)
    .map((item) => item.key)
    .join("\u0001");
  useEffect(() => {
    schedule();
  }, [signature, schedule]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  return { verdicts, status, errorMessage, checkNow };
}
