"""Start Stepwise on this computer and open the board in your browser.

    python tools/start_web.py        (Windows: double-click start-stepwise.bat)

Starts two programs and keeps them running until you press Ctrl+C or close
the window:
  - the checker (verifier API) on http://127.0.0.1:8000
  - the web app (Next.js dev server) on http://localhost:3000

First run: installs Node.js if it's missing (asks first) and the web app's
libraries (`npm ci`, 1-3 minutes). Everything shown is also written to
start-log.txt, which helps when something goes wrong.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "verifier"
WEB = ROOT / "web"
LOG = ROOT / "start-log.txt"
VENV_PYTHON = VERIFIER / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
API_URL = "http://127.0.0.1:8000"
WEB_URL = "http://localhost:3000"
MIN_NODE = (20, 9)
NODE_DIRS = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs"]

_local = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_log_lock = threading.Lock()

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")
    except AttributeError:
        pass


def say(text: str = "") -> None:
    with _log_lock:
        print(text, flush=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(text + "\n")


def fetch(url: str, timeout: float = 3) -> str | None:
    try:
        with _local.open(url, timeout=timeout) as response:
            return response.read().decode("utf-8", "replace") if response.status == 200 else None
    except OSError:
        return None


def ask_yes(question: str) -> bool:
    try:
        answer = input(f"{question} [Y/n] ").strip().lower()
    except EOFError:
        return False
    return answer in ("", "y", "yes", "o", "oui")


# --- Node.js ---------------------------------------------------------------

def find_node() -> Path | None:
    found = shutil.which("node")
    if found:
        return Path(found)
    for folder in NODE_DIRS:
        exe = folder / ("node.exe" if os.name == "nt" else "node")
        if exe.is_file():
            return exe
    return None


def node_version(node: Path) -> tuple[int, int]:
    out = subprocess.run([str(node), "--version"], capture_output=True, text=True).stdout
    match = re.match(r"v(\d+)\.(\d+)", out.strip())
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def ensure_node() -> Path | None:
    node = find_node()
    if node and node_version(node) >= MIN_NODE:
        return node
    if node:
        say(f"      Node.js {'.'.join(map(str, node_version(node)))} is too old "
            f"(need {MIN_NODE[0]}.{MIN_NODE[1]} or newer).")
    else:
        say("      Node.js isn't installed. The web app needs it.")
    if os.name == "nt" and shutil.which("winget"):
        if ask_yes("      Install Node.js (LTS) now? About 2 minutes; Windows may ask for permission."):
            subprocess.run(["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS"])
            node = find_node()
            if node and node_version(node) >= MIN_NODE:
                return node
    say("      Install Node.js LTS from https://nodejs.org (keep the default options),")
    say("      then run this again.")
    return None


def npm_command(node: Path) -> list[str]:
    npm = node.parent / ("npm.cmd" if os.name == "nt" else "npm")
    return [str(npm)] if npm.exists() else [shutil.which("npm") or "npm"]


def libraries_up_to_date() -> bool:
    marker = WEB / "node_modules" / ".package-lock.json"
    lock = WEB / "package-lock.json"
    return marker.is_file() and marker.stat().st_mtime >= lock.stat().st_mtime


# --- running the two programs ----------------------------------------------

def pipe_output(proc: subprocess.Popen, prefix: str) -> None:
    for line in proc.stdout:
        say(f"{prefix} {line.rstrip()}")


def start(cmd: list[str], cwd: Path, env: dict, prefix: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    threading.Thread(target=pipe_output, args=(proc, prefix), daemon=True).start()
    return proc


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":  # also stop the programs it started
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()


def wait_until(check, seconds: float, processes: list[subprocess.Popen]) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check():
            return True
        if any(p.poll() is not None for p in processes):
            return False
        time.sleep(0.5)
    return False


def main() -> int:
    LOG.write_text(f"Stepwise start log, {time.strftime('%Y-%m-%d %H:%M:%S')}\n", encoding="utf-8")

    say("[1/4] Checking the checker's Python setup")
    if not VENV_PYTHON.exists():
        say("      Not set up yet. Double-click setup.bat (or run tools/setup_dev.py) first.")
        return 1
    say("      OK.")

    say("[2/4] Checking Node.js (runs the web app)")
    node = ensure_node()
    if not node:
        return 1
    say(f"      Node.js {'.'.join(map(str, node_version(node)))}")
    env = dict(os.environ, NEXT_TELEMETRY_DISABLED="1")
    env["PATH"] = str(node.parent) + os.pathsep + env.get("PATH", "")

    say("[3/4] Checking the web app's libraries")
    if libraries_up_to_date():
        say("      Up to date.")
    else:
        say("      Installing (first time or after an update: 1-3 minutes)...")
        result = subprocess.run(npm_command(node) + ["ci", "--no-audit", "--no-fund"], cwd=WEB, env=env)
        if result.returncode != 0:
            say("      Installing the libraries failed (see the messages above).")
            return 1
    if not (WEB / "public" / "mathlive" / "fonts").is_dir():
        subprocess.run([str(node), "scripts/copy-mathlive-assets.mjs"], cwd=WEB, env=env)

    say("[4/4] Starting the checker and the web app")
    processes: list[subprocess.Popen] = []
    try:
        if fetch(f"{API_URL}/health"):
            say("      The checker is already running.")
        else:
            processes.append(start(
                [str(VENV_PYTHON), "-m", "uvicorn", "api:app", "--port", "8000"],
                VERIFIER, env, "[checker]"))
        page = fetch(WEB_URL)
        if page and "Stepwise" in page:
            say("      The web app is already running.")
        else:
            next_bin = WEB / "node_modules" / "next" / "dist" / "bin" / "next"
            processes.append(start([str(node), str(next_bin), "dev", "-p", "3000"], WEB, env, "[web]"))

        if not wait_until(lambda: fetch(f"{API_URL}/health") is not None, 120, processes):
            say("\nThe checker didn't start. The reason is in the messages above (also in start-log.txt).")
            return 1
        say("      The checker is ready. Preparing the web page (first time: up to a minute)...")
        if not wait_until(lambda: fetch(WEB_URL, timeout=90) is not None, 240, processes):
            say("\nThe web app didn't start. The reason is in the messages above (also in start-log.txt).")
            return 1

        say("")
        say(f"Stepwise is running: {WEB_URL}  (opening it in your browser)")
        say("Keep this window open while you use it. Press Ctrl+C or close it to stop.")
        say("")
        webbrowser.open(WEB_URL)
        while processes and all(p.poll() is None for p in processes):
            time.sleep(1)
        if not processes:  # both were already running in another window
            return 0
        say("\nOne of the programs stopped. The reason is in the messages above.")
        return 1
    except KeyboardInterrupt:
        say("\nStopping...")
        return 0
    finally:
        for proc in processes:
            stop(proc)


if __name__ == "__main__":
    sys.exit(main())
