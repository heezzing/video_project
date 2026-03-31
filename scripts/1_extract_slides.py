"""
STEP 2: PDF 슬라이드 → PNG 이미지 추출
실행: python scripts/1_extract_slides.py
"""

import os
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent          # video_project/
PDF_PATH   = BASE_DIR / "유튜브_콘텐츠제작용_슬라이드.pdf"
SLIDES_DIR = BASE_DIR / "slides"
SLIDES_DIR.mkdir(exist_ok=True)

# ── 변환 실행 ──────────────────────────────────────────────
def extract_slides():
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("❌ PyMuPDF가 없습니다. 아래 명령어로 설치해주세요:")
        print("   pip install pymupdf")
        return

    print(f"📄 PDF 불러오는 중: {PDF_PATH}")
    doc = fitz.open(str(PDF_PATH))
    total = len(doc)

    for i, page in enumerate(doc):
        # 1920×1080 기준 DPI (PDF 기본 72dpi 기준 → 2배 = 144dpi)
        mat  = fitz.Matrix(2.0, 2.0)
        pix  = page.get_pixmap(matrix=mat)
        out  = SLIDES_DIR / f"slide_{i+1:02d}.png"
        pix.save(str(out))
        print(f"  ✅ [{i+1:02d}/{total}] {out.name} 저장 완료")

    doc.close()
    print(f"\n🎉 완료! slides/ 폴더에 {total}장 저장됐습니다.")

if __name__ == "__main__":
    extract_slides()
