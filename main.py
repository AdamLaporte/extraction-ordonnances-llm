"""
Point d'entrée principal en ligne de commande pour le pipeline d'analyse d'ordonnances (JAF).

Ce script interactif orchestre l'ensemble des opérations du projet :
1. Sélection du mode d'extraction (texte complet, découpé, OCR amélioré, QCM libre).
2. Lancement asynchrone des requêtes LLM pour extraire les informations clés.
3. Fusion automatique des JSON partiels en dossiers complets.
4. Création de la base de données tabulaire consolidée.
5. Évaluation et comparaison des résultats avec la correction humaine.
"""

import logging
import sys
import os
import asyncio
from pathlib import Path

chemin_scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.append(chemin_scripts)

from jointure_json import fusion 
from json_to_database import jsons_vers_base_unique
from compare_database import comparer_resultats
from llm_pydantic_opvc_2021 import main as extraction_llm
from llm_pydantic_opvc_2021 import lancer_qcm_adhoc

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pipeline.log", encoding="utf-8")
    ]
)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 PIPELINE D'EXTRACTION OPVC - JUSTICE 🤖")
    print("="*50)

    print("\n⚙️  MODE D'EXTRACTION")
    print("1. OPVC Classique (Lit les fichiers .txt dans le dossier opvc_ano)")
    print("2. OPVC Découpées par Partie (Lit le fichier ordonnances_decoupees.json)")
    print("3. OPVC Better OCR (Lit les fichiers .json structurés dans opvc_better_ocr)")
    print("4. QCM libre (Poser une question à choix multiples sur l'ensemble des documents)")
    choix_mode = input("👉 Choisis le mode (1, 2, 3 ou 4) [défaut: 2] : ").strip()
    
    # ----------------------------------------------------
    # BRANCHE 4 : MODE QCM AD-HOC
    # ----------------------------------------------------
    if choix_mode == "4":
        print("\n=== MODE QCM SUR L'ENSEMBLE DES DOCUMENTS ===")
        print("💡 Le LLM va analyser tous les textes (dossier opvc_ano par défaut) et classer chaque document.")
        
        question_user = input("❓ Tape ta question : ").strip()
        
        choix_possibles = []
        print("\nSaisis maintenant les réponses possibles (appuie sur Entrée à vide pour terminer) :")
        while True:
            idx = len(choix_possibles) + 1
            choix = input(f"   Choix {idx} : ").strip()
            if not choix:
                if len(choix_possibles) < 2:
                    print("⚠️ Tu dois saisir au moins 2 choix possibles !")
                    continue
                break
            choix_possibles.append(choix)
            
        dossier_source = "data/1_raw/opvc_better_ocr"
        dossier_destination = "data/3_final/qcm_resultats"
        
        print(f"\n🚀 Lancement du QCM sur {dossier_source}...")
        asyncio.run(lancer_qcm_adhoc(question_user, choix_possibles, dossier_source, dossier_destination))
        sys.exit(0)

    # ----------------------------------------------------
    # BRANCHES CLASSIQUES (1, 2 ou 3) - SANS CHUNKS
    # ----------------------------------------------------
    elif choix_mode == "1":
        mode_extraction = "llm_texte_complet"
        suffixe = ""
        dossier_textes_entree = "data/1_raw/opvc_ano"
    elif choix_mode == "3":
        mode_extraction = "llm_better_ocr"
        suffixe = "_better_ocr"
        dossier_textes_entree = "data/1_raw/opvc_better_ocr"
    else:
        mode_extraction = "llm_par_partie"
        suffixe = "_bis"
        dossier_textes_entree = "data/1_raw/ordonnances_decoupees.json"

    print(f"✅ Mode sélectionné : {mode_extraction}")

    # -> SUPPRESSION DU QUESTIONNAIRE SUR LES CHUNKS ICI <-

    rep_post_traitement = input("\n▶️ Veux-tu générer la base JSON finale et le rapport statistique ? (O/N) : ").strip().lower()
    lancer_post_traitement = (rep_post_traitement in ['o', 'oui'])
    print("="*50 + "\n")

    sections_a_traiter = [
        "a_procedure", "b_profil_social", "c_violences_denoncees", 
        "d_demandes", "e_reponses_sur_violences", "f_reponses_sur_demandes",
        "g_violences_retenues_jaf", "h_decision_jaf", "i_bracelet_anti_rapprochement"
    ]

    json_a_traiter = [f"data/2_interim/JSON_{sec}{suffixe}" for sec in sections_a_traiter]
    
    if mode_extraction == "llm_better_ocr":
        dossier_intermediaire_fusion = f"data/2_interim/JSON_final{suffixe}"
    else:
        dossier_intermediaire_fusion = f"data/2_interim/JSON__final{suffixe}"

    dossier_final = "data/3_final/resultats_final"
    fichier_base_finale = f"database_finale{suffixe}.json"
    chemin_reponses = f"{dossier_final}/{fichier_base_finale}"
    
    chemin_corrige = "data/1_raw/opvc_reponses.xlsx"
    chemin_libelles = "data/1_raw/nom_des_variables.xlsx"
    
    dossier_compare = "data/3_final/compare_results"
    fichier_compare = f"rapport_statistique{suffixe}.json"

    try:
        logging.info(f"=== DÉBUT DE L'EXTRACTION SUR LES 9 SECTIONS (Mode: {mode_extraction}) ===")
        for section in sections_a_traiter:
            # Appel de extraction_llm sans les variables chunk_index / chunk_size
            asyncio.run(extraction_llm(section, dossier_textes_entree, mode=mode_extraction))
        
        logging.info("=== DÉBUT DE LA FUSION AUTOMATIQUE ===")
        manquants = fusion(json_a_traiter, dossier_intermediaire_fusion)
        
        if manquants:
            logging.warning("⚠️ Lancement du rattrapage ciblé...")
            for section, fichiers in manquants.items():
                asyncio.run(extraction_llm(section, dossier_textes_entree, mode=mode_extraction))

            manquants_restants = fusion(json_a_traiter, dossier_intermediaire_fusion)

        logging.info("=== NETTOYAGE DES DOSSIERS INTERMÉDIAIRES ===")
        for dossier in json_a_traiter:
            if os.path.exists(dossier):
                for filename in os.listdir(dossier):
                    file_path = os.path.join(dossier, filename)
                    try:
                        if os.path.isfile(file_path): os.unlink(file_path)
                    except: pass

        if lancer_post_traitement:
            logging.info("=== CRÉATION DE LA BASE GLOBALE ===")
            jsons_vers_base_unique(dossier_intermediaire_fusion, dossier_final, fichier_base_finale)

            logging.info("=== COMPARAISON DES RÉSULTATS ===")
            comparer_resultats(chemin_reponses, chemin_corrige, chemin_libelles, dossier_compare, fichier_compare)
        else:
            logging.info("=== TRAITEMENT FINAL IGNORÉ ===")

    except KeyboardInterrupt:
        logging.warning("🛑 INTERRUPTION PAR L'UTILISATEUR (Ctrl+C)")
        sys.exit(130)