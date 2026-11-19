"""
Script d'extraction de texte (OCR standard) pour les ordonnances de protection.

Ce module utilise Tesseract (via pytesseract) pour extraire le texte brut 
des documents PDF scannés. Il inclut des étapes de conversion PDF vers PNG 
et de prétraitement d'image (binarisation, rognage) pour optimiser 
la qualité de l'OCR avant le traitement par le pipeline LLM.
"""

import os
import gc
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter, ImageChops
import pytesseract
from tqdm import tqdm

# --- 1. CONFIGURATION DES CHEMINS ---
base_dir = Path("scan_non_ocr")
pdf_dir = base_dir  # Modifié : Le script cherche les PDF directement dans scan_fusion

# Modifié : Le dossier de destination pour les fichiers texte finaux
txt_dir = Path("scan_ocr_non_ano") 

# Dossiers temporaires pour les images (vous pouvez les laisser se créer dans scan_fusion)
png_dir = base_dir / "PNG"
pngproc_dir = base_dir / "PNG_PROC"

# Création des dossiers s'ils n'existent pas
for d in [png_dir, pngproc_dir, txt_dir]:
    d.mkdir(parents=True, exist_ok=True)

log_file = txt_dir / "log.txt" # J'ai déplacé le fichier log dans votre nouveau dossier
if log_file.exists():
    log_file.unlink()  # On part d'un log vide

def write_log(message):
    """
    Écrit un message dans le fichier de log et l'affiche dans la console.

    Parameters
    ----------
    message : str
        Le message d'information ou d'erreur à consigner.

    Returns
    -------
    None
    """
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")
    print(message)

# --- 2. FONCTIONS DE TRAITEMENT ---

def pdf_to_png(pdf_path, out_dir=png_dir, dpi=400):
    """
    Convertit un document PDF en une série d'images au format PNG.

    Parameters
    ----------
    pdf_path : pathlib.Path
        Le chemin vers le fichier PDF à convertir.
    out_dir : pathlib.Path, optional
        Le dossier de destination pour les images générées (default is png_dir).
    dpi : int, optional
        La résolution (Dots Per Inch) pour la conversion de l'image (default is 400).

    Returns
    -------
    list of pathlib.Path
        Une liste contenant les chemins vers les fichiers PNG générés pour chaque page.
    """
    # convert_from_path requiert Poppler sur le système
    images = convert_from_path(pdf_path, dpi=dpi)
    png_paths = []
    
    for i, image in enumerate(images):
        page_num = i + 1
        filename = out_dir / f"{pdf_path.stem}_page{page_num:03d}.png"
        image.save(filename, "PNG")
        png_paths.append(filename)
        
    return png_paths

def trim_image(im):
    """
    Rogne les marges vides d'une image (équivalent de la fonction image_trim dans magick).

    Parameters
    ----------
    im : PIL.Image.Image
        L'image originale à rogner.

    Returns
    -------
    PIL.Image.Image
        L'image rognée sans les marges vides, ou l'image d'origine si aucun recadrage n'est nécessaire.
    """
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def preprocess_image(png_path, out_dir=pngproc_dir):
    """
    Traite l'image pour optimiser l'extraction OCR en appliquant 
    une conversion en niveaux de gris, une binarisation et un rognage.

    Parameters
    ----------
    png_path : pathlib.Path
        Le chemin vers l'image PNG brute à traiter.
    out_dir : pathlib.Path, optional
        Le dossier de destination pour l'image traitée (default is pngproc_dir).

    Returns
    -------
    pathlib.Path or None
        Le chemin vers la nouvelle image traitée, ou None en cas d'échec du traitement.
    """
    try:
        img = Image.open(png_path)
    except Exception as e:
        write_log(f"[READ-FAIL] {png_path} – {e}")
        return None

    w, h = img.size
    if w <= 0 or h <= 0:
        write_log(f"[ZERO-SIZE] {png_path} – w={w}, h={h}")
        return None

    try:
        # 1. Conversion en niveaux de gris
        img = img.convert("L")
        
        # 2. Binarisation (Seuillage) : Tout pixel plus clair que 150 devient blanc (255)
        # et tout pixel plus foncé devient noir (0). Cela supprime le fond gris/jaune des scans.
        seuil = 150
        img = img.point(lambda p: 255 if p > seuil else 0)
        
        # 3. Rognage (Trim) des marges vides
        img = trim_image(img)
        
        # Sauvegarde
        out_path = out_dir / f"{png_path.stem}_proc.png"
        img.save(out_path, "PNG")
        return out_path
        
    except Exception as e:
        write_log(f"[PROCESS-FAIL] {png_path} – {e}")
        return None

def ocr_png(png_path, lang="fra"):
    """
    Extrait le texte de l'image traitée en utilisant le moteur Tesseract OCR.

    Parameters
    ----------
    png_path : pathlib.Path
        Le chemin vers l'image traitée à analyser.
    lang : str, optional
        La langue de reconnaissance OCR (default is "fra").

    Returns
    -------
    str
        Le texte extrait de l'image. Retourne une chaîne vide en cas d'erreur lors de l'extraction.
    """
    try:
        # --oem 3 : Utilise le moteur par défaut (LSTM, réseau de neurones très performant)
        # --psm 3 : Mode par défaut. (Essayez --psm 4 si votre texte est en plusieurs colonnes)
        # --psm 6 : À utiliser si Tesseract a du mal à garder les lignes de texte ensemble.
        custom_config = r'--oem 3 --psm 3'
        
        return pytesseract.image_to_string(Image.open(png_path), lang=lang, config=custom_config)
    except Exception as e:
        write_log(f"[OCR-FAIL] {png_path} – {e}")
        return ""

# --- 3. BOUCLE PRINCIPALE ---

# Lister les fichiers PDF
pdf_files = list(pdf_dir.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError(f"Aucun fichier PDF trouvé dans le dossier {pdf_dir}")

print("Début du traitement...")

# Barre de progression
for pdf_path in tqdm(pdf_files, desc="Traitement des PDF", unit="fichier"):
    
    # 1. Conversion
    png_paths = pdf_to_png(pdf_path)
    
    # 2. Pré-traitement
    png_proc_paths = []
    for p in png_paths:
        proc_path = preprocess_image(p)
        if proc_path:
            png_proc_paths.append(proc_path)
            
    # 3. OCR
    page_texts = []
    for proc_path in png_proc_paths:
        text = ocr_png(proc_path)
        page_texts.append(text)
        
    # 4. Assemblage et sauvegarde du texte
    full_text = "\n\n".join(page_texts)
    txt_path = txt_dir / f"{pdf_path.stem}.txt"
    
    with open(txt_path, "w", encoding="utf-8") as f_out:
        f_out.write(full_text)
        
    # 5. Nettoyage des fichiers temporaires PNG
    for p in png_paths:
        if p.exists():
            p.unlink()
            
    for p in png_proc_paths:
        if p.exists():
            p.unlink()
            
    # Forcer le ramasse-miettes (Garbage Collector)
    gc.collect()

print(f"\nTerminé ! Les fichiers texte sont dans le dossier : {txt_dir}")
print(f"Un log détaillé des éventuels problèmes se trouve dans : {log_file}")