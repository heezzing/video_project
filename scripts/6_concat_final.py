"""
STEP 6: combined_clip_01~20 → output/final_avatar_video.mp4
실행: python scripts/6_concat_final.py

전제:
  - output/tmp_avatar/combined_clip_01.mp4 ~ combined_clip_20.mp4 준비됨
결과:
  - output/final_avatar_video.mp4
"""

import subprocess
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
TMP_DIR    = BASE_DIR / "output" / "tmp_avatar"
OUTPUT     = BASE_DIR / "output" / "final_avatar_video.mp4"
TOTAL      = 20


def concat_clips(clips: list[Path], output: Path):
    list_file = output.parent / "concat_avatar_list.txt"
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
        check=True
    )
    list_file.unlink()


if __name__ == "__main__":
    import sys

    clips = []
    missing = []
    for i in range(1, TOTAL + 1):
        p = TMP_DIR / f"combined_clip_{i:02d}.mp4"
        if p.exists():
            clips.append(p)
        else:
            missing.append(i)

    if missing:
        print(f"❌ 누락된 클립: {missing}")
        print(f"   scripts/5_make_avatar_clips.py 를 먼저 실행하세요.")
        sys.exit(1)

    print(f"🔗 {len(clips)}개 클립 이어붙이는 중...")
    concat_clips(clips, OUTPUT)
    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"🎉 완료! → {OUTPUT}  ({size_mb:.1f} MB)")
