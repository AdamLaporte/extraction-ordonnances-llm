"""
Utilitaire d'extraction du numéro RG et de renommage en masse des documents.

Ce script parcourt les fichiers textes bruts (.txt) d'ordonnances de protection, 
utilise des expressions régulières (Regex) pour en extraire le Numéro de 
Répertoire Général (N° RG) officiel, puis renomme les fichiers textes 
et leurs fichiers JSON associés (résultats d'extraction LLM) de façon harmonisée 
pour la préparation et la manipulation des données du projet.
"""

import re
from pathlib import Path

# =========================================================
# 1. CONFIGURATION - Adaptez ces chemins à vos dossiers
# =========================================================
DOSSIER_TXT = Path(r"data/1_raw/opvc_ano")
DOSSIER_JSON = Path(r"data/2_interim/JSON__final")
DOSSIER_JSON_bis = Path(r"data/2_interim/JSON__final_bis")

SUFFIXE_JSON = "_fusion"  # Suffixe présent sur les fichiers JSON
SEPARATEUR_SAFE = "-"     # Remplaçant du '/' interdit dans les noms de fichier

# Expression régulière pour détecter "N° RG 12/34567", "N°RG : 12/34567", etc.
REGEX_RG = re.compile(r"N[°oO]?\s*RG\s*:?\s*(\d+/\d+)", re.IGNORECASE)

def extraire_numero_rg(chemin_fichier):
    """
    Lit le contenu d'un fichier texte et en extrait le numéro RG via une expression régulière.

    Parameters
    ----------
    chemin_fichier : pathlib.Path or str
        Le chemin d'accès vers le fichier texte à analyser.

    Returns
    -------
    str or None
        Le numéro RG nettoyé et formaté de manière sécurisée pour les noms de fichiers 
        (remplacement des slashs par des tirets, ex: '12-34567') s'il est trouvé, sinon None.
    """
    try:
        # Lecture avec tolérance pour les caractères spéciaux (UTF-8 avec fallback)
        with open(chemin_fichier, "r", encoding="utf-8", errors="ignore") as f:
            contenu = f.read()
        
        match = REGEX_RG.search(contenu)
        if match:
            numero_brut = match.group(1)
            # Remplacement de l'anti-slash ou slash par un tiret
            return numero_brut.replace("/", SEPARATEUR_SAFE)
    except Exception as e:
        print(f"❌ Erreur de lecture sur {chemin_fichier.name} : {e}")
    return None

def renommer_fichiers():
    """
    Parcourt les fichiers du répertoire source, extrait leur N° RG et harmonise les noms.

    Pour chaque fichier texte, si un N° RG est détecté, le fichier .txt est renommé 
    avec cet identifiant. Les fichiers de résultats .json correspondants dans les 
    différents répertoires intermédiaires sont également renommés de manière 
    synchronisée (en conservant le suffixe '_fusion') pour assurer la cohérence 
    globale des documents avant l'intégration en base de données.

    Returns
    -------
    None
    """
    if not DOSSIER_TXT.exists() or not DOSSIER_JSON.exists():
        print("❌ Erreur : Vérifiez que les chemins DOSSIER_TXT et DOSSIER_JSON existent.")
        return

    print("🔍 Début du scan et du renommage...\n" + "-"*40)

    for fichier_txt in DOSSIER_TXT.glob("*.txt"):
        numero_rg = extraire_numero_rg(fichier_txt)
        
        if not numero_rg:
            print(f"⚠️  Aucun N° RG trouvé dans : {fichier_txt.name} (ignoré)")
            continue

        # --- GESTION DU FICHIER TXT ---
        nouveau_nom_txt = f"{numero_rg}.txt"
        nouveau_chemin_txt = DOSSIER_TXT / nouveau_nom_txt

        # --- GESTION DU FICHIER JSON ---
        # Si le TXT s'appelait "541.txt", on cherche "541_fusion.json"
        nom_json_actuel = f"{fichier_txt.stem}{SUFFIXE_JSON}.json"
        ancien_chemin_json = DOSSIER_JSON / nom_json_actuel
        ancien_chemin_json_bis = DOSSIER_JSON_bis / nom_json_actuel
        nouveau_nom_json = f"{numero_rg}{SUFFIXE_JSON}.json"
        nouveau_chemin_json = DOSSIER_JSON / nouveau_nom_json
        nouveau_chemin_json_bis = DOSSIER_JSON_bis / nouveau_nom_json
        
        # 1. Renommage TXT
        if nouveau_chemin_txt.exists() and nouveau_chemin_txt != fichier_txt:
            print(f"⛔ Conflit : {nouveau_nom_txt} existe déjà ! Renommage de {fichier_txt.name} annulé.")
            continue
        else:
            fichier_txt.rename(nouveau_chemin_txt)
            print(f"✅ TXT  : {fichier_txt.name} ➔ {nouveau_nom_txt}")

        # 2. Renommage JSON
        if ancien_chemin_json.exists():
            if nouveau_chemin_json.exists() and nouveau_chemin_json != ancien_chemin_json:
                print(f"⛔ Conflit JSON : {nouveau_nom_json} existe déjà !")
            else:
                ancien_chemin_json.rename(nouveau_chemin_json)
                print(f"✅ JSON : {nom_json_actuel} ➔ {nouveau_nom_json}")
        else:
            print(f"ℹ️  JSON introuvable pour {fichier_txt.stem} (attendu : {nom_json_actuel})")
        
        if ancien_chemin_json_bis.exists():
            if nouveau_chemin_json_bis.exists() and nouveau_chemin_json_bis != ancien_chemin_json_bis:
                print(f"⛔ Conflit JSON : {nouveau_nom_json} existe déjà !")
            else:
                ancien_chemin_json_bis.rename(nouveau_chemin_json_bis)
                print(f"✅ JSON : {nom_json_actuel} ➔ {nouveau_nom_json}")
        else:
            print(f"ℹ️  JSON introuvable pour {fichier_txt.stem} (attendu : {nom_json_actuel})")

    print("\n" + "-"*40 + "\n🏁 Opération terminée !")

if __name__ == "__main__":
    renommer_fichiers()