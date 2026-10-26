#!/usr/bin/env python3
"""Status line for Claude Code: shows the router's latest decision.

Example output:
  Opus 5.5 | router: deep -> router-deep | ran: router-deep (ok)

"ran" lists the subagents launched since the last prompt. "(ok)" means the
last one matches the hint, "(override)" means the main session picked a
different tier, and "waiting" means nothing has been delegated yet.
"""
import json
import os
import re
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    model = (payload.get("model") or {}).get("display_name") or "?"
    session_id = payload.get("session_id") or ""

    state = {}
    if session_id:
        safe_id = re.sub(r"[^\w-]", "_", session_id)
        try:
            with open(os.path.expanduser(f"~/.claude/router-state/{safe_id}.json")) as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}

    if not state:
        print(f"{model} | router: no prompt classified yet")
        return 0

    ran = state.get("ran") or []
    if not ran:
        result = "waiting"
    else:
        verdict = "ok" if ran[-1] == state.get("expected") else "override"
        result = f"{', '.join(ran)} ({verdict})"
    print(f"{model} | router: {state.get('tier')} -> {state.get('expected')} | ran: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
