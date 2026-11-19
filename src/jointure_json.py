"""
Script de fusion des fichiers JSON générés par le LLM.

Ce module permet de regrouper les résultats d'extraction individuels 
de chaque section (a_procedure, b_profil_social, etc.) en un fichier 
JSON unique par ordonnance. Il prend en charge les formats d'extraction 
classiques ainsi que les formats étendus incluant les justifications du modèle.
"""

import os
import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fusion(dossiers_sources, dossier_cible):
    """
    Fusionne les fichiers JSON individuels des différentes sections 
    en un seul fichier JSON unifié par dossier (no_rg_fusion.json).

    Prend en charge les JSON classiques (dictionnaire plat) et les JSON 
    "avec justifications" (séparant données extraites et raisonnement LLM).

    Parameters
    ----------
    dossiers_sources : list of str or pathlib.Path
        Liste des chemins vers les répertoires contenant les JSON partiels 
        à fusionner (ex: ['data/2_interim/JSON_a_procedure', ...]).
    dossier_cible : str or pathlib.Path
        Chemin du répertoire de destination où seront sauvegardés 
        les fichiers JSON fusionnés.

    Returns
    -------
    dict
        Un dictionnaire listant les fichiers manquants par section. 
        Les clés sont les noms des sections et les valeurs sont 
        des listes d'identifiants de dossiers non trouvés (ex: '12345.txt').
    """
    os.makedirs(dossier_cible, exist_ok=True)
    fichiers_manquants_par_section = {}
    
    # 1. Identifier tous les identifiants uniques présents dans tous les dossiers
    tous_les_ids = set()
    fichiers_par_dossier = {}
    
    for dossier in dossiers_sources:
        chemin_dossier = Path(dossier)
        nom_section = chemin_dossier.name.replace("JSON_", "")
        fichiers_par_dossier[nom_section] = []
        
        if chemin_dossier.exists():
            for fichier in chemin_dossier.glob("*.json"):
                # --- CORRECTION : On nettoie le suffixe "_fusion" pour éviter les doublons ---
                id_fichier = fichier.stem.replace("_fusion", "")
                tous_les_ids.add(id_fichier)
                fichiers_par_dossier[nom_section].append(id_fichier)
                
    # 2. Reconstruire un JSON global par identifiant
    for id_dossier in tous_les_ids:
        donnees_fusionnees = {"no_rg": id_dossier}
        est_mode_justification = False
        
        for dossier in dossiers_sources:
            chemin_dossier = Path(dossier)
            nom_section = chemin_dossier.name.replace("JSON_", "")
            # On cherche toujours le fichier source original sans "_fusion"
            chemin_fichier = chemin_dossier / f"{id_dossier}.json"
            
            if chemin_fichier.exists():
                try:
                    with open(chemin_fichier, 'r', encoding='utf-8') as f:
                        donnees_section = json.load(f)
                        
                        # Nettoyage des clés inutiles à la racine
                        donnees_section.pop("no_cmpst", None)
                        donnees_section.pop("no_rg", None)
                        donnees_section.pop("NO_CMPST", None)
                        
                        # --- Gestion des fichiers avec justifications ---
                        if "donnees_extraites" in donnees_section and "justifications" in donnees_section:
                            est_mode_justification = True
                            
                            # Initialiser les sous-dicos s'ils n'existent pas encore
                            if "donnees_extraites" not in donnees_fusionnees:
                                donnees_fusionnees["donnees_extraites"] = {}
                            if "justifications" not in donnees_fusionnees:
                                donnees_fusionnees["justifications"] = {}
                            
                            # Nettoyer l'intérieur de donnees_extraites
                            donnees_extraites = donnees_section["donnees_extraites"]
                            donnees_extraites.pop("no_cmpst", None)
                            donnees_extraites.pop("no_rg", None)
                            donnees_extraites.pop("NO_CMPST", None)
                            
                            # Fusionner le contenu des sous-dicos
                            donnees_fusionnees["donnees_extraites"].update(donnees_extraites)
                            donnees_fusionnees["justifications"].update(donnees_section["justifications"])
                        else:
                            # --- CAS CLASSIQUE (Données pures) ---
                            donnees_fusionnees.update(donnees_section)
                            
                except Exception as e:
                    logging.error(f"Erreur de lecture du JSON {chemin_fichier} : {e}")
            else:
                if nom_section not in fichiers_manquants_par_section:
                    fichiers_manquants_par_section[nom_section] = []
                fichiers_manquants_par_section[nom_section].append(f"{id_dossier}.txt")
                
        # 3. Sauvegarder le fichier fusionné
        if len(donnees_fusionnees) > 1:
            # Réorganiser joliment si on est en mode justification
            if est_mode_justification:
                json_final = {
                    "no_rg": id_dossier,
                    "donnees_extraites": donnees_fusionnees.get("donnees_extraites", {}),
                    "justifications": donnees_fusionnees.get("justifications", {})
                }
            else:
                json_final = donnees_fusionnees

            chemin_sortie = Path(dossier_cible) / f"{id_dossier}_fusion.json"
            with open(chemin_sortie, 'w', encoding='utf-8') as f_out:
                json.dump(json_final, f_out, ensure_ascii=False, indent=4)
                
    return fichiers_manquants_par_section

if __name__ == "__main__":
    CHEMIN_SCRIPT = Path(__file__).resolve()
    RACINE_PROJET = CHEMIN_SCRIPT.parent.parent if CHEMIN_SCRIPT.parent.name == "scripts" else CHEMIN_SCRIPT.parent

    dossier_interim = RACINE_PROJET / "data/2_interim"
    
    # --- CORRECTION : Exclusion formelle des dossiers "final" pour éviter les boucles ---
    
    # 1. Identifier automatiquement tous les dossiers "classiques" 
    dossiers_classiques = [
        str(d) for d in dossier_interim.iterdir() 
        if d.is_dir() and d.name.startswith("JSON_") 
        and "final" not in d.name 
        and "avec_justification" not in d.name
    ]
    dossier_sortie_classique = str(dossier_interim / "JSON__final")
    
    # 2. Identifier automatiquement tous les dossiers "avec justifications"
    dossiers_justifs = [
        str(d) for d in dossier_interim.iterdir() 
        if d.is_dir() and d.name.startswith("JSON_") 
        and "final" not in d.name 
        and "avec_justification" in d.name
    ]
    dossier_sortie_justifs = str(dossier_interim / "JSON__final_avec_justification")

    # --- Lancement des Fusions ---
    if dossiers_classiques:
        logging.info(f"🔄 Début de la fusion pour {len(dossiers_classiques)} dossiers CLASSIQUES...")
        fusion(dossiers_classiques, dossier_sortie_classique)
        logging.info(f"✅ Fusion classique terminée : {dossier_sortie_classique}")
        
    if dossiers_justifs:
        logging.info(f"🔄 Début de la fusion pour {len(dossiers_justifs)} dossiers AVEC JUSTIFICATIONS...")
        fusion(dossiers_justifs, dossier_sortie_justifs)
        logging.info(f"✅ Fusion avec justifications terminée : {dossier_sortie_justifs}")