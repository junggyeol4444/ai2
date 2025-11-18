#!/usr/bin/env bash
# 간단 FFmpeg 렌더(유닉스 쉘)
# usage: bash scripts/render.sh edl.json output/final.mp4
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 edl.json output/final.mp4"
  exit 1
fi
EDL="$1"
OUT="$2"
TMPDIR="$(mktemp -d)"
PARTLIST="$TMPDIR/parts.txt"
CONCAT="$TMPDIR/concat.txt"
> "$PARTLIST"
> "$CONCAT"
python3 - <<PY
import json,sys,os,shlex
edl=json.load(open(sys.argv[1],'r'))
events=edl.get("events",[])
tmp=sys.argv[2]
for i,ev in enumerate(events):
    infile=ev['infile']
    s=ev['in_start']
    e=ev['in_end']
    out=os.path.join(tmp,f"part_{i:04d}.mp4")
    print(shlex.quote(infile)+"|"+str(s)+"|"+str(e)+"|"+shlex.quote(out))
PY "$EDL" "$TMPDIR" > "$PARTLIST"
while IFS='|' read -r infile s e outpath; do
  ffmpeg -y -hide_banner -loglevel error -ss "$s" -to "$e" -i "$infile" -c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart "$outpath"
  echo "file '$outpath'" >> "$CONCAT"
done < "$PARTLIST"
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$CONCAT" -c copy "$OUT"
echo "Rendered $OUT"
