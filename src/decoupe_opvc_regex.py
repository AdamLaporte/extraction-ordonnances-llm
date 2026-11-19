"""
Script de segmentation par expressions régulières (Regex) des Ordonnances de Protection.

Ce module permet de découper les gros blocs de texte brut (générés par l'OCR) 
en parties logiques structurées (Identification, Prétentions, Motifs, Décision) 
afin de faciliter et d'optimiser l'extraction d'informations par le LLM.
"""

import re
import json
from pathlib import Path

def decouper_ordonnance(texte_opvc):
    """
    Découpe le texte brut d'une Ordonnance de Protection (OPVC) en 4 blocs logiques principaux.
    
    Cette version finale est ultra-robuste et conçue pour parer aux erreurs d'OCR 
    ainsi qu'aux variations de mise en page. En cas de structure non reconnue 
    (ex: absence du mot "Motifs"), la fonction n'échoue pas mais fusionne les blocs 
    pour permettre au LLM de traiter l'ensemble du texte.

    Parameters
    ----------
    texte_opvc : str
        Le texte intégral et brut de l'ordonnance de protection à segmenter.

    Returns
    -------
    dict
        Un dictionnaire contenant les 4 sections extraites :
        - 'Identification_Procedure' (str) : En-tête et historique de la procédure.
        - 'Pretentions_Demandes' (str) : Exposé du litige et demandes des parties.
        - 'Motifs_Juge' (str) : Raisonnement du juge.
        - 'Decisions_Finales' (str) : Dispositif final (les mesures ordonnées).
    """
    # 1. Exposé du litige
    regex_pivot_1 = r"(?im)^[\s\W]*(?:EXPOS[EÉ]\s+DU\s+LITIGE|EXPOS[EÉ]\s+DES\s+FAITS|FAITS,?\s*PROC[EÉ]DURE|FAITS\s+ET\s+PROC[EÉ]DURE|PR[EÉ]TENTIONS\s+ET\s+MOYENS)"
    
    # 2. Motifs (Tolère nn, MOLIFS, MOTIES, et les espaces invisibles)
    regex_pivot_2 = r"(?im)^[\s\W]*(?:MOTI[FEL]S\s+DE\s+LA\s+D[EÉ]CISION|nn\s+DE\s+LA\s+D[EÉ]CISION|MOTI[FEL]S\s*$|MOLIFS\s*$|SUR\s+CE,?|MOTIFS\s+DE|LA\s+D[EÉ]CISION)"
    
    # 3. Dispositif 
    regex_pivot_3 = r"(?im)^[\s\W]*(?:PAR\s+CES\s+MOTIFS|EN\s+CONS[EÉ]Q.*?ENCE|PAR\s+CES\s+CAUSES)"

    match_1 = re.search(regex_pivot_1, texte_opvc)
    match_2 = re.search(regex_pivot_2, texte_opvc)
    match_3 = re.search(regex_pivot_3, texte_opvc)

    # --- SÉCURITÉ ASSOUPLIE ---
    # Si on ne trouve vraiment pas le début des motifs, le script ne plante plus !
    # Il mettra tout le texte dans le premier bloc, et le LLM se débrouillera.
    if not match_2:
        return {
            "Identification_Procedure": texte_opvc.strip(),
            "Pretentions_Demandes": "",
            "Motifs_Juge": "",
            "Decisions_Finales": ""
        }

    idx_p2 = match_2.start()
    
    # Si on trouve match_3, on coupe. Sinon, la fin va dans Decisions_Finales
    idx_p3 = match_3.start() if match_3 else len(texte_opvc)

    # --- GESTION INTELLIGENTE DU PIVOT 1 ---
    # Si le juge a oublié le titre de l'exposé du litige
    if match_1 and match_1.start() < idx_p2:
        idx_p1 = match_1.start()
        en_tete = texte_opvc[0:idx_p1].strip()
        expose = texte_opvc[idx_p1:idx_p2].strip()
    else:
        en_tete = texte_opvc[0:idx_p2].strip()
        expose = "[Titre absent - fusionné avec Identification]"

    # --- EXTRACTION FINALE ---
    return {
        "Identification_Procedure": en_tete,
        "Pretentions_Demandes": expose,
        "Motifs_Juge": texte_opvc[idx_p2:idx_p3].strip(),
        "Decisions_Finales": texte_opvc[idx_p3:].strip() if match_3 else "[Titre absent - fusionné avec Motifs]"
    }

def traiter_dossier(chemin_dossier_entree, chemin_fichier_sortie, chemin_log_erreurs):
    """
    Parcourt tous les fichiers .txt d'un répertoire, les découpe structurellement, 
    sauvegarde les succès dans un fichier JSON et consigne les échecs dans un journal.

    Parameters
    ----------
    chemin_dossier_entree : str
        Le chemin vers le dossier contenant les fichiers texte (.txt) bruts à analyser.
    chemin_fichier_sortie : str
        Le chemin du fichier JSON de destination où seront stockés les documents découpés.
    chemin_log_erreurs : str
        Le chemin du fichier texte (.log) de sortie où consigner les éventuelles 
        erreurs de lecture ou de découpage.

    Returns
    -------
    None
        La fonction ne retourne rien, mais écrit directement les résultats 
        et les journaux d'erreurs sur le disque.
    """
    dossier = Path(chemin_dossier_entree)
    resultats_globaux = {}
    fichiers_en_erreur = []

    if not dossier.is_dir():
        print(f"Erreur : Le dossier '{chemin_dossier_entree}' n'existe pas.")
        return

    print(f"Analyse du dossier : {dossier.resolve()}...")
    fichiers_txt = list(dossier.glob("*.txt"))
    
    if not fichiers_txt:
        print("Aucun fichier .txt trouvé dans ce dossier.")
        return

    # Boucle d'analyse de chaque fichier
    for fichier in fichiers_txt:
        try:
            texte_brut = fichier.read_text(encoding='utf-8') 
            blocs = decouper_ordonnance(texte_brut)
            
            # Vérification si la fonction a renvoyé une erreur de structure
            if "Erreur" in blocs:
                fichiers_en_erreur.append(f"{fichier.name} : {blocs['Erreur']}")
                print(f"[ÉCHEC] - {fichier.name}")
            else:
                resultats_globaux[fichier.name] = blocs
                print(f"[SUCCÈS] - {fichier.name}")
            
        except Exception as e:
            erreur_msg = f"Impossible de lire le fichier (problème d'encodage ou d'accès) : {e}"
            fichiers_en_erreur.append(f"{fichier.name} : {erreur_msg}")
            print(f"[ERREUR LECTURE] - {fichier.name}")

    # 1. Sauvegarde des données valides en JSON
    try:
        with open(chemin_fichier_sortie, 'w', encoding='utf-8') as f:
            json.dump(resultats_globaux, f, ensure_ascii=False, indent=4)
        print("\n" + "="*30)
        print(f"BILAN DES OPÉRATIONS")
        print("="*30)
        print(f"✅ Succès : {len(resultats_globaux)} ordonnances sauvegardées dans '{chemin_fichier_sortie}'.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

    # 2. Création du fichier d'erreurs s'il y a eu des échecs
    if fichiers_en_erreur:
        try:
            with open(chemin_log_erreurs, 'w', encoding='utf-8') as f_log:
                f_log.write("=== RAPPORTS D'ERREURS DE DÉCOUPAGE ===\n")
                f_log.write("Ces fichiers nécessitent une vérification manuelle pour identifier de nouveaux titres de parties.\n\n")
                for erreur in fichiers_en_erreur:
                    f_log.write(f"- {erreur}\n")
            print(f"❌ Échecs : {len(fichiers_en_erreur)} fichiers rejetés. Consultez '{chemin_log_erreurs}' pour la liste.")
        except Exception as e:
            print(f"Erreur lors de la création du fichier log : {e}")
    else:
        print("🎉 Échecs : 0. Tous les fichiers du dossier ont été découpés avec succès !")

# --- EXÉCUTION ---
# N'oubliez pas de mettre à jour ces chemins selon l'emplacement de vos données
DOSSIER_TXT = "./data/1_raw/opvc_ano" 
FICHIER_JSON = "./data/1_raw/ordonnances_decoupees.json"
FICHIER_LOG = "./erreurs_decoupage.log"

if __name__ == "__main__":
    traiter_dossier(DOSSIER_TXT, FICHIER_JSON, FICHIER_LOG)