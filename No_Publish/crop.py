import pymupdf
import sys

doc = pymupdf.open("realbook.pdf")
page_num = int(sys.argv[1])
page = doc[page_num - 1]

# Zone du haut : 18 % de la hauteur, sans le coin du numéro de page
r = page.rect
clip = pymupdf.Rect(0, 0, r.width * 0.85, r.height * 0.18)

pix = page.get_pixmap(clip=clip, dpi=300)
pix.save(f"crop_{page_num}.png")
print(f"Sauvé : crop_{page_num}.png")
