#!/usr/bin/env bash
# Cloud environment setup script for the model router.
#
# Paste this into your cloud environment's settings (environment menu in the
# session title bar > Edit > Setup script), or have the setup script run:
#   curl -fsSL https://raw.githubusercontent.com/sumanoj/claude-model-router/main/cloud-setup.sh | bash
#
# It installs, at user scope so every repo in the environment gets them:
#   1. the model-router plugin (this repo's marketplace)
#   2. Superpowers and UI UX Pro Max plugins
#   3. the Codex CLI
# Codex sign-in is restored by the plugin's SessionStart hook, because setup
# scripts cannot read the environment's saved variables.
# Every step is idempotent; failures are reported but do not stop the script.

install_plugin() {  # $1 = marketplace repo, $2 = plugin@marketplace
  if claude plugin list 2>/dev/null | grep -q "$2"; then
    echo "plugin already installed: $2"
    return 0
  fi
  claude plugin marketplace add "$1" || true
  if claude plugin install "$2" --scope user; then
    echo "plugin installed: $2"
  else
    echo "plugin FAILED: $2" >&2
  fi
}

install_plugin sumanoj/claude-model-router model-router@claude-model-router
install_plugin obra/superpowers-marketplace superpowers@superpowers-marketplace
install_plugin nextlevelbuilder/ui-ux-pro-max-skill ui-ux-pro-max@ui-ux-pro-max-skill

if ! command -v codex >/dev/null 2>&1; then
  npm install -g @openai/codex && echo "codex installed: $(codex --version 2>/dev/null)" \
    || echo "codex install FAILED" >&2
fi
exit 0
