# Claude Model Router

Automatic model routing for Claude Code. Each prompt is classified and handed to the cheapest model that can do the job well, from Haiku 5.5 up to Opus 5.5 at high effort, with OpenAI Codex (via your ChatGPT plan) as a fourth route.

## How it works

```
Your prompt
    |
    v
UserPromptSubmit hook (route_prompt.py)  -- scores keywords + length, logs decision
    |
    v  "tier = fast | standard | deep | codex"
Main Claude session (follows CLAUDE.md routing policy)
    |
    +--> router-fast      Haiku 5.5,  low effort     lookups, typos, renames
    +--> router-standard  Sonnet 5.5, medium effort  features, tests, ordinary bugs
    +--> router-deep      Opus 5.5,   high effort    architecture, refactors, hard bugs
    +--> codex-worker     OpenAI Codex (codex exec)  Codex/GPT requests, second opinions
```

Subagents escalate to a higher tier if a task turns out harder than classified. After a significant `router-deep` change, Codex does a read-only review when signed in.

## What's in the repo

| Path | Role |
|---|---|
| `.claude/hooks/route_prompt.py` | Classifies each prompt and injects the routing hint |
| `.claude/agents/*.md` | The four tier subagents (model + effort per tier) |
| `CLAUDE.md` | Routing policy the main session follows |
| `.claude/hooks/session_setup.sh` | Cloud sessions only: installs Superpowers, UI UX Pro Max, Composio skills and Codex CLI |
| `.claude/settings.json` | Registers both hooks |
| `tests/` | Classifier tests: `python3 -m unittest discover tests` |

## Setup

1. Start Claude Code sessions on this repo (cloud or local).
2. Cloud environment network access must allow `auth.openai.com`, `chatgpt.com` and `api.openai.com` for Codex.
3. Sign in to Codex once per session: ask Claude to "connect Codex". It runs `codex login --device-auth` and gives you a link and code to approve.

### Keeping the Codex sign-in across cloud sessions (optional)

Cloud containers are wiped between sessions. To skip signing in each time:

1. After signing in, run `base64 -w0 ~/.codex/auth.json`.
2. Add the output as an environment variable `CODEX_AUTH_JSON_B64` in the cloud environment settings.

The setup hook restores it on each start. This value grants access to your ChatGPT account, so only do this in an environment you alone use, and sign out (`codex logout`) and remove the variable if it leaks.

## Tuning

- Edit the pattern lists in `route_prompt.py` to change what counts as fast or deep.
- Review past decisions in `~/.claude/router-log.jsonl`.
- The main session runs on whatever model the session was started with. Starting it on Sonnet keeps orchestration cheap while Opus still handles deep tasks.

## Limits

- Routing is keyword-based, so it can misclassify. The main session may override an obviously wrong hint.
- Local sessions skip the setup hook unless `ROUTER_SETUP_LOCAL=1` is set; install plugins locally with `/plugin`.
- The 858 Composio skills add many skill descriptions to every session's context, and the app-automation ones need the Rube MCP server (`https://rube.app/mcp`).
