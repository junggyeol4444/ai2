#!/usr/bin/env python3
"""
modules/bgm.py
- bgm 폴더 인덱스 및 간단한 tempo 기반 선택기
- 규칙: bgm/ 폴더 내 파일만 사용
"""
from pathlib import Path
import librosa
import json

def index_bgm_folder(bgm_folder: Path, log_fn=print):
    bgm_folder = Path(bgm_folder)
    index = []
    for f in sorted(bgm_folder.glob("*.*")):
        if f.suffix.lower() not in [".mp3", ".wav", ".m4a", ".aac", ".flac"]:
            continue
        try:
            y, sr = librosa.load(str(f), sr=None, mono=True, duration=60.0)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            index.append({"file": str(f), "tempo": float(tempo), "duration": float(librosa.get_duration(y=y, sr=sr))})
            log_fn(f"Indexed BGM: {f.name} tempo={tempo:.1f}")
        except Exception as e:
            log_fn(f"Failed index {f.name}: {e}")
    # write index
    with open(bgm_folder / "bgm_index.json", "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)
    return index

def choose_bgm_for_style(bgm_folder: Path, target_tempo=None):
    idx_file = Path(bgm_folder) / "bgm_index.json"
    if not idx_file.exists():
        index_bgm_folder(bgm_folder)
    try:
        index = json.load(open(idx_file, "r", encoding="utf-8"))
    except Exception:
        index = []
    if not index:
        return None
    if target_tempo is None:
        return index[0]["file"]
    # pick nearest tempo
    best = min(index, key=lambda x: abs(x.get("tempo",0)-target_tempo))
    return best["file"]
