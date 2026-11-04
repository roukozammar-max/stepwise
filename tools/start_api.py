"""Start the verifier API and open its test page in your browser.

    python tools/start_api.py

Run setup first (setup.bat on Windows, or python tools/setup_dev.py).
Stop it with Ctrl+C or by closing the window.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "verifier"
VENV_PYTHON = VERIFIER / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PORT = 8000
URL = f"http://127.0.0.1:{PORT}"

# Talk to our own server directly, never through a proxy.
_local = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _is_up() -> bool:
    try:
        with _local.open(f"{URL}/health", timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def main() -> int:
    if not VENV_PYTHON.exists():
        print("Stepwise isn't set up yet. Run setup.bat (Windows) or "
              "python tools/setup_dev.py first.")
        return 1
    if _is_up():
        print(f"The checker is already running. Opening {URL}/docs")
        webbrowser.open(f"{URL}/docs")
        return 0

    print("Starting the Stepwise checker (takes a few seconds)...\n", flush=True)
    server = subprocess.Popen(
        [str(VENV_PYTHON), "-m", "uvicorn", "api:app", "--port", str(PORT)],
        cwd=VERIFIER,
    )
    try:
        deadline = time.time() + 120
        while not _is_up():
            if server.poll() is not None:
                print("\nThe checker stopped before it was ready. "
                      "The error is in the messages above.")
                return 1
            if time.time() > deadline:
                print("\nThe checker didn't start within 2 minutes.")
                server.terminate()
                return 1
            time.sleep(0.5)

        print(f"\nReady. Test page: {URL}/docs (opening it in your browser)")
        print("Keep this window open while you use it. "
              "Press Ctrl+C or close the window to stop.\n", flush=True)
        webbrowser.open(f"{URL}/docs")
        return server.wait()
    except KeyboardInterrupt:
        server.terminate()
        server.wait(10)
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
