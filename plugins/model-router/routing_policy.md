# Model router policy

The model-router plugin is active. Before each user prompt, a hook adds a hint like "Model router: this prompt is classified as tier 'deep' ... The matching subagent is 'model-router:router-deep'".

Follow the hint and delegate the work to the matching subagent:

| Tier | Subagent | Model | Use for |
|---|---|---|---|
| fast | `model-router:router-fast` | Haiku 5.5, low effort | lookups, typos, renames, formatting, short answers |
| standard | `model-router:router-standard` | Sonnet 5.5, medium effort | features, tests, ordinary bugs, docs |
| deep | `model-router:router-deep` | Opus 5.5, high effort | architecture, refactors, migrations, security, hard bugs, plans |
| codex | `model-router:codex-worker` | OpenAI Codex (ChatGPT plan) | anything mentioning Codex/GPT/OpenAI, second opinions |

Rules:
- Pass the subagent the full task and any context it needs. It does not see this conversation.
- If a subagent replies "Escalate to router-standard" or "Escalate to router-deep", re-run the task on that tier.
- Override the hint only when it is clearly wrong (for example a short prompt that asks for a full system design). Say which tier you used and why in one line.
- Trivial conversational replies (thanks, yes/no answers about your last message) need no delegation.
- After `model-router:router-deep` finishes a significant code change, and Codex is signed in, ask `model-router:codex-worker` for a read-only review and relay any real issues it finds.
- If the user asks for the router status, run `python3 ~/.claude/model-router/router_stats.py` and show the output.

## Connecting Codex

If the user asks to "connect Codex":
1. Run `codex login --device-auth` in the background, writing output to a file.
2. Read the file and give the user the sign-in link and one-time code.
3. When the command finishes, confirm with `codex login status`.
