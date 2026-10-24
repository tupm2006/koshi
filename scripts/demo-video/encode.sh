#!/usr/bin/env bash
# Encode the screencast frames recorded by record.py in <dir> to the landing page's demo.mp4
# (H.264, faststart so it plays before fully downloading) plus a poster frame.
set -euo pipefail
dir="${1:?usage: encode.sh <recording-dir>}"
cd "$(dirname "$0")/../.."
out=source/frontend/public
mkdir -p "$out"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$dir/frames.txt" -vf "fps=30,scale=1280:720" -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart -an "$out/demo.mp4"
ffmpeg -y -loglevel error -ss 3 -i "$out/demo.mp4" -frames:v 1 -q:v 4 "$out/demo-poster.jpg"
ls -lh "$out/demo.mp4" "$out/demo-poster.jpg"
