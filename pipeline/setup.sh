#!/usr/bin/env bash
# One-time setup in a fresh workspace: Python packages + free voice model.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TTS="${MT_TTS_DIR:-$HERE/tts}"
pip install --break-system-packages -q kokoro-onnx soundfile numpy pillow 2>/dev/null
mkdir -p "$TTS"
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s "$TTS/voices.bin" ] || curl -sSL -m 300 -o "$TTS/voices.bin" "$BASE/voices-v1.0.bin"
[ -s "$TTS/kokoro.onnx" ] || curl -sSL -m 600 -o "$TTS/kokoro.onnx" "$BASE/kokoro-v1.0.onnx"
command -v ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
echo "setup ok"
