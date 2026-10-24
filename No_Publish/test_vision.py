import ollama, sys

MODEL = "qwen2.5vl:7b"
PROMPT = (
    "Cette image est le haut d'une partition de jazz manuscrite. "
    "Donne UNIQUEMENT le titre du morceau : c'est le gros texte en majuscules, "
    "souligné d'un trait épais. Ignore les indications entre parenthèses "
    "(style, tempo) et le nom du compositeur (souvent précédé d'un tiret). "
    "Si aucun titre n'est visible, réponds exactement : SUITE. "
    "Réponds par le titre seul, sans phrase ni guillemets."
)

for path in sys.argv[1:]:
    r = ollama.chat(model=MODEL, messages=[
        {"role": "user", "content": PROMPT, "images": [path]}
    ])
    print(path, "->", repr(r["message"]["content"].strip()))
