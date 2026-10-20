#!/usr/bin/env bash
# Upload a built video + thumbnail as a GitHub release so Metricool can fetch
# them from a public link. Prints the two public URLs.
# Usage: upload.sh SLUG OUT_DIR
set -euo pipefail
SLUG="$1"; OUT="$2"
REPO="femmequalification-hash/moontales-videos"
TAG="video-$SLUG"
gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1 && gh release delete "$TAG" --repo "$REPO" --yes --cleanup-tag
gh release create "$TAG" --repo "$REPO" --title "$SLUG" \
  --notes "Temporary copy for YouTube scheduling. Deleted after the video is published." \
  "$OUT/$SLUG.mp4" "$OUT/${SLUG}_thumb.jpg" >/dev/null
echo "VIDEO_URL=https://github.com/$REPO/releases/download/$TAG/$SLUG.mp4"
echo "THUMB_URL=https://github.com/$REPO/releases/download/$TAG/${SLUG}_thumb.jpg"
