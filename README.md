# Claude Model Router

A Claude Code plugin that routes each prompt to the cheapest model that can do the job well, from Haiku 5.5 up to Opus 5.5 at high effort, with OpenAI Codex (via your ChatGPT plan) as a fourth route. Install it once and it works in every project.

## How it works

```
Your prompt
    |
    v
UserPromptSubmit hook (route_prompt.py)  -- scores keywords + length, logs decision
    |
    v  "tier = fast | standard | deep | codex"
Main Claude session (follows the routing policy injected at session start)
    |
    +--> router-fast      Haiku 5.5,  low effort     lookups, typos, renames
    +--> router-standard  Sonnet 5.5, medium effort  features, tests, ordinary bugs
    +--> router-deep      Opus 5.5,   high effort    architecture, refactors, hard bugs
    +--> codex-worker     OpenAI Codex (codex exec)  Codex/GPT requests, second opinions
```

Subagents escalate to a higher tier if a task turns out harder than classified. After a significant `router-deep` change, Codex does a read-only review when signed in.

## Install

### On your computer (terminal CLI)

Run once, inside any Claude Code session:

```
/plugin install model-router --marketplace sumanoj/claude-model-router
```

On Claude Code older than 2.1.275, use two steps instead:

```
/plugin marketplace add sumanoj/claude-model-router
/plugin install model-router@claude-model-router
```

Optional extras:

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill
```

For Codex: `npm install -g @openai/codex`.

For the status line, add this to `~/.claude/settings.json` (the plugin keeps the file up to date each session):

```json
"statusLine": {"type": "command", "command": "python3 ~/.claude/model-router/statusline.py"}
```

### In cloud sessions (Claude app, claude.ai/code)

Cloud containers start fresh every session, so the install goes in the environment's setup script:

1. Open the environment menu in a session's title bar, then **Edit**.
2. Under **Setup script**, add:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/sumanoj/claude-model-router/main/cloud-setup.sh | bash
   ```
3. Save. Every new session in that environment, on any repo, gets the router, Superpowers, UI UX Pro Max and the Codex CLI.

Cloud environment network access must allow `auth.openai.com`, `chatgpt.com` and `api.openai.com` for Codex.

### Codex sign-in

Ask Claude to "connect Codex" once per session. It runs `codex login --device-auth` and gives you a link and code to approve.

To keep the sign-in across cloud sessions:

1. After signing in, run `base64 -w0 ~/.codex/auth.json`.
2. Add the output as an environment variable `CODEX_AUTH_JSON_B64` in the cloud environment settings.

The plugin restores it at the start of each session. This value grants access to your ChatGPT account, so only do this in an environment you alone use, and sign out (`codex logout`) and remove the variable if it leaks.

## Checking that routing works

1. **Session start**: `Model router active. Codex signed in.` (or why not).
2. **Every prompt**: `Router: deep -> model-router:router-deep (Opus 5.5, high effort)`, then when a subagent starts, `Router: delegated to model-router:router-deep (matches hint)` or `(hint was ...)`.
3. **Status line** (terminal): `Sonnet 5.5 | router: deep -> router-deep | ran: router-deep (ok)`. `waiting` means nothing delegated yet; `override` means a different agent was used.
4. **Report**: ask Claude for "router status", or run `python3 ~/.claude/model-router/router_stats.py`.

No `Router:` line at all means the plugin is not installed or not enabled: check `/plugin`.

## What's in the repo

| Path | Role |
|---|---|
| `.claude-plugin/marketplace.json` | Makes this repo a plugin marketplace |
| `plugins/model-router/agents/` | The four tier subagents (model + effort per tier) |
| `plugins/model-router/hooks/hooks.json` | Registers the hooks |
| `plugins/model-router/scripts/session_start.py` | Injects the routing policy, installs status line helpers, restores Codex sign-in |
| `plugins/model-router/scripts/route_prompt.py` | Classifies each prompt and shows the decision |
| `plugins/model-router/scripts/track_delegation.py` | Records which subagent actually ran |
| `plugins/model-router/scripts/statusline.py` | Status line |
| `plugins/model-router/scripts/router_stats.py` | Report from the routing log |
| `plugins/model-router/routing_policy.md` | The rules every session follows |
| `cloud-setup.sh` | Cloud environment setup script |
| `tests/` | `python3 -m unittest discover tests` |

## Tuning

- Edit the pattern lists in `route_prompt.py` to change what counts as fast or deep.
- Edit `routing_policy.md` to change how the main session follows the hints.
- Bump `version` in `plugins/model-router/.claude-plugin/plugin.json` when you release changes; then `/plugin marketplace update claude-model-router` picks them up.
- Review past decisions in `~/.claude/router-log.jsonl`.
- The main session runs on whatever model the session was started with. Starting it on Sonnet keeps orchestration cheap while Opus still handles deep tasks.

## Limits

- Routing is keyword-based, so it can misclassify. The main session may override an obviously wrong hint.
- The router runs in every project once installed. To turn it off for one project, add `"enabledPlugins": {"model-router@claude-model-router": false}` to that project's `.claude/settings.json`.
- Plugins cannot set the status line, so that one line is a manual step in `~/.claude/settings.json`.
