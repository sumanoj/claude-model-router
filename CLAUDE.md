# Claude Model Router

This repo is a Claude Code plugin marketplace. The router itself is the `model-router` plugin in `plugins/model-router/`.

## Layout

- `.claude-plugin/marketplace.json`: marketplace manifest listing the plugin.
- `plugins/model-router/`: the plugin.
  - `agents/`: the four tier subagents. Plugin agents are namespaced, so they are called as `model-router:router-fast` and so on.
  - `hooks/hooks.json`: registers the hooks below.
  - `scripts/session_start.py`: injects `routing_policy.md`, copies the status line helpers to `~/.claude/model-router/`, restores the Codex sign-in.
  - `scripts/route_prompt.py`: classifies each prompt.
  - `scripts/track_delegation.py`: records which subagent actually ran.
  - `scripts/statusline.py`, `scripts/router_stats.py`: the status line and report.
  - `routing_policy.md`: the routing rules every session receives. Edit this, not this file, to change routing behavior.
- `cloud-setup.sh`: cloud environment setup script.
- `tests/`: `python3 -m unittest discover tests`.

## Working on the plugin

- Run the tests after any change to `scripts/`.
- Validate with `claude plugin validate .` and `claude plugin validate plugins/model-router`.
- Bump `version` in `plugins/model-router/.claude-plugin/plugin.json` for each release, or installed copies will not update.
- To try local changes without installing: `claude --plugin-dir plugins/model-router`.
