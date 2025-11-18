#!/usr/bin/env python3
"""
modules/preview.py
- 썸네일 클릭시 해당 장면 재생을 위한 유틸
- play_scene_clip(video_path, start, end, length_sec=2.0)
  -> ffmpeg로 짧은 임시 클립 생성 후 시스템 기본 플레이어로 실행
"""
from pathlib import Path
import subprocess
import tempfile
import os
import shlex
import sys

def _create_temp_clip(video_path: str, mid_s: float, length_sec: float=2.0):
    tmpdir = Path(tempfile.mkdtemp(prefix="preview_clip_"))
    out_file = tmpdir / "clip_preview.mp4"
    half = length_sec / 2.0
    start = max(0.0, mid_s - half)
    # use -ss and -t for reliable trimming; re-encode to ensure compatibility
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(length_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "28",
        "-c:a", "aac",
        str(out_file)
    ]
    subprocess.run(cmd, check=True)
    return str(out_file)

def _open_with_default_app(path: str):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform.startswith("darwin"):
        subprocess.run(["open", path])
    else:
        # assume linux-like
        subprocess.run(["xdg-open", path])

def play_scene_clip(video_path: str, start: float, end: float, length_sec: float=2.0):
    """
    Create a short clip centered around the scene midpoint and open it.
    Returns path to temp clip.
    """
    try:
        mid = (start + end) / 2.0
        clip = _create_temp_clip(video_path, mid, length_sec=length_sec)
        _open_with_default_app(clip)
        return clip
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create preview clip: {e}")
