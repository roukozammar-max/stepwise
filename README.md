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
| Step verifier (SymPy) + API | `verifier/` | Working: 23 tests, 46-step eval, 0 false accepts |
| Web app (Next.js) | `web/` | Working locally: board, maths input, live checking. Deploy next. |
| Real-time sync (Yjs + Hocuspocus) | `sync/` | Phase 2, not started |
| AI hints | `verifier/` or `hints/` | Phase 3, not started |

The full plan, split into tasks, is in [docs/ROADMAP.md](docs/ROADMAP.md).

## Run it

**Windows, easiest:**

1. `setup.bat`: once, installs the checker's Python libraries and runs its tests.
2. `start-stepwise.bat`: starts the checker and the web app and opens the
   board at http://localhost:3000. The first time it installs Node.js (asks
   first) and the web app's libraries.
3. `publish-to-github.bat`: saves your changes and uploads them to GitHub.

`start-api.bat` starts only the checker, with its API test page.

**Any system:** `python tools/setup_dev.py`, then `python tools/start_web.py`.

By hand:

```bash
# Checker (from verifier/, with .venv active)
pip install -r requirements.txt
python -m pytest -q && python eval.py
uvicorn api:app --reload             # http://127.0.0.1:8000/docs

# Web app (from web/, in a second terminal)
npm ci
npm run dev                          # http://localhost:3000
```

Details: [verifier/README.md](verifier/README.md) and [web/README.md](web/README.md).

## Key numbers

Updated as the project grows. These are what go on the resume, so they are
always measured, never estimated.

| Metric | Now |
|---|---|
| Eval set size | 46 steps |
| False-accept rate (wrong step marked ✅) | 0% |
| Median / p95 check time per step (Linux) | ~45 ms / ~70 ms |
| Phase 1 acceptance checks passing locally in a real browser | 10 of 11 (11 is using it for real homework) |
| Weekly active boards | — |
| Hint leak rate | — |
