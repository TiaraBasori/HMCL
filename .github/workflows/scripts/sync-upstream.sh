#!/usr/bin/env bash
# Sync this fork with HMCL-dev/HMCL from a local checkout.
#
# Design: main is a *plain* upstream mirror plus fork-only workflow files (README, release config).
# No source patching happens on main anymore — the Release workflow applies
# .github/workflows/patches/*.patch inside its build workspace only.
#
# Usage:   bash .github/workflows/scripts/sync-upstream.sh [--no-push]
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

git fetch upstream main
git merge -X theirs upstream/main --no-edit || true

# Upstream workflows this fork does not want.
git rm -f --ignore-unmatch -- \
  .github/workflows/mirror.yml \
  .github/workflows/release.yml \
  .github/workflows/pr-size-label.yml \
  .github/workflows/check-codes-comment.yml \
  .github/scripts/pr-size-label.js \
  .github/scripts/check-codes-comment.js

# Leftovers from earlier patch runs must never be committed.
git rm -f --ignore-unmatch -- '*.orig' '*.rej'

# Keep the fork README (upstream merge would otherwise overwrite it).
cp .github/workflows/patches/README.md README.md

unresolved=$(git diff --name-only --diff-filter=U || true)
if [ -n "$unresolved" ]; then
  echo "Unresolved conflicts:" >&2
  echo "$unresolved" >&2
  exit 1
fi

git add -A
if ! git diff --cached --quiet; then
  git commit --author="TiaraBasori <mintabyss233@gmail.com>" -m "Sync upstream"
else
  echo "Nothing to commit"
fi

if [ "${1:-}" = "--no-push" ]; then
  echo "Skipping push (--no-push)."
  exit 0
fi

if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  git push origin main
else
  echo "Already up to date"
fi
