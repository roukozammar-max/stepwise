"""Set up Stepwise for development, then prove it works.

    python tools/setup_dev.py

Steps: create verifier/.venv, install the libraries, run the unit tests, run
the eval. Everything is also written to setup-log.txt in the project folder.
On Windows, double-clicking setup.bat finds Python and runs this for you.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "verifier"
VENV = VERIFIER / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
LOG = ROOT / "setup-log.txt"
MIN_PYTHON = (3, 10)

# Never crash on characters the Windows console can't display.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")
    except AttributeError:
        pass


def log(text: str) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(text)


def say(text: str = "") -> None:
    print(text, flush=True)
    log(text + "\n")


def run(cmd: list, cwd: Path, show: bool) -> tuple[int, list[str]]:
    """Run a command, stream its output to the log (and to the screen if
    show), and return (exit code, output lines)."""
    log(f"\n$ {' '.join(str(c) for c in cmd)}   (in {cwd})\n")
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(
        [str(c) for c in cmd], cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    lines = []
    for line in proc.stdout:
        lines.append(line)
        log(line)
        if show:
            print(line, end="", flush=True)
    return proc.wait(), lines


def fail(step: str, lines: list[str] | None = None) -> int:
    if lines:
        say("\n".join(["", "Last lines of output:"] + [l.rstrip() for l in lines[-15:]]))
    say("")
    say(f"Setup stopped at: {step}")
    say(f"Full details are in {LOG}")
    say("Tell Claude \"setup failed\" and it can read the log.")
    return 1


def main() -> int:
    LOG.write_text(
        f"Stepwise setup log, {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Python {sys.version.split()[0]} at {sys.executable}\n"
        f"{platform.platform()}\n",
        encoding="utf-8",
    )

    say("[1/5] Checking Python")
    say(f"      Python {sys.version.split()[0]} ({sys.executable})")
    if sys.version_info < MIN_PYTHON:
        say(f"      Stepwise needs Python {'.'.join(map(str, MIN_PYTHON))} or newer.")
        return fail("checking Python")

    say("[2/5] Creating the project's private Python space (verifier/.venv)")
    if VENV_PYTHON.exists():
        say("      Already there, keeping it.")
    else:
        code, lines = run([sys.executable, "-m", "venv", VENV], ROOT, show=False)
        if code != 0 or not VENV_PYTHON.exists():
            return fail("creating .venv", lines)
        say("      Done.")

    say("[3/5] Installing the libraries (1-3 minutes)")
    code, lines = run(
        [VENV_PYTHON, "-m", "pip", "install", "--disable-pip-version-check",
         "-r", VERIFIER / "requirements.txt"],
        VERIFIER, show=False,
    )
    if code != 0:
        return fail("installing the libraries", lines)
    say("      Done.")

    say("[4/5] Running the 20 safety checks (about 1 minute on Windows)")
    code, lines = run([VENV_PYTHON, "-m", "pytest", "-q"], VERIFIER, show=True)
    if code != 0:
        return fail("the safety checks (tests)")

    say("[5/5] Running the accuracy quiz: 46 maths steps (about 1 minute on Windows)")
    code, lines = run([VENV_PYTHON, "eval.py"], VERIFIER, show=True)
    if code != 0:
        return fail("the accuracy quiz (eval)")

    say("")
    say("All done. Stepwise works on this computer.")
    if os.name == "nt":
        say("Next: double-click start-api.bat to try it in your browser.")
    else:
        say("Next: run  python tools/start_api.py  to try it in your browser.")
    return 0


if __name__ == "__main__":  # required: the tests start worker processes
    sys.exit(main())
