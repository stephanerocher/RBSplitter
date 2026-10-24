# titres.py
import pymupdf, ollama, sys, csv, os

PDF = "realbook.pdf"          # <-- adapte le nom de ton fichier
MODEL = "qwen2.5vl:7b"
CROP_HAUT = 0.22              # fraction de la hauteur de page à garder (haut)
ZOOM = 3                      # résolution du rendu
PROMPT = (
    "Cette image est le haut d'une partition de jazz manuscrite. "
    "Donne UNIQUEMENT le titre du morceau : c'est le gros texte en majuscules, "
    "souligné d'un trait épais. Ignore les indications entre parenthèses "
    "(style, tempo) et le nom du compositeur (souvent précédé d'un tiret). "
    "Si aucun titre n'est visible, réponds exactement : SUITE. "
    "Réponds par le titre seul, sans phrase ni guillemets."
)

debut = int(sys.argv[1]) if len(sys.argv) > 1 else 200   # numéro de page PDF (1 = première)
nb = int(sys.argv[2]) if len(sys.argv) > 2 else 20

os.makedirs("crops", exist_ok=True)
doc = pymupdf.open(PDF)
rows = []

for n in range(debut, min(debut + nb, len(doc) + 1)):
    page = doc[n - 1]
    r = page.rect
    clip = pymupdf.Rect(0, 0, r.width, r.height * CROP_HAUT)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip)
    chemin = f"crops/page_{n:03d}.png"
    pix.save(chemin)

    rep = ollama.chat(model=MODEL, messages=[
        {"role": "user", "content": PROMPT, "images": [chemin]}
    ])
    titre = rep["message"]["content"].strip()
    print(f"{n:3d} -> {titre!r}")
    rows.append((n, titre))

with open("titres.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows([("page", "titre"), *rows])
