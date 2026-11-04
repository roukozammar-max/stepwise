"""Upload (push) Stepwise to its GitHub repository.

    python tools/publish_github.py https://github.com/<you>/stepwise.git \\
        [--name "Your Name" --email "id+you@users.noreply.github.com"]

On Windows, double-click publish-to-github.bat instead. Safe to run again
later: it saves (commits) what changed, brings in anything newer from GitHub,
then uploads. A log is written to publish-log.txt.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "publish-log.txt"
COMMIT_MESSAGE = (
    "Start Stepwise: step verifier, eval set, CI\n\n"
    "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
    "Claude-Session: https://claude.ai/code/session_01R7FGtFq6dqhdMHSe5KTj7g\n"
)
UPDATE_MESSAGE = (
    "Update Stepwise\n\n"
    "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
    "Claude-Session: https://claude.ai/code/session_01R7FGtFq6dqhdMHSe5KTj7g\n"
)
WINDOWS_GIT_PATHS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/cmd/git.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Git/cmd/git.exe",
]

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


def find_git() -> str | None:
    found = shutil.which("git")
    if found:
        return found
    for path in WINDOWS_GIT_PATHS:
        if path.is_file():
            return str(path)
    return None


def ask_yes(question: str) -> bool:
    answer = input(f"{question} [Y/n] ").strip().lower()
    log(f"{question} -> {answer!r}\n")
    return answer in ("", "y", "yes", "o", "oui")


class Git:
    def __init__(self, exe: str):
        self.exe = exe

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [self.exe, *args], cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        log(f"\n$ git {' '.join(args)}\n{result.stdout}{result.stderr}(exit {result.returncode})\n")
        if check and result.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed:\n{result.stderr.strip() or result.stdout.strip()}")
        return result

    def value(self, *args: str) -> str:
        return self.run(*args, check=False).stdout.strip()


def ensure_identity(git: Git, name: str | None, email: str | None) -> None:
    """Commits need an author name and email. Use the ones given (stored for
    this project only), else Git's own settings, else ask."""
    if name and email:
        git.run("config", "user.name", name)    # this project only
        git.run("config", "user.email", email)
        say(f"      Commits will be signed as: {name} <{email}>")
        return
    name = git.value("config", "user.name")
    email = git.value("config", "user.email")
    if name and email:
        say(f"      Commits will be signed as: {name} <{email}>")
        return
    say("      Git needs a name and email to label your saved versions (commits).")
    say("      Use the email of your GitHub account so they count on your GitHub profile.")
    while not name:
        name = input("      Your name: ").strip()
    while "@" not in email:
        email = input("      Your GitHub email: ").strip()
    git.run("config", "user.name", name)    # this project only
    git.run("config", "user.email", email)
    log(f"identity set for this repo: {name} <{email}>\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Stepwise to GitHub.")
    parser.add_argument("remote_url", help="e.g. https://github.com/<you>/stepwise.git")
    parser.add_argument("--name", help="author name for commits")
    parser.add_argument("--email", help="author email for commits")
    args = parser.parse_args()
    remote_url = args.remote_url
    page_url = remote_url.removesuffix(".git")
    LOG.write_text(f"Stepwise publish log\nRemote: {remote_url}\n", encoding="utf-8")

    say("[1/5] Checking the project files")
    if not (ROOT / "verifier" / "verifier.py").is_file():
        say("      This doesn't look like the Stepwise folder.")
        return 1
    say("      All there.")

    say("[2/5] Checking Git (the tool that uploads code to GitHub)")
    exe = find_git()
    if not exe and os.name == "nt" and shutil.which("winget"):
        say("      Git isn't installed.")
        if ask_yes("      Install Git now (about 2 minutes, Windows may ask for permission)?"):
            subprocess.run(["winget", "install", "-e", "--id", "Git.Git"])
            exe = find_git()
    if not exe:
        say("      Git isn't installed. Get it from https://git-scm.com/download/win")
        say("      (keep the default options), then run this again.")
        return 1
    git = Git(exe)
    say("      " + git.value("--version"))

    try:
        say("[3/5] Saving this version of the project (a 'commit')")
        if not (ROOT / ".git").is_dir():
            git.run("init")
        ensure_identity(git, args.name, args.email)
        git.run("add", "-A")
        files = git.value("ls-files").splitlines()
        if git.run("diff", "--cached", "--quiet", check=False).returncode != 0:
            first = git.run("rev-parse", "--verify", "HEAD", check=False).returncode != 0
            git.run("commit", "-m", COMMIT_MESSAGE if first else UPDATE_MESSAGE)
            say(f"      Saved {len(files)} files.")
        else:
            say("      Nothing changed since the last save.")
        git.run("branch", "-M", "main")

        say("[4/5] Connecting to your GitHub repository")
        current = git.value("remote", "get-url", "origin")
        if not current:
            git.run("remote", "add", "origin", remote_url)
        elif current != remote_url:
            git.run("remote", "set-url", "origin", remote_url)
        say(f"      {page_url}")

        # If GitHub has changes this computer doesn't (e.g. files added on the
        # website), bring them in first, otherwise GitHub refuses the upload.
        remote_main = git.run("ls-remote", "--heads", "origin", "main", check=False)
        if remote_main.returncode == 0 and remote_main.stdout.strip():
            git.run("fetch", "origin", "main")
            behind = git.value("rev-list", "--count", "HEAD..origin/main")
            if behind not in ("", "0"):
                say(f"      Bringing in {behind} newer change(s) from GitHub first.")
                git.run("pull", "--rebase", "origin", "main")
    except RuntimeError as error:
        say(f"\n{error}\n\nDetails are in {LOG}. Tell Claude \"publish failed\".")
        return 1

    say("[5/5] Uploading to GitHub")
    say("      If a GitHub sign-in window opens, sign in and click Authorize.")
    log("\n$ git push -u origin main   (interactive, output on screen only)\n")
    push = subprocess.run([exe, "push", "-u", "origin", "main"], cwd=ROOT)
    log(f"(exit {push.returncode})\n")
    if push.returncode != 0:
        say("")
        say("The upload didn't go through (see the message above).")
        say(f"Details are in {LOG}. Tell Claude \"publish failed\".")
        return 1

    say("")
    say("Done. Your project is on GitHub:")
    say(f"  {page_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
