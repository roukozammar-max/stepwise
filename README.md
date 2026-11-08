# Stepwise

[![CI](https://github.com/roukozammar-max/stepwise/actions/workflows/ci.yml/badge.svg)](https://github.com/roukozammar-max/stepwise/actions/workflows/ci.yml)

A shared problem-solving board for maths and physics study groups that checks
every line of a derivation with a computer algebra system, and gives AI hints
that point at the mistake without giving away the answer.

```
\frac{d}{dx}\sin(x^2)
= \cos(x^2) \cdot 2x     ✅ Equal.
= \cos(x^2)              ❌ Not equal: at x = 1, the previous line gives 1.081
                            but this line gives 0.5403.

x^2 = 4
x = 2                    ❌ This step lost x = -2.
```

## Status

| Part | Folder | Status |
|---|---|---|
| Step verifier (SymPy) + API | `verifier/` | Working: 20 tests, 46-step eval, 0 false accepts |
| Web app (Next.js) | `web/` | Phase 1, scaffolded (Next.js 16, TypeScript, Tailwind) |
| Real-time sync (Yjs + Hocuspocus) | `sync/` | Phase 2, not started |
| AI hints | `verifier/` or `hints/` | Phase 3, not started |

The full plan, split into tasks, is in [docs/ROADMAP.md](docs/ROADMAP.md).

## Run the verifier

**Windows, easiest:** double-click `setup.bat` (installs everything and runs
the checks, writing `setup-log.txt`), then double-click `start-api.bat`
(opens the test page in your browser). `publish-to-github.bat` saves and
uploads your latest changes to GitHub.

**Any system:** `python tools/setup_dev.py`, then `python tools/start_api.py`.

By hand, Windows (PowerShell):

```powershell
cd verifier
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python eval.py
uvicorn api:app --reload   # http://127.0.0.1:8000/docs
```

macOS / Linux: same steps, with `python3 -m venv .venv` and
`source .venv/bin/activate`.

Details, design and limitations: [verifier/README.md](verifier/README.md).

## Key numbers

Updated as the project grows. These are what go on the resume, so they are
always measured, never estimated.

| Metric | Now |
|---|---|
| Eval set size | 46 steps |
| False-accept rate (wrong step marked ✅) | 0% |
| Median / p95 check time | ~55 ms / ~85 ms |
| Weekly active boards | — |
| Hint leak rate | — |
