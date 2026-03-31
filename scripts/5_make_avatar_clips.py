"""
STEP 5: 오디오 진폭 분석 → 아바타 말하기 애니메이션 → 슬라이드+아바타 합성 클립 생성
실행: python scripts/5_make_avatar_clips.py

전제:
  - avatar/mouth_closed.png, avatar/mouth_open.png 준비됨 (4_prepare_mouth.py 실행 후)
  - slides/slide_01.png ~ slide_20.png
  - audio/audio_01.mp3 ~ audio_20.mp3

결과:
  - output/tmp_avatar/combined_clip_XX.mp4  (1920x1080, 슬라이드 70% + 아바타 30%)
"""

import subprocess
import shutil
import numpy as np
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
AVATAR_DIR  = BASE_DIR / "avatar"
SLIDES_DIR  = BASE_DIR / "slides"
AUDIO_DIR   = BASE_DIR / "audio"
OUTPUT_DIR  = BASE_DIR / "output"
TMP_DIR     = OUTPUT_DIR / "tmp_avatar"
TMP_DIR.mkdir(parents=True, exist_ok=True)

CLOSED_IMG  = AVATAR_DIR / "mouth_closed.png"
OPEN_IMG    = AVATAR_DIR / "mouth_open.png"

TOTAL       = 20
FPS         = 25
SLIDE_W     = 1344   # 1920 * 0.70
AVATAR_W    = 576    # 1920 * 0.30
HEIGHT      = 1080

# 진폭 임계값: 이 값보다 크면 입 open. 0.0~1.0 사이, 필요시 조정.
AMPLITUDE_THRESHOLD = 0.015


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def get_amplitude_frames(audio_path: Path, fps: int) -> np.ndarray:
    """오디오를 fps 단위로 RMS 진폭 분석, 0~1 정규화 배열 반환"""
    import librosa
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    hop_length = sr // fps
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    if rms.max() > 0:
        rms = rms / rms.max()
    return rms


def make_avatar_video(slide_num: int, frames_dir: Path) -> Path:
    """진폭 기반 입 애니메이션 프레임 생성 → avatar 영상"""
    from PIL import Image

    audio_path = AUDIO_DIR / f"audio_{slide_num:02d}.mp3"
    out_path   = TMP_DIR / f"avatar_clip_{slide_num:02d}.mp4"

    if out_path.exists():
        return out_path

    amp = get_amplitude_frames(audio_path, FPS)
    closed = Image.open(CLOSED_IMG)
    opened = Image.open(OPEN_IMG)

    frame_dir = frames_dir / f"slide_{slide_num:02d}"
    frame_dir.mkdir(exist_ok=True)

    for i, a in enumerate(amp):
        frame = opened if a > AMPLITUDE_THRESHOLD else closed
        frame.save(frame_dir / f"frame_{i:05d}.png")

    # PNG 시퀀스 → MP4
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(frame_dir / "frame_%05d.png"),
            "-i", str(audio_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(out_path),
        ],
        check=True, capture_output=True
    )

    # 프레임 임시 폴더 삭제
    shutil.rmtree(frame_dir)
    return out_path


def make_slide_video(slide_num: int) -> Path:
    """슬라이드 이미지 + 오디오 → 슬라이드 영상 (1344x1080)"""
    slide_path = SLIDES_DIR / f"slide_{slide_num:02d}.png"
    audio_path = AUDIO_DIR  / f"audio_{slide_num:02d}.mp3"
    out_path   = TMP_DIR    / f"slide_clip_{slide_num:02d}.mp4"

    if out_path.exists():
        return out_path

    duration = get_audio_duration(audio_path)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(slide_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-vf", f"scale={SLIDE_W}:{HEIGHT}:force_original_aspect_ratio=decrease,"
                   f"pad={SLIDE_W}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black",
            str(out_path),
        ],
        check=True, capture_output=True
    )
    return out_path


def combine_side_by_side(slide_clip: Path, avatar_clip: Path, slide_num: int) -> Path:
    """슬라이드(1344) + 아바타(576) → 합성 클립(1920x1080)"""
    out_path = TMP_DIR / f"combined_clip_{slide_num:02d}.mp4"

    if out_path.exists():
        return out_path

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(slide_clip),
            "-i", str(avatar_clip),
            "-filter_complex",
            f"[0:v]scale={SLIDE_W}:{HEIGHT}[left];"
            f"[1:v]scale={AVATAR_W}:{HEIGHT}[right];"
            f"[left][right]hstack=inputs=2[v]",
            "-map", "[v]",
            "-map", "0:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path),
        ],
        check=True, capture_output=True
    )
    return out_path


# ── 실행 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    for f in [CLOSED_IMG, OPEN_IMG]:
        if not f.exists():
            print(f"❌ {f.name} 없음! scripts/4_prepare_mouth.py 먼저 실행하세요.")
            sys.exit(1)

    frames_tmp = TMP_DIR / "frames_tmp"
    frames_tmp.mkdir(exist_ok=True)

    # 테스트 모드: TEST=1 이면 슬라이드 1개만 처리
    test_only = len(sys.argv) > 1 and sys.argv[1] == "--test"
    targets   = [1] if test_only else range(1, TOTAL + 1)
    total     = 1  if test_only else TOTAL

    for i in targets:
        print(f"\n[{i:02d}/{total}] 슬라이드 {i} 처리 중...")

        print(f"  🎙  아바타 영상 생성...")
        av = make_avatar_video(i, frames_tmp)
        print(f"  ✅ {av.name}")

        print(f"  🖼  슬라이드 영상 생성...")
        sv = make_slide_video(i)
        print(f"  ✅ {sv.name}")

        print(f"  🔗 좌우 합성...")
        cv = combine_side_by_side(sv, av, i)
        print(f"  ✅ {cv.name}")

    shutil.rmtree(frames_tmp, ignore_errors=True)

    if test_only:
        print(f"\n🎬 테스트 완료! output/tmp_avatar/combined_clip_01.mp4 를 확인하세요.")
        print(f"   문제 없으면: python scripts/5_make_avatar_clips.py  (전체 실행)")
    else:
        print(f"\n🎉 전체 완료! scripts/6_concat_final.py 를 실행하세요.")
