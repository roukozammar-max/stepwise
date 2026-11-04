"""Warm-up module, imported once by the worker server (see verifier._mp_context).

SymPy loads parts of itself lazily: the first LaTeX parse, simplify() and
solveset() in a fresh process take ~0.5 s, later ones ~20 ms. Running one
check of each kind here means every worker forked from the server starts
with that work already done.
"""
from verifier import _check_step

_check_step(r"\frac{d}{dx}\sin(x^2)", r"\cos(x^2)", 1)        # parse, diff, numeric
_check_step(r"(x+1)^2", r"x^2 + 2x + 1", 1)                   # simplify
_check_step(r"x^2 = 4", r"x = 2", 1)                          # solveset
_check_step(r"\int x^2 dx", r"\frac{x^3}{3} + C", 1)          # integrals
