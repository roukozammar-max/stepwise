"""
Stepwise step verifier.

Takes a derivation written as LaTeX lines and checks each line against the
previous one with SymPy. Every step gets one of three verdicts:

  correct    the two lines are mathematically the same (for equations:
             they have the same solutions)
  incorrect  they are provably different; we attach a counterexample
             whenever we can find one
  unknown    we couldn't decide (unsupported notation, inequalities,
             timeouts...). Saying "I don't know" beats guessing.

How a step is checked, in order:
  1. Symbolic: simplify(previous - current) == 0
  2. Numeric:  evaluate both lines at several points; any real-valued
               point where they differ is a counterexample
  3. Equations only: compare solution sets (catches "x^2 = 4 -> x = 2",
               which silently loses x = -2)

Every check runs in a separate process with a hard time limit, because
SymPy's simplify() can occasionally run for a very long time.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from typing import Any, Callable, Optional

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.parsing.latex import parse_latex

DEFAULT_TIMEOUT = 5.0  # seconds per step

# Values tried first when hunting for a counterexample. "Nice" numbers make
# feedback readable ("at x = 1 ...") instead of "at x = 1.83749...".
NICE_VALUES = [sp.Integer(1), sp.Integer(2), sp.Integer(-1),
               sp.Rational(1, 2), sp.Integer(3), sp.Integer(-2)]
RANDOM_POINTS = 14       # extra random points after the nice ones
MIN_AGREEING_POINTS = 5  # how many points must agree before we trust "equal"


@dataclass(frozen=True)
class StepResult:
    line: int                     # index of the line being judged (0-based)
    status: str                   # "start" | "correct" | "incorrect" | "unknown"
    method: str = ""              # how we decided: symbolic, numeric, solution-set...
    message: str = ""             # short explanation shown to the student
    counterexample: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def parse_line(latex: str) -> tuple[str, Any]:
    """Turn one line of LaTeX into a SymPy object.

    Returns (kind, obj) where kind is "expr" (an expression), "eq" (an
    equation) or "rel" (an inequality). A line starting with "=" continues
    the previous expression, as in a chain of equalities:

        \\frac{d}{dx}\\sin(x^2)
        = \\cos(x^2) \\cdot 2x
    """
    text = latex.strip()
    if text.startswith("="):
        text = text[1:].strip()
    if not text:
        raise ValueError("empty line")

    # parse_latex builds SymPy objects directly; it never eval()s the text.
    # Never feed raw user input to sympify()/parse_expr(): those use eval().
    obj = parse_latex(text, backend="antlr")
    obj = _normalise(obj)

    if isinstance(obj, sp.logic.boolalg.BooleanAtom):
        raise ValueError("this line is always true or always false")
    if isinstance(obj, sp.Equality):
        return "eq", obj
    if isinstance(obj, sp.core.relational.Relational):
        return "rel", obj
    return "expr", obj


FUNCTION_NAMES = {"f", "g", "h"}  # letters that really are function names


def _calls_to_products(obj):
    """The parser reads x(x+1) as "the function x applied to x+1".
    Students mean multiplication, so rewrite single-letter calls (except f, g,
    h) as products. Loop because calls can be nested: x(x(x+1))."""
    for _ in range(10):
        replacements = {
            call: sp.Symbol(call.func.__name__) * call.args[0]
            for call in obj.atoms(AppliedUndef)
            if len(call.func.__name__) == 1
            and call.func.__name__ not in FUNCTION_NAMES
            and len(call.args) == 1
        }
        if not replacements:
            break
        obj = obj.xreplace(replacements)
    return obj


def _normalise(obj):
    """Apply the conventions students assume without writing them down."""
    obj = _calls_to_products(obj)
    # "e" means Euler's number.
    obj = obj.subs({s: sp.E for s in obj.free_symbols if s.name == "e"})
    # Every variable is a real number.
    obj = obj.xreplace({s: sp.Symbol(s.name, real=True) for s in obj.free_symbols})
    return obj


def _indefinite_integration_variable(obj):
    """If obj contains an indefinite integral, return its variable."""
    for integral in obj.atoms(sp.Integral):
        for limit in integral.limits:
            if len(limit) == 1:          # ((x,),) means no bounds
                return limit[0]
    return None


# --------------------------------------------------------------------------
# Low-level checks
# --------------------------------------------------------------------------

def _is_zero_symbolic(expr) -> bool:
    try:
        return sp.simplify(expr) == 0
    except Exception:
        return False


def _as_real_number(value) -> Optional[float]:
    """Return a float if value is a finite real number, else None."""
    try:
        c = complex(value)
    except (TypeError, ValueError):
        return None
    if c != c or abs(c) == float("inf"):          # NaN or infinite
        return None
    if abs(c.imag) > 1e-9 * max(1.0, abs(c.real)):
        return None                                # not real at this point
    return c.real


def _sample_points(symbols, rng):
    if not symbols:
        return [{}]
    points = []
    for i in range(len(NICE_VALUES)):
        # Shift each variable so they don't all get the same value.
        points.append({s: NICE_VALUES[(i + 2 * j) % len(NICE_VALUES)]
                       for j, s in enumerate(symbols)})
    for _ in range(RANDOM_POINTS):
        points.append({s: sp.Float(rng.uniform(-3, 3), 15) for s in symbols})
    return points


def _numeric_compare(left, right):
    """Evaluate left and right at many points.

    Returns ("equal", n), ("different", point, left_value, right_value)
    or ("undecided",). Points where either side is undefined or not real
    (e.g. sqrt of a negative) are skipped: we only compare where both
    lines make sense.
    """
    # Use the variables of both sides, not of (left - right): in
    # "x + 1 - x" vs "2" the x cancels in the difference but each side
    # still needs a value for x to be evaluated.
    symbols = sorted(left.free_symbols | right.free_symbols, key=lambda s: s.name)
    rng = random.Random(f"{left}|{right}")  # deterministic: same input, same verdict
    agreeing = 0
    for point in _sample_points(symbols, rng):
        try:
            lv = _as_real_number(left.evalf(15, subs=point))
            rv = _as_real_number(right.evalf(15, subs=point))
        except Exception:
            continue
        if lv is None or rv is None:
            continue
        if abs(lv - rv) <= 1e-8 * max(1.0, abs(lv), abs(rv)):
            agreeing += 1
        else:
            return ("different", point, lv, rv)
    needed = 1 if not symbols else MIN_AGREEING_POINTS
    return ("equal", agreeing) if agreeing >= needed else ("undecided",)


def _format_point(point) -> dict:
    out = {}
    for s, v in point.items():
        out[s.name] = str(v) if isinstance(v, (sp.Integer, sp.Rational)) else f"{float(v):.3f}"
    return out


def _counterexample(point, lv, rv) -> dict:
    return {"at": _format_point(point), "previous": f"{lv:.4g}", "this": f"{rv:.4g}"}


def _point_text(point) -> str:
    return ", ".join(f"{k} = {v}" for k, v in _format_point(point).items()) or "this value"


# --------------------------------------------------------------------------
# Comparing two lines
# --------------------------------------------------------------------------

def _compare_expressions(a, b, index: int) -> StepResult:
    var = _indefinite_integration_variable(a) or _indefinite_integration_variable(b)
    a_val, b_val = a.doit(), b.doit()

    if var is not None:
        # Antiderivatives may differ by a constant (+ C), so compare their
        # derivatives instead of the expressions themselves.
        left, right = sp.diff(a_val, var), sp.diff(b_val, var)
        suffix = " (up to a constant of integration)"
    else:
        left, right = a_val, b_val
        suffix = ""

    if _is_zero_symbolic(left - right):
        return StepResult(index, "correct", "symbolic", f"Equal{suffix}.")

    verdict = _numeric_compare(left, right)
    if verdict[0] == "equal":
        return StepResult(index, "correct", "numeric",
                          f"Equal{suffix} (checked at {verdict[1]} points).")
    if verdict[0] == "different":
        _, point, lv, rv = verdict
        if var is not None:
            msg = (f"Not the same antiderivative: differentiating both lines gives "
                   f"different results at {_point_text(point)} ({lv:.4g} vs {rv:.4g}).")
        else:
            msg = (f"Not equal: at {_point_text(point)}, the previous line gives "
                   f"{lv:.4g} but this line gives {rv:.4g}.")
        return StepResult(index, "incorrect", "numeric", msg, _counterexample(point, lv, rv))

    return StepResult(index, "unknown", "numeric",
                      "Couldn't decide: the lines don't simplify to the same thing, "
                      "but no counterexample was found either.")


def _solutions_text(var, solutions) -> str:
    items = sorted(solutions, key=lambda v: float(v) if v.is_real else 0)
    return ", ".join(f"{var} = {v}" for v in items)


def _compare_equations(a, b, index: int) -> StepResult:
    d1 = (a.lhs - a.rhs).doit()
    d2 = (b.lhs - b.rhs).doit()

    if _is_zero_symbolic(d1 - d2):
        return StepResult(index, "correct", "symbolic", "Same equation, rearranged.")

    if not _is_zero_symbolic(d2):
        ratio = sp.simplify(d1 / d2)
        if ratio.is_number and ratio.is_finite and ratio != 0:
            return StepResult(index, "correct", "constant-factor",
                              f"Same equation, both sides scaled by {ratio}.")

    symbols = sorted(d1.free_symbols | d2.free_symbols, key=lambda s: s.name)
    if len(symbols) == 1:
        x = symbols[0]
        before = sp.solveset(d1, x, domain=sp.S.Reals)
        after = sp.solveset(d2, x, domain=sp.S.Reals)
        if before == after:
            return StepResult(index, "correct", "solution-set", "Same solutions.")
        if isinstance(before, sp.FiniteSet) and isinstance(after, sp.FiniteSet):
            lost, gained = before - after, after - before
            if lost.is_empty is not None and gained.is_empty is not None:
                parts = []
                if not lost.is_empty:
                    parts.append(f"lost {_solutions_text(x, lost)}")
                if not gained.is_empty:
                    parts.append(f"added {_solutions_text(x, gained)}, "
                                 f"which doesn't solve the previous line")
                if parts:
                    return StepResult(index, "incorrect", "solution-set",
                                      "This step " + " and ".join(parts) + ".")
                return StepResult(index, "correct", "solution-set", "Same solutions.")

    if len(symbols) > 1:
        result = _compare_by_solving(d1, d2, symbols, index)
        if result is not None:
            return result

    return StepResult(index, "unknown", "solution-set",
                      "Couldn't decide whether these equations have the same solutions.")


def _compare_by_solving(d1, d2, symbols, index: int) -> Optional[StepResult]:
    """For equations with several variables (y = 2x + 3 -> x = ...), solve
    both lines for one variable and compare the two formulas."""
    for s in symbols:
        try:
            sol1, sol2 = sp.solve(d1, s), sp.solve(d2, s)
        except Exception:
            continue
        if len(sol1) != 1 or len(sol2) != 1:
            continue  # only use variables with a single, clean solution
        e1, e2 = sol1[0], sol2[0]
        if _is_zero_symbolic(e1 - e2):
            return StepResult(index, "correct", "solved-for",
                              f"Same equation (both give {s} = {e1}).")
        verdict = _numeric_compare(e1, e2)
        if verdict[0] == "equal":
            return StepResult(index, "correct", "solved-for",
                              f"Same equation (both give the same {s}).")
        if verdict[0] == "different":
            _, point, lv, rv = verdict
            return StepResult(
                index, "incorrect", "solved-for",
                f"Solving both lines for {s} gives different answers: at "
                f"{_point_text(point)}, the previous line gives {s} = {lv:.4g} "
                f"but this line gives {s} = {rv:.4g}.",
                _counterexample(point, lv, rv))
    return None


def _check_step(prev: str, curr: str, index: int) -> StepResult:
    try:
        kind_a, a = parse_line(prev)
    except Exception:
        return StepResult(index, "unknown", "parse", "Couldn't read the previous line.")
    try:
        kind_b, b = parse_line(curr)
    except Exception:
        return StepResult(index, "unknown", "parse",
                          "Couldn't read this line. Check the LaTeX.")

    if "rel" in (kind_a, kind_b):
        return StepResult(index, "unknown", "unsupported", "Inequalities aren't supported yet.")
    if kind_a != kind_b:
        return StepResult(index, "unknown", "mismatch",
                          "One line is an equation and the other isn't, "
                          "so they can't be compared directly.")
    if kind_a == "eq":
        return _compare_equations(a, b, index)
    return _compare_expressions(a, b, index)


def _check_step_dict(prev: str, curr: str, index: int) -> dict:
    return _check_step(prev, curr, index).to_dict()


# --------------------------------------------------------------------------
# Running checks with a hard time limit
# --------------------------------------------------------------------------

_context = None


def _mp_context():
    """Pick how worker processes are started.

    "forkserver" forks each worker from a helper process that has already
    imported and warmed up SymPy (see verifier_warmup.py), so a check starts
    in milliseconds, and it's safe to use from a multi-threaded web server.
    Windows only has "spawn", where every check pays the ~1 s warm-up.
    """
    global _context
    if _context is None:
        if "forkserver" in mp.get_all_start_methods():
            _context = mp.get_context("forkserver")
            _context.set_forkserver_preload(["verifier_warmup"])
        else:
            _context = mp.get_context("spawn")
    return _context


def _noop():
    return True


def start_workers() -> None:
    """Boot and warm up the worker server now (takes a few seconds once),
    so the first real check isn't slow. Call it when your app starts."""
    run_with_timeout(_noop, (), timeout=60)


def _child(conn, fn, args):
    try:
        conn.send(("started", None))  # imports are done; the time limit starts now
        conn.send(("ok", fn(*args)))
    except BaseException as exc:  # report the failure instead of dying silently
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()


STARTUP_TIMEOUT = 120.0  # seconds a worker may take to start (slow first run on Windows)


def run_with_timeout(fn: Callable, args: tuple = (), timeout: float = DEFAULT_TIMEOUT):
    """Run fn(*args) in a separate process and kill it if it takes too long.

    The time limit covers fn itself, not starting the worker: on Windows a
    fresh worker has to import SymPy first, which can take seconds on the
    first run, and that shouldn't turn a simple step into "unknown".

    Returns ("ok", value), ("timeout", None) or ("error", message).
    fn must be defined at module level so it can be sent to the child.
    """
    ctx = _mp_context()
    receiver, sender = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(sender, fn, args), daemon=True)
    proc.start()
    sender.close()
    try:
        if not receiver.poll(STARTUP_TIMEOUT):
            return ("error", "worker didn't start")
        status, value = receiver.recv()
        if status != "started":
            return (status, value)
        if receiver.poll(timeout):
            return receiver.recv()
        return ("timeout", None)
    except EOFError:
        return ("error", "worker exited without a result")
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(1)
        receiver.close()


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

@lru_cache(maxsize=4096)
def _check_pair(prev: str, curr: str, timeout: float) -> StepResult:
    """Check one step, cached by the two lines only (not their position), so
    inserting or deleting a line elsewhere doesn't force a re-check."""
    status, value = run_with_timeout(_check_step_dict, (prev, curr, 0), timeout)
    if status == "ok":
        return StepResult(**value)
    if status == "timeout":
        return StepResult(0, "unknown", "timeout",
                          f"Gave up after {timeout:g}s: this step is too complex "
                          f"to check automatically.")
    return StepResult(0, "unknown", "error", "Something went wrong checking this step.")


def check_step(prev: str, curr: str, index: int = 1,
               timeout: float = DEFAULT_TIMEOUT) -> StepResult:
    """Check one step. Results are cached, so re-checking a board after one
    line changes only recomputes the steps touching that line."""
    return replace(_check_pair(prev, curr, timeout), line=index)


# How many steps of one derivation are checked at the same time. Each check
# runs in its own process, so this mostly helps on Windows, where starting a
# worker takes ~1 s. Lower it on small servers (e.g. 2 on a 512 MB free tier).
MAX_PARALLEL_CHECKS = max(1, int(os.environ.get("STEPWISE_PARALLEL_CHECKS", "4")))


def check_derivation(lines: list[str], timeout: float = DEFAULT_TIMEOUT) -> list[StepResult]:
    """Check every step of a derivation. The first line is the starting point."""
    if not lines:
        return []
    try:
        parse_line(lines[0])
        first = StepResult(0, "start", "", "Starting point.")
    except Exception:
        first = StepResult(0, "unknown", "parse", "Couldn't read this line. Check the LaTeX.")
    steps = [(lines[i - 1], lines[i], i) for i in range(1, len(lines))]
    workers = min(MAX_PARALLEL_CHECKS, len(steps))
    if workers <= 1:
        return [first] + [check_step(p, c, i, timeout) for p, c, i in steps]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # pool.map keeps the results in the same order as the steps
        return [first] + list(pool.map(lambda s: check_step(*s, timeout=timeout), steps))


_INLINE_MATH = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$|\\\((.+?)\\\)", re.S)
_UNEVALUATED = (sp.Derivative, sp.Integral, sp.Limit)


def hint_reveals_answer(hint: str, answer: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """True if any maths in the hint is equivalent to the final answer.

    Used to block AI hints that give the solution away. The hint's maths is
    checked with the same verifier, so "$\\cos(x^2) \\cdot 2x$" is caught as
    a leak of "2x\\cos(x^2)" even though the text is different.
    """
    targets = [answer]
    try:
        kind, parsed = parse_line(answer)
        if kind == "eq" and isinstance(parsed.lhs, sp.Symbol):
            targets.append(sp.latex(parsed.rhs))   # "x = 2" also leaks as "2"
    except Exception:
        pass

    for groups in _INLINE_MATH.findall(hint):
        fragment = next(g for g in groups if g)
        try:
            _, parsed_fragment = parse_line(fragment)
        except Exception:
            continue
        # Restating the question (e.g. "d/dx sin(x^2)") isn't a leak, even
        # though it evaluates to the answer.
        if parsed_fragment.atoms(*_UNEVALUATED):
            continue
        for target in targets:
            if check_step(target, fragment, 1, timeout).status == "correct":
                return True
    return False
