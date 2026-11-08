# Stepwise

A maths/physics study board that checks every derivation step with SymPy.
Plan, phases and next tasks: `docs/ROADMAP.md`.

## Commands

Python, run from `verifier/` with `.venv` activated (Windows PowerShell:
`.venv\Scripts\Activate.ps1`; macOS/Linux: `source .venv/bin/activate`):

- Install: `pip install -r requirements.txt`
- Tests: `python -m pytest -q` (one test: `python -m pytest -q test_verifier.py -k lost_solution`)
- Eval: `python eval.py` (exits 1 if any wrong step is marked correct)
- API: `uvicorn api:app --reload`, docs at http://127.0.0.1:8000/docs
- One-step setup from the repo root: `python tools/setup_dev.py` (Windows:
  `setup.bat`); it logs to `setup-log.txt`. Start the API with the test
  page opened: `python tools/start_api.py` (Windows: `start-api.bat`).

A verifier change is done only when the tests and the eval both pass.
Show the output, don't just say it passed. On Windows each check takes ~1 s,
so the eval takes about a minute; that's expected, not a bug.

Web app, run from `web/` (Next.js 16: read `web/AGENTS.md` before writing
Next.js code, this version differs from older docs):

- Install: `npm ci`
- Dev server: `npm run dev` (http://localhost:3000; needs the API running)
- Checks: `npm run lint && npm run typecheck && npm test && npm run build`
- Start everything at once from the repo root: `python tools/start_web.py`
  (Windows: `start-stepwise.bat`); it logs to `start-log.txt`.

A web change is done only when all four web checks pass and you've tried
the change in the browser.

## Verifier rules

- A wrong step marked "correct" (a false accept) is the worst bug in this
  project. When unsure, return "unknown" with a reason.
- Any change to how steps are judged needs new cases in `eval_cases.json`:
  at least one correct step and one with a planted mistake.
- Never pass user text to `sympify()` or `parse_expr()`: they call `eval()`.
  Use `parse_line()`.
- Heavy SymPy work goes through `run_with_timeout`, never directly in the
  API process.
- Scripts that use the verifier need `if __name__ == "__main__":` because
  worker processes re-import the main module.
- If new SymPy functionality is slow on first use, add one call to
  `verifier_warmup.py` so workers start warm.

## Conventions

- Folders: `verifier/` (Python checker + API), `web/` (Next.js app),
  `tools/` (setup/start/publish scripts), `docs/` (roadmap and specs).
  `sync/` (Hocuspocus server) is created in Phase 2.
- Web app rules: verdicts are keyed by (previous line, line), see
  `web/lib/verify.ts`; keep that, it's what makes late answers harmless.
  Keep `lib/` free of React so it stays unit-testable.
- Commit messages: short, imperative ("Add solution-set check for quadratics").
- When a roadmap task is finished, tick it in `docs/ROADMAP.md` and update
  "Key numbers" in the root README if they changed.
- Secrets live in `.env` (gitignored). Add the variable name to `.env.example`.
