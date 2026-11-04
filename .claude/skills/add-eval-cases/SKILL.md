---
name: add-eval-cases
description: Turn derivation steps from my worksheets (pasted text or a photo) into labelled cases in verifier/eval_cases.json.
disable-model-invocation: true
argument-hint: "[steps as text, or the path of a photo]"
---

Add eval cases from: $ARGUMENTS

1. Extract each step as a pair of LaTeX lines (previous → current). Use
   notation the verifier supports (see "Known limitations" in
   `verifier/README.md`). List steps it can't express yet instead of
   dropping them silently.
2. Show me a table: topic, previous line, current line, your proposed label
   (correct / incorrect), and for incorrect steps the mistake in a few words.
3. Wait for me to confirm or fix every label. I decide the labels, not you:
   a wrong label makes the eval lie.
4. Append the confirmed cases to `verifier/eval_cases.json` in the existing
   format, skipping duplicates.
5. Run `python eval.py` from `verifier/` and show the summary. For any new
   case that fails, say whether it looks like a verifier bug, a parser
   limitation or a wrong label. Don't change the verifier in this step.
