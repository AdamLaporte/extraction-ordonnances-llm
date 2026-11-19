"""
Script de renommage en masse des fichiers JSON d'ordonnances (OCR amélioré).

Ce module parcourt les fichiers JSON issus de l'OCR, lit leur contenu textuel 
(clé 'texte'), détecte le numéro de Répertoire Général (N° RG) à l'aide d'une 
expression régulière, et renomme le fichier source avec cet identifiant 
de manière sécurisée.
"""

import json
import re
from pathlib import Path

# =========================================================
# 1. CONFIGURATION
# =========================================================
DOSSIER_SOURCE = Path(r"data/1_raw/opvc_better_ocr")

# Remplaçant du '/' interdit dans les noms de fichier sous OS (ex: 12/34567 -> 12-34567)
SEPARATEUR_SAFE = "-"     

# Expression régulière pour détecter "N° RG 12/34567", "N°RG : 12/34567", etc.
REGEX_RG = re.compile(r"N[°oO]?\s*RG\s*:?\s*(\d+/\d+)", re.IGNORECASE)

def extraire_numero_rg(chemin_fichier):
    """
    Lit un fichier JSON, récupère la valeur 'texte' et extrait le numéro RG.

    Parameters
    ----------
    chemin_fichier : pathlib.Path or str
        Le chemin d'accès vers le fichier JSON à analyser.

    Returns
    -------
    str or None
        Le numéro RG formaté de manière sécurisée pour les noms de fichiers 
        (remplacement des slashs par des tirets, ex: '12-34567') s'il est trouvé. 
        Retourne None si le numéro n'est pas trouvé ou en cas d'erreur de lecture.
    """
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Récupération du contenu de la clé "texte"
        contenu = data.get("texte", "")
        
        match = REGEX_RG.search(contenu)
        if match:
            numero_brut = match.group(1)
            # Remplacement du '/' interdit par un caractère sûr
            return numero_brut.replace("/", SEPARATEUR_SAFE)
            
    except json.JSONDecodeError:
        print(f"❌ Erreur : {chemin_fichier.name} n'est pas un JSON valide.")
    except Exception as e:
        print(f"❌ Erreur de lecture sur {chemin_fichier.name} : {e}")
        
    return None

def renommer_fichiers_json():
    """
    Parcourt les fichiers JSON du dossier cible, extrait le N° RG et renomme le fichier.

    Assure la sécurité du renommage en vérifiant que le nouveau nom n'existe 
    pas déjà pour éviter d'écraser des données en cas de conflit d'identifiant.

    Returns
    -------
    None
    """
    if not DOSSIER_SOURCE.exists():
        print(f"❌ Erreur : Le dossier '{DOSSIER_SOURCE}' est introuvable.")
        return

    print(f"🔍 Scan du dossier : {DOSSIER_SOURCE}...\n" + "-"*50)

    for fichier_json in DOSSIER_SOURCE.glob("*.json"):
        numero_rg = extraire_numero_rg(fichier_json)
        
        if not numero_rg:
            print(f"⚠️  Aucun N° RG trouvé dans : {fichier_json.name} (ignoré)")
            continue

        nouveau_nom = f"{numero_rg}.json"
        nouveau_chemin = DOSSIER_SOURCE / nouveau_nom

        # Sécurité : Si le fichier a déjà le bon nom, on ignore
        if fichier_json == nouveau_chemin:
            continue

        # Sécurité : Éviter d'écraser un fichier existant si deux fichiers ont le même N° RG
        if nouveau_chemin.exists():
            print(f"⛔ Conflit : {nouveau_nom} existe déjà ! Renommage de {fichier_json.name} annulé.")
            continue

        try:
            fichier_json.rename(nouveau_chemin)
            print(f"✅ Renommé : {fichier_json.name} ➔ {nouveau_nom}")
        except Exception as e:
            print(f"❌ Erreur lors du renommage de {fichier_json.name} : {e}")

    print("\n" + "-"*50 + "\n🏁 Opération terminée !")

if __name__ == "__main__":
    renommer_fichiers_json()