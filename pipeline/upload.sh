#!/usr/bin/env bash
# Put a built video + thumbnail on the "upload" branch so Metricool can fetch
# them from a public raw.githubusercontent.com link.
#   upload.sh push  SLUG OUT_DIR   -> prints VIDEO_URL / THUMB_URL
#   upload.sh clear                -> replaces the branch with an empty note
# Metricool copies the files to its own storage when the post is scheduled,
# so run "clear" right after createScheduledPost succeeds.
# (Releases and branch deletion are not allowed from Claude sessions; a
#  force-push of the single "upload" branch works.)
set -euo pipefail
REPO_URL="https://github.com/femmequalification-hash/moontales-videos"
RAW="https://raw.githubusercontent.com/femmequalification-hash/moontales-videos/upload"
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
case "$1" in
  push)
    SLUG="$2"; OUT="$3"
    cp "$OUT/$SLUG.mp4" "$OUT/${SLUG}_thumb.jpg" .
    git add . && commit "Temporary video for YouTube scheduling: $SLUG"
    git push -q --force "$REPO_URL" upload:upload 2>&1 | grep -v "negotiation\|acknowledgments" || true
    echo "VIDEO_URL=$RAW/$SLUG.mp4"
    echo "THUMB_URL=$RAW/${SLUG}_thumb.jpg"
    ;;
  clear)
    echo "Nothing here: videos are removed after they are scheduled on YouTube." > README.md
    git add . && commit "Clear temporary video"
    git push -q --force "$REPO_URL" upload:upload 2>&1 | grep -v "negotiation\|acknowledgments" || true
    echo "cleared"
    ;;
esac
