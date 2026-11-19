"""
Script d'extraction de texte (OCR) avancé pour les ordonnances de protection (JAF).

Ce module convertit des documents PDF scannés en texte brut pour alimenter 
le pipeline LLM. Il utilise OpenCV pour nettoyer visuellement les documents 
(effacement des surlignages) et PaddleOCR pour une extraction de texte 
performante.
"""

import os
import json
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from pdf2image import convert_from_path
from paddleocr import PaddleOCR

# ==========================================
# CONFIGURATION DES CHEMINS
# ==========================================
CHEMIN_SCRIPT = Path(__file__).resolve()
RACINE_PROJET = CHEMIN_SCRIPT.parent.parent if CHEMIN_SCRIPT.parent.name == "scripts" else CHEMIN_SCRIPT.parent

# Dossiers d'entrée et de sortie
DOSSIER_PDFS = Path(r"data/1_raw/scan_pdf")      # 👈 Mets ici le dossier avec tes 100 PDF
DOSSIER_SORTIE_JSON = Path(r"data/1_raw/ordonnances_classiques") # Dossier cible pour le LLM
DOSSIER_SORTIE_TXT = Path(r"data/2_interim/TXT_final")   # (Optionnel) Pour vérification humaine

DOSSIER_SORTIE_JSON.mkdir(parents=True, exist_ok=True)
DOSSIER_SORTIE_TXT.mkdir(parents=True, exist_ok=True)

# ==========================================
# 1. NETTOYAGE ANTI-FLUO EN MÉMOIRE
# ==========================================
def nettoyer_page_anti_fluo(image_pil):
    """
    Convertit une page PDF (objet PIL) en matrice OpenCV en niveaux de gris
    et applique un filtre d'égalisation d'histogramme adaptatif (CLAHE) 
    pour effacer le surligneur fluo.

    Parameters
    ----------
    image_pil : PIL.Image.Image
        L'image de la page PDF générée par la bibliothèque pdf2image.

    Returns
    -------
    numpy.ndarray
        L'image nettoyée et convertie en niveaux de gris sous forme de 
        matrice NumPy, prête à être analysée par l'OCR.
    """
    # Conversion de l'image PIL (RGB) vers OpenCV (Numpy array)
    image_cv = np.array(image_pil)
    image_gris = cv2.cvtColor(image_cv, cv2.COLOR_RGB2GRAY)
    
    # Application du contraste adaptatif (efface les zones claires comme le fluo)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    image_propre = clahe.apply(image_gris)
    
    return image_propre

# ==========================================
# 2. TRAITEMENT D'UN DOSSIER COMPLET
# ==========================================
def traiter_lot_pdfs():
    """
    Parcourt et traite l'ensemble des fichiers PDF présents dans le dossier source.

    Pour chaque document PDF, cette fonction :
    - Convertit le document en images (300 DPI).
    - Applique un nettoyage anti-fluo page par page.
    - Extrait le texte via l'intelligence artificielle PaddleOCR.
    - Exporte le résultat final en format JSON (pour l'étape suivante du pipeline LLM) 
      et TXT (pour vérification manuelle).

    Les fichiers possédant déjà un JSON généré dans le dossier cible 
    sont automatiquement ignorés pour gagner du temps.

    Returns
    -------
    None
    """
    fichiers_pdf = sorted(list(DOSSIER_PDFS.glob("*.pdf")))
    
    if not fichiers_pdf:
        print(f"❌ Aucun fichier PDF trouvé dans : {DOSSIER_PDFS}")
        return

    print(f"🚀 Initialisation de PaddleOCR (GPU activé)...")
    # Initialisation unique du modèle pour ne pas recharger la carte graphique à chaque fichier
    ocr = PaddleOCR(use_angle_cls=True, lang='fr', show_log=False)

    print(f"📂 Démarrage de l'analyse sur {len(fichiers_pdf)} fichiers PDF...\n")

    # Barre de progression tqdm (issue de ton requirements.txt)
    for fichier_pdf in tqdm(fichiers_pdf, desc="Analyse OCR en cours", unit="dossier"):
        nom_sans_ext = fichier_pdf.stem
        chemin_json_sortie = DOSSIER_SORTIE_JSON / f"{nom_sans_ext}.json"
        chemin_txt_sortie = DOSSIER_SORTIE_TXT / f"{nom_sans_ext}.txt"

        # Évite de refaire un OCR qui prend du temps si le fichier a déjà été traité
        if chemin_json_sortie.exists():
            continue

        try:
            # 1. Conversion du PDF en images (300 DPI est parfait pour l'OCR)
            pages_pil = convert_from_path(str(fichier_pdf), dpi=300)
            
            texte_complet_pdf = []

            # 2. Lecture page par page
            for num_page, page_pil in enumerate(pages_pil, start=1):
                # Nettoyage anti-fluo
                page_nettoyee = nettoyer_page_anti_fluo(page_pil)
                
                # Envoi direct de la matrice Numpy à PaddleOCR
                resultats = ocr.ocr(page_nettoyee, cls=True)
                
                lignes_page = []
                if resultats and resultats[0] is not None:
                    for ligne in resultats[0]:
                        texte_trouve = ligne[1][0]
                        lignes_page.append(texte_trouve)
                
                # Assemblage du texte de la page
                texte_page_str = "\n".join(lignes_page)
                texte_complet_pdf.append(f"--- PAGE {num_page} ---\n{texte_page_str}")

            # 3. Assemblage final du document
            texte_final = "\n\n".join(texte_complet_pdf)

            # 4. Sauvegarde en JSON (Format attendu par ton pipeline LLM)
            with open(chemin_json_sortie, "w", encoding="utf-8") as f_json:
                json.dump({"texte": texte_final}, f_json, ensure_ascii=False, indent=4)

            # 5. Sauvegarde en TXT pour vérification rapide
            with open(chemin_txt_sortie, "w", encoding="utf-8") as f_txt:
                f_txt.write(texte_final)

        except Exception as e:
            tqdm.write(f"⚠️ Erreur sur le fichier '{fichier_pdf.name}' : {str(e)}")

    print("\n✅ Traitement par lots terminé avec succès !")
    print(f"📁 JSON générés dans : {DOSSIER_SORTIE_JSON}")

if __name__ == "__main__":
    traiter_lot_pdfs()