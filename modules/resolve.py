#!/usr/bin/env python3
"""
modules/resolve.py
- DaVinci Resolve 자동 타임라인 생성 (Resolve Python API)
- Requires DaVinci Resolve to be installed and DaVinciResolveScript module accessible.
"""
from pathlib import Path
import os
import json

def _import_resolve_module():
    try:
        import DaVinciResolveScript
        return DaVinciResolveScript
    except Exception:
        # Try known macOS path
        possible = [
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/DaVinciResolveScript.py"
        ]
        for p in possible:
            if Path(p).exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("DaVinciResolveScript", p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
    raise RuntimeError("DaVinci Resolve scripting module not found. Ensure Resolve is installed and scripting module is available.")

def export_to_resolve_project(edl_path: str, media_folder: Path, log_fn=print):
    """
    Create a Resolve project and timeline from edl.json.
    Returns path or project name created.
    """
    log_fn("Resolve export: initializing")
    drs = _import_resolve_module()
    resolve = drs.scriptapp("Resolve")
    pm = resolve.GetProjectManager()
    project_name = f"AutoEdit_{Path(edl_path).stem}"
    project = pm.CreateProject(project_name)
    if not project:
        raise RuntimeError("Failed to create Resolve project")
    log_fn(f"Created Resolve project: {project_name}")
    # Import media
    media_storage = resolve.GetMediaStorage()
    edl = json.load(open(edl_path, "r", encoding="utf-8"))
    events = edl.get("events", [])
    media_paths = set([e["infile"] for e in events])
    for mp in media_paths:
        log_fn(f"Importing {mp}")
        media_storage.AddItemToMediaPool(str(Path(mp).resolve()))
    # create timeline
    project.SetSetting("timelineResolutionWidth", "1920")
    project.SetSetting("timelineResolutionHeight", "1080")
    timeline = project.CreateTimeline(project_name + "_timeline")
    # append clips to timeline in order: note this uses Resolve API high-level methods
    # In many Resolve versions, AppendToTimeline may accept clip objects imported in MediaPool
    med_pool = resolve.GetMediaPool()
    mp_items = med_pool.GetRootFolder().GetClipList() if hasattr(med_pool.GetRootFolder(), "GetClipList") else []
    # Simple approach: create timeline and place clips by filename matching
    for e in events:
        infile = str(Path(e["infile"]).resolve())
        # find clip in media pool
        try:
            media_pool_item = med_pool.ImportMedia([infile])
        except Exception:
            log_fn(f"Failed to import media pool item for {infile}")
            continue
    # Save project
    pm.SaveProject()
    log_fn("Resolve project saved")
    return project_name
