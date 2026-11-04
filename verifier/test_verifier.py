"""Unit tests. Run with:  pytest -q"""
import time

import pytest
from fastapi.testclient import TestClient

import verifier
from api import app
from verifier import check_derivation, check_step, hint_reveals_answer, run_with_timeout


# --- expressions -----------------------------------------------------------

def test_correct_expansion():
    assert check_step(r"(x+1)^2", r"x^2 + 2x + 1").status == "correct"


def test_continuation_line_starting_with_equals():
    assert check_step(r"\frac{d}{dx}\sin(x^2)", r"= \cos(x^2) \cdot 2x").status == "correct"


def test_missed_chain_rule_gives_readable_counterexample():
    r = check_step(r"\frac{d}{dx}\sin(x^2)", r"\cos(x^2)")
    assert r.status == "incorrect"
    assert r.counterexample["at"] == {"x": "1"}   # tries nice numbers first


def test_respects_domain_sqrt_x_squared_is_not_x():
    r = check_step(r"\sqrt{x^2}", r"x")
    assert r.status == "incorrect"
    assert r.counterexample["at"] == {"x": "-1"}


def test_variables_that_cancel_still_get_values():
    # Regression: x cancels in (left - right), but each side still needs x.
    assert check_step(r"x + 1 - x", r"2").status == "incorrect"


def test_implicit_multiplication_x_of_x_plus_1():
    # The parser reads x(x+1) as a function call; we treat it as a product.
    assert check_step(r"x(x+1)", r"x^2 + x").status == "correct"


def test_indefinite_integral_up_to_constant():
    assert check_step(r"\int x^2 dx", r"\frac{x^3}{3} + C").status == "correct"
    assert check_step(r"\int x^2 dx", r"x^3 + C").status == "incorrect"


# --- equations -------------------------------------------------------------

def test_scaling_both_sides_is_fine():
    r = check_step(r"2x = 4", r"x = 2")
    assert (r.status, r.method) == ("correct", "constant-factor")


def test_lost_solution_is_named():
    r = check_step(r"x^2 = 4", r"x = 2")
    assert r.status == "incorrect"
    assert "x = -2" in r.message


def test_two_variable_equation_error():
    r = check_step(r"y = 2x + 3", r"x = \frac{y + 3}{2}")
    assert (r.status, r.method) == ("incorrect", "solved-for")


# --- honest "unknown" ------------------------------------------------------

@pytest.mark.parametrize("prev,curr,method", [
    (r"\frac{x", r"x", "parse"),
    (r"x \le 3", r"x \le 4", "unsupported"),
    (r"x + 1", r"x = 1", "mismatch"),
])
def test_unknown_cases(prev, curr, method):
    r = check_step(prev, curr)
    assert (r.status, r.method) == ("unknown", method)


def _slow():
    time.sleep(60)


def test_run_with_timeout_kills_slow_work():
    # Worker start-up isn't counted (it can take seconds on Windows), so we
    # only check that we return long before the 60 s sleep would end.
    t0 = time.perf_counter()
    status, _ = run_with_timeout(_slow, (), timeout=0.5)
    assert status == "timeout"
    assert time.perf_counter() - t0 < 30


def test_timeout_becomes_unknown(monkeypatch):
    monkeypatch.setattr(verifier, "run_with_timeout", lambda *a, **k: ("timeout", None))
    r = check_step(r"x + 41", r"x + 41", 1, 0.25)   # unique args, avoids the cache
    assert (r.status, r.method) == ("unknown", "timeout")


# --- whole derivations and hints --------------------------------------------

def test_check_derivation_chain():
    lines = [r"\frac{d}{dx} x^3 e^x", r"= 3x^2 e^x + x^3 e^x", r"= 3x^2 e^x"]
    assert [r.status for r in check_derivation(lines)] == ["start", "correct", "incorrect"]


def test_hint_leak_detected_even_when_written_differently():
    assert hint_reveals_answer(r"It simplifies to $\cos(x^2) \cdot 2x$.", r"2x\cos(x^2)")


def test_restating_the_question_is_not_a_leak():
    assert not hint_reveals_answer(r"Start again from $\frac{d}{dx}\sin(x^2)$.", r"2x\cos(x^2)")


def test_numeric_answer_leak():
    assert hint_reveals_answer(r"So you should get $2$.", r"x = 2")
    assert not hint_reveals_answer(r"What do you get if you divide both sides by $2$?", r"x = 7")


# --- API -------------------------------------------------------------------

def test_api():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"ok": True}

        steps = client.post("/verify", json={"lines": ["(x+1)^2", "= x^2 + 1"]}).json()["steps"]
        assert [s["status"] for s in steps] == ["start", "incorrect"]

        leak = client.post("/hint-check", json={"hint": "Try $x = 2$", "answer": "x = 2"}).json()
        assert leak == {"reveals_answer": True}

        assert client.post("/verify", json={"lines": []}).status_code == 422
