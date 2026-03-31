"""
STEP 4: 슬라이드 이미지 + 음성 → 최종 영상 합성
실행: python scripts/3_make_video.py
"""

import subprocess
import os
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
SLIDES_DIR      = BASE_DIR / "slides"
AUDIO_DIR       = BASE_DIR / "audio"
OUTPUT_DIR      = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FINAL_VIDEO     = OUTPUT_DIR / "final_video.mp4"
TOTAL           = 20
SLIDE_01_VIDEO  = BASE_DIR / "output" / "intro_video.mp4"  # slide_01.png 대신 사용할 영상

def get_duration(audio_path: Path) -> float:
    """ffprobe로 오디오 길이(초) 반환"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def make_clip_from_video(video_path: Path, audio_path: Path, out: Path) -> Path:
    """MP4 영상 + 오디오 합성 (영상이 짧으면 반복 재생으로 오디오 길이에 맞춤)"""
    audio_dur = get_duration(audio_path)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(video_path),  # 무한 반복
            "-i", str(audio_path),
            "-filter_complex",
            "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(audio_dur),
            str(out),
        ],
        check=True, capture_output=True
    )
    return out


def make_clip(slide_num: int, tmp_dir: Path) -> Path:
    """슬라이드 이미지 + 오디오 → 개별 클립 생성"""
    img   = SLIDES_DIR / f"slide_{slide_num:02d}.png"
    audio = AUDIO_DIR  / f"audio_{slide_num:02d}.mp3"
    out   = tmp_dir    / f"clip_{slide_num:02d}.mp4"

    if not img.exists():
        raise FileNotFoundError(f"슬라이드 이미지 없음: {img}")
    if not audio.exists():
        raise FileNotFoundError(f"음성 파일 없음: {audio}")

    duration = get_duration(audio)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img),
            "-i", str(audio),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            str(out),
        ],
        check=True, capture_output=True
    )
    return out

def concat_clips(clips: list[Path], output: Path):
    """클립 목록을 하나의 영상으로 이어붙이기"""
    list_file = output.parent / "concat_list.txt"
    with open(list_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output),
        ],
        check=True, capture_output=True
    )
    list_file.unlink()

# ── 실행 ──────────────────────────────────────────────────
if __name__ == "__main__":
    tmp_dir = OUTPUT_DIR / "tmp_clips"
    tmp_dir.mkdir(exist_ok=True)

    clips = []
    for i in range(1, TOTAL + 1):
        clip_path = tmp_dir / f"clip_{i:02d}.mp4"
        if clip_path.exists():
            print(f"  ⏭️  [{i:02d}/{TOTAL}] 이미 존재 — 건너뜀")
            clips.append(clip_path)
            continue

        print(f"  🎬  [{i:02d}/{TOTAL}] 클립 생성 중...")
        try:
            if i == 1 and SLIDE_01_VIDEO.exists():
                clip = make_clip_from_video(
                    SLIDE_01_VIDEO,
                    AUDIO_DIR / "audio_01.mp3",
                    tmp_dir / "clip_01.mp4"
                )
            else:
                clip = make_clip(i, tmp_dir)
            clips.append(clip)
            print(f"  ✅  완료: {clip.name}")
        except Exception as e:
            print(f"  ❌  오류 (slide {i}): {e}")
            break
    else:
        print(f"\n🔗 {len(clips)}개 클립 이어붙이는 중...")
        concat_clips(clips, FINAL_VIDEO)
        print(f"🎉 완료! → {FINAL_VIDEO}")

        # 임시 클립 삭제
        for clip in clips:
            clip.unlink()
        tmp_dir.rmdir()
