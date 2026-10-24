# RBSplitter

Découpe automatiquement un PDF de recueil de partitions (type *Real Book*, ~300 pages) en **un PDF par morceau**, nommé d'après le titre lu en haut de la partition.

- Détection des titres par un modèle de vision **local** (Ollama + Qwen2.5-VL) : aucune donnée envoyée sur Internet.
- Gestion des morceaux sur **2 ou 3 pages** (regroupés dans un seul PDF).
- Export **léger** (gris / noir & blanc) avec qualité réglable.
- Cache des titres détectés (`*_titres.csv`) pour relancer l'export sans repasser dans le modèle.

---

## Fonctionnement

1. **Nettoyage** du PDF source (copie propre dans un fichier temporaire).
2. **Détection** : la bande haute de chaque page est envoyée au modèle de vision, qui renvoie le titre (ou `SUITE` si la page continue le morceau précédent).
3. **Regroupement** des pages `SUITE` avec leur morceau.
4. **Export** : un PDF par standard dans un dossier portant le nom du PDF source.

---

## Prérequis

| Élément | Version conseillée |
|---|---|
| Python | 3.10 ou plus récent |
| [Ollama](https://ollama.com) | dernière version |
| Modèle | `qwen2.5vl:3b` (~3 Go) |
| RAM | 8 Go minimum, 16 Go confortable |

### Dépendances Python

- `pymupdf`
- `ollama`
- `pillow`

---

## Installation sur macOS

```bash
# 1. Cloner le dépôt
git clone https://github.com/stephanerocher/RBSplitter.git
cd <RBSplitter>

# 2. Installer Ollama (via Homebrew, ou télécharger l'app sur ollama.com)
brew install ollama

# 3. Lancer le serveur Ollama (laisser ce terminal ouvert,
#    ou utiliser l'application Ollama qui le lance automatiquement)
ollama serve
```

Dans un **second terminal** :

```bash
cd <RBSplitter>

# 4. Télécharger le modèle de vision (une seule fois)
ollama pull qwen2.5vl:3b

# 5. Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 6. Installer les dépendances
pip install --upgrade pip
pip install pymupdf ollama pillow

# 7. Lancer le programme
python decouper.py
```

> Sur Mac Apple Silicon (M1/M2/M3/M4), Ollama utilise automatiquement le GPU : aucune configuration supplémentaire.

---

## Installation sur Linux (Debian / Ubuntu)

```bash
# 1. Cloner le dépôt
git clone https://github.com/stephanerocher/RBSplitter.git
cd <RBSplitter>

# 2. Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 3. Vérifier que le service tourne (installé en service systemd)
systemctl status ollama
# sinon : ollama serve
```

```bash
# 4. Télécharger le modèle
ollama pull qwen2.5vl:3b

# 5. Python, pip et venv (si absents)
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

# 6. Environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 7. Dépendances
pip install --upgrade pip
pip install pymupdf ollama pillow

# 8. Lancer
python decouper.py
```

> Sur d'autres distributions : Fedora `sudo dnf install python3 python3-pip`, Arch `sudo pacman -S python python-pip`.
> Avec une carte NVIDIA, installe les pilotes propriétaires : Ollama utilisera le GPU. Sinon, tout fonctionne sur CPU, en plus lent.

---

## Fichier `requirements.txt` (optionnel)

```txt
pymupdf
ollama
pillow
```

Installation en une commande :

```bash
pip install -r requirements.txt
```

---

## Utilisation

1. Place ton PDF dans le dossier du projet (ex. `monrealbook.pdf`).
2. Vérifie que **Ollama tourne** et que le modèle est téléchargé.
3. Active le venv puis lance :

```bash
source venv/bin/activate
python decouper.py
```

Le programme te demande :

- **Le nom du fichier PDF** (avec ou sans `.pdf`). Le même nom sert pour le dossier d'export.
- **Le numéro de la page de départ**, pour ignorer la couverture, la préface ou l'index.

Résultat :

```
realbook/
├── ALL THE THINGS YOU ARE.pdf
├── AUTUMN LEAVES.pdf
├── BLUE BOSSA.pdf
├── ...
realbook_titres.csv      # cache des titres détectés
```

### Relancer l'export sans re-détecter

Si `realbook_titres.csv` existe, la détection est ignorée pour les pages déjà traitées. Pour tout recommencer de zéro, supprime ce fichier.

---

## Configuration

Les réglages se trouvent en haut de `decouper.py`.

| Variable | Défaut | Rôle |
|---|---|---|
| `MODEL` | `qwen2.5vl:3b` | Modèle Ollama utilisé (`qwen2.5vl:7b` = plus précis, ~2x plus lent) |
| `PAGE_FIN` | `None` | Dernière page à traiter (`None` = jusqu'à la fin) |
| `CROP_RATIO` | `0.20` | Part haute de la page envoyée au modèle |
| `ZOOM` | `1.0` | Résolution de l'image envoyée au modèle |
| `WORKERS` | `1` | Nombre de requêtes parallèles |
| `MODE_EXPORT` | `"auto"` | `auto`, `gray_jpeg` ou `bw_1bit` |
| `ZOOM_EXPORT` | `2.0` | Résolution des PDF exportés |
| `QUALITE_JPEG` | `70` | Qualité JPEG (50 à 80) |

### Qualité des PDF exportés

| `ZOOM_EXPORT` | Résolution | Usage |
|---|---|---|
| 1.6 | ~115 dpi | Lecture sur tablette, très léger |
| 2.0 | ~145 dpi | Bon compromis |
| 2.5 | ~180 dpi | Impression nette |
| 3.0 | ~215 dpi | Quasi archive |

Pour le meilleur rendu : `MODE_EXPORT = "gray_jpeg"`, `ZOOM_EXPORT = 2.0`, `QUALITE_JPEG = 75`.

Si le noir & blanc 1 bit perd des traits fins ou fait apparaître des taches, ajuste le seuil dans `page_vers_image` :

```python
img.point(lambda v: 255 if v > 160 else 0)
```

Monte la valeur (180-200) si des traits disparaissent, baisse-la (130-140) si le papier apparaît en taches.

---

## Dépannage

| Problème | Solution |
|---|---|
| `FileNotFoundError: no such file` | Le PDF doit être dans le dossier d'où tu lances le script, ou donne un chemin complet. |
| `ConnectionError` / connexion refusée à Ollama | Lance `ollama serve` (ou l'app Ollama sur Mac). |
| `model not found` | Exécute `ollama pull qwen2.5vl:3b`. |
| Titres mal lus ou tronqués | Passe à `qwen2.5vl:7b` et/ou augmente `CROP_RATIO` (0.25) et `ZOOM` (1.5). |
| Pages blanches dans les PDF exportés | Utilise la dernière version du script (export par rendu d'image). |
| Détection trop lente | Garde le modèle 3b, `ZOOM = 1.0`, `CROP_RATIO = 0.20`. |
| `ModuleNotFoundError` | Le venv n'est pas activé : `source venv/bin/activate`. |

Quitter le venv : `deactivate`.

---