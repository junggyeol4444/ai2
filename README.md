# Auto Edit Style - Local MVP (확장판)

추가된 기능
- 스타일 분석 미리보기: 샷 길이 히스토그램(.png) 및 대표 프레임(썸네일) 자동 생성/미리보기
- Whisper 통합: 로컬 Whisper 모델로 자막(segments)을 추출하여 SRT 저장 및 스타일에 반영
- 전환(디졸브) 감지 및 적용: 분석 시 디졸브 구간 추정, 렌더 시 FFmpeg xfade/acrossfade로 적용
- DaVinci Resolve 연동: Resolve Python API로 자동 프로젝트/타임라인 생성(Resolve 설치 필요)
- 미리보기 GUI 개선: 썸네일 클릭 시 해당 장면의 짧은 클립 재생

필수(시스템)
- Python 3.9+
- ffmpeg (시스템)
- yt-dlp (시스템)
- (옵션) DaVinci Resolve (타임라인 자동 생성 시)
- (권장) GPU + torch 설치 — Whisper 모델 사용시 성능 향상

파이썬 의존성
- requirements.txt에 지정 (whisper는 모델 로컬 로딩에 torch 필요)

설치 예시 (Ubuntu)
1. 가상환경
   python3 -m venv .venv
   source .venv/bin/activate
2. pip 의존성 설치
   pip install -r requirements.txt
3. 시스템 패키지
   sudo apt update && sudo apt install -y ffmpeg
4. Whisper 사용을 원하면 (torch 설치가 필요)
   pip install -U torch torchvision --extra-index-url https://download.pytorch.org/whl/cu117
   pip install -U openai-whisper

사용법(요약)
1. python app.py 로 실행
2. [스타일 분석] → 유튜브 링크 또는 로컬 파일 → 분석 진행
   - 분석 완료 후 히스토그램과 대표 프레임 미리보기(팝업)
   - Whisper 사용을 선택하면 자막(.srt)도 같이 생성
   - 스타일 저장 위치 선택 → style 폴더(package) 생성
3. [편집] → 편집할 클립 선택 → 모드 선택(자동 / 스타일 적용)
   - 렌더 완료 후 프리뷰 및 확인
   - '수동 편집으로 열기' 선택 시 DaVinci Resolve로 타임라인을 자동 생성(Resolve 설치 필요)하거나 결과 폴더 열기

주의
- Whisper를 사용하려면 로컬에 적절한 torch가 설치되어 있어야 합니다. 모델 로드에 시간이 걸리고 VRAM을 사용합니다.
- DaVinci Resolve 연동은 Resolve의 Python API(예: /Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Script) 가 시스템에 설치되어 있어야 합니다.
- BGM은 여전히 프로젝트 루트의 bgm/ 폴더만 사용됩니다.

문제 발생시
- GUI와 콘솔 로그를 확인하세요.
- Whisper 관련 오류: torch 설치 또는 모델 다운로드 문제일 가능성 높음.
- Resolve 관련 오류: Resolve 설치 및 DaVinciResolveScript 모듈 접근 권한 확인 필요.