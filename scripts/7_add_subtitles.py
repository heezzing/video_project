"""
STEP 7: 대본 기반 한국어 자막 생성 → 영상에 burn-in
실행: ./venv/bin/python scripts/7_add_subtitles.py

전제:
  - output/final_video.mp4 존재
  - TTS_대본_완성본.txt 존재
  - audio/audio_01.mp3 ~ audio_20.mp3 존재

결과:
  - output/subtitles.srt         (자막 파일)
  - output/final_video_sub.mp4   (자막 포함 최종 영상)

자막 스타일:
  - 하단 배치
  - 흰 배경 + 검정 글씨
"""

import re
import subprocess
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
SCRIPT_PATH = BASE_DIR / "TTS_대본_완성본.txt"
AUDIO_DIR   = BASE_DIR / "audio"
OUTPUT_DIR  = BASE_DIR / "output"
SRT_FILE    = OUTPUT_DIR / "subtitles.srt"
INPUT_VIDEO = OUTPUT_DIR / "final_video.mp4"
OUTPUT_VIDEO= OUTPUT_DIR / "final_video_sub.mp4"
FONT_PATH   = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
TOTAL       = 20


# ── 대본 파싱 ─────────────────────────────────────────────
def parse_script(path: Path) -> dict[int, str]:
    text    = path.read_text(encoding="utf-8")
    pattern = r"\[슬라이드\s*(\d+)\]"
    parts   = re.split(pattern, text)
    slides  = {}
    i = 1
    while i < len(parts) - 1:
        num     = int(parts[i])
        content = parts[i + 1]
        lines   = []
        for line in content.splitlines():
            s = line.strip()
            if any(s.startswith(x) for x in ["예상", "===", "END", "※", "[제작", "—", "─"]):
                continue
            if s.startswith("[슬라이드"):
                break
            lines.append(s)
        clean = "\n".join(lines)
        clean = re.sub(r"\(잠깐 멈춤\)|\(멈춤\)|\(긴 멈춤\)", "", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
        if clean:
            slides[num] = clean
        i += 2
    return slides


# ── 오디오 길이 ───────────────────────────────────────────
def get_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


# ── 문장 분리 ─────────────────────────────────────────────
def split_sentences(text: str) -> list[str]:
    """마침표/물음표/느낌표 기준으로 문장 분리, 너무 길면 추가 분리"""
    raw = re.split(r'(?<=[.?!])\s+', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        # 한 문장이 30자 초과면 쉼표/조사 기준으로 추가 분리
        if len(s) > 30:
            parts = re.split(r'(?<=[,])\s*', s)
            chunk = ""
            for p in parts:
                if len(chunk) + len(p) <= 30:
                    chunk += p
                else:
                    if chunk:
                        sentences.append(chunk.strip())
                    chunk = p
            if chunk:
                sentences.append(chunk.strip())
        else:
            sentences.append(s)
    return [s for s in sentences if s]


# ── SRT 시간 포맷 ─────────────────────────────────────────
def fmt_time(sec: float) -> str:
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── SRT 생성 ──────────────────────────────────────────────
def build_srt(slides: dict[int, str]) -> str:
    entries = []
    idx     = 1
    offset  = 0.0   # 슬라이드 누적 시간

    for num in range(1, TOTAL + 1):
        audio_path = AUDIO_DIR / f"audio_{num:02d}.mp3"
        duration   = get_duration(audio_path)
        text       = slides.get(num, "")

        if text:
            sentences  = split_sentences(text)
            total_chars = sum(len(s) for s in sentences) or 1
            t = offset
            for sent in sentences:
                ratio    = len(sent) / total_chars
                seg_dur  = max(1.0, duration * ratio)
                end_t    = min(t + seg_dur, offset + duration - 0.1)
                entries.append(
                    f"{idx}\n{fmt_time(t)} --> {fmt_time(end_t)}\n{sent}\n"
                )
                idx += 1
                t = end_t

        offset += duration

    return "\n".join(entries)


# ── ffmpeg burn-in ────────────────────────────────────────
WATERMARK_TEXT     = "생성모델응용-K2025016_김희경"
WATERMARK_END_SEC  = 80.112   # audio_01.mp3 길이 (1번 클립 종료 시점)

def burn_subtitles(srt: Path, input_video: Path, output_video: Path):
    # 하단 자막: 흰 배경 박스 + 검정 글씨, 크기 30
    sub_style = (
        "FontName=AppleSDGothicNeo,"
        "FontSize=20,"
        "PrimaryColour=&H00000000,"   # 검정 글씨
        "BackColour=&H00FFFFFF,"      # 흰 배경
        "BorderStyle=3,"
        "Outline=0,"
        "Shadow=0,"
        "MarginV=30,"
        "Alignment=2"                 # 하단 중앙
    )
    # 좌상단 첫 번째 줄: "생성모델응용-K2025016_김희경" (1번 클립에만)
    watermark1 = (
        f"drawtext=text='{WATERMARK_TEXT}'"
        f":fontfile=/System/Library/Fonts/AppleSDGothicNeo.ttc"
        f":fontsize=30"
        f":fontcolor=white"
        f":box=1:boxcolor=black:boxborderw=6"
        f":x=10:y=10"
        f":enable='between(t,0,{WATERMARK_END_SEC})'"
    )
    # 좌상단 두 번째 줄: "Attention&Transformer" (1번 클립에만)
    watermark2 = (
        f"drawtext=text='Attention&Transformer'"
        f":fontfile=/System/Library/Fonts/AppleSDGothicNeo.ttc"
        f":fontsize=30"
        f":fontcolor=white"
        f":box=1:boxcolor=black:boxborderw=6"
        f":x=10:y=50"
        f":enable='between(t,0,{WATERMARK_END_SEC})'"
    )
    vf = f"{watermark1},{watermark2}"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(input_video),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_video),
        ],
        check=True
    )


# ── 실행 ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("📖 대본 파싱 중...")
    slides = parse_script(SCRIPT_PATH)
    print(f"   → {len(slides)}개 슬라이드 인식")

    print("⏱  자막 타이밍 계산 중...")
    srt_content = build_srt(slides)
    SRT_FILE.write_text(srt_content, encoding="utf-8")
    print(f"   → {SRT_FILE.name} 저장 완료")

    print("🎬 영상에 자막 burn-in 중... (시간이 걸릴 수 있어요)")
    burn_subtitles(SRT_FILE, INPUT_VIDEO, OUTPUT_VIDEO)

    size_mb = OUTPUT_VIDEO.stat().st_size / (1024 * 1024)
    print(f"\n🎉 완료! → {OUTPUT_VIDEO} ({size_mb:.1f} MB)")
