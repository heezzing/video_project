"""
OpenAI TTS 6가지 목소리 샘플 생성
실행: ./venv/bin/python scripts/sample_voices.py
결과: audio/voice_samples/ 폴더에 sample_*.mp3 6개 생성
"""

from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR   = Path(__file__).parent.parent
SAMPLE_DIR = BASE_DIR / "audio" / "voice_samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

SAMPLE_TEXT = (
    "안녕하세요. 저는 Transformer와 Attention에 대해 설명해 드릴 강사입니다. "
    "오늘 강의가 여러분께 도움이 되길 바랍니다."
)

VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

if __name__ == "__main__":
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    for voice in VOICES:
        out = SAMPLE_DIR / f"sample_{voice}.mp3"
        print(f"  🎙  {voice} 생성 중...")
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=SAMPLE_TEXT,
            speed=0.95,
        )
        out.write_bytes(response.content)
        print(f"  ✅  저장: {out.name}")

    print(f"\n🎉 완료! audio/voice_samples/ 폴더를 확인하세요.")
