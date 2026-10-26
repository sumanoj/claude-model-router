#!/usr/bin/env bash
# SessionStart hook: installs the tools this repo depends on.
#   1. Superpowers and UI UX Pro Max plugins
#   2. Composio awesome-claude-skills (general + app-automation skills)
#   3. Codex CLI, plus ChatGPT sign-in restored from CODEX_AUTH_JSON_B64 if set
# Every step is idempotent and failures are reported, never fatal.

LOG="$HOME/.claude/session-setup.log"
mkdir -p "$HOME/.claude/skills"
: > "$LOG"
note() { echo "$*" | tee -a "$LOG" >&2; }

# Only cloud sessions start from a blank container. Locally, set
# ROUTER_SETUP_LOCAL=1 to run this anyway.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ] && [ "${ROUTER_SETUP_LOCAL:-}" != "1" ]; then
  exit 0
fi

# --- 1. Plugins ------------------------------------------------------------
install_plugin() {  # $1 = marketplace repo, $2 = plugin@marketplace
  if claude plugin list 2>/dev/null | grep -q "$2"; then
    return 0
  fi
  claude plugin marketplace add "$1" >>"$LOG" 2>&1
  if claude plugin install "$2" >>"$LOG" 2>&1; then
    note "plugin installed: $2"
  else
    note "plugin FAILED: $2 (see $LOG)"
  fi
}
install_plugin obra/superpowers-marketplace superpowers@superpowers-marketplace
install_plugin nextlevelbuilder/ui-ux-pro-max-skill ui-ux-pro-max@ui-ux-pro-max-skill

# --- 2. Composio skills ----------------------------------------------------
# Skipped: skill-creator and template-skill (a built-in version exists / empty).
if [ ! -d "$HOME/.claude/skills/changelog-generator" ]; then
  tmp=$(mktemp -d)
  if git clone -q --depth 1 https://github.com/ComposioHQ/awesome-claude-skills.git "$tmp/acs" >>"$LOG" 2>&1; then
    n=0
    for d in "$tmp"/acs/*/ "$tmp"/acs/composio-skills/*/; do
      name=$(basename "$d")
      case "$name" in skill-creator|template-skill) continue ;; esac
      [ -f "$d/SKILL.md" ] || continue
      [ -e "$HOME/.claude/skills/$name" ] && continue
      cp -r -- "$d" "$HOME/.claude/skills/" && n=$((n + 1))
    done
    note "composio skills installed: $n"
  else
    note "composio skills FAILED: clone error"
  fi
  rm -rf "$tmp"
fi

# --- 3. Codex CLI ----------------------------------------------------------
if ! command -v codex >/dev/null 2>&1; then
  if npm install -g @openai/codex >>"$LOG" 2>&1; then
    note "codex installed: $(codex --version 2>/dev/null)"
  else
    note "codex install FAILED"
  fi
fi

# Restore a ChatGPT sign-in saved as an environment secret (see README).
if [ -n "${CODEX_AUTH_JSON_B64:-}" ] && [ ! -f "$HOME/.codex/auth.json" ]; then
  mkdir -p "$HOME/.codex" && chmod 700 "$HOME/.codex"
  if echo "$CODEX_AUTH_JSON_B64" | base64 -d > "$HOME/.codex/auth.json" 2>/dev/null; then
    chmod 600 "$HOME/.codex/auth.json"
    note "codex sign-in restored from CODEX_AUTH_JSON_B64"
  else
    rm -f "$HOME/.codex/auth.json"
    note "codex sign-in restore FAILED: CODEX_AUTH_JSON_B64 is not valid base64"
  fi
fi

if command -v codex >/dev/null 2>&1; then
  if codex login status >/dev/null 2>&1; then
    echo "Codex: signed in."
  else
    echo "Codex: installed but not signed in. Ask Claude to 'connect Codex' to sign in with ChatGPT."
  fi
fi
exit 0
