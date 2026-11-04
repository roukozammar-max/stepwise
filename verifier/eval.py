"""Run the verifier over labelled steps and report how often it's wrong.

    python eval.py

The number that matters most is the FALSE-ACCEPT rate: how often a wrong
step gets a green tick. A student trusting a wrong green tick is the worst
outcome, so this script exits with an error if any wrong step is accepted.
That makes it usable as a CI check.

"unknown" is not counted as a mistake, but it's reported: a verifier that
answers "unknown" to everything would be safe and useless.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from verifier import check_step, start_workers

CASES_FILE = Path(__file__).with_name("eval_cases.json")


def main() -> int:
    cases = json.loads(CASES_FILE.read_text())
    start_workers()

    rows, latencies = [], []
    for case in cases:
        t0 = time.perf_counter()
        result = check_step(case["prev"], case["curr"])
        latencies.append((time.perf_counter() - t0) * 1000)
        rows.append((case, result))

    should_pass = [(c, r) for c, r in rows if c["expected"] == "correct"]
    should_fail = [(c, r) for c, r in rows if c["expected"] == "incorrect"]
    false_accepts = [(c, r) for c, r in should_fail if r.status == "correct"]
    false_rejects = [(c, r) for c, r in should_pass if r.status == "incorrect"]
    unknowns = [(c, r) for c, r in rows if r.status == "unknown"]
    right = [(c, r) for c, r in rows if r.status == c["expected"]]

    def show(title, items):
        if items:
            print(f"\n{title}")
            for c, r in items:
                print(f"  [{c['topic']}] {c['prev']}  ->  {c['curr']}")
                print(f"      got {r.status}: {r.message}")

    show("FALSE ACCEPTS (wrong step marked correct):", false_accepts)
    show("FALSE REJECTS (correct step marked incorrect):", false_rejects)
    show("UNKNOWN:", unknowns)

    n = len(rows)
    p95 = sorted(latencies)[max(0, int(0.95 * n) - 1)]
    print(f"\n{n} steps ({len(should_pass)} correct, {len(should_fail)} with planted errors)")
    print(f"  agreed with label   {len(right)}/{n} ({100 * len(right) / n:.0f}%)")
    print(f"  false-accept rate   {len(false_accepts)}/{len(should_fail)} "
          f"({100 * len(false_accepts) / max(1, len(should_fail)):.1f}%)")
    print(f"  false-reject rate   {len(false_rejects)}/{len(should_pass)} "
          f"({100 * len(false_rejects) / max(1, len(should_pass)):.1f}%)")
    print(f"  unknown             {len(unknowns)}/{n}")
    print(f"  latency per step    median {statistics.median(latencies):.0f} ms, p95 {p95:.0f} ms")

    return 1 if false_accepts else 0


if __name__ == "__main__":  # required: the verifier starts worker processes
    sys.exit(main())
