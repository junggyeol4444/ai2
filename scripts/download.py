#!/usr/bin/env python3
"""
scripts/download.py
- 간단한 yt-dlp 래퍼
usage:
  python scripts/download.py --urls urls.txt --outdir samples/raw
or
  echo "https://youtube..." | python scripts/download.py --urls -
"""
import argparse
import subprocess
from pathlib import Path
import sys
import shlex

def download(url, outdir):
    outtmpl = str(Path(outdir) / "%(uploader)s-%(id)s.%(ext)s")
    cmd = ["yt-dlp", "-f", "bestvideo+bestaudio/best", "-o", outtmpl, url]
    subprocess.run(cmd, check=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--urls", required=True, help="URLs file, or '-' to read stdin")
    p.add_argument("--outdir", required=False, default="samples/raw")
    args = p.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if args.urls == "-":
        data = sys.stdin.read().strip()
        if not data:
            print("No URL on stdin")
            return
        urls = [data]
    else:
        urls = [l.strip() for l in open(args.urls, "r", encoding="utf-8") if l.strip()]
    for u in urls:
        print("Downloading", u)
        download(u, outdir)

if __name__ == "__main__":
    main()
