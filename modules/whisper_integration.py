#!/usr/bin/env python3
"""
modules/whisper_integration.py
- openai/whisper 기반 간단 자막 추출기
- 출력: SRT 파일 (path)
Note: requires 'openai-whisper' (pip) and torch backend installed.
"""
from pathlib import Path
import whisper
import tempfile
import srt
import datetime
import os

def transcribe_with_whisper(video_path: Path, model_name="small", progress_callback=print):
    """
    Transcribe using Whisper and write an SRT file next to the video (tmp file).
    Returns path to srt.
    """
    progress_callback(f"Whisper: loading model {model_name} (may take time)...")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        progress_callback(f"Whisper model load failed: {e}")
        raise RuntimeError("Whisper model failed to load. Ensure 'torch' is installed and choose a smaller model if necessary.")
    progress_callback("Whisper: transcribing (this may take long)...")
    try:
        result = model.transcribe(str(video_path), verbose=False)
    except Exception as e:
        progress_callback(f"Whisper transcription failed during transcribe(): {e}")
        raise RuntimeError("Whisper transcription failed during model.transcribe(). Check system resources and model compatibility.")
    segments = result.get("segments", [])
    subtitles = []
    for i, seg in enumerate(segments, start=1):
        start = datetime.timedelta(seconds=seg["start"])
        end = datetime.timedelta(seconds=seg["end"])
        content = seg["text"].strip()
        sub = srt.Subtitle(index=i, start=start, end=end, content=content)
        subtitles.append(sub)
    srt_text = srt.compose(subtitles)
    out_srt = Path(tempfile.mkdtemp(prefix="whisper_srt_")) / (Path(video_path).stem + ".srt")
    with open(out_srt, "w", encoding="utf-8") as fh:
        fh.write(srt_text)
    progress_callback(f"Whisper: wrote SRT to {out_srt}")
    return str(out_srt)
