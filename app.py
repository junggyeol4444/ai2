#!/usr/bin/env python3
"""
app.py (확장판)
- 스타일 분석 미리보기 (샷 히스토그램 + 대표 프레임)
- Whisper 옵션(자막 생성)
- 편집 후 DaVinci Resolve 타임라인 생성 옵션
- 썸네일 클릭 시 해당 장면 재생 (modules.preview)
"""
import os
import subprocess
import json
import shutil
import sys
from pathlib import Path
import PySimpleGUI as sg

from modules.analyzer import analyze_with_preview
from modules.editor import create_edl_and_render
from modules.style import save_style_package, load_style
from modules.bgm import index_bgm_folder
from modules.resolve import export_to_resolve_project
from modules.preview import play_scene_clip

# 프로젝트 폴더 설정
ROOT = Path.cwd()
STYLES_DIR = ROOT / "styles"
CLIPS_DIR = ROOT / "clips"
EDLS_DIR = ROOT / "edls"
OUTPUT_DIR = ROOT / "output"
BGM_DIR = ROOT / "bgm"

for d in [STYLES_DIR, CLIPS_DIR, EDLS_DIR, OUTPUT_DIR, BGM_DIR]:
    d.mkdir(parents=True, exist_ok=True)

sg.theme("SystemDefault")

layout = [
    [sg.Text("Auto Edit Style (Local MVP) — 확장판", font=("Helvetica", 16))],
    [sg.Button("스타일 분석", size=(20,2)), sg.Button("편집", size=(20,2))],
    [sg.HorizontalSeparator()],
    [sg.Text("로그 출력:")],
    [sg.Multiline(key="-LOG-", size=(100,14), disabled=True)]
]

window = sg.Window("Auto Edit Style", layout, finalize=True)


def log(msg):
    window["-LOG-"].print(msg)


def run_style_analysis():
    # Ask for YouTube URL or local file(s)
    layout_choice = [
        [sg.Text("스타일 분석 - 소스 선택")],
        [sg.Radio("유튜브 링크", "SRC", default=False, key="-URLRADIO-"), sg.Radio("로컬 파일 업로드", "SRC", key="-FILRADIO-", default=True)],
        [sg.Text("유튜브 URL (하나만 가능):"), sg.Input(key="-URL-")],
        [sg.Text("또는 파일 선택:"), sg.Input(key="-FILES-"), sg.FilesBrowse(file_types=(("Video Files", "*.mp4;*.mov;*.mkv;*.webm"),))],
        [sg.Checkbox("Whisper로 자막 생성 (설치 필요)", key="-WHISPER-")],
        [sg.Button("분석 시작"), sg.Button("취소")]
    ]
    w = sg.Window("스타일 분석", layout_choice, modal=True)
    while True:
        ev, vals = w.read()
        if ev in (sg.WIN_CLOSED, "취소"):
            w.close(); return
        if ev == "분석 시작":
            use_whisper = bool(vals["-WHISPER-"])
            if vals["-URLRADIO-"]:
                url = vals["-URL-"].strip()
                if not url:
                    sg.popup("유튜브 링크를 입력하세요.")
                    continue
                tmpdir = ROOT / "samples" / "raw"
                tmpdir.mkdir(parents=True, exist_ok=True)
                log(f"다운로드 요청: {url}")
                try:
                    import tempfile
                    tf = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt")
                    tf.write(url)
                    tf.flush()
                    tf.close()
                    subprocess.run([sys.executable, "scripts/download.py", "--urls", tf.name, "--outdir", str(tmpdir)], check=True)
                    os.unlink(tf.name)
                except subprocess.CalledProcessError as e:
                    log(f"다운로드 실패: {e}")
                    sg.popup("다운로드 실패. 콘솔 로그 확인.")
                    continue
                downloaded = list(tmpdir.glob("*.*"))
                if not downloaded:
                    sg.popup("다운로드된 파일이 없습니다.")
                    continue
                # perform analysis WITH preview (generates histogram and thumbnails)
                try:
                    style, preview = analyze_with_preview(downloaded, use_whisper=use_whisper, progress_callback=log)
                except Exception as e:
                    log(f"분석 실패: {e}")
                    sg.popup("분석 실패. 콘솔 로그 확인.")
                    continue
            else:
                files = vals["-FILES-"]
                if not files:
                    sg.popup("분석할 로컬 비디오 파일을 선택하세요.")
                    continue
                paths = [Path(p) for p in files.split(";") if p]
                try:
                    style, preview = analyze_with_preview(paths, use_whisper=use_whisper, progress_callback=log)
                except Exception as e:
                    log(f"분석 실패: {e}")
                    sg.popup("분석 실패. 콘솔 로그 확인.")
                    continue

            # show preview: histogram + thumbnails + subtitle excerpt if exists
            hist_png = preview.get("histogram_png")
            thumbs = preview.get("thumbs", [])
            srt = preview.get("srt_path")
            # build preview layout
            preview_layout = [[sg.Text("분석 결과 미리보기")]]
            if hist_png and Path(hist_png).exists():
                preview_layout.append([sg.Image(hist_png)])
            # create buttons for thumbnails
            thumb_buttons = []
            for idx, t in enumerate(thumbs):
                thumb_path = t["thumb"]
                if Path(thumb_path).exists():
                    thumb_buttons.append(sg.Button(image_filename=str(thumb_path), key=f"-THUMB-{idx}-", pad=(2,2)))
            if thumb_buttons:
                # show in rows of up to 4
                rows = [thumb_buttons[i:i+4] for i in range(0, len(thumb_buttons), 4)]
                for r in rows:
                    preview_layout.append(r)
            if srt and Path(srt).exists():
                preview_layout.append([sg.Text("추출된 자막(일부):")])
                lines = open(srt, "r", encoding="utf-8").read().splitlines()[:20]
                preview_layout.append([sg.Multiline("\n".join(lines), size=(80,10), disabled=True)])
            preview_layout.append([sg.Button("저장"), sg.Button("취소")])
            pv = sg.Window("미리보기", preview_layout, modal=True, finalize=True)
            # map thumb button keys to metadata
            thumb_map = {f"-THUMB-{i}-": t for i,t in enumerate(thumbs)}
            while True:
                ev2, vals2 = pv.read()
                if ev2 in (sg.WIN_CLOSED, "취소"):
                    pv.close()
                    w.close()
                    return
                if ev2 == "저장":
                    save_to = sg.popup_get_folder("스타일 저장할 위치 선택", default_path=str(STYLES_DIR))
                    if not save_to:
                        sg.popup("저장 취소됨.")
                        pv.close(); w.close(); return
                    style_pkg_path = save_style_package(style, Path(save_to))
                    # copy preview assets into package assets
                    assets_dir = Path(style_pkg_path) / "assets"
                    assets_dir.mkdir(exist_ok=True)
                    if hist_png:
                        shutil.copy(hist_png, assets_dir / Path(hist_png).name)
                    for t in thumbs:
                        shutil.copy(t["thumb"], assets_dir / Path(t["thumb"]).name)
                    if srt:
                        shutil.copy(srt, assets_dir / Path(srt).name)
                    log(f"스타일 저장 완료: {style_pkg_path}")
                    sg.popup(f"스타일 저장 완료: {style_pkg_path}")
                    pv.close(); w.close(); return
                # thumbnail clicked
                if ev2 in thumb_map:
                    meta = thumb_map[ev2]
                    video = meta.get("video")
                    start = meta.get("start")
                    end = meta.get("end")
                    try:
                        log(f"Play preview: {video} ({start:.2f}-{end:.2f})")
                        play_scene_clip(video, start, end, length_sec=2.0)
                    except Exception as e:
                        log(f"Preview play failed: {e}")
                        sg.popup("미리보기 재생 실패. 콘솔 로그 확인.")
            # end preview loop


def run_edit_flow():
    # Select clips to edit
    files = sg.popup_get_file("편집할 클립들을 선택하세요 (다중 선택 가능)", multiple_files=True, file_types=(("Video Files","*.mp4;*.mov;*.mkv;*.webm"),), default_path=str(CLIPS_DIR))
    if not files:
        return
    clip_paths = [Path(p) for p in files.split(";") if p]
    # choose mode
    mode = sg.popup_get_text("모드 선택: 1 = 편집(자동), 2 = 스타일 편집\n입력(1 또는 2):", default_text="1")
    if not mode:
        return
    if mode.strip() == "1":
        style_path = None
    else:
        style_path = sg.popup_get_file("적용할 스타일 JSON 파일을 선택하세요", file_types=(("Style JSON","*.json"),), default_path=str(STYLES_DIR))
        if not style_path:
            sg.popup("스타일 선택 취소")
            return
        style_path = Path(style_path)
    # index bgm
    index_bgm_folder(BGM_DIR, lambda m: window["-LOG-"].print(m))
    out_base = EDLS_DIR / f"edl_{os.getpid()}"
    out_base.mkdir(parents=True, exist_ok=True)
    try:
        edl_path, rendered = create_edl_and_render(clip_paths, style_path, out_base, log_fn=log)
    except Exception as e:
        log(f"편집/렌더 실패: {e}")
        sg.popup("편집 또는 렌더 중 오류가 발생했습니다. 콘솔 로그 확인.")
        return
    log(f"EDL 저장: {edl_path}")
    log(f"렌더 결과: {rendered}")
    # confirm dialog with Resolve option
    action = sg.popup_yes_no("편집이 완료되었습니다. 확인(Yes) 또는 수동 편집(아니오)을 선택하세요.\n(Yes = 완료, No = 수동 편집으로 열기)")
    if action == "Yes":
        sg.popup("편집 완료되었습니다.")
    else:
        # offer Resolve export
        choice = sg.popup_yes_no("DaVinci Resolve 타임라인으로 내보내시겠습니까?\n(Yes = Resolve로, No = 폴더 열기)")
        if choice == "Yes":
            try:
                project_path = export_to_resolve_project(edl_path, Path(rendered).parent, lambda m: window["-LOG-"].print(m))
                sg.popup(f"Resolve 프로젝트 생성 완료: {project_path}")
            except Exception as e:
                log(f"Resolve export 실패: {e}")
                sg.popup("Resolve export 실패. 로그 확인.")
        else:
            # open folder
            try:
                out_base_path = Path(rendered).parent
                if sys.platform.startswith("win"):
                    os.startfile(out_base_path)
                elif sys.platform.startswith("darwin"):
                    subprocess.run(["open", out_base_path])
                else:
                    subprocess.run(["xdg-open", out_base_path])
            except Exception:
                log("폴더 열기 실패")

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if event == "스타일 분석":
        run_style_analysis()
    if event == "편집":
        run_edit_flow()

window.close()