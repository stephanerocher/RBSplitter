#!/usr/bin/env python3
"""Decoupe un recueil PDF en un PDF par standard (multi-pages gere)."""
import csv
import io
import os
import re
from concurrent.futures import ThreadPoolExecutor

import pymupdf
import ollama
from PIL import Image

# ---------------- CONFIG ----------------
MODEL = "qwen2.5vl:3b"           # 3b = ~2x plus rapide que 7b
PAGE_FIN = None                  # None = jusqu'a la fin
CROP_RATIO = 0.20                # bande haute envoyee au modele (petite = rapide)
ZOOM = 1.0                       # 1.0 = rapide, 2.0 = precis
WORKERS = 1                      # 1 = sequentiel, 2 si Ollama a OLLAMA_NUM_PARALLEL>=2

# Export leger
MODE_EXPORT = "auto"             # "auto" | "gray_jpeg" | "bw_1bit"
ZOOM_EXPORT = 2                # ~115 dpi ; 2.0 si trop flou
QUALITE_JPEG = 58                # 50-70

PROMPT = (
    "Cette image est le haut d'une partition de jazz. "
    "Le TITRE du morceau est le gros texte en majuscules italiques, "
    "souvent sur UNE OU DEUX LIGNES. Recopie le titre COMPLET, "
    "toutes les lignes jointes par un espace, exactement lettre par lettre. "
    "Ignore les petits chiffres (numeros de page), les indications entre "
    "parentheses (style, tempo) et le nom du compositeur. "
    "S'il n'y a PAS de gros titre (page qui n'a que des portees), "
    "reponds exactement : SUITE. N'invente jamais un titre. "
    "Reponds par le titre seul ou par SUITE, sans phrase ni guillemets."
)

# Renseignes au demarrage par demander_parametres()
SOURCE = CLEAN = OUT_DIR = CACHE = RAPPORT = ""
PAGE_DEBUT = 1


# ---------------- SAISIE ----------------
def demander_parametres():
    global SOURCE, CLEAN, OUT_DIR, CACHE, RAPPORT, PAGE_DEBUT

    while True:
        nom = input("Nom du fichier PDF (avec ou sans .pdf) : ").strip().strip('"').strip("'")
        if not nom.lower().endswith(".pdf"):
            nom += ".pdf"
        if os.path.isfile(nom):
            break
        print(f"  Fichier introuvable : {nom}")

    base = os.path.splitext(os.path.basename(nom))[0]
    SOURCE = nom
    CLEAN = f"{base}_clean.pdf"
    OUT_DIR = base                      # dossier d'export = nom du PDF
    CACHE = f"{base}_titres.csv"
    RAPPORT = f"{base}_titres_pages.txt"

    d = pymupdf.open(SOURCE)
    total = len(d)
    d.close()

    while True:
        rep = input(f"Page de depart (1-{total}) [defaut 1] : ").strip()
        if not rep:
            PAGE_DEBUT = 1
            break
        if rep.isdigit() and 1 <= int(rep) <= total:
            PAGE_DEBUT = int(rep)
            break
        print(f"  Entre un nombre entre 1 et {total}.")

    print(f"\nPDF : {SOURCE} | page de depart : {PAGE_DEBUT} | export : {OUT_DIR}/\n")


# ---------------- OUTILS ----------------
def normaliser(titre):
    t = titre.strip().strip('"').strip("'").strip()
    t = re.sub(r"\s*\((?:p\.?|page|pg\.?)\s*\d+\)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*\(\s*(?:suite|cont\.?|continued)\s*\)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*\(\d+\s*/\s*\d+\)\s*$", "", t)
    return t.strip()


def nom_fichier(titre):
    s = re.sub(r'[\\/:*?"<>|]', "", titre).strip()
    return s or "SANS_TITRE"


def nettoyer_pdf():
    if os.path.exists(CLEAN):
        print("PDF nettoye deja present, etape sautee.")
        return
    print("Nettoyage du PDF source...")
    doc = pymupdf.open(SOURCE)
    doc.save(CLEAN, garbage=4, deflate=True, clean=True)
    doc.close()
    print("OK")


def charger_cache():
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].isdigit():
                    cache[int(row[0])] = row[1]
    return cache


def sauver_cache(cache):
    with open(CACHE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for p in sorted(cache):
            w.writerow([p, cache[p]])


def lire_titre(num):
    """Crop le haut de la page, interroge le modele, supprime le fichier temporaire.
    Ouvre son propre document (PyMuPDF n'est pas thread-safe)."""
    doc = pymupdf.open(CLEAN)
    try:
        page = doc[num - 1]
        r = page.rect
        clip = pymupdf.Rect(0, 0, r.width, r.height * CROP_RATIO)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip)
        tmp = f"_crop_tmp_{num}.png"
        pix.save(tmp)
    finally:
        doc.close()
    try:
        rep = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": PROMPT, "images": [tmp]}],
            options={"num_predict": 32, "temperature": 0},
            keep_alive="30m",
        )
        texte = rep["message"]["content"].strip()
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return texte.splitlines()[0].strip() if texte else ""


def traiter_page(num):
    try:
        return num, lire_titre(num) or "SUITE"
    except Exception as e:
        print(f"  p.{num}: erreur ({e}) -> SUITE")
        return num, "SUITE"


# ---------------- EXPORT LEGER ----------------
def page_vers_image(page):
    """Rend la page en niveaux de gris et retourne (bytes, largeur_pt, hauteur_pt).
    Encode en TIFF G4 1-bit si la page est quasi N&B pure, sinon JPEG gris."""
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM_EXPORT, ZOOM_EXPORT),
                          colorspace=pymupdf.csGRAY, alpha=False)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)

    mode = MODE_EXPORT
    if mode == "auto":
        hist = img.histogram()
        extremes = sum(hist[:40]) + sum(hist[215:])
        mode = "bw_1bit" if extremes / (pix.width * pix.height) > 0.97 else "gray_jpeg"

    buf = io.BytesIO()
    if mode == "bw_1bit":
        img.point(lambda v: 255 if v > 160 else 0).convert("1").save(
            buf, "TIFF", compression="group4")
    else:
        img.save(buf, "JPEG", quality=QUALITE_JPEG, optimize=True)
    return buf.getvalue(), page.rect.width, page.rect.height


# ---------------- ETAPES ----------------
def detecter(doc):
    cache = charger_cache()
    fin = PAGE_FIN or len(doc)
    a_faire = [p for p in range(PAGE_DEBUT, fin + 1) if p not in cache]

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for num, titre in ex.map(traiter_page, a_faire):
            cache[num] = titre
            sauver_cache(cache)
            print(f"{num} -> {titre}")

    titres = {p: normaliser(t) for p, t in cache.items()
              if PAGE_DEBUT <= p <= fin}

    with open(RAPPORT, "w", encoding="utf-8") as f:
        for p in sorted(titres):
            f.write(f"{p}\t{titres[p]}\n")
    print(f"\nRapport ecrit dans {RAPPORT}")
    return titres


def grouper(titres):
    groupes = []          # liste de [titre, [pages]]
    dernier = None
    for p in sorted(titres):
        t = titres[p]
        if groupes and (t.upper() == "SUITE" or t.lower() == (dernier or "").lower()):
            groupes[-1][1].append(p)
        else:
            groupes.append([t, [p]])
            dernier = t
    return groupes


def exporter(doc, groupes):
    os.makedirs(OUT_DIR, exist_ok=True)
    utilises = {}
    for titre, pages in groupes:
        base = nom_fichier(titre)
        n = utilises.get(base.lower(), 0)
        utilises[base.lower()] = n + 1
        nom = base if n == 0 else f"{base} ({n + 1})"
        out = pymupdf.open()
        for p in pages:
            data, w, h = page_vers_image(doc[p - 1])
            np_ = out.new_page(width=w, height=h)
            np_.insert_image(np_.rect, stream=data)
        out.save(os.path.join(OUT_DIR, nom + ".pdf"),
                 garbage=4, deflate=True, clean=True)
        out.close()
        print(f"{nom}.pdf  ({len(pages)} p.)")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    demander_parametres()
    nettoyer_pdf()
    doc = pymupdf.open(CLEAN)
    titres = detecter(doc)
    groupes = grouper(titres)
    print(f"\n{len(groupes)} standards detectes. Export...")
    exporter(doc, groupes)
    doc.close()
    print("Termine.")