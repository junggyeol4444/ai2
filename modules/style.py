#!/usr/bin/env python3
"""
modules/style.py
- style_profile 입출력 및 style 패키지 저장
"""
from pathlib import Path
import json
import shutil
import uuid

def save_style_package(style_dict, target_folder: Path):
    # Create folder named by style name or uuid
    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)
    sid = style_dict.get("name") or f"style_{uuid.uuid4().hex[:8]}"
    base = target_folder / sid
    if base.exists():
        # ensure unique
        base = target_folder / (sid + "_" + uuid.uuid4().hex[:4])
    base.mkdir(parents=True)
    # save json
    with open(base / "style.json", "w", encoding="utf-8") as fh:
        json.dump(style_dict, fh, indent=2, ensure_ascii=False)
    # create assets subfolder
    (base / "assets").mkdir(exist_ok=True)
    return str(base)

def load_style(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return json.load(open(p, "r", encoding="utf-8"))
