"""
1.mp4 ~ 6.mp4 를 랜덤 교차편집 → 80초짜리 intro_video.mp4 생성
실행: ./venv/bin/python scripts/make_intro_video.py
결과: output/intro_video.mp4
"""

import subprocess
import random
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_SEC = 80.0
CLIPS      = [BASE_DIR / f"{i}.mp4" for i in [1, 3, 4, 5, 2, 6]]  # 고정 순서
OUTPUT     = OUTPUT_DIR / "intro_video.mp4"


def get_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def build_playlist(clips: list[Path], target_sec: float) -> tuple:
    """고정 순서로 반복 재생해 target_sec 이상 채우는 플레이리스트 생성"""
    durations = {c: get_duration(c) for c in clips}
    playlist  = []
    total     = 0.0

    while total < target_sec:
        for c in clips:
            playlist.append(c)
            total += durations[c]
            if total >= target_sec:
                break

    return playlist, total


def concat_and_trim(playlist: list[Path], target_sec: float, output: Path):
    """플레이리스트 이어붙이기 → target_sec 길이로 정확히 자르기"""
    list_file = output.parent / "_intro_concat_list.txt"
    with open(list_file, "w") as f:
        for clip in playlist:
            f.write(f"file '{clip.resolve()}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",                     # 오디오 없음 (나중에 audio_01.mp3 합성)
            "-t", str(target_sec),
            str(output),
        ],
        check=True
    )
    list_file.unlink()


if __name__ == "__main__":
    print("🎲 랜덤 플레이리스트 생성 중...")
    playlist, total = build_playlist(CLIPS, TARGET_SEC)

    print(f"   클립 순서: {' → '.join(c.name for c in playlist)}")
    print(f"   총 길이: {total:.1f}초 → {TARGET_SEC}초로 자름\n")

    print("🎬 영상 합성 중...")
    concat_and_trim(playlist, TARGET_SEC, OUTPUT)

    print(f"✅ 완료! → {OUTPUT}")
    print(f"   (오디오 없는 영상이에요. 3_make_video.py가 audio_01.mp3를 합성해요.)")
