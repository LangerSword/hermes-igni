#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/demo/raw"
EDIT="$ROOT/demo/edit"
OUTDIR="$HOME/Videos/igni"
FONT="$ROOT/assets/fonts/IBMPlexMono-Bold.ttf"
mkdir -p "$EDIT" "$OUTDIR"

# Normalize the three takes. The raw recordings start on a loading frame, so
# each trim starts where the actual film or loaded board begins.
ffmpeg -y -v error -i "$RAW/kinetic.webm" -ss 0.4 -t 27.0 \
  -vf "fps=30,scale=1920:1080,format=yuv420p" -an \
  -c:v libx264 -crf 18 -preset medium "$EDIT/01-kinetic.mp4"

ffmpeg -y -v error -i "$RAW/ui.webm" -ss 1.3 -t 24.2 \
  -vf "fps=30,scale=1920:1080,format=yuv420p,tpad=stop_mode=clone:stop_duration=0.8,fade=t=in:st=0:d=0.35,fade=t=out:st=24.5:d=0.5" \
  -an -c:v libx264 -crf 18 -preset medium "$EDIT/02-ui.mp4"

ffmpeg -y -v error -i "$RAW/endcard.webm" -ss 0.4 -t 8.0 \
  -vf "fps=30,scale=1920:1080,format=yuv420p,fade=t=in:st=0:d=0.35" -an \
  -c:v libx264 -crf 18 -preset medium "$EDIT/03-end.mp4"

printf "file '%s'\nfile '%s'\nfile '%s'\n" \
  "$EDIT/01-kinetic.mp4" "$EDIT/02-ui.mp4" "$EDIT/03-end.mp4" > "$EDIT/concat.txt"

ffmpeg -y -v error -f concat -safe 0 -i "$EDIT/concat.txt" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -r 30 -an \
  "$EDIT/silent.mp4"

# "Achaidh Cheide" by Kevin MacLeod, CC BY 4.0. The credit is burned into the
# end card and repeated in demo/CREDITS.md.
ffmpeg -y -v error -ss 8 -t 60 -i "$RAW/Achaidh_Cheide.mp3" \
  -af "atrim=0:60,afade=t=in:st=0:d=1.2,afade=t=out:st=57.2:d=2.8,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:a pcm_s16le "$EDIT/bed.wav"

FILTERS=$(tr '\n' ' ' < "$ROOT/demo/edit/filters.txt")

ffmpeg -y -v error -i "$EDIT/silent.mp4" -i "$EDIT/bed.wav" \
  -vf "$FILTERS" \
  -map 0:v:0 -map 1:a:0 -t 60 \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart \
  "$OUTDIR/igni-demo.mp4"

echo "wrote $OUTDIR/igni-demo.mp4"
