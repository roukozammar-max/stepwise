# Stepwise verifier

The engine behind Stepwise: give it a derivation as LaTeX lines and it marks
every step ✅ correct, ❌ incorrect (with a counterexample) or ❓ unknown.

```
\frac{d}{dx}\sin(x^2)
= \cos(x^2) \cdot 2x     ✅ Equal.
= \cos(x^2)              ❌ Not equal: at x = 1, the previous line gives 1.081
                            but this line gives 0.5403.
```

```
x^2 = 4
x = 2                    ❌ This step lost x = -2.
```

## Quick start

Run everything from this `verifier/` folder.

**Windows (PowerShell):**

```powershell
cd verifier
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m pytest -q       # 20 unit tests (about 30-60 s on Windows)
python eval.py            # labelled eval set (about 1 min on Windows)
uvicorn api:app --reload  # then open http://127.0.0.1:8000/docs
```

If activating says "running scripts is disabled on this system", run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and
activate again.

**macOS / Linux:**

```bash
cd verifier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m pytest -q
python eval.py
uvicorn api:app --reload
```

Try the API in your browser at http://127.0.0.1:8000/docs: open
`POST /verify`, click "Try it out", and send
`{"lines": ["x^2 = 4", "x = 2"]}`.

Speed: on Windows each check takes ~1 s instead of ~50 ms, because Windows
can't reuse a warmed-up worker (see "Safety and speed" below). That's fine
for development. The published version runs on a Linux server, where it's
fast.

## Files

| File | What it does |
|---|---|
| `verifier.py` | Parsing, the three checks, timeouts, caching, hint leak check |
| `verifier_warmup.py` | Warms up SymPy once so every check starts fast |
| `api.py` | FastAPI endpoints: `/verify`, `/hint-check`, `/health` |
| `eval_cases.json` | 46 labelled steps (25 correct, 21 with planted mistakes) |
| `eval.py` | Runs the eval set; exits with an error if any wrong step gets ✅ |
| `test_verifier.py` | Unit tests, including the API |

## How a step is checked

1. **Parse** each line with SymPy's LaTeX parser (`parse_latex`), then apply
   student conventions: `e` is Euler's number, variables are real numbers,
   `x(x+1)` means multiplication (single letters other than f, g, h).
2. **Symbolic**: `simplify(previous - current) == 0` means ✅.
3. **Numeric**: evaluate both lines at nice values (1, 2, -1, 1/2...) then
   random ones. Any point where both are defined and real but differ is a
   counterexample, so ❌. Points where a line is undefined are skipped, so
   `ln(x^2) -> 2 ln(x)` is accepted on the domain where both make sense.
4. **Equations**: same equation rearranged or scaled by a constant gives ✅.
   Otherwise compare solution sets, which catches lost or added solutions.
   With several variables, solve both lines for one variable and compare.
5. **Indefinite integrals**: compare derivatives, so `+ C` doesn't matter.

Anything it can't decide is ❓ with a reason, never a guess.

## Safety and speed

- **No `eval`**: `parse_latex` builds SymPy objects directly. Never pass user
  text to `sympify()` or `parse_expr()`; those run `eval()` on it.
- **Timeouts**: `simplify()` can occasionally run for a very long time, so every
  check runs in its own process and is killed after 5 s (result: ❓).
- **Speed**: worker processes are forked from a "forkserver" that has already
  warmed up SymPy (`verifier_warmup.py`). The first check in a fresh process
  costs ~0.5 s; from a warm worker it's ~20–100 ms. `start_workers()` pays the
  one-time boot (~1 s) when the API starts.
- **Cache**: results are cached per (previous line, line), not by position, so
  editing line 7 of a board only re-checks steps 7 and 8, and inserting a line
  only re-checks the two steps around it.
- **Parallel steps**: the steps of one derivation are checked at the same time
  (`STEPWISE_PARALLEL_CHECKS`, default 4). On Windows this halves the time for
  a fresh 5-line board. Use 2 on a 512 MB free server.
- Any script that uses the verifier needs the `if __name__ == "__main__":`
  guard, because the workers re-import the main script.

## Settings (environment variables)

| Variable | Default | What it does |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Web pages allowed to call the API from a browser (CORS), comma-separated. Add the Vercel URL in production. |
| `STEPWISE_PARALLEL_CHECKS` | `4` | How many steps of one board are checked at once. |

## The eval, and why false-accepts are the number that matters

A wrong step marked ✅ is the worst outcome: the student trusts it. `eval.py`
reports the false-accept rate and fails CI if it's above zero. ❓ isn't counted
as a mistake, but watch it: a verifier that answers ❓ to everything is safe
and useless.

The starter set is small and was written alongside the code, so 100% on it
proves little. Grow it to 500+ steps using real mistakes from your own problem
sets and your users' boards. That number is what goes on your resume.

## Known limitations (good next issues)

- No `\pm`, no function notation like `f(x) = ...` / `f'(x)`, no inequalities.
- `i` is treated as a variable, not the imaginary unit.
- `\frac{x^2-1}{x-1} = x + 1` is accepted (true except at x = 1); decide
  whether you want to warn about excluded points.
- Production: run checks in a job queue (ARQ or Celery) with hard time and
  memory limits, and move the cache to Redis.
