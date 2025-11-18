#!/usr/bin/env python3
"""
Simple smoke test to validate core functionality locally.
Usage:
  python scripts/smoke_test.py path/to/sample.mp4
"""
import sys
from pathlib import Path
from modules.analyzer import analyze_local_file
from modules.bgm import index_bgm_folder

def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/smoke_test.py <sample_video.mp4>')
        return
    sample = Path(sys.argv[1])
    if not sample.exists():
        print('Sample not found:', sample)
        return
    print('Indexing bgm folder...')
    try:
        index_bgm_folder(Path('bgm'), log_fn=print)
    except Exception as e:
        print('BGM index failed:', e)
    print('Analyzing sample (no Whisper)...')
    try:
        profile = analyze_local_file(sample, use_whisper=False, progress_callback=print)
        print('Profile summary:')
        print(' num_scenes:', profile.get('num_scenes'))
        print(' avg_cut_length:', profile.get('avg_cut_length'))
        print(' audio tempo:', profile.get('audio',{}).get('tempo'))
    except Exception as e:
        print('Analysis failed:', e)

if __name__ == '__main__':
    main()
