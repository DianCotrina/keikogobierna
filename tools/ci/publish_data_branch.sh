#!/usr/bin/env bash
# Publish files to an orphan data branch via a temporary git worktree.
#
# Usage: tools/ci/publish_data_branch.sh <branch> <commit-msg> <cmd> [args...]
#
# Runs <cmd> with DATA_DIR set to the worktree path (checked out at the branch
# tip, or an empty orphan on first run), then commits and pushes only when the
# command changed something. Never touches the current checkout or its config:
# the bot identity is passed inline to the commit. Data branches are outside
# the protect-main ruleset, which only covers the default branch.
set -euo pipefail

branch=$1
msg=$2
shift 2

tmp=$(mktemp -d)
if git fetch --depth 1 origin "$branch" 2>/dev/null; then
  git worktree add "$tmp" FETCH_HEAD
else
  git worktree add --detach "$tmp"
  git -C "$tmp" checkout --orphan "$branch"
  git -C "$tmp" rm -rf . >/dev/null 2>&1 || true
fi

DATA_DIR="$tmp" "$@"

git -C "$tmp" add -A
if git -C "$tmp" diff --cached --quiet; then
  echo "no changes to $branch"
else
  git -C "$tmp" -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit -m "$msg"
  git -C "$tmp" push origin "HEAD:$branch"
fi
git worktree remove --force "$tmp"
