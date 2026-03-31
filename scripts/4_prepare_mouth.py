"""
STEP 4: avatar.png → mouth_closed.png / mouth_open.png 자동 생성
실행: ./venv/bin/python scripts/4_prepare_mouth.py

준비:
  - 프로젝트 루트에 avatar.png 배치 (정면 얼굴 사진 또는 일러스트)
결과:
  - avatar/mouth_closed.png  (576x1080, 입 닫힘)
  - avatar/mouth_open.png    (576x1080, 입 열림)
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR    = Path(__file__).parent.parent
AVATAR_SRC  = BASE_DIR / "avatar.png"
AVATAR_DIR  = BASE_DIR / "avatar"
AVATAR_DIR.mkdir(exist_ok=True)

OUT_CLOSED  = AVATAR_DIR / "mouth_closed.png"
OUT_OPEN    = AVATAR_DIR / "mouth_open.png"

PANEL_W, PANEL_H = 576, 1080


def load_and_resize(src: Path) -> Image.Image:
    img = Image.open(src).convert("RGB")
    iw, ih = img.size
    scale = max(PANEL_W / iw, PANEL_H / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - PANEL_W) // 2
    top  = (new_h - PANEL_H) // 2
    return img.crop((left, top, left + PANEL_W, top + PANEL_H))


def detect_mouth_opencv(src: Path):
    """OpenCV 얼굴 박스 기반으로 입 위치 추정 (패널 기준 좌표 반환)"""
    import cv2

    img_bgr = cv2.imread(str(src))
    if img_bgr is None:
        return None

    oh, ow = img_bgr.shape[:2]

    # 패널 기준 scale/offset (load_and_resize 와 동일 로직)
    scale    = max(PANEL_W / ow, PANEL_H / oh)
    new_w    = int(ow * scale)
    new_h    = int(oh * scale)
    offset_x = (new_w - PANEL_W) // 2
    offset_y = (new_h - PANEL_H) // 2

    def to_panel(x, y):
        return x * scale - offset_x, y * scale - offset_y

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60, 60))
    if len(faces) == 0:
        return None

    fx, fy, fw, fh = faces[0]

    # 입 = 얼굴 박스 하단 82% 지점 (눈(35%) → 코(60%) → 입(82%) 비율)
    abs_cx = fx + fw // 2
    abs_cy = fy + int(fh * 0.82)
    pcx, pcy = to_panel(abs_cx, abs_cy)
    prx = fw * scale * 0.22
    pry = fh * scale * 0.07

    return {"cx": pcx, "cy": pcy, "rx": prx, "ry": pry}


def heuristic_mouth(panel_w, panel_h):
    """얼굴 감지 실패시 화면 비율 기반 heuristic (정면 인물 사진 기준)"""
    cx = panel_w * 0.5
    cy = panel_h * 0.72      # 세로 72% 지점 (턱-코 중간)
    rx = panel_w * 0.14
    ry = panel_h * 0.025
    return {"cx": cx, "cy": cy, "rx": rx, "ry": ry}


def sample_lip_color(base_img: Image.Image, cx: float, cy: float, ry: float) -> tuple:
    """원본 이미지에서 입 주변 색상 샘플링 → 입술 색 추정"""
    sample_y = int(cy - ry * 1.5)
    sample_x = int(cx)
    w, h = base_img.size
    sample_x = max(0, min(w - 1, sample_x))
    sample_y = max(0, min(h - 1, sample_y))
    r, g, b = base_img.getpixel((sample_x, sample_y))
    # 피부색에서 입술색 추정: 더 붉고 어둡게
    lip_r = min(255, int(r * 0.85 + 30))
    lip_g = max(0,   int(g * 0.60 - 10))
    lip_b = max(0,   int(b * 0.60 - 10))
    return (lip_r, lip_g, lip_b)


def make_mouth_open(base_img: Image.Image, mouth: dict) -> Image.Image:
    """자연스러운 입 열림 이미지 생성"""
    import numpy as np

    cx, cy = mouth["cx"], mouth["cy"]
    rx, ry = mouth["rx"], mouth["ry"]

    open_img = base_img.copy()
    w, h = open_img.size

    lip_color  = sample_lip_color(base_img, cx, cy, ry)
    dark_color = (max(0, lip_color[0] - 60), max(0, lip_color[1] - 40), max(0, lip_color[2] - 40))

    # ── 1. 입 내부 (어두운 타원) ─────────────────────────────
    inner_mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(inner_mask)
    # 좌우는 rx 그대로, 세로는 약간 납작한 타원
    md.ellipse([cx - rx, cy - ry * 0.85, cx + rx, cy + ry * 0.85], fill=255)
    inner_mask = inner_mask.filter(ImageFilter.GaussianBlur(radius=max(3, int(ry * 0.5))))

    inner_layer = Image.new("RGB", (w, h), dark_color)
    open_img = Image.composite(inner_layer, open_img, inner_mask)

    draw = ImageDraw.Draw(open_img)

    # ── 2. 아랫입술 (두툼하게) ───────────────────────────────
    low_ry = max(3, int(ry * 0.55))
    low_mask = Image.new("L", (w, h), 0)
    ld = ImageDraw.Draw(low_mask)
    ld.ellipse(
        [cx - rx * 0.88, cy + ry * 0.15,
         cx + rx * 0.88, cy + ry * 0.85 + low_ry * 2],
        fill=220
    )
    low_mask = low_mask.filter(ImageFilter.GaussianBlur(radius=max(2, int(ry * 0.4))))
    low_layer = Image.new("RGB", (w, h), lip_color)
    open_img = Image.composite(low_layer, open_img, low_mask)

    # ── 3. 윗입술 (좀 더 얇게) ───────────────────────────────
    up_ry = max(2, int(ry * 0.38))
    up_mask = Image.new("L", (w, h), 0)
    ud = ImageDraw.Draw(up_mask)
    ud.ellipse(
        [cx - rx * 0.88, cy - ry * 0.85 - up_ry * 2,
         cx + rx * 0.88, cy - ry * 0.15],
        fill=200
    )
    up_mask = up_mask.filter(ImageFilter.GaussianBlur(radius=max(2, int(ry * 0.35))))
    darker_lip = tuple(max(0, c - 20) for c in lip_color)
    up_layer = Image.new("RGB", (w, h), darker_lip)
    open_img = Image.composite(up_layer, open_img, up_mask)

    # ── 4. 인중 위 경계 부드럽게 블렌딩 ─────────────────────
    blend_mask = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(blend_mask)
    bd.ellipse(
        [cx - rx * 1.05, cy - ry * 1.35,
         cx + rx * 1.05, cy + ry * 1.35],
        fill=80
    )
    blend_mask = blend_mask.filter(ImageFilter.GaussianBlur(radius=max(4, int(ry * 0.7))))
    open_img = Image.composite(open_img, base_img, blend_mask)

    return open_img


# ── 실행 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if not AVATAR_SRC.exists():
        print(f"❌ avatar.png 가 없습니다!")
        print(f"   → 프로젝트 루트({BASE_DIR})에 avatar.png 를 배치해 주세요.")
        sys.exit(1)

    print(f"📸 avatar.png 로드 및 리사이즈 중... ({PANEL_W}x{PANEL_H})")
    panel_img = load_and_resize(AVATAR_SRC)
    panel_img.save(OUT_CLOSED)
    print(f"  ✅ mouth_closed.png 저장")

    print(f"🔍 얼굴/입 위치 감지 중...")
    mouth = detect_mouth_opencv(AVATAR_SRC)

    if mouth:
        print(f"  ✅ 입 위치 감지 성공 (cx={mouth['cx']:.0f}, cy={mouth['cy']:.0f})")
    else:
        print(f"  ⚠️  얼굴 감지 실패 → 화면 비율 기반 heuristic 사용")
        mouth = heuristic_mouth(PANEL_W, PANEL_H)

    open_img = make_mouth_open(panel_img, mouth)
    open_img.save(OUT_OPEN)
    print(f"  ✅ mouth_open.png 저장")

    print(f"\n🎉 완료! avatar/ 폴더를 확인하세요.")
    print(f"   mouth_closed.png / mouth_open.png 두 파일을 열어서")
    print(f"   입 위치가 자연스러운지 확인한 뒤 다음 단계를 실행하세요.")
