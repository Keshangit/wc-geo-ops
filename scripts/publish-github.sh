#!/usr/bin/env bash
# Create public GitHub repo and push (run after: gh auth login)
set -euo pipefail

REPO_NAME="${1:-wc-geo-ops}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! gh auth status >/dev/null 2>&1; then
  echo "Run: gh auth login"
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote origin already exists: $(git remote get-url origin)"
  git push -u origin main
else
  gh repo create "$REPO_NAME" \
    --public \
    --source=. \
    --remote=origin \
    --push \
    --description "GEO Operations API backend for WC GEO (quick + full audits)"
fi

echo "Done: https://github.com/$(gh api user -q .login)/${REPO_NAME}"
