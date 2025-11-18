#!/usr/bin/env python3
"""
modules/editor.py (확장)
- EDL 생성 (ASL 기반)
- 전환(dissolve) 정보 반영
- FFmpeg로 xfade / acrossfade 체인을 생성해 비디오+오디오 dissolve 적용
- fallback: simple concat (no transitions)
"""
from pathlib import Path
import json
from moviepy.editor import VideoFileClip
from modules.style import load_style
from modules.bgm import choose_bgm_for_style
import subprocess
import os
import shlex

def chop_clip_parts(path, part_len):
    clip = VideoFileClip(str(path))
    dur = clip.duration
    parts = []
    t = 0.0
    while t < dur - 0.01:
        end = min(dur, t + part_len)
        parts.append({"file": str(path), "in_start": float(t), "in_end": float(end), "duration": float(end-t)})
        t = end
    clip.close()
    return parts

def _trim_parts(clips, events, tmpdir, log_fn=print):
    tmpdir = Path(tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    part_paths = []
    for i, ev in enumerate(events):
        part_out = tmpdir / f"part_{i:04d}.mp4"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(ev["in_start"]), "-to", str(ev["in_end"]),
            "-i", ev["infile"],
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-movflags", "+faststart", str(part_out)
        ]
        log_fn(f"Trimming: {' '.join(shlex.quote(x) for x in cmd)}")
        subprocess.run(cmd, check=True)
        part_paths.append({"path": str(part_out), "duration": ev["duration"], "transition": ev.get("transition","cut"), "transition_duration": ev.get("transition_duration", 0.0)})
    return part_paths

def _render_concat(part_paths, out_file, tmpdir, log_fn=print):
    concat_txt = Path(tmpdir) / "concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as fconcat:
        for p in part_paths:
            fconcat.write(f"file '{Path(p['path']).resolve()}'\n")
    cmd_concat = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", out_file]
    log_fn("Running concat")
    subprocess.run(cmd_concat, check=True)

def _render_with_transitions(part_paths, out_file, tmpdir, log_fn=print):
    """
    Build ffmpeg filter_complex with sequential xfades (video) and acrossfade (audio).
    Assumes part_paths is list with dict {path, duration, transition, transition_duration}
    """
    # For simplicity, we will build a chain: input0 input1 input2 ... then sequentially apply xfade
    input_args = []
    for p in part_paths:
        input_args.extend(["-i", p["path"]])
    filter_parts = []
    vid_streams = []
    aud_streams = []
    for i in range(len(part_paths)):
        vid_streams.append(f"[{i}:v]")
        aud_streams.append(f"[{i}:a]")

    # Build video xfade chain
    vchain = vid_streams[0]
    achain = aud_streams[0]
    filter_idx = 0
    filters = []
    for i in range(1, len(part_paths)):
        cur = vid_streams[i]
        cur_a = aud_streams[i]
        trans = part_paths[i-1].get("transition")
        tdur = part_paths[i].get("transition_duration") or part_paths[i-1].get("transition_duration") or 0.4
        # offset: duration of previous clip - transition_duration
        prev_dur = part_paths[i-1]["duration"]
        offset = max(0.001, prev_dur - tdur)
        # name outputs
        out_v = f"[v{filter_idx+1}]"
        out_a = f"[a{filter_idx+1}]"
        # xfade for video (use fade transition)
        vf = f"{vchain}{cur}xfade=transition=fade:duration={tdur}:offset={offset}{out_v}"
        # acrossfade for audio
        af = f"{achain}{cur_a}acrossfade=d={tdur}{out_a}"
        filters.append(vf)
        filters.append(af)
        vchain = out_v
        achain = out_a
        filter_idx += 1

    # final map
    filter_complex = ";".join(filters)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    cmd += input_args
    if filter_complex:
        cmd += ["-filter_complex", filter_complex, "-map", vchain, "-map", achain, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", str(out_file)]
    else:
        # fallback
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(Path(tmpdir)/"concat.txt"), "-c", "copy", str(out_file)]
    log_fn(f"Running ffmpeg with transitions (may be slow)")
    subprocess.run(cmd, check=True)


def create_edl_and_render(clips, style_path, out_base: Path, log_fn=print):
    out_base = Path(out_base)
    out_base.mkdir(parents=True, exist_ok=True)
    # load style
    if style_path:
        style = load_style(style_path)
        asl = style.get("mean_avg_cut_length") or style.get("median_avg_cut_length") or 3.0
        tempo = style.get("tempo_median")
    else:
        asl = 3.0
        tempo = None
        style = {"note":"auto"}
    events = []
    out_time = 0.0
    # create events via chopping
    for c in clips:
        parts = chop_clip_parts(c, asl)
        for p in parts:
            ev = {
                "infile": p["file"],
                "in_start": p["in_start"],
                "in_end": p["in_end"],
                "out_start": out_time,
                "duration": p["duration"],
                "transition": "cut",
                "transition_duration": 0.0
            }
            events.append(ev)
            out_time += p["duration"]
    # NOTE: if style contains transition suggestions (from analysis), we could map them to events;
    # For now, keep events as cuts. Future improvement: match scene boundaries to events and set transition types.
    edl = {"style": style, "events": events}
    edl_path = out_base / "edl.json"
    with open(edl_path, "w", encoding="utf-8") as fh:
        json.dump(edl, fh, indent=2, ensure_ascii=False)
    log_fn(f"EDL created: {edl_path}")
    # choose bgm if present
    bgm_file = choose_bgm_for_style(Path("bgm"), tempo)
    rendered = out_base / "final.mp4"
    # Trim parts
    tmpdir = out_base / "parts"
    part_paths = _trim_parts(clips, events, tmpdir, log_fn=log_fn)
    # decide if any transitions requested
    has_dissolve = any(p.get("transition") == "dissolve" for p in part_paths)
    if has_dissolve:
        try:
            _render_with_transitions(part_paths, str(rendered), tmpdir, log_fn=log_fn)
        except Exception as e:
            log_fn(f"Transition render failed: {e}. Falling back to concat.")
            _render_concat(part_paths, str(rendered), tmpdir, log_fn=log_fn)
    else:
        _render_concat(part_paths, str(rendered), tmpdir, log_fn=log_fn)
    # bgm mixing (simple ducking not per speech, just mix)
    if bgm_file:
        mixed = out_base / "final_bgm.mp4"
        cmd_mix = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(rendered), "-i", str(bgm_file),
            "-filter_complex", "[1:a]volume=0.25[a1];[0:a][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", str(mixed)
        ]
        try:
            subprocess.run(cmd_mix, check=True)
            Path(mixed).replace(rendered)
        except Exception:
            log_fn("BGM mix failed; keeping original audio")
    return str(edl_path), str(rendered)
