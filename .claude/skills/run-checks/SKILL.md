---
name: run-checks
description: Run the verifier's unit tests and eval set and report the results with evidence. Use after any change in verifier/ and before committing.
---

Run these from `verifier/` with the project's `.venv` active:

1. `python -m pytest -q`
2. `python eval.py`

(On Windows these take about a minute in total. That's expected.)

Then report:

- Tests: how many passed and failed. For each failure, the test name and the
  assertion that failed.
- Eval: copy the summary lines exactly (agreement, false-accept rate,
  false-reject rate, unknown, latency).
- If the false-accept rate is above 0, say that first: it blocks committing.

Don't change any code here. If something fails, explain the likely cause and
propose a fix for me to approve.
