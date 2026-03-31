"""
STEP 3: 대본 → OpenAI TTS → 슬라이드별 MP3 생성
실행: python scripts/2_generate_tts.py
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

# ── 설정 ───────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
SCRIPT_PATH = BASE_DIR / "TTS_대본_완성본.txt"
AUDIO_DIR  = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# TTS 설정
MODEL  = "tts-1"          # tts-1 (빠름/저렴) | tts-1-hd (고품질)
VOICE  = "nova"           # alloy | echo | fable | onyx | nova | shimmer
SPEED  = 1.0              # 0.25 ~ 4.0 (1.0 = 기본, 강의는 0.9~1.0 추천)

# ── 대본 파싱: 슬라이드별로 분리 ──────────────────────────
def parse_script(path: Path) -> dict[int, str]:
    text = path.read_text(encoding="utf-8")
    # [슬라이드 N] 태그 기준으로 분리
    pattern = r"\[슬라이드\s*(\d+)\]"
    parts   = re.split(pattern, text)

    slides = {}
    i = 1
    while i < len(parts) - 1:
        num     = int(parts[i])
        content = parts[i + 1]
        # 메타 정보 줄 제거 (예상 낭독 시간, ===, END 등)
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(x) for x in ["예상", "===", "END", "※", "[제작", "—", "─"]):
                continue
            if stripped.startswith("[슬라이드"):
                break
            lines.append(stripped)
        # 멈춤 태그 제거 후 빈 줄 정리
        clean = "\n".join(lines)
        clean = re.sub(r"\(잠깐 멈춤\)|\(멈춤\)|\(긴 멈춤\)", "", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
        if clean:
            slides[num] = clean
        i += 2

    return slides

# ── TTS 생성 ───────────────────────────────────────────────
def generate_tts(slides: dict[int, str]):
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ openai 패키지가 없습니다. 아래 명령어로 설치해주세요:")
        print("   pip install openai")
        return

    client = OpenAI(api_key=OPENAI_API_KEY)
    total  = len(slides)

    for num, text in sorted(slides.items()):
        out = AUDIO_DIR / f"audio_{num:02d}.mp3"
        if out.exists():
            print(f"  ⏭️  [{num:02d}/{total}] 이미 존재 — 건너뜀: {out.name}")
            continue

        print(f"  🎙️  [{num:02d}/{total}] 생성 중: slide {num} ({len(text)}자)")
        try:
            response = client.audio.speech.create(
                model=MODEL,
                voice=VOICE,
                input=text,
                speed=SPEED,
            )
            response.stream_to_file(str(out))
            print(f"  ✅  저장 완료: {out.name}")
        except Exception as e:
            print(f"  ❌  오류 (slide {num}): {e}")

    print(f"\n🎉 완료! audio/ 폴더에 {total}개 파일 생성됐습니다.")

# ── 실행 ───────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"📖 대본 파싱 중: {SCRIPT_PATH.name}")
    slides = parse_script(SCRIPT_PATH)
    print(f"   → {len(slides)}개 슬라이드 대본 인식\n")
    generate_tts(slides)
