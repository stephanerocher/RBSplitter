import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pathlib import Path

PDF_PATH = "realbook.pdf"
OUT_DIR = Path("standards")
OUT_DIR.mkdir(exist_ok=True)

doc = fitz.open(PDF_PATH)

def get_title(page):
    """Essaie le texte natif, sinon OCR sur le haut de la page."""
    rect = page.rect
    zone = fitz.Rect(0, 0, rect.width, rect.height * 0.15)  # 15% du haut

    text = page.get_text("text", clip=zone).strip()
    if len(text) >= 3:
        return text.split("\n")[0].strip()

    # OCR fallback
    pix = page.get_pixmap(clip=zone, dpi=300)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    text = pytesseract.image_to_string(img, config="--psm 7").strip()
    return text

def clean(name):
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    return name.strip().title()

# 1. Détecter les titres page par page
titles = []
for i, page in enumerate(doc):
    t = get_title(page)
    titles.append(t)
    print(i + 1, "->", repr(t))  # pour vérifier à l'œil
"""
# 2. Regrouper : une page "début" = titre non vide et différent du précédent
starts = []
for i, t in enumerate(titles):
    if t and len(t) > 2:
        starts.append((i, clean(t)))

# 3. Écrire les PDF
for idx, (start, name) in enumerate(starts):
    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(doc)
    out = fitz.open()
    out.insert_pdf(doc, from_page=start, to_page=end - 1)
    out.save(OUT_DIR / f"{name}.pdf")
    out.close()
"""
