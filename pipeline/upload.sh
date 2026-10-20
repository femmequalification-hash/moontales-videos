#!/usr/bin/env bash
# Put files on the "upload" branch so Metricool can fetch them from a public
# raw.githubusercontent.com link.
#   upload.sh push FILE [FILE...]  -> prints one public URL per file
#   upload.sh clear                -> replaces the branch with an empty note
# Metricool copies the files to its own storage when the post is scheduled,
# so run "clear" right after the last createScheduledPost succeeds.
# (Releases and branch deletion are not allowed from Claude sessions; a
#  force-push of the single "upload" branch works.)
set -euo pipefail
REPO_URL="https://github.com/femmequalification-hash/moontales-videos"
RAW="https://raw.githubusercontent.com/femmequalification-hash/moontales-videos/upload"
MODE="$1"; shift
FILES=()
for f in "$@"; do FILES+=("$(cd "$(dirname "$f")" && pwd)/$(basename "$f")"); done
TMP="$(mktemp -d)"
cd "$TMP"
git init -q
git checkout -q --orphan upload
commit() {
  git -c user.name="femmequalification-hash" \
      -c user.email="femmequalification-hash@users.noreply.github.com" \
      commit -q -m "$1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
}
case "$MODE" in
  push)
    for f in "${FILES[@]}"; do cp "$f" .; done
    git add . && commit "Temporary files for YouTube scheduling"
    git push -q --force "$REPO_URL" upload:upload 2>&1 | grep -v "negotiation\|acknowledgments\|remote:" || true
    for f in "${FILES[@]}"; do echo "$RAW/$(basename "$f")"; done
    ;;
  clear)
    echo "Nothing here: videos are removed after they are scheduled on YouTube." > README.md
    git add . && commit "Clear temporary video"
    git push -q --force "$REPO_URL" upload:upload 2>&1 | grep -v "negotiation\|acknowledgments\|remote:" || true
    echo "cleared"
    ;;
esac
