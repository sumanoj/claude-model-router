#!/usr/bin/env python3
"""UserPromptSubmit hook: classify each prompt into a model tier.

Reads the hook payload from stdin, scores the prompt with simple keyword and
length heuristics, and returns a routing hint as additionalContext. The main
agent then delegates the work to the matching subagent (see CLAUDE.md).

Tiers:
  fast      -> router-fast     (Haiku 5.5, low effort)
  standard  -> router-standard (Sonnet 5.5, medium effort)
  deep      -> router-deep     (Opus 5.5, high effort)
  codex     -> codex-worker    (OpenAI Codex via ChatGPT login)

Every decision is appended to ~/.claude/router-log.jsonl for review, shown to
the user as a systemMessage, and saved to ~/.claude/router-state/<session>.json
for the status line (statusline.py).
"""
import json
import os
import re
import sys
import time

# Signals that a task needs deep reasoning (Opus, high effort).
DEEP_PATTERNS = [
    r"\barchitect(ure)?\b", r"\bdesign (a|an|the)\b", r"\bsystem design\b",
    r"\brefactor\b", r"\bmigrat(e|ion)\b", r"\bsecurity\b", r"\bvulnerab",
    r"\brace condition\b", r"\bdeadlock\b", r"\bconcurren", r"\bdistributed\b",
    r"\broot cause\b", r"\bperformance\b", r"\boptimi[sz]e\b", r"\bscal(e|ing|able)\b",
    r"\bimplementation plan\b", r"\bplan (out|for)\b", r"\btrade-?offs?\b",
    r"\bproduction\b", r"\bacross (the|all|multiple)\b", r"\bentire (codebase|repo)\b",
    r"\bintermittent\b", r"\bflaky\b", r"\bmemory leak\b", r"\balgorithm\b",
    r"\brag\b", r"\bpipeline\b",
]

# Signals that a task is small and mechanical (Haiku, low effort).
FAST_PATTERNS = [
    r"\btypo\b", r"\brename\b", r"\bformat(ting)?\b", r"\blint\b",
    r"\bwhat is\b", r"\bwhat does\b", r"\bwhere is\b", r"\bfind\b", r"\bgrep\b",
    r"\blist\b", r"\bsummari[sz]e\b", r"\bcount\b", r"\bshow me\b",
    r"\bcomment\b", r"\bdocstring\b", r"\bbump\b", r"\bversion\b",
]

# Verbs that mean "build or change something". A short prompt with one of
# these and no fast keyword is ordinary engineering, not a quick lookup.
WORK_PATTERNS = [
    r"\badd\b", r"\bimplement\b", r"\bwrite\b", r"\bcreate\b", r"\bbuild\b",
    r"\bfix\b", r"\bupdate\b", r"\bendpoint\b", r"\btests?\b", r"\bfeature\b",
]

# Signals that the user wants OpenAI Codex specifically.
CODEX_PATTERNS = [
    r"\bcodex\b", r"\bgpt-?\d", r"\bopenai\b", r"\bsecond opinion\b",
    r"\bcross-?check\b",
]


def count_hits(patterns, text):
    return sum(1 for p in patterns if re.search(p, text))


def classify(prompt):
    """Return (tier, reason) for a prompt."""
    text = prompt.lower()
    length = len(prompt)

    codex_hits = count_hits(CODEX_PATTERNS, text)
    if codex_hits:
        return "codex", f"{codex_hits} Codex/OpenAI signal(s)"

    deep = count_hits(DEEP_PATTERNS, text)
    fast = count_hits(FAST_PATTERNS, text)
    work = count_hits(WORK_PATTERNS, text)

    # Long prompts usually carry multi-step requirements.
    if length > 800:
        deep += 2
    elif length > 300:
        deep += 1
    elif length < 120 and (fast or not work):
        fast += 1

    # Several code blocks or file paths suggest multi-file work.
    if prompt.count("```") >= 4 or len(re.findall(r"\b[\w/.-]+\.\w{1,5}\b", prompt)) >= 4:
        deep += 1

    if deep >= 2 and deep > fast:
        return "deep", f"deep={deep} fast={fast} len={length}"
    if fast > deep and deep == 0:
        return "fast", f"deep={deep} fast={fast} len={length}"
    return "standard", f"deep={deep} fast={fast} len={length}"


AGENT_FOR_TIER = {
    "fast": "router-fast",
    "standard": "router-standard",
    "deep": "router-deep",
    "codex": "codex-worker",
}


MODEL_FOR_TIER = {
    "fast": "Haiku 5.5, low effort",
    "standard": "Sonnet 5.5, medium effort",
    "deep": "Opus 5.5, high effort",
    "codex": "OpenAI Codex",
}


def log_decision(tier, reason, prompt, session_id=""):
    path = os.path.expanduser("~/.claude/router-log.jsonl")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "event": "classified",
                "session": session_id,
                "tier": tier,
                "reason": reason,
                "prompt_preview": prompt[:120],
            }) + "\n")
    except OSError:
        pass  # logging must never block a prompt


def save_state(session_id, tier):
    """Record the latest classification for the status line. Clears 'ran'."""
    if not session_id:
        return
    safe_id = re.sub(r"[^\w-]", "_", session_id)
    path = os.path.expanduser(f"~/.claude/router-state/{safe_id}.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"tier": tier, "expected": AGENT_FOR_TIER[tier], "ran": []}, f)
    except OSError:
        pass


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = payload.get("prompt") or ""
    if not prompt.strip():
        return 0
    # Background subagent results come back through this hook as
    # <task-notification> messages. They are not user prompts: classifying
    # them would show a false tier and reset the status line.
    if prompt.lstrip().startswith("<task-notification>"):
        return 0

    session_id = payload.get("session_id") or ""
    tier, reason = classify(prompt)
    log_decision(tier, reason, prompt, session_id)
    save_state(session_id, tier)

    context = (
        f"Model router: this prompt is classified as tier '{tier}' ({reason}). "
        f"The matching subagent is '{AGENT_FOR_TIER[tier]}'. "
        "Routing policy is in CLAUDE.md under 'Model routing'."
    )
    print(json.dumps({
        "systemMessage": f"Router: {tier} -> {AGENT_FOR_TIER[tier]} ({MODEL_FOR_TIER[tier]})",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
