#!/usr/bin/env python3
"""
modules/analyzer.py (확장)
- 샷 분할(PySceneDetect)
- 오디오 분석(librosa)
- dissolve 전환 감지 (간단 휴리스틱)
- 히스토그램 이미지 생성 + 대표 프레임 추출(썸네일)
- Whisper 호출 hook (실제 추론은 modules/whisper_integration.py)
"""
from pathlib import Path
import json
import tempfile
import subprocess
import os
import numpy as np
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
import librosa
from typing import List, Dict
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from modules.whisper_integration import transcribe_with_whisper
from PIL import Image

def detect_scenes(video_path: Path, threshold=30.0):
    video_manager = VideoManager([str(video_path)])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    try:
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list(video_manager.get_base_timecode())
        pairs = [(st.get_seconds(), ed.get_seconds()) for (st, ed) in scene_list]
        return pairs
    finally:
        video_manager.release()

def extract_audio_wav(video_path: Path, out_wav: Path):
    cmd = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "22050", str(out_wav)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def analyze_audio(video_path: Path):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = Path(tmp.name)
    try:
        extract_audio_wav(video_path, tmp_wav)
        y, sr = librosa.load(str(tmp_wav), sr=None, mono=True)
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        rms_std = float(np.std(rms))
        try:
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, trim=False)
            tempo = float(tempo)
        except Exception:
            tempo = None
        return {
            "sr": int(sr),
            "duration": float(len(y)/sr),
            "rms_mean": rms_mean,
            "rms_std": rms_std,
            "tempo": tempo
        }
    finally:
        try:
            os.remove(tmp_wav)
        except Exception:
            pass

def extract_representative_frame(video_path: Path, start_s: float, end_s: float, out_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    mid = (start_s + end_s) / 2.0
    frame_idx = int(mid * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if ret:
        # convert BGR to RGB and save thumbnail
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img.thumbnail((320, 180))
        img.save(str(out_path))
    cap.release()

def detect_dissolves(video_path: Path, scenes: List[tuple], window=8, sensitivity=0.03):
    """
    간단 휴리스틱: 연속 프레임 간 MSE 변화가 서서히 증가/감소하는 구간을 dissolve로 본다.
    scenes: list of (start, end)
    return: list of transitions: [{"between": (i,i+1), "type":"dissolve", "duration": approx_seconds}, ...]
    """
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    transitions = []
    # compute per-frame luminance differences for window around scene boundaries
    for idx in range(len(scenes)-1):
        # region covering last window frames of scene idx and first window frames of next scene
        last_end = scenes[idx][1]
        next_start = scenes[idx+1][0]
        # sample frames around boundary
        samples = []
        start_time = max(0, last_end - window/fps)
        end_time = min(next_start + window/fps, cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps)
        times = np.linspace(start_time, end_time, num=2*window)
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t*1000)
            ret, frame = cap.read()
            if not ret:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            samples.append(gray.astype(np.float32))
        if len(samples) < 4:
            continue
        diffs = []
        for i in range(1, len(samples)):
            mse = np.mean((samples[i] - samples[i-1])**2) / (255.0**2)
            diffs.append(mse)
        # look for a ramp-up and ramp-down pattern: mean diffs relatively low but gradually changing
        diffs = np.array(diffs)
        if diffs.size == 0:
            continue
        # heuristic: if diffs show a smooth peak (low variance but non-zero mean) => dissolve
        if diffs.mean() < 0.05 and diffs.std() < 0.02 and diffs.max() > sensitivity:
            # estimate duration from number of frames around peak
            approx_sec = max(0.2, (len(diffs)/fps))
            transitions.append({"between": (idx, idx+1), "type": "dissolve", "duration": approx_sec})
    cap.release()
    return transitions

def make_histogram_png(cut_lengths: List[float], out_png: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(6,3))
    if cut_lengths:
        plt.hist(cut_lengths, bins=[0,1,2,3,4,5,10,30], edgecolor='black')
        plt.title("Cut length distribution (s)")
    else:
        plt.text(0.5,0.5,"No cuts detected", ha='center')
    plt.tight_layout()
    plt.savefig(str(out_png))
    plt.close()

def analyze_local_file(path: Path, use_whisper=False, progress_callback=print):
    scenes = []
    try:
        scenes = detect_scenes(path)
    except Exception as e:
        progress_callback(f"Scene detect failed for {path}: {e}")
        scenes = []
    cut_lengths = [ed-st for st,ed in scenes] if scenes else []
    avg_cut = float(np.mean(cut_lengths)) if cut_lengths else None
    audio = {}
    try:
        audio = analyze_audio(path)
    except Exception as e:
        progress_callback(f"Audio analyze failed for {path}: {e}")
        audio = {}
    # detect dissolves across scenes
    transitions = []
    try:
        if scenes and len(scenes) > 1:
            transitions = detect_dissolves(path, scenes)
    except Exception as e:
        progress_callback(f"Transition detect failed for {path}: {e}")
        transitions = []

    # whisper transcription (optional)
    srt_path = None
    if use_whisper:
        try:
            srt_path = transcribe_with_whisper(path, progress_callback=progress_callback)
        except Exception as e:
            progress_callback(f"Whisper transcription failed: {e}")
            srt_path = None

    profile = {
        "path": str(path),
        "num_scenes": len(scenes),
        "scenes": scenes,
        "avg_cut_length": avg_cut,
        "cut_lengths": cut_lengths,
        "audio": audio,
        "transitions": transitions,
        "srt": srt_path
    }
    return profile

def analyze_with_preview(paths: List[Path], use_whisper=False, progress_callback=print):
    # analyze each, aggregate style, generate preview assets (histogram png, thumbnails)
    profiles = []
    for p in paths:
        progress_callback(f"분석중: {p}")
        prof = analyze_local_file(p, use_whisper=use_whisper, progress_callback=progress_callback)
        profiles.append(prof)
    avg_cuts = [p["avg_cut_length"] for p in profiles if p.get("avg_cut_length")]
    tempos = [p.get("audio", {}).get("tempo") for p in profiles if p.get("audio", {}).get("tempo")]
    style = {
        "source_count": len(profiles),
        "mean_avg_cut_length": float(np.mean(avg_cuts)) if avg_cuts else 3.0,
        "median_avg_cut_length": float(np.median(avg_cuts)) if avg_cuts else 3.0,
        "tempo_median": float(np.median(tempos)) if tempos else None,
        "profiles": profiles
    }
    # generate histogram png from merged cut lengths
    all_cut_lengths = []
    for p in profiles:
        all_cut_lengths.extend(p.get("cut_lengths", []))
    tmpdir = Path(tempfile.mkdtemp(prefix="style_preview_"))
    hist_png = tmpdir / "cut_hist.png"
    make_histogram_png(all_cut_lengths, hist_png)
    # choose representative frames: pick longest shots across first video (or all)
    thumbs = []
    for p in profiles:
        scenes = p.get("scenes") or []
        # pick up to 4 longest scenes
        scenes_sorted = sorted(scenes, key=lambda x: x[1]-x[0], reverse=True)[:4]
        for i, (st, ed) in enumerate(scenes_sorted):
            out_thumb = tmpdir / f"{Path(p['path']).stem}_thumb_{i}.jpg"
            try:
                extract_representative_frame(Path(p['path']), st, ed, out_thumb)
                # store thumb metadata so GUI can play corresponding snippet
                thumbs.append({"thumb": str(out_thumb), "video": p['path'], "start": float(st), "end": float(ed)})
            except Exception as e:
                progress_callback(f"Thumb extract failed: {e}")
    preview = {"histogram_png": str(hist_png), "thumbs": thumbs}
    # attach first found srt (if any)
    for p in profiles:
        if p.get("srt"):
            preview["srt_path"] = p.get("srt")
            break
    return style, preview
