#!/usr/bin/env python3
"""Summarize ~/.claude/router-log.jsonl.

Usage:
  python3 router_stats.py            # summary + last 10 events
  python3 router_stats.py --last 30  # show more recent events
  python3 router_stats.py --log path/to/router-log.jsonl
"""
import argparse
import json
import os
from collections import Counter


def load(path):
    events = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", default=os.path.expanduser("~/.claude/router-log.jsonl"))
    parser.add_argument("--last", type=int, default=10)
    args = parser.parse_args()

    events = load(args.log)
    if not events:
        print(f"No router events in {args.log}. Send a prompt in a session on this repo first.")
        return 0

    # Older log lines have no "event" field; they are all classifications.
    classified = [e for e in events if e.get("event", "classified") == "classified"]
    delegated = [e for e in events if e.get("event") == "delegated"]

    print(f"Prompts classified: {len(classified)}")
    for tier, n in Counter(e.get("tier") for e in classified).most_common():
        print(f"  {tier:<9} {n:>5}  ({100 * n / len(classified):.0f}%)")

    print(f"\nSubagent runs: {len(delegated)}")
    for agent, n in Counter(e.get("agent") for e in delegated).most_common():
        print(f"  {agent:<16} {n:>5}")
    judged = [e for e in delegated if e.get("match") is not None]
    if judged:
        hits = sum(1 for e in judged if e["match"])
        print(f"  followed hint: {hits}/{len(judged)} ({100 * hits / len(judged):.0f}%)")

    print(f"\nLast {args.last} events:")
    for e in events[-args.last:]:
        if e.get("event") == "delegated":
            tag = "ok" if e.get("match") else ("no hint" if e.get("match") is None else f"hint was {e.get('expected')}")
            print(f"  {e.get('ts')}  ran        {e.get('agent')} ({tag})")
        else:
            print(f"  {e.get('ts')}  classified {e.get('tier'):<8} {e.get('prompt_preview', '')[:60]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
