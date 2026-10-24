import fitz
import sys

doc = fitz.open("realbook.pdf")
page_num = int(sys.argv[1])  # numéro de page, à partir de 1
page = doc[page_num - 1]

print(f"Taille de la page : {page.rect}")
print("--- Texte natif (position, taille, texte) ---")
for block in page.get_text("dict")["blocks"]:
    if block["type"] != 0:
        continue
    for line in block["lines"]:
        for span in line["spans"]:
            txt = span["text"].strip()
            if txt:
                x, y = span["bbox"][0], span["bbox"][1]
                print(f"y={y:6.1f} x={x:6.1f} taille={span['size']:5.1f}  {txt!r}")

print("--- Images sur la page ---")
print(len(page.get_images()), "image(s)")
