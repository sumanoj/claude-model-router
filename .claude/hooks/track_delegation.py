#!/usr/bin/env python3
"""PreToolUse hook (Agent/Task tool): record which subagent actually ran.

route_prompt.py only records the tier it recommended. This hook records the
subagent the main session really delegated to, so you can check that the hint
was followed. It never blocks the tool call.

For each delegation it:
  - appends a "delegated" event to ~/.claude/router-log.jsonl
  - adds the agent to ~/.claude/router-state/<session>.json (status line)
  - shows a one-line systemMessage saying whether it matches the hint
"""
import json
import os
import re
import sys
import time


def state_path(session_id):
    safe_id = re.sub(r"[^\w-]", "_", session_id)
    return os.path.expanduser(f"~/.claude/router-state/{safe_id}.json")


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in ("Agent", "Task"):
        return 0

    agent = (payload.get("tool_input") or {}).get("subagent_type") or "general-purpose"
    session_id = payload.get("session_id") or ""

    # Read the hint for this session and append the agent that ran.
    state = {}
    if session_id:
        path = state_path(session_id)
        try:
            with open(path) as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
        state.setdefault("ran", []).append(agent)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(state, f)
        except OSError:
            pass

    expected = state.get("expected")
    match = expected == agent if expected else None

    try:
        log = os.path.expanduser("~/.claude/router-log.jsonl")
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a") as f:
            f.write(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "event": "delegated",
                "session": session_id,
                "agent": agent,
                "expected": expected,
                "match": match,
            }) + "\n")
    except OSError:
        pass  # logging must never block a tool call

    if expected is None:
        note = "no router hint for this prompt"
    elif match:
        note = "matches hint"
    else:
        note = f"hint was {expected}"
    print(json.dumps({"systemMessage": f"Router: delegated to {agent} ({note})"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
