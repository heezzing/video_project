# PPT 설명 영상 자동 생성 파이프라인

**생성모델응용 - K2025016 김희경**

Claude AI와의 대화(바이브코딩)로 제작한 PPT 설명 영상 자동화 파이프라인입니다.

---

## 프로젝트 구조

```
video_project/
├── 유튜브_콘텐츠제작용_슬라이드.pdf   # 원본 슬라이드 PDF
├── TTS_대본_완성본.txt                 # 슬라이드별 TTS 대본 ([슬라이드 N] 태그 구분)
├── 1.mp4 ~ 6.mp4                       # 인트로 영상 소스 클립
├── .env                                # OpenAI API 키
├── venv/                               # Python 가상환경
├── slides/                             # 추출된 슬라이드 이미지 (slide_01.png ~ slide_20.png)
├── audio/                              # 생성된 TTS 음성 (audio_01.mp3 ~ audio_20.mp3)
├── output/                             # 최종 영상 출력 폴더
│   ├── final_video.mp4                 # 오버레이 없는 원본 영상
│   └── final_video_sub.mp4            # 오버레이 적용 최종 완성본 ✅
└── scripts/                            # 자동화 스크립트
```

---

## 실행 순서

> 모든 명령어는 프로젝트 루트에서 실행하세요.
> ```bash
> cd /Users/hk/study/kookmin/video_project
> ```

### Step 1. 슬라이드 이미지 추출

```bash
./venv/bin/python scripts/1_extract_slides.py
```

- PDF → `slides/slide_01.png ~ slide_20.png` 추출

---

### Step 2. TTS 음성 생성

```bash
./venv/bin/python scripts/2_generate_tts.py
```

- `TTS_대본_완성본.txt` 파싱 → OpenAI TTS API → `audio/audio_01.mp3 ~ audio_20.mp3`
- 설정 (`scripts/2_generate_tts.py` 상단):
  - `MODEL`: `tts-1` (빠름) / `tts-1-hd` (고품질)
  - `VOICE`: `nova` (기본값) / alloy, echo, fable, onyx, shimmer
  - `SPEED`: `1.0`

목소리 샘플 미리 듣기:
```bash
./venv/bin/python scripts/sample_voices.py
# → audio/voice_samples/ 폴더에 6가지 목소리 샘플 생성
```

---

### Step 3. 인트로 영상 생성 (슬라이드 1 대체)

```bash
./venv/bin/python scripts/make_intro_video.py
```

- `1.mp4 ~ 6.mp4`를 `1→3→4→5→2→6` 순서로 반복 → 80초짜리 `output/intro_video.mp4` 생성

---

### Step 4. 슬라이드 + 음성 합성 (최종 영상)

```bash
./venv/bin/python scripts/3_make_video.py
```

- 슬라이드 1: `output/intro_video.mp4` + `audio_01.mp3`
- 슬라이드 2~20: `slide_XX.png` + `audio_XX.mp3`
- 출력: `output/final_video.mp4`

---

### Step 5. 오버레이 적용 (최종 완성본)

```bash
./venv/bin/python scripts/7_add_subtitles.py
```

- 좌상단 오버레이 (0~80초 구간):
  - `생성모델응용-K2025016_김희경` (흰 글자, 검정 배경, 30pt)
  - `Attention&Transformer` (흰 글자, 검정 배경, 30pt)
- 출력: `output/final_video_sub.mp4` ✅ **최종 완성본**

---

## 환경 설정

### 가상환경 활성화

```bash
source venv/bin/activate
# 또는 직접 경로 사용
./venv/bin/python scripts/XXX.py
```

### .env 파일

```
OPENAI_API_KEY=sk-...
```

### 패키지 설치

```bash
pip install openai python-dotenv mediapipe librosa numpy pillow
```

---

## 대본 형식

`TTS_대본_완성본.txt`는 아래 형식을 따릅니다:

```
[슬라이드 1] — 제목
예상 낭독 시간: 약 X분
================================================================

본문 내용...

(멈춤)

...

[슬라이드 2] — 제목
...
```

- `[슬라이드 N]` 태그로 슬라이드 구분
- `(멈춤)`, `(잠깐 멈춤)`, `(긴 멈춤)` → TTS 생성 시 자동 제거
- `— 제목` 부분 → TTS 생성 시 자동 제거

---

## 사용 기술

| 항목 | 도구 | 용도 |
|------|------|------|
| AI 코딩 | Claude AI (바이브코딩) | 전체 파이프라인 코드 생성 |
| TTS | OpenAI TTS API (tts-1, nova) | 대본 → 슬라이드별 음성 자동 변환 |
| 영상 합성 | ffmpeg | 슬라이드·음성·오버레이 합성 및 편집 |
| 언어 | Python 3.12 | 전체 자동화 스크립트 |
