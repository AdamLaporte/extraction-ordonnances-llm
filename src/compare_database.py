"""
Script d'évaluation de la qualité de l'extraction (comparaison Humain vs LLM).

Ce module compare les résultats compilés des extractions du modèle de langage (JSON) 
avec un fichier de correction de référence (Excel) rempli par un expert humain. 
Il évalue la qualité de l'extraction et génère un rapport statistique détaillé 
sur les performances du pipeline.
"""

import pandas as pd
import json
import logging
import os

def comparer_resultats(chemin_reponses, chemin_corrige, chemin_libelles, dossier_sortie, nom_fichier_rapport):
    """
    Compare les données extraites par le LLM avec la vérité terrain (Excel) 
    et calcule les indicateurs de performance globaux et stricts pour chaque variable.

    Parameters
    ----------
    chemin_reponses : str
        Chemin vers le fichier JSON contenant les réponses extraites par le LLM.
    chemin_corrige : str
        Chemin vers le fichier Excel contenant les corrections de référence (humain).
    chemin_libelles : str
        Chemin vers le fichier Excel contenant le dictionnaire des variables et leurs libellés.
    dossier_sortie : str
        Dossier de destination où le rapport statistique sera sauvegardé.
    nom_fichier_rapport : str
        Nom du fichier JSON de sortie pour le rapport statistique.

    Returns
    -------
    None
        La fonction ne retourne rien, mais écrit un fichier JSON sur le disque.
    """
    logging.info("--- DÉBUT DE LA COMPARAISON DES RÉSULTATS ---")
    
    if not os.path.exists(chemin_reponses):
        logging.error(f"Fichier de réponses introuvable : {chemin_reponses}")
        return
    if not os.path.exists(chemin_corrige):
        logging.error(f"Fichier corrigé introuvable : {chemin_corrige}")
        return

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_rapport = os.path.join(dossier_sortie, nom_fichier_rapport)

    colonnes_dates = [
        "da_audience", "da_dec", "da_fix_audience", "da_nais_def", 
        "da_nais_dem", "da_renvoi_audience", "da_saisine"
    ]

    def normaliser_type_et_valeur(val, nom_colonne):
        """
        Standardise une valeur brute pour permettre une comparaison stricte,
        en gérant spécifiquement les données manquantes, les dates et les nombres.

        Parameters
        ----------
        val : any
            La valeur brute à normaliser.
        nom_colonne : str
            Le nom de la colonne associée, pour appliquer des formats spécifiques (ex: dates).

        Returns
        -------
        str
            La valeur normalisée en chaîne de caractères, 'none' pour une absence totale 
            d'information, ou 'x' pour une mention explicite 'non précisé'.
        """
        # 1. HORS CHAMP : On isole formellement None, les cases vides et les NaN
        if pd.isna(val): return "none"
        s = str(val).strip().lower()
        if s in ["nan", "nat", "none", "", "<na>", "null"]: 
            return "none"
            
        # 2. NON PRÉCISÉ : On isole la lettre X et les mentions d'inconnu
        if s in ["x", "non renseigné", "non précisé", "inconnu", "nc", "aucun"]: 
            return "x"

        # 3. VALEURS CLASSIQUES (Dates et nombres)
        if nom_colonne in colonnes_dates:
            if len(s) >= 10 and s[4] == '-' and s[7] == '-': return s[:10]
            try: return str(pd.to_datetime(val).date())
            except: return s
        try:
            s_clean = s.replace(',', '.')
            f_val = float(s_clean)
            if f_val.is_integer(): return str(int(f_val))
            return str(f_val)
        except ValueError:
            return s

    try:
        dict_libelles = {}
        if os.path.exists(chemin_libelles):
            df_lib = pd.read_excel(chemin_libelles)
            df_lib.columns = [str(c).strip().lower() for c in df_lib.columns]
            if 'nom_colonne' in df_lib.columns and 'libelle_colonne' in df_lib.columns:
                dict_libelles = {
                    str(k).strip().lower(): str(v).strip() 
                    for k, v in zip(df_lib['nom_colonne'], df_lib['libelle_colonne'])
                }

        logging.info(f"Lecture JSON LLM : {chemin_reponses}")
        df_rep = pd.read_json(chemin_reponses)
        
        logging.info(f"Lecture EXCEL Humain : {chemin_corrige}")
        df_cor = pd.read_excel(chemin_corrige)

        def nettoyer_id(val):
            """
            Nettoie et standardise les identifiants de documents (ex: No RG).

            Parameters
            ----------
            val : any
                L'identifiant brut.

            Returns
            -------
            str
                L'identifiant standardisé en minuscules et sans espaces/extensions.
            """
            if pd.isna(val): return "inconnu"
            s = str(val).strip()
            if s.endswith('.0'): s = s[:-2]
            for ext in ['.txt', '.json', '.xlsx']:
                if s.lower().endswith(ext): s = s[:-len(ext)]
            s = s.replace(" ", "") 
            return s.lower()

        def get_col_id(df):
            """
            Recherche dynamiquement le nom de la colonne servant d'identifiant unique.

            Parameters
            ----------
            df : pandas.DataFrame
                Le DataFrame à inspecter.

            Returns
            -------
            str
                Le nom de la colonne ('no_rg' si trouvé, sinon la première colonne).
            """
            for col in df.columns:
                if str(col).strip().lower() == 'no_rg': return col
            return df.columns[0]

        # ---------------------------------------------------------
        # Préparation et alignement des jeux de données
        # ---------------------------------------------------------
        col_id_rep = get_col_id(df_rep)
        df_rep['id_clean'] = df_rep[col_id_rep].apply(nettoyer_id)
        df_rep = df_rep[df_rep['id_clean'] != "inconnu"]
        df_rep = df_rep.drop_duplicates(subset=['id_clean'], keep='first')
        df_rep.set_index('id_clean', inplace=True)

        col_id_cor = get_col_id(df_cor)
        df_cor['id_clean'] = df_cor[col_id_cor].apply(nettoyer_id)
        df_cor = df_cor[df_cor['id_clean'] != "inconnu"]
        df_cor = df_cor.drop_duplicates(subset=['id_clean'], keep='first')
        df_cor.set_index('id_clean', inplace=True)

        # Alignement strict 1 pour 1 (intersection des index)
        df_rep, df_cor = df_rep.align(df_cor, join='inner', axis=0)
        
        variables_communes = [col for col in df_rep.columns if col in df_cor.columns and col != 'id_clean']
        total_questionnaires = len(df_rep)
        statistiques = []

        # ---------------------------------------------------------
        # Calcul des statistiques variable par variable
        # ---------------------------------------------------------
        for var in variables_communes:
            col_rep = df_rep[var].apply(lambda x: normaliser_type_et_valeur(x, var))
            col_cor = df_cor[var].apply(lambda x: normaliser_type_et_valeur(x, var))

            # --- NOUVELLE LOGIQUE DE COMPARAISON SÉPARÉE ---
            
            # On définit ce qui est considéré comme une absence de valeur
            est_absence_rep = col_rep.isin(["none", "x"])
            est_absence_cor = col_cor.isin(["none", "x"])

            # 1. Les accords parfaits ventilés par type
            match_none = (col_rep == "none") & (col_cor == "none")
            match_x = (col_rep == "x") & (col_cor == "x")
            match_valeurs = (col_rep == col_cor) & ~est_absence_rep
            
            # Équivalence des vides (L'un dit 'none' et l'autre dit 'x')
            match_vide_equivalent = est_absence_rep & est_absence_cor & (col_rep != col_cor)

            # 2. Le bonus LLM (L'humain a laissé vide ou mis X, mais le LLM a trouvé la vraie info)
            est_llm_bonus = est_absence_cor & ~est_absence_rep
            
            # 3. Les erreurs (Tout ce qui n'est ni un match exact, ni un match vide équivalent, ni un bonus)
            est_erreur = (col_rep != col_cor) & ~match_vide_equivalent & ~est_llm_bonus

            # --- CALCULS GLOBAUX ---
            nb_match_none = int(match_none.sum())
            nb_match_x = int(match_x.sum())
            nb_match_val = int(match_valeurs.sum())
            nb_match_vide_equivalent = int(match_vide_equivalent.sum())
            nb_bonus = int(est_llm_bonus.sum())
            nb_erreur = int(est_erreur.sum())

            nb_correct_global = nb_match_none + nb_match_x + nb_match_val + nb_match_vide_equivalent + nb_bonus
            pct_correct = (nb_correct_global / total_questionnaires) if total_questionnaires > 0 else 0

            # --- CALCULS STRICTS (Humain ET LLM ont répondu) ---
            # NOUVELLE RÈGLE : 
            # "none" (nan) = hors champ = n'a pas répondu.
            # "x" = a répondu (pour dire "non précisé").
            # Toute autre valeur = a répondu.
            
            a_repondu_rep = (col_rep != "none")
            a_repondu_cor = (col_cor != "none")
            
            # Cas où les deux ont donné une réponse (que ce soit une valeur exacte ou "x")
            repondu_par_les_deux = a_repondu_rep & a_repondu_cor
            nb_repondu_par_les_deux = int(repondu_par_les_deux.sum())
            
            # Parmi ces cas, combien sont identiques ? 
            # (Si les deux répondent "x", ce sera compté comme une bonne réponse commune !)
            bonnes_reponses_communes = (col_rep == col_cor) & repondu_par_les_deux
            nb_bonnes_reponses_communes = int(bonnes_reponses_communes.sum())
            
            pct_correct_communes = (nb_bonnes_reponses_communes / nb_repondu_par_les_deux) if nb_repondu_par_les_deux > 0 else 0
            
            statistiques.append({
                'Libellé': dict_libelles.get(var, 'Non défini'),
                'Variable': var,
                'Nb_Total_Dossiers': total_questionnaires,
                'Accords_Valeurs_Exactes': nb_match_val,
                'Accords_Hors_Champ_(None)': nb_match_none,
                'Accords_Non_Precise_(X)': nb_match_x,
                'Accords_Equivalence_Vides_(None_vs_X)': nb_match_vide_equivalent, 
                'Bonus_LLM_(Trouve_vs_Vide)': nb_bonus,
                'Erreurs_LLM': nb_erreur,
                '%_Reussite_Globale': f"{pct_correct * 100:.1f} %",
                # Nouvelles métriques strictes pour Streamlit
                'Nb_Repondu_Par_Les_Deux': nb_repondu_par_les_deux,
                'Nb_Bonnes_Reponses_Communes': nb_bonnes_reponses_communes,
                '%_Reussite_Communes': f"{pct_correct_communes * 100:.1f} %"
            })

        with open(chemin_rapport, 'w', encoding='utf-8') as f:
            json.dump(statistiques, f, ensure_ascii=False, indent=4)

        logging.info(f"✅ Rapport statistique généré avec succès : '{chemin_rapport}'")

    except Exception as e:
        logging.error(f"Une erreur est survenue lors de la comparaison : {e}")
        
    logging.info("--- FIN DE LA COMPARAISON DES RÉSULTATS ---\n")


if __name__ == "__main__":
    fichier_genere = "data/3_final/resultats_final/database_finale_better_ocr.json"
    fichier_corrige = "data/1_raw/opvc_reponses.xlsx"
    fichier_libelles = "data/1_raw/nom_des_variables.xlsx"
    dossier_rapport_sortie = "data/3_final/compare_results"
    nom_fichier_rapport = "rapport_statistique_better_ocr.json"
    
    comparer_resultats(fichier_genere, fichier_corrige, fichier_libelles, dossier_rapport_sortie, nom_fichier_rapport)