#!/usr/bin/env python3
"""SessionStart hook: prepare the model router for this session.

1. Injects the routing policy (routing_policy.md) as additionalContext. Plugins
   cannot ship a CLAUDE.md, so this is how every project learns the policy.
   It runs on startup, resume, clear and compact so the policy survives
   context compaction.
2. Copies statusline.py and router_stats.py to ~/.claude/model-router/ so the
   status line and the stats report have a fixed path across plugin updates.
3. Restores a Codex sign-in saved as CODEX_AUTH_JSON_B64 (see README).
4. Shows a one-line systemMessage with the router and Codex status.

Every step is best effort: a failure is reported, never fatal.
"""
import base64
import binascii
import json
import os
import shutil
import subprocess
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME_DIR = os.path.expanduser("~/.claude/model-router")


def install_helpers():
    os.makedirs(HOME_DIR, exist_ok=True)
    for name in ("statusline.py", "router_stats.py"):
        shutil.copy2(os.path.join(PLUGIN_ROOT, "scripts", name), os.path.join(HOME_DIR, name))


def restore_codex_auth():
    """Return a short note if a sign-in was restored or failed, else ''."""
    data = os.environ.get("CODEX_AUTH_JSON_B64")
    path = os.path.expanduser("~/.codex/auth.json")
    if not data or os.path.exists(path):
        return ""
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return "Codex sign-in restore failed: CODEX_AUTH_JSON_B64 is not valid base64"
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return "Codex sign-in restored"


def codex_status():
    if not shutil.which("codex"):
        return "Codex CLI not installed"
    try:
        ok = subprocess.run(["codex", "login", "status"], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    return "Codex signed in" if ok else "Codex not signed in (say 'connect Codex')"


def main():
    notes = []
    try:
        install_helpers()
    except OSError as e:
        notes.append(f"status line helpers not copied: {e}")
    try:
        note = restore_codex_auth()
    except OSError as e:
        note = f"Codex sign-in restore failed: {e}"
    if note:
        notes.append(note)
    notes.append(codex_status())

    try:
        with open(os.path.join(PLUGIN_ROOT, "routing_policy.md")) as f:
            policy = f.read()
    except OSError:
        policy = ""

    out = {"systemMessage": "Model router active. " + ". ".join(notes) + "."}
    if policy:
        out["hookSpecificOutput"] = {"hookEventName": "SessionStart", "additionalContext": policy}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
