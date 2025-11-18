# Auto Edit Style - Local MVP (확장판)

요약
- 로컬 GUI 프로그램: "스타일 분석"과 "편집" 기능 제공
- 주요 기능: 샷 분할, 컷 길이 통계, 자막(Whisper), 전환(dissolve) 감지, EDL 생성, FFmpeg 렌더, DaVinci Resolve 타임라인 내보내기

요구사항(요약)
- Python 3.9+
- ffmpeg (시스템 PATH에 있어야 함)
- yt-dlp (선택: 유튜브 다운로드)
- (선택) DaVinci Resolve (타임라인 자동 내보내기)
- (선택/권장) GPU + torch — Whisper(자막) 사용 시 권장

목차
1. 설치(플랫폼별)
2. 가상환경 및 파이썬 의존성 설치
3. 시스템 도구 설치(FFmpeg, yt-dlp)
4. Whisper(자막) 설치권장 및 GPU 설정
5. 실행 예제(간단)
6. 스모크 테스트(오류 감지용)
7. 문제 해결(자주 발생하는 오류와 수정법)
8. 배포/릴리즈(간단)

1. 설치(플랫폼별)
- 공통(먼저)
  1) 저장소 클론:
     git clone https://github.com/junggyeol4444/ai2.git
     cd ai2
  2) 가상환경 생성:
     python3 -m venv .venv
     source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1 (PowerShell) 또는 .\.venv\Scripts\activate.bat (CMD)

- Ubuntu / Debian
  sudo apt update
  sudo apt install -y python3 python3-venv python3-pip ffmpeg
  # optional: yt-dlp
  pip install -U yt-dlp

- macOS (Homebrew)
  brew update
  brew install python ffmpeg yt-dlp
  python3 -m venv .venv
  source .venv/bin/activate

- Windows (PowerShell)
  # Install Python from official installer (3.9+), add to PATH.
  # Install ffmpeg: use winget/choco or download and add to PATH
  winget install --id=Gyan.FFmpeg
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -U pip

2. 파이썬 의존성 설치
  pip install -r requirements.txt

주의:
- 일부 패키지(librosa, ffmpeg 접속 등)는 추가 시스템 라이브러리(예: libsndfile 등)를 요구할 수 있습니다.
- 만약 librosa 설치 문제 발생 시: pip install soundfile 또는 시스템 패키지 설치 필요.

3. Whisper(자막) 설치(권장)
- Whisper는 torch backend가 필요합니다. GPU 사용 환경(CUDA) 추천.
- 예 (CUDA 11.7 예시):
  pip install --upgrade pip
  pip install --extra-index-url https://download.pytorch.org/whl/cu117 torch torchvision
  pip install -U openai-whisper
- CPU만 사용할 경우 model 크기를 "small" 대신 "base" 또는 "tiny"로 선택하면 시간이 단축됩니다.

4. 실행(간단)
- GUI 실행:
  source .venv/bin/activate
  python app.py
- 스타일 분석(로컬 파일):
  - GUI에서 [스타일 분석] → 로컬 파일 선택 → 분석 시작
- 편집:
  - GUI에서 [편집] → 편집할 클립 선택 → 모드(자동 / 스타일) 선택 → 렌더

5. 스모크 테스트(오류 감지)
- 사전: clips/ 폴더에 테스트용 짧은 비디오(예: test.mp4) 1개를 넣으세요.
- 명령:
  source .venv/bin/activate
  python3 scripts/smoke_test.py clips/test.mp4
- 스모크 테스트는 주요 모듈(샷 감지, 오디오 추출, BGM 인덱스, 간단 EDL 생성)을 실행하여 예외를 포착합니다.

6. 자주 발생하는 오류 및 해결법
- ffmpeg not found / subprocess.CalledProcessError
  증상: FFmpeg 호출 시 파일/명령 실패
  해결:
    - ffmpeg가 시스템 PATH에 있는지 확인: ffmpeg -version
    - Windows: ffmpeg 설치 경로를 PATH에 추가
    - FFmpeg 호출 실패 메시지(콘솔)를 확인

- Whisper / torch 관련 오류 (메모리 부족, 모델 로드 실패)
  해결:
    - 작은 모델(tiny/base)을 사용
    - GPU가 없으면 CPU 모드로 시도하되 느림을 감수
    - torch 설치가 플랫폼과 CUDA 버전에 맞는지 확인

- PySceneDetect / OpenCV 프레임 읽기 실패
  해결:
    - opencv-python 버전 충돌 가능 → pip install opencv-python-headless 특정 버전 시도
    - 코덱 지원 문제: ffmpeg 설치 상태 확인

- librosa 오류(sndfile) 또는 soundfile ImportError
  해결:
    - 시스템에 libsndfile 설치(예: Ubuntu: sudo apt install libsndfile1)
    - pip install soundfile

7. 스크립트(권장) — smoke_test.py
- 파일: scripts/smoke_test.py (리포지토리 루트의 scripts/ 폴더에 넣고 실행)
(see scripts/smoke_test.py in repo)

8. 깃 작업(변경·커밋·푸시)
- README를 업데이트한 뒤:
  git add README.md
  git commit -m "docs: expand platform install & run guide"
  git push origin main
