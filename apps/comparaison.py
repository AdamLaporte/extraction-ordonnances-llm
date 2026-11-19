"""
Application Streamlit de Dashboard OPVC - Justice.

Interface interactive permettant de comparer les performances des différentes 
méthodes d'extraction de données (Modèles LLM) par rapport aux corrections humaines 
dans le cadre de l'analyse d'Ordonnances de Protection (JAF).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
import json

# ==========================================
#     CONFIGURATION ET CONSTANTES
# ==========================================
st.set_page_config(
    page_title="Dashboard OPVC - Justice", 
    page_icon="⚖️", 
    layout="wide"
)

CHEMIN_GENERE_M1 = "data/3_final/resultats_final/database_finale.json"
CHEMIN_STATS_M1 = "data/3_final/compare_results/rapport_statistique.json"

CHEMIN_GENERE_M2 = "data/3_final/resultats_final/database_finale_bis.json"
CHEMIN_STATS_M2 = "data/3_final/compare_results/rapport_statistique_bis.json"

CHEMIN_GENERE_M3 = "data/3_final/resultats_final/database_finale_better_ocr.json"
CHEMIN_STATS_M3 = "data/3_final/compare_results/rapport_statistique_better_ocr.json"

# ---> Chemin vers le fichier des justifications
CHEMIN_JUSTIF = "data/3_final/resultats/database_justifications.json" 

CHEMIN_EXCEL_CORRIGE = "data/1_raw/opvc_reponses.xlsx"

SECTIONS_MAPPING = {
    "a": "Procédure d'identification", "b": "Profil social", "c": "Violences dénoncées",
    "d": "Demandes", "e": "Réponses sur violences", "f": "Réponses sur demandes",
    "g": "Violences retenues JAF", "h": "Décision JAF", "i": "Bracelet anti-rapprochement"
}

COLONNES_DATES = [
    "da_audience", "da_dec", "da_fix_audience", "da_nais_def", 
    "da_nais_dem", "da_renvoi_audience", "da_saisine"
]

# Liste des variables où M4 adopte les prédictions du Modèle 2
VARS_M2_IN_M4 = [
    "psy_enft_denonc", "enft_cee_dem_mt", "lieu_dom_dem_denonc", 
    "addict_alcool_dem", "preuv_temoin_proche_assist", "menace_enft_denonc", 
    "divorce_ok_def", "posture_fond", "temoin_enft_repdef", "temoin_autre_denonc", 
    "aj_prov_dem", "contrib_mrge_dem_mt", "violence_repete_retenu", "enft_visit_dem", 
    "enft_mini_an_nais", "economic_dem_denonc", "preuv_temoin_enft", "minim_justif_def", 
    "preuv_temoin_proche_non_assist", "art_700_def", "proces_encours_preventive", 
    "patho_psy_def", "lieu_interdi_w_dem", "temoin_proche_repdef", "addict_stup_dem", 
    "enft_iec_media_dem", "enft_heberg_def", "enft_pass_bras_dem", "dept_res_def", 
    "dept_res_dem", "contrib_mrge_dem", "depression_def", "art_696_dem", "mp_presence", 
    "resid_separe_dem", "enft_maxi_an_nais", "preuv_plainte_avant", "temoin_proche_denonc", 
    "fix_audience_notif", "logt_pec_frais_dem", "psy_control_dem_denonc", "depression_dem", 
    "patho_psy_dem", "pays_nais_def", "pays_nais_dem", "renvoi_motif_contrad", "renvoi_motif_avocat",
     "renvoi_motif_autre", "preuv_plainte_avant_nb", "enft_mesure_socioeduc", 
     "passe_venft_conda_map", "aj_dem_ok", "phys_enft_denonc", "addict_stup_def", 
     "an_mariage_couple", "degrad_dem_denonc", "enft_media_dem", "intrusion_dem_denonc",
     "proces_encours_lien_op", "lieu_tiers_denonc", "enft_dvh_dem"
]

# Liste des variables considérées comme 100% correctes dans M4 (erreur humaine de correction)
VARS_FORCE_CORRECT = [
    "l_com_loc", "da_nais_dem", "da_nais_def", "da_renvoi_audience", 
    "hc_opvc", "natio_dem", "natio_def", "dept_res_dem", "dept_res_def","mp_presence"
]

# ==========================================
#     INITIALISATION DE LA MÉMOIRE
# ==========================================
MENU_GLOBAL = "📈 Vue Globale"
MENU_TABLEAU = "📋 Performance Détaillée"
MENU_VARIABLE = "🔍 Explorateur de Variables"
MENU_DOSSIER = "📄 Deep Dive par Dossier"
MENU_SECTION = "🗂️ Analyse par Section"
MENU_COMPARAISON = "⚖️ Performance Comparée (M1 vs M2 vs M3 vs M4)"
MENU_JUSTIF = "🔎 Analyse des Justifications (M3)"
MENU_DEBUG = "🛠️ Debug & Incohérences"

if "page" not in st.session_state: st.session_state.page = MENU_GLOBAL
if "selected_var" not in st.session_state: st.session_state.selected_var = None

# ==========================================
#     PARSERS ET DICTIONNAIRES
# ==========================================
def nettoyer_id_global(val):
    """
    Nettoie et standardise les identifiants de dossiers (ex: numéros RG) de 
    manière uniforme pour l'ensemble du pipeline.

    Supprime les extensions de fichiers (txt, json, xlsx), la décimale '.0' 
    et certains caractères spéciaux (espaces, tirets, slash, underscores) 
    pour garantir une correspondance exacte entre différentes sources.

    Parameters
    ----------
    val : any
        La valeur de l'identifiant brut à nettoyer.

    Returns
    -------
    str
        L'identifiant nettoyé et mis en minuscules. Retourne 'inconnu' si 
        la valeur est manquante ou invalide.
    """
    if pd.isna(val): return "inconnu"
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    for ext in ['.txt', '.json', '.xlsx']:
        if s.lower().endswith(ext): s = s[:-len(ext)]
    # Supprime les espaces, les tirets, les slash et les underscores 
    # pour que "12/34567" matche parfaitement avec "12-34567"
    s = re.sub(r"[\s\-\/\_]", "", s)
    return s.lower()

@st.cache_data
def build_variable_to_section_mapping():
    """
    Construit un dictionnaire qui associe chaque variable extraite 
    à son code de section d'origine (a, b, c, etc.) en parsant les fichiers de prompts.

    Returns
    -------
    dict
        Dictionnaire dont les clés sont les noms des variables (en minuscules) 
        et les valeurs sont les codes de section correspondants.
    """
    mapping = {}
    fichiers_sections = {
        "a": "a_procedure.txt", "b": "b_profil_social.txt", "c": "c_violences_denoncees.txt",
        "d": "d_demandes.txt", "e": "e_reponses_sur_violences.txt", "f": "f_reponses_sur_demandes.txt",
        "g": "g_violences_retenues_jaf.txt", "h": "h_decision_jaf.txt", "i": "i_bracelet_anti_rapprochement.txt"
    }
    for code, fichier in fichiers_sections.items():
        chemin = os.path.join("prompts", fichier)
        if os.path.exists(chemin):
            with open(chemin, 'r', encoding='utf-8') as f:
                contenu = f.read()
                variables_trouvees = re.findall(r"^([A-Z0-9_]+)\s*:", contenu, re.MULTILINE)
                for var in variables_trouvees:
                    mapping[var.lower()] = code
    return mapping

def charger_dictionnaire_variable(variable, section_code):
    """
    Extrait les instructions spécifiques fournies au LLM pour une 
    variable donnée à partir du fichier de prompt correspondant.

    Parameters
    ----------
    variable : str
        Le nom technique de la variable recherchée.
    section_code : str
        Le code de la section (ex: 'a', 'b', 'c') identifiant le fichier source.

    Returns
    -------
    str
        Le bloc de texte décrivant les instructions et modalités de la variable. 
        Renvoie un message d'erreur si la variable ou le fichier n'est pas trouvé.
    """
    fichiers_sections = {
        "a": "a_procedure.txt", "b": "b_profil_social.txt", "c": "c_violences_denoncees.txt",
        "d": "d_demandes.txt", "e": "e_reponses_sur_violences.txt", "f": "f_reponses_sur_demandes.txt",
        "g": "g_violences_retenues_jaf.txt", "h": "h_decision_jaf.txt", "i": "i_bracelet_anti_rapprochement.txt"
    }
    nom_fichier = fichiers_sections.get(section_code)
    if not nom_fichier: return "Section inconnue ou fichier introuvable."
    chemin_fichier = os.path.join("prompts", nom_fichier)
    if not os.path.exists(chemin_fichier): return f"Fichier source introuvable ({chemin_fichier})"
        
    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        contenu = f.read()
    pattern = rf"^({variable}\s*:.*?)(?=^[A-Z0-9_]+\s*:|\Z)"
    match = re.search(pattern, contenu, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match:
        texte = match.group(1).strip()
        texte = re.sub(r"\s+", " ", texte)
        return texte
    return "Aucun détail trouvé pour cette variable dans le fichier source."

def normaliser_pour_affichage(val, nom_colonne=""):
    """
    Normalise une valeur pour un affichage propre dans l'interface,
    notamment en gérant les dates, les nombres décimaux et les valeurs nulles.

    Parameters
    ----------
    val : any
        La valeur brute à normaliser.
    nom_colonne : str, optional
        Le nom de la colonne associée, utilisé pour appliquer un traitement 
        particulier (ex: formatage des dates), par défaut "".

    Returns
    -------
    str
        La valeur formatée sous forme de chaîne de caractères, 
        ou 'nan' si la valeur d'origine est considérée comme nulle.
    """
    if pd.isna(val): return "nan"
    s = str(val).strip()
    s_lower = s.lower()
    
    if s_lower in ["nan", "nat", "none", "", "<na>", "null", "x"]: 
        return "nan"
    
    if nom_colonne in COLONNES_DATES:
        if len(s) >= 10 and s[4] == '-' and s[7] == '-': return s[:10]
        try: return str(pd.to_datetime(val).date())
        except: return s
        
    try:
        s_clean = s.replace(',', '.')
        f_val = float(s_clean)
        if f_val.is_integer(): return str(int(f_val))
        return str(f_val)
    except ValueError:
        pass
    return s

def extraire_colonne_securisee(df, var_name, index_cible):
    """
    Extrait une colonne d'un DataFrame de façon sécurisée tout en 
    appliquant une normalisation stricte à l'ensemble de la série.

    Parameters
    ----------
    df : pandas.DataFrame
        Le DataFrame à partir duquel extraire la colonne.
    var_name : str
        Le nom de la variable/colonne à extraire.
    index_cible : pandas.Index
        L'index de référence attendu pour l'alignement des données.

    Returns
    -------
    pandas.Series
        La série correspondante formatée et indexée. Renvoie une série 
        remplie de 'nan' si la colonne n'est pas trouvée.
    """
    var_lower = str(var_name).lower().strip()
    if var_lower in df.columns:
        return df.loc[index_cible, var_lower].apply(lambda x: normaliser_pour_affichage(x, var_lower))
    return pd.Series("nan", index_cible)

# ==========================================
#     MOTEUR DE DIAGNOSTIC (DEBUGGING)
# ==========================================
@st.cache_data
def get_debug_diagnostics(path_excel, path_m1, path_m2, path_m3, path_stats_m1, path_stats_m2, path_stats_m3):
    """
    Analyse les fichiers sources (humains et modèles) pour détecter des 
    incohérences structurelles avant tout alignement.

    Parameters
    ----------
    path_excel : str
        Chemin vers le fichier de réponses humaines (référentiel).
    path_m1 : str
        Chemin vers la base de données JSON générée par le Modèle 1.
    path_m2 : str
        Chemin vers la base de données JSON générée par le Modèle 2.
    path_m3 : str
        Chemin vers la base de données JSON générée par le Modèle 3.
    path_stats_m1 : str
        Chemin vers le rapport statistique du Modèle 1.
    path_stats_m2 : str
        Chemin vers le rapport statistique du Modèle 2.
    path_stats_m3 : str
        Chemin vers le rapport statistique du Modèle 3.

    Returns
    -------
    dict
        Dictionnaire contenant la liste des anomalies trouvées :
        fichiers inaccessibles, doublons, dossiers fantômes, dossiers 
        manquants et écarts au niveau des colonnes (manquantes/inventées).
    """
    diag = {"fichiers_inaccessibles": []}
    
    for chemin in [path_excel, path_m1, path_m2, path_m3, path_stats_m1, path_stats_m2, path_stats_m3]:
        if not os.path.exists(chemin):
            diag["fichiers_inaccessibles"].append(chemin)
            
    fichiers_sections = [
        "a_procedure.txt", "b_profil_social.txt", "c_violences_denoncees.txt",
        "d_demandes.txt", "e_reponses_sur_violences.txt", "f_reponses_sur_demandes.txt",
        "g_violences_retenues_jaf.txt", "h_decision_jaf.txt", "i_bracelet_anti_rapprochement.txt"
    ]
    for fic in fichiers_sections:
        ch = os.path.join("prompts", fic)
        if not os.path.exists(ch): diag["fichiers_inaccessibles"].append(ch)

    if not os.path.exists(path_excel) or not os.path.exists(path_m1):
        return diag

    def get_col_id(df):
        for col in df.columns:
            if str(col).strip().lower() == 'no_rg': return col
        return df.columns[0]

    df_cor = pd.read_excel(path_excel)
    df_m1 = pd.read_json(path_m1)
    df_m2 = pd.read_json(path_m2) if os.path.exists(path_m2) else pd.DataFrame()
    df_m3 = pd.read_json(path_m3) if os.path.exists(path_m3) else pd.DataFrame()

    col_cor = get_col_id(df_cor)
    col_m1 = get_col_id(df_m1)
    
    df_cor['id_clean'] = df_cor[col_cor].apply(nettoyer_id_global)
    df_m1['id_clean'] = df_m1[col_m1].apply(nettoyer_id_global)
    if not df_m2.empty:
        col_m2 = get_col_id(df_m2)
        df_m2['id_clean'] = df_m2[col_m2].apply(nettoyer_id_global)
    if not df_m3.empty:
        col_m3 = get_col_id(df_m3)
        df_m3['id_clean'] = df_m3[col_m3].apply(nettoyer_id_global)

    diag["doublons_humain"] = df_cor[df_cor.duplicated(subset=['id_clean'], keep=False)][col_cor].tolist()
    diag["doublons_m1"] = df_m1[df_m1.duplicated(subset=['id_clean'], keep=False)][col_m1].tolist()
    diag["doublons_m2"] = df_m2[df_m2.duplicated(subset=['id_clean'], keep=False)][col_m2].tolist() if not df_m2.empty else []
    diag["doublons_m3"] = df_m3[df_m3.duplicated(subset=['id_clean'], keep=False)][col_m3].tolist() if not df_m3.empty else []

    ids_cor = set(df_cor['id_clean'])
    ids_m1 = set(df_m1['id_clean'])
    ids_m2 = set(df_m2['id_clean']) if not df_m2.empty else set()
    ids_m3 = set(df_m3['id_clean']) if not df_m3.empty else set()

    diag["fantomes_m1"] = sorted(list(ids_m1 - ids_cor))
    diag["fantomes_m2"] = sorted(list(ids_m2 - ids_cor))
    diag["fantomes_m3"] = sorted(list(ids_m3 - ids_cor))
    
    diag["manquants_m1"] = sorted(list(ids_cor - ids_m1))
    diag["manquants_m2"] = sorted(list(ids_cor - ids_m2))
    diag["manquants_m3"] = sorted(list(ids_cor - ids_m3))

    cols_cor = set([str(c).lower() for c in df_cor.columns]) - {'id_clean', str(col_cor).lower()}
    cols_m1 = set([str(c).lower() for c in df_m1.columns]) - {'id_clean', str(col_m1).lower()}
    
    diag["cols_manquantes_m1"] = sorted(list(cols_cor - cols_m1))
    diag["cols_inventees_m1"] = sorted(list(cols_m1 - cols_cor))

    return diag

# ==========================================
#          GÉNÉRATION MODÈLE 4 (HYBRIDE)
# ==========================================
def generer_modele_m4(df_rep_m2, df_rep_m3, df_stats_m2, df_stats_m3):
    """
    Construit dynamiquement les données et statistiques du Modèle 4 (Hybride).

    Le Modèle 4 fusionne les performances du Modèle 2 et du Modèle 3 en appliquant 
    les résultats du M2 sur une liste de variables spécifiques (VARS_M2_IN_M4) 
    et en forçant un taux de réussite de 100% sur certaines variables 
    (VARS_FORCE_CORRECT) considérées comme corrigées suite à une erreur humaine.

    Parameters
    ----------
    df_rep_m2 : pandas.DataFrame
        Base de données des réponses du Modèle 2.
    df_rep_m3 : pandas.DataFrame
        Base de données des réponses du Modèle 3.
    df_stats_m2 : pandas.DataFrame
        Rapport statistique du Modèle 2.
    df_stats_m3 : pandas.DataFrame
        Rapport statistique du Modèle 3.

    Returns
    -------
    tuple
        (pandas.DataFrame, pandas.DataFrame)
        Le premier élément est la table des réponses du Modèle 4.
        Le second élément est la table des statistiques du Modèle 4.
    """
    if df_rep_m3.empty or df_stats_m3.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    df_rep_m4 = df_rep_m3.copy()
    df_stats_m4 = df_stats_m3.copy()
    
    for var in VARS_M2_IN_M4:
        var_l = var.lower().strip()
        if var_l in df_rep_m2.columns and var_l in df_rep_m4.columns:
            df_rep_m4[var_l] = df_rep_m2[var_l]
            
        row_m2 = df_stats_m2[df_stats_m2['Variable'] == var_l]
        if not row_m2.empty:
            idx_m4 = df_stats_m4[df_stats_m4['Variable'] == var_l].index
            if len(idx_m4) > 0:
                # Ajout des 3 nouvelles colonnes à transférer
                colonnes_a_transferer = [
                    'Nb_Bonnes_Reponses', 'Nb_Mauvaises_Reponses', '%_Bonnes_Reponses', 
                    '%_Bonnes_Reponses_Num', 'Nb_Reponses_Fournies', 'Nb_Repondu_Par_Les_Deux', 
                    'Nb_Bonnes_Reponses_Communes', '%_Reussite_Communes'
                ]
                for col_stat in colonnes_a_transferer:
                    if col_stat in row_m2.columns:
                        df_stats_m4.loc[idx_m4, col_stat] = row_m2.iloc[0][col_stat]
                        
    for var in VARS_FORCE_CORRECT:
        var_l = var.lower().strip()
        idx_m4 = df_stats_m4[df_stats_m4['Variable'] == var_l].index
        if len(idx_m4) > 0:
            nb_rep = df_stats_m4.loc[idx_m4, 'Nb_Reponses_Fournies'].values[0]
            df_stats_m4.loc[idx_m4, 'Nb_Bonnes_Reponses'] = nb_rep
            df_stats_m4.loc[idx_m4, 'Nb_Mauvaises_Reponses'] = 0
            df_stats_m4.loc[idx_m4, '%_Bonnes_Reponses_Num'] = 100.0
            df_stats_m4.loc[idx_m4, '%_Bonnes_Reponses'] = "100.0 %"
            # Force la correction sur les métriques strictes aussi
            if 'Nb_Repondu_Par_Les_Deux' in df_stats_m4.columns:
                nb_rep_strict = df_stats_m4.loc[idx_m4, 'Nb_Repondu_Par_Les_Deux'].values[0]
                df_stats_m4.loc[idx_m4, 'Nb_Bonnes_Reponses_Communes'] = nb_rep_strict
                df_stats_m4.loc[idx_m4, '%_Reussite_Communes'] = "100.0 %"
            
    return df_rep_m4, df_stats_m4
# ==========================================
#          CHARGEMENT DES DONNÉES JSON
# ==========================================
@st.cache_data
def load_data(path_excel, path_m1, path_stats_m1, path_m2, path_stats_m2, path_m3, path_stats_m3):
    """
    Charge, consolide et synchronise les bases de données issues de l'expertise humaine 
    et des pipelines d'extraction LLM.

    Traite la suppression des doublons, aligne les index par numéro RG, normalise 
    les types des colonnes et génère les statistiques par section.
    
    Parameters
    ----------
    path_excel : str
        Chemin d'accès au fichier Excel de référence (expert).
    path_m1 : str
        Chemin vers le JSON de résultats du Modèle 1.
    path_stats_m1 : str
        Chemin vers le JSON de statistiques du Modèle 1.
    path_m2 : str
        Chemin vers le JSON de résultats du Modèle 2.
    path_stats_m2 : str
        Chemin vers le JSON de statistiques du Modèle 2.
    path_m3 : str
        Chemin vers le JSON de résultats du Modèle 3.
    path_stats_m3 : str
        Chemin vers le JSON de statistiques du Modèle 3.

    Returns
    -------
    tuple
        Tuple contenant l'ensemble des DataFrames (réponses et stats) pour 
        les modèles M1, M2, M3, M4, le référentiel humain, et les listes de 
        dossiers manquants pour chaque modèle.
    """
    if not os.path.exists(path_excel):
        st.error("Fichier de correction introuvable.")
        st.stop()
        
    df_cor = pd.read_excel(path_excel)
    
    try:
        df_rep_m1 = pd.read_json(path_m1)
        df_stats_m1 = pd.read_json(path_stats_m1)
        
        df_rep_m2 = pd.read_json(path_m2) if os.path.exists(path_m2) else pd.DataFrame()
        df_stats_m2 = pd.read_json(path_stats_m2) if os.path.exists(path_stats_m2) else pd.DataFrame()
        
        df_rep_m3 = pd.read_json(path_m3) if os.path.exists(path_m3) else pd.DataFrame()
        df_stats_m3 = pd.read_json(path_stats_m3) if os.path.exists(path_stats_m3) else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Impossible de charger l'un des fichiers JSON. As-tu bien relancé les pipelines ?\n\nErreur : {e}")
        st.stop()
        
    df_cor.columns = [str(c).lower().strip() for c in df_cor.columns]
    df_rep_m1.columns = [str(c).lower().strip() for c in df_rep_m1.columns]
    if not df_rep_m2.empty:
        df_rep_m2.columns = [str(c).lower().strip() for c in df_rep_m2.columns]
    if not df_rep_m3.empty:
        df_rep_m3.columns = [str(c).lower().strip() for c in df_rep_m3.columns]
    
    if 'no_cmpst' in df_cor.columns: df_cor.drop(columns=['no_cmpst'], inplace=True)
    if 'no_cmpst' in df_rep_m1.columns: df_rep_m1.drop(columns=['no_cmpst'], inplace=True)
    if not df_rep_m2.empty and 'no_cmpst' in df_rep_m2.columns: df_rep_m2.drop(columns=['no_cmpst'], inplace=True)
    if not df_rep_m3.empty and 'no_cmpst' in df_rep_m3.columns: df_rep_m3.drop(columns=['no_cmpst'], inplace=True)
    
    def get_col_id(df):
        for col in df.columns:
            if str(col).strip().lower() == 'no_rg': return col
        return df.columns[0]

    col_id_cor = get_col_id(df_cor)
    df_cor['id_clean'] = df_cor[col_id_cor].apply(nettoyer_id_global)
    
    col_id_m1 = get_col_id(df_rep_m1)
    df_rep_m1['id_clean'] = df_rep_m1[col_id_m1].apply(nettoyer_id_global)
    
    if not df_rep_m2.empty:
        col_id_m2 = get_col_id(df_rep_m2)
        df_rep_m2['id_clean'] = df_rep_m2[col_id_m2].apply(nettoyer_id_global)
        
    if not df_rep_m3.empty:
        col_id_m3 = get_col_id(df_rep_m3)
        df_rep_m3['id_clean'] = df_rep_m3[col_id_m3].apply(nettoyer_id_global)
    
    df_cor = df_cor[df_cor['id_clean'] != "inconnu"].drop_duplicates(subset=['id_clean'], keep='first')
    df_rep_m1 = df_rep_m1[df_rep_m1['id_clean'] != "inconnu"].drop_duplicates(subset=['id_clean'], keep='first')
    if not df_rep_m2.empty:
        df_rep_m2 = df_rep_m2[df_rep_m2['id_clean'] != "inconnu"].drop_duplicates(subset=['id_clean'], keep='first')
    if not df_rep_m3.empty:
        df_rep_m3 = df_rep_m3[df_rep_m3['id_clean'] != "inconnu"].drop_duplicates(subset=['id_clean'], keep='first')

    df_cor.set_index('id_clean', inplace=True, drop=False)
    df_rep_m1.set_index('id_clean', inplace=True, drop=False)
    if not df_rep_m2.empty:
        df_rep_m2.set_index('id_clean', inplace=True, drop=False)
    if not df_rep_m3.empty:
        df_rep_m3.set_index('id_clean', inplace=True, drop=False)
    
    index_communs = df_cor.index.intersection(df_rep_m1.index)
    if not df_rep_m2.empty:
        index_communs = index_communs.intersection(df_rep_m2.index)
    if not df_rep_m3.empty:
        index_communs = index_communs.intersection(df_rep_m3.index)
        
    df_cor = df_cor.loc[index_communs]
    df_rep_m1 = df_rep_m1.loc[index_communs]
    if not df_rep_m2.empty:
        df_rep_m2 = df_rep_m2.loc[index_communs]
    if not df_rep_m3.empty:
        df_rep_m3 = df_rep_m3.loc[index_communs]
        
    dossiers_attendus = set(df_cor.index)
    manquants_m1 = sorted(list(dossiers_attendus - set(df_rep_m1.index)))
    manquants_m2 = sorted(list(dossiers_attendus - set(df_rep_m2.index)))
    manquants_m3 = sorted(list(dossiers_attendus - set(df_rep_m3.index)))
    
    var_to_section = build_variable_to_section_mapping()
    
    for df_s in [df_stats_m1, df_stats_m2, df_stats_m3]:
        if not df_s.empty:
            mapping_colonnes = {
                '%_Reussite_Globale': '%_Bonnes_Reponses',
                'Nb_Total_Dossiers': 'Nb_Reponses_Fournies',
                'Erreurs_LLM': 'Nb_Mauvaises_Reponses'
            }
            df_s.rename(columns=mapping_colonnes, inplace=True, errors='ignore')
            
            if 'Nb_Bonnes_Reponses' not in df_s.columns and 'Nb_Reponses_Fournies' in df_s.columns and 'Nb_Mauvaises_Reponses' in df_s.columns:
                df_s['Nb_Bonnes_Reponses'] = df_s['Nb_Reponses_Fournies'] - df_s['Nb_Mauvaises_Reponses']
            
            if '%_Reponse' not in df_s.columns:
                df_s['%_Reponse'] = "100.0 %" 

            df_s['Variable'] = df_s['Variable'].astype(str).str.lower().str.strip()
            df_s.drop(df_s[df_s['Variable'] == 'no_cmpst'].index, inplace=True, errors='ignore')
            
            if '%_Bonnes_Reponses' in df_s.columns:
                df_s['%_Bonnes_Reponses_Num'] = df_s['%_Bonnes_Reponses'].astype(str).str.replace(' %', '', regex=False).astype(float)
            else:
                df_s['%_Bonnes_Reponses_Num'] = 0.0
                
            df_s['Section_Code'] = df_s['Variable'].apply(lambda x: var_to_section.get(str(x).lower(), 'Autre'))
            df_s['Section_Nom'] = df_s['Section_Code'].map(SECTIONS_MAPPING).fillna("Autres variables")
            
    df_rep_m4, df_stats_m4 = generer_modele_m4(df_rep_m2, df_rep_m3, df_stats_m2, df_stats_m3)
    manquants_m4 = manquants_m3
        
    return df_rep_m1, df_stats_m1, df_rep_m2, df_stats_m2, df_rep_m3, df_stats_m3, df_rep_m4, df_stats_m4, df_cor, manquants_m1, manquants_m2, manquants_m3, manquants_m4

(
    df_rep_m1, df_stats_m1, 
    df_rep_m2, df_stats_m2, 
    df_rep_m3, df_stats_m3, 
    df_rep_m4, df_stats_m4,
    df_cor, 
    manquants_m1, manquants_m2, manquants_m3, manquants_m4
) = load_data(
    CHEMIN_EXCEL_CORRIGE, 
    CHEMIN_GENERE_M1, CHEMIN_STATS_M1, 
    CHEMIN_GENERE_M2, CHEMIN_STATS_M2,
    CHEMIN_GENERE_M3, CHEMIN_STATS_M3
)

# ==========================================
#      INTERFACE GRAPHIQUE & NAVIGATION
# ==========================================
st.sidebar.title("🧭 Menu Principal")

st.sidebar.markdown("### 1. Choix des données")
choix_modele = st.sidebar.radio(
    "Sélectionne le modèle :", 
    [
        "Modèle 1 (Texte Complet)", 
        "Modèle 2 (Texte Découpé)", 
        "Modèle 3 (Méthode 3)",
        "Modèle 4 (Hybride M2+M3)"
    ]
)

if choix_modele == "Modèle 1 (Texte Complet)":
    df_rep_active = df_rep_m1
    df_stats_active = df_stats_m1
    manquants_actifs = manquants_m1
    titre_modele = "M1 (Texte Complet)"
elif choix_modele == "Modèle 2 (Texte Découpé)":
    df_rep_active = df_rep_m2
    df_stats_active = df_stats_m2
    manquants_actifs = manquants_m2
    titre_modele = "M2 (Texte Découpé par section)"
elif choix_modele == "Modèle 3 (Méthode 3)":
    df_rep_active = df_rep_m3
    df_stats_active = df_stats_m3
    manquants_actifs = manquants_m3
    titre_modele = "M3 (Méthode 3)"
else:
    df_rep_active = df_rep_m4
    df_stats_active = df_stats_m4
    manquants_actifs = manquants_m4
    titre_modele = "M4 (Hybride M3 + M2 + Corrections)"

st.sidebar.markdown("### 2. Filtres & Alertes")

# --- Interrupteur d'affichage ---
mode_calcul = st.sidebar.radio(
    "Méthode de calcul des statistiques :",
    ["🌐 Global (Inclut vides & déductions)", "🎯 Strict (Humain ET LLM ont répondu)"]
)

if mode_calcul == "🎯 Strict (Humain ET LLM ont répondu)":
    if not df_stats_active.empty and 'Nb_Repondu_Par_Les_Deux' in df_stats_active.columns:
        df_stats_active = df_stats_active.copy()
        # On remplace les colonnes globales par les colonnes strictes
        df_stats_active['Nb_Reponses_Fournies'] = df_stats_active['Nb_Repondu_Par_Les_Deux']
        df_stats_active['Nb_Bonnes_Reponses'] = df_stats_active['Nb_Bonnes_Reponses_Communes']
        df_stats_active['Nb_Mauvaises_Reponses'] = df_stats_active['Nb_Repondu_Par_Les_Deux'] - df_stats_active['Nb_Bonnes_Reponses_Communes']
        df_stats_active['%_Bonnes_Reponses_Num'] = df_stats_active['%_Reussite_Communes'].astype(str).str.replace(' %', '').astype(float)
else:
    df_stats_active = df_stats_active.copy()

min_vol_global = 0
max_vol_global = 100
dfs_presents = [df for df in [df_stats_m1, df_stats_m2, df_stats_m3, df_stats_m4] if not df.empty]
if dfs_presents:
    min_vol_global = min(int(df['Nb_Reponses_Fournies'].min()) for df in dfs_presents)
    max_vol_global = max(int(df['Nb_Reponses_Fournies'].max()) for df in dfs_presents)

if "seuil_volume" not in st.session_state: st.session_state.seuil_volume = min_vol_global

seuil_volume = st.sidebar.slider(
    "Volume minimum de réponses :", 
    min_value=min_vol_global, max_value=max_vol_global, key="seuil_volume"
)

if not df_stats_active.empty:
    df_stats_active = df_stats_active[df_stats_active['Nb_Reponses_Fournies'] >= seuil_volume]

if manquants_actifs:
    with st.sidebar.expander(f"⚠️ {len(manquants_actifs)} dossiers manquants", expanded=False):
        st.error(f"Le lot analysé compte **{len(manquants_actifs)} dossiers** qui ont été ratés avec ce LLM.")
        st.write(", ".join(str(x).upper() for x in manquants_actifs))

st.sidebar.divider()

st.sidebar.markdown("### 3. Vues analytiques")
choix_page = st.sidebar.radio("Navigation", [
    MENU_GLOBAL, MENU_TABLEAU, MENU_VARIABLE, 
    MENU_DOSSIER, MENU_SECTION, MENU_COMPARAISON, 
    MENU_JUSTIF,  
    MENU_DEBUG
], key="page", label_visibility="collapsed")

st.title(f"🤖 Dashboard Analytique OPVC — {titre_modele}")

if choix_page not in [MENU_COMPARAISON, MENU_JUSTIF, MENU_DEBUG]:
    st.caption(f"Analyse sur {len(df_rep_active)} dossiers | Variables filtrées (≥ {seuil_volume} réponses).")

# ==================================================
# ONGLET 1 : VUE GLOBALE
# ==================================================
if choix_page == MENU_GLOBAL:
    st.subheader(f"📊 Indicateurs Clés ({titre_modele})")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Taux de Précision Moyen", f"{df_stats_active['%_Bonnes_Reponses_Num'].mean():.1f} %" if not df_stats_active.empty else "N/A")
    col2.metric("Total Dossiers Analysés", len(df_rep_active))
    col3.metric("Variables Suivies (Filtrées)", len(df_stats_active))
    
    st.divider()
    
    st.subheader("🏆 Le Top 5 : Les variables les mieux extraites")
    if not df_stats_active.empty:
        df_top5 = df_stats_active.sort_values(by='%_Bonnes_Reponses_Num', ascending=False).head(5)
        fig_top = px.bar(
            df_top5, x='%_Bonnes_Reponses_Num', y='Libellé', orientation='h',
            color='%_Bonnes_Reponses_Num', color_continuous_scale='Greens',
            text=df_top5['%_Bonnes_Reponses_Num'].apply(lambda x: f"{x:.1f}%")
        )
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, coloraxis_showscale=False, height=300)
        st.plotly_chart(fig_top, width="stretch")
    else:
        st.info("Aucune donnée disponible pour ce niveau de filtre.")

# ==================================================
# ONGLET 2 : TABLEAU DÉTAILLÉ
# ==================================================
elif choix_page == MENU_TABLEAU:
    st.subheader(f"📋 Tableau de Bord Détaillé ({titre_modele})")
    st.markdown("💡 **Astuce : Clique sur une ligne du tableau pour enquêter dessus directement dans l'Explorateur de Variables !**")
    
    if not df_stats_active.empty:
        df_display = df_stats_active[[
            'Section_Nom', 'Variable', 'Libellé', 'Nb_Reponses_Fournies',
            '%_Reponse', 'Nb_Bonnes_Reponses', 'Nb_Mauvaises_Reponses', '%_Bonnes_Reponses_Num'
        ]].copy().rename(columns={
            'Section_Nom': 'Section', 'Libellé': 'Question abordée', 'Nb_Reponses_Fournies': 'Volume de réponses',
            '%_Reponse': 'Taux de présence', 'Nb_Bonnes_Reponses': '✅ Bonnes',
            'Nb_Mauvaises_Reponses': '❌ Erreurs', '%_Bonnes_Reponses_Num': '🎯 Précision (%)'
        })
        
        styled_df = df_display.style.background_gradient(subset=['🎯 Précision (%)'], cmap='RdYlGn', vmin=0, vmax=100)\
            .background_gradient(subset=['Volume de réponses'], cmap='Blues')\
            .background_gradient(subset=['❌ Erreurs'], cmap='Reds').format({'🎯 Précision (%)': "{:.1f} %"})
        
        selection_event = st.dataframe(styled_df, width="stretch", height=500, hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if selection_event.selection.rows:
            row_idx = selection_event.selection.rows[0]
            st.session_state.selected_var = df_display.iloc[row_idx]['Variable']
            st.session_state.page = MENU_VARIABLE
            st.rerun()
    else:
        st.info("Aucune donnée disponible pour ce niveau de filtre.")

# ==================================================
# ONGLET 3 : EXPLORATEUR DE VARIABLES
# ==================================================
elif choix_page == MENU_VARIABLE:
    st.subheader("🔍 Face-à-face Modèles vs Humain")
    
    if df_stats_active.empty:
        st.warning("Aucune variable à explorer avec le niveau de filtre actuel.")
    else:
        col_filtre_sec, col_tri_var = st.columns(2)
        with col_filtre_sec:
            list_sections = ["Toutes les sections"] + sorted(list(df_stats_active['Section_Nom'].unique()))
            sel_section = st.selectbox("🗂️ Filtrer par sous-section :", list_sections)
            
        with col_tri_var:
            criteres_tri = {
                "❌ Mauvaises réponses (Décroissant - Le plus d'erreurs)": ("Nb_Mauvaises_Reponses", False),
                "🎯 % Bonnes réponses (Croissant - Les moins précis)": ("%_Bonnes_Reponses_Num", True),
                "🎯 % Bonnes réponses (Décroissant - Les plus précis)": ("%_Bonnes_Reponses_Num", False),
                "📊 Volume de réponses (Décroissant)": ("Nb_Reponses_Fournies", False),
                "🔤 Ordre alphabétique (Code variable)": ("Variable", True)
            }
            sel_tri = st.selectbox("↕️ Ordonner les variables par :", list(criteres_tri.keys()), index=0)
            
        df_explorer = df_stats_active.copy()
        if sel_section != "Toutes les sections":
            df_explorer = df_explorer[df_explorer['Section_Nom'] == sel_section]
            
        col_tri, asc = criteres_tri[sel_tri]
        df_explorer = df_explorer.sort_values(by=col_tri, ascending=asc)
        
        if df_explorer.empty:
            st.warning("Aucune variable ne correspond aux critères de filtre pour cette sous-section.")
        else:
            def format_label(r):
                nb_err = int(float(r['Nb_Mauvaises_Reponses'])) if pd.notna(r['Nb_Mauvaises_Reponses']) else 0
                return f"{r['Variable']} — {r['Libellé']} [❌ Erreurs : {nb_err} | 🎯 Précision : {r['%_Bonnes_Reponses_Num']:.1f}%]"
            
            options_variables = df_explorer.apply(format_label, axis=1).tolist()
            
            index_par_defaut = 0
            if st.session_state.selected_var:
                for i, opt in enumerate(options_variables):
                    if opt.startswith(f"{st.session_state.selected_var} —"):
                        index_par_defaut = i
                        break
            
            selection_var = st.selectbox("Sélectionner la variable à inspecter :", options_variables, index=index_par_defaut)
            var_technique = selection_var.split(' — ')[0].strip().lower()
            st.session_state.selected_var = var_technique
            
            row_stats = df_explorer[df_explorer['Variable'] == var_technique].iloc[0]
            
            with st.expander(f"📖 Voir les modalités de réponse pour : {var_technique}", expanded=False):
                st.code(charger_dictionnaire_variable(var_technique, row_stats['Section_Code']), language="text")
            
            col_dossier = df_rep_active['no_rg'] if 'no_rg' in df_rep_active.columns else df_rep_active.index
            df_alignement = pd.DataFrame({
                "Dossier": col_dossier,
                "Humain": extraire_colonne_securisee(df_cor, var_technique, df_rep_active.index),
                "LLM 1 (Complet)": extraire_colonne_securisee(df_rep_m1, var_technique, df_rep_active.index),
                "LLM 2 (Découpé)": extraire_colonne_securisee(df_rep_m2, var_technique, df_rep_active.index),
                "LLM 3 (Méthode 3)": extraire_colonne_securisee(df_rep_m3, var_technique, df_rep_active.index),
                "LLM 4 (Hybride)": extraire_colonne_securisee(df_rep_m4, var_technique, df_rep_active.index)
            })
            
            def evaluer_statut(llm, cor, var_name, is_m4=False):
                if is_m4 and var_name in VARS_FORCE_CORRECT:
                    return "✅ Conforme (Erreur Humaine Corrigée)"
                if llm == cor: return "✅ Conforme"
                if cor == "nan" and llm != "nan": return "🔹 LLM en Plus (Accepté)"
                return "❌ Écart détecté"
                    
            df_alignement['Statut M1'] = df_alignement.apply(lambda r: evaluer_statut(r['LLM 1 (Complet)'], r['Humain'], var_technique, False), axis=1)
            df_alignement['Statut M2'] = df_alignement.apply(lambda r: evaluer_statut(r['LLM 2 (Découpé)'], r['Humain'], var_technique, False), axis=1)
            df_alignement['Statut M3'] = df_alignement.apply(lambda r: evaluer_statut(r['LLM 3 (Méthode 3)'], r['Humain'], var_technique, False), axis=1)
            df_alignement['Statut M4'] = df_alignement.apply(lambda r: evaluer_statut(r['LLM 4 (Hybride)'], r['Humain'], var_technique, True), axis=1)
            
            mode_affichage = st.radio("Affichage :", ["Tous les dossiers", "Uniquement les lignes problématiques (Écarts)"], horizontal=True)
            if "Écarts" in mode_affichage:
                df_alignement = df_alignement[
                    (df_alignement['Statut M1'] == "❌ Écart détecté") | 
                    (df_alignement['Statut M2'] == "❌ Écart détecté") | 
                    (df_alignement['Statut M3'] == "❌ Écart détecté") |
                    (df_alignement['Statut M4'] == "❌ Écart détecté")
                ]
            # --- Application du filtre visuel Strict ---
            # Si le toggle de la sidebar est sur Strict, on retire les dossiers 
            # où l'humain OU le LLM actif n'a pas répondu.
            if mode_calcul == "🎯 Strict (Humain ET LLM ont répondu)":
                # On détermine quelle est la colonne LLM active selon le choix de la sidebar
                if "Modèle 1" in choix_modele: col_llm_active = "LLM 1 (Complet)"
                elif "Modèle 2" in choix_modele: col_llm_active = "LLM 2 (Découpé)"
                elif "Modèle 3" in choix_modele: col_llm_active = "LLM 3 (Méthode 3)"
                else: col_llm_active = "LLM 4 (Hybride)"

                # On filtre le dataframe pour ne garder que les vraies réponses
                df_alignement = df_alignement[
                    (df_alignement['Humain'] != "nan") & 
                    (df_alignement[col_llm_active] != "nan")
                ]
                st.info(f"Filtre Strict actif : Seuls les dossiers où l'humain et le {col_llm_active} ont formulé une réponse (y compris 'x') sont affichés.")
            
            col_table, col_pie = st.columns([2, 1])
            with col_table: 
                st.dataframe(
                    df_alignement, width="stretch", hide_index=True, 
                    column_config={"Statut M1": None, "Statut M2": None, "Statut M3": None, "Statut M4": None}
                )
                
            with col_pie:
                st.markdown("##### Distribution des réponses")
                color_map = {
                    "✅ Conforme": "#2ca02c", 
                    "✅ Conforme (Erreur Humaine Corrigée)": "#2ca02c",
                    "🔹 LLM en Plus (Accepté)": "#1a73e8", 
                    "❌ Écart détecté": "#d62728"
                }
                
                for mode_nom, col_statut in [
                    ("M1 (Texte Complet)", 'Statut M1'), 
                    ("M2 (Texte Découpé)", 'Statut M2'), 
                    ("M3 (Méthode 3)", 'Statut M3'),
                    ("M4 (Hybride M2+M3)", 'Statut M4')
                ]:
                    rep = df_alignement[col_statut].value_counts()
                    if not rep.empty:
                        fig = px.pie(values=rep.values, names=rep.index, title=mode_nom, color=rep.index, color_discrete_map=color_map, hole=0.4)
                        fig.update_layout(margin=dict(t=40, b=10, l=0, r=0), height=220)
                        st.plotly_chart(fig, width="stretch")

# ==================================================
# ONGLET 4 : DEEP DIVE PAR DOSSIER
# ==================================================
elif choix_page == MENU_DOSSIER:
    st.subheader(f"📄 Fiche d'audit unifiée ({titre_modele})")
    
    if df_rep_active.empty:
        st.warning("Aucun dossier disponible pour ce modèle.")
    else:
        id_col_name = 'no_rg' if 'no_rg' in df_rep_active.columns else df_rep_active.columns[0]
        id_dossier_affich = st.selectbox("Choisir un identifiant de dossier :", sorted(df_rep_active[id_col_name].unique()))
        id_clean_sel = df_rep_active[df_rep_active[id_col_name] == id_dossier_affich].index[0]
        
        champs_m1 = df_rep_m1.loc[id_clean_sel] if not df_rep_m1.empty else pd.Series()
        champs_m2 = df_rep_m2.loc[id_clean_sel] if not df_rep_m2.empty else pd.Series()
        champs_m3 = df_rep_m3.loc[id_clean_sel] if not df_rep_m3.empty else pd.Series()
        champs_m4 = df_rep_m4.loc[id_clean_sel] if not df_rep_m4.empty else pd.Series()
        champs_humain = df_cor.loc[id_clean_sel]
        
        liste_audit = []
        for _, row in df_stats_active.iterrows():
            var = row['Variable']
            val_m1 = normaliser_pour_affichage(champs_m1.get(var, ''), var)
            val_m2 = normaliser_pour_affichage(champs_m2.get(var, ''), var)
            val_m3 = normaliser_pour_affichage(champs_m3.get(var, ''), var)
            val_m4 = normaliser_pour_affichage(champs_m4.get(var, ''), var)
            val_human = normaliser_pour_affichage(champs_humain.get(var, ''), var)
            
            if choix_modele == "Modèle 1 (Texte Complet)": val_active = val_m1
            elif choix_modele == "Modèle 2 (Texte Découpé)": val_active = val_m2
            elif choix_modele == "Modèle 3 (Méthode 3)": val_active = val_m3
            else: val_active = val_m4
            
            if choix_modele == "Modèle 4 (Hybride M2+M3)" and var in VARS_FORCE_CORRECT:
                statut_actif = "✅ Correct (Erreur Humaine Corrigée)"
            elif val_active == val_human: statut_actif = "✅ Correct"
            elif val_human == "nan" and val_active != "nan": statut_actif = "🔹 LLM en Plus"
            else: statut_actif = "❌ Écart"
            
            def format_llm(llm, cor):
                if llm == cor: return f"✅ {llm}"
                if cor == "nan" and llm != "nan": return f"🔹 {llm}"
                return f"❌ {llm}"
            
            liste_audit.append({
                "Section": row['Section_Nom'], "Variable": var, "Libellé": row['Libellé'], 
                "Humain": val_human, 
                "LLM 1 (Complet)": format_llm(val_m1, val_human),
                "LLM 2 (Découpé)": format_llm(val_m2, val_human),
                "LLM 3 (Méthode 3)": format_llm(val_m3, val_human),
                "LLM 4 (Hybride)": "✅ (Erreur Humaine Corrigée)" if var in VARS_FORCE_CORRECT else format_llm(val_m4, val_human),
                "Résultat Actif": statut_actif
            })
            
        df_audit = pd.DataFrame(liste_audit)
        
        def colorier_cellules(row):
            res = row['Résultat Actif']
            if res == "❌ Écart": return ['background-color: #fce8e6; color: #a51d24; font-weight: bold;'] * len(row)
            if res in ["🔹 LLM en Plus", "✅ Correct (Erreur Humaine Corrigée)"]: return ['background-color: #e8f0fe; color: #1a73e8; font-weight: bold;'] * len(row)
            return [''] * len(row)
        
        st.write("Les cases en **bleu** représentent les cas acceptés où le LLM apporte une information non saisie par l'humain ou corrige une erreur humaine (pour M4).")
        
        st.dataframe(
            df_audit.style.apply(colorier_cellules, axis=1), 
            column_config={"Résultat Actif": None}, 
            width="stretch", 
            hide_index=True, 
            height=500
        )

# ==================================================
# ONGLET 5 : PERFORMANCE PAR SECTION
# ==================================================
elif choix_page == MENU_SECTION:
    st.subheader(f"🗂️ Analyse macro par bloc juridique ({titre_modele})")
    
    if not df_stats_active.empty:
        df_sections = df_stats_active[df_stats_active['Section_Code'] != 'Autre'].groupby('Section_Nom').agg(
            Total_Bonnes=('Nb_Bonnes_Reponses', 'sum'),
            Total_Reponses=('Nb_Reponses_Fournies', 'sum'),
            Nombre_Variables=('Variable', 'count')
        ).reset_index()
        
        df_sections['Precision_Moyenne'] = (df_sections['Total_Bonnes'] / df_sections['Total_Reponses']) * 100
        df_sections = df_sections.sort_values(by='Precision_Moyenne', ascending=False)
        
        fig_sec = px.bar(
            df_sections, x='Precision_Moyenne', y='Section_Nom', orientation='h',
            color='Precision_Moyenne', color_continuous_scale='Viridis',
            text=df_sections['Precision_Moyenne'].apply(lambda x: f"{x:.1f}%")
        )
        fig_sec.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig_sec, width="stretch")
    else:
        st.info("Aucune donnée disponible pour ce niveau de filtre.")

# ==================================================
# ONGLET 6 : COMPARAISON DE DUELS (M4 CENTERED)
# ==================================================
elif choix_page == MENU_COMPARAISON:
    st.title("⚖️ Performance Comparée (Focus Modèle 4)")
    st.markdown(f"Cet onglet compare directement la précision du **Modèle 4 (Hybride)** par rapport aux trois autres méthodes pour les variables possédant au moins **{seuil_volume} réponses**.")
    
    if df_stats_m1.empty or df_stats_m2.empty or df_stats_m3.empty or df_stats_m4.empty:
        st.error("Comparaison impossible : l'un des quatre modèles possède des statistiques vides.")
    else:
        # Importation structurée des volumes de réponses et précisions
        df_stats_compare = pd.merge(
            df_stats_m1[['Variable', 'Libellé', 'Section_Nom', 'Section_Code', 'Nb_Reponses_Fournies', 'Nb_Bonnes_Reponses', '%_Bonnes_Reponses_Num']].rename(
                columns={'Nb_Reponses_Fournies': 'Nb_Reponses_Fournies_M1', 'Nb_Bonnes_Reponses': 'Nb_Bonnes_Reponses_M1', '%_Bonnes_Reponses_Num': '%_Bonnes_Reponses_Num_M1'}
            ),
            df_stats_m2[['Variable', 'Nb_Reponses_Fournies', 'Nb_Bonnes_Reponses', '%_Bonnes_Reponses_Num']].rename(
                columns={'Nb_Reponses_Fournies': 'Nb_Reponses_Fournies_M2', 'Nb_Bonnes_Reponses': 'Nb_Bonnes_Reponses_M2', '%_Bonnes_Reponses_Num': '%_Bonnes_Reponses_Num_M2'}
            ),
            on='Variable'
        )
        
        for num_mod, df_s in [("M3", df_stats_m3), ("M4", df_stats_m4)]:
            df_stats_compare = pd.merge(
                df_stats_compare,
                df_s[['Variable', 'Nb_Reponses_Fournies', 'Nb_Bonnes_Reponses', '%_Bonnes_Reponses_Num']].rename(
                    columns={'Nb_Reponses_Fournies': f'Nb_Reponses_Fournies_{num_mod}', 'Nb_Bonnes_Reponses': f'Nb_Bonnes_Reponses_{num_mod}', '%_Bonnes_Reponses_Num': f'%_Bonnes_Reponses_Num_{num_mod}'}
                ),
                on='Variable', how='left'
            )

        df_stats_compare = df_stats_compare[df_stats_compare['Nb_Reponses_Fournies_M1'] >= seuil_volume]
        
        # Calcul des trois duels demandés (toujours centrés sur le gain apporté par M4)
        df_stats_compare['Évolution M4 vs M1 (pts)'] = df_stats_compare['%_Bonnes_Reponses_Num_M4'] - df_stats_compare['%_Bonnes_Reponses_Num_M1']
        df_stats_compare['Évolution M4 vs M2 (pts)'] = df_stats_compare['%_Bonnes_Reponses_Num_M4'] - df_stats_compare['%_Bonnes_Reponses_Num_M2']
        df_stats_compare['Évolution M4 vs M3 (pts)'] = df_stats_compare['%_Bonnes_Reponses_Num_M4'] - df_stats_compare['%_Bonnes_Reponses_Num_M3']
        
        if df_stats_compare.empty:
            st.warning("Filtre de volume trop élevé : aucune variable n'a assez de réponses pour être comparée.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            mean_m4 = df_stats_compare['%_Bonnes_Reponses_Num_M4'].mean()
            
            col1.metric("Moyenne M4 (Hybride)", f"{mean_m4:.1f} %")
            col2.metric("M4 vs M1 (Complet)", f"{df_stats_compare['%_Bonnes_Reponses_Num_M1'].mean():.1f} %", delta=f"{df_stats_compare['Évolution M4 vs M1 (pts)'].mean():+.1f} pts (M4 vs M1)")
            col3.metric("M4 vs M2 (Découpé)", f"{df_stats_compare['%_Bonnes_Reponses_Num_M2'].mean():.1f} %", delta=f"{df_stats_compare['Évolution M4 vs M2 (pts)'].mean():+.1f} pts (M4 vs M2)")
            col4.metric("M4 vs M3 (Méthode 3)", f"{df_stats_compare['%_Bonnes_Reponses_Num_M3'].mean():.1f} %", delta=f"{df_stats_compare['Évolution M4 vs M3 (pts)'].mean():+.1f} pts (M4 vs M3)")
            
            st.divider()
            st.subheader("🗂️ Comparaison Macro par Bloc Juridique (Section)")
            
            # Agrégation et division de chaque modèle par son propre dénominateur
            df_sections_comp = df_stats_compare[df_stats_compare['Section_Code'] != 'Autre'].groupby('Section_Nom').agg(
                Total_Bonnes_M1=('Nb_Bonnes_Reponses_M1', 'sum'),
                Total_Reponses_M1=('Nb_Reponses_Fournies_M1', 'sum'),
                Total_Bonnes_M2=('Nb_Bonnes_Reponses_M2', 'sum'),
                Total_Reponses_M2=('Nb_Reponses_Fournies_M2', 'sum'),
                Total_Bonnes_M3=('Nb_Bonnes_Reponses_M3', 'sum'),
                Total_Reponses_M3=('Nb_Reponses_Fournies_M3', 'sum'),
                Total_Bonnes_M4=('Nb_Bonnes_Reponses_M4', 'sum'),
                Total_Reponses_M4=('Nb_Reponses_Fournies_M4', 'sum')
            ).reset_index()
            
            df_sections_comp['M1 (Complet)'] = (df_sections_comp['Total_Bonnes_M1'] / df_sections_comp['Total_Reponses_M1']) * 100
            df_sections_comp['M2 (Par Partie)'] = (df_sections_comp['Total_Bonnes_M2'] / df_sections_comp['Total_Reponses_M2']) * 100
            df_sections_comp['M3 (Méthode 3)'] = (df_sections_comp['Total_Bonnes_M3'] / df_sections_comp['Total_Reponses_M3']) * 100
            df_sections_comp['M4 (Hybride M2+M3)'] = (df_sections_comp['Total_Bonnes_M4'] / df_sections_comp['Total_Reponses_M4']) * 100
            
            df_sections_comp = df_sections_comp.sort_values(by='M4 (Hybride M2+M3)', ascending=True)

            mode_visu_section = st.radio(
                "Choisir le format d'affichage :", 
                ["📊 Graphique Maxi-Barres (Vue globale comparative)", "🗂️ Blocs Détachés (Cartes individuelles par section)"],
                horizontal=True
            )
            
            if "Graphique" in mode_visu_section:
                df_sections_melted = df_sections_comp.melt(
                    id_vars='Section_Nom', 
                    value_vars=['M1 (Complet)', 'M2 (Par Partie)', 'M3 (Méthode 3)', 'M4 (Hybride M2+M3)'], 
                    var_name='Modèle', value_name='Précision (%)'
                )
                
                fig_sec_comp = px.bar(
                    df_sections_melted, x='Précision (%)', y='Section_Nom', color='Modèle', orientation='h', barmode='group',
                    text=df_sections_melted['Précision (%)'].apply(lambda x: f"{x:.1f}%"),
                    color_discrete_map={"M1 (Complet)": "#1f77b4", "M2 (Par Partie)": "#ff7f0e", "M3 (Méthode 3)": "#2ca02c", "M4 (Hybride M2+M3)": "#9467bd"}
                )
                
                fig_sec_comp.update_layout(
                    height=900,         
                    bargap=0.15,        
                    bargroupgap=0.03,   
                    xaxis=dict(range=[0, 108], title="Précision Moyenne (%)", tickfont=dict(size=12)),
                    yaxis=dict(title="", tickfont=dict(size=13, weight="bold")),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=13)),
                    margin=dict(l=10, r=20, t=50, b=20)
                )
                fig_sec_comp.update_traces(textposition='outside', textfont=dict(size=12, weight="bold"), cliponaxis=False)
                st.plotly_chart(fig_sec_comp, width="stretch")
                
            else:
                df_sections_rev = df_sections_comp.sort_values(by='M4 (Hybride M2+M3)', ascending=False)
                for _, r_sec in df_sections_rev.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### 📑 {r_sec['Section_Nom']}")
                        c_m4, c_m1, c_m2, c_m3 = st.columns(4)
                        
                        val_m1 = r_sec['M1 (Complet)']
                        val_m2 = r_sec['M2 (Par Partie)']
                        val_m3 = r_sec['M3 (Méthode 3)']
                        val_m4 = r_sec['M4 (Hybride M2+M3)']
                        
                        c_m4.metric("🌟 Moyenne M4", f"{val_m4:.1f} %")
                        c_m1.metric("M1 (Complet)", f"{val_m1:.1f} %", delta=f"{val_m4 - val_m1:+.1f} pts (M4 vs M1)")
                        c_m2.metric("M2 (Par Partie)", f"{val_m2:.1f} %", delta=f"{val_m4 - val_m2:+.1f} pts (M4 vs M2)")
                        c_m3.metric("M3 (Méthode 3)", f"{val_m3:.1f} %", delta=f"{val_m4 - val_m3:+.1f} pts (M4 vs M3)")
            
            st.divider()
            st.subheader("📋 Tableau des Évolutions par Variable (Deltas Centrés sur M4)")
            
            df_display_comp = df_stats_compare[[
                'Section_Nom', 'Variable', 'Libellé', 'Nb_Reponses_Fournies_M1',
                '%_Bonnes_Reponses_Num_M1', '%_Bonnes_Reponses_Num_M2', '%_Bonnes_Reponses_Num_M3', '%_Bonnes_Reponses_Num_M4',
                'Évolution M4 vs M1 (pts)', 'Évolution M4 vs M2 (pts)', 'Évolution M4 vs M3 (pts)'
            ]].rename(columns={
                'Section_Nom': 'Section', 
                'Nb_Reponses_Fournies_M1': 'Vol. Rép.',
                '%_Bonnes_Reponses_Num_M1': 'M1 (%)', 
                '%_Bonnes_Reponses_Num_M2': 'M2 (%)', 
                '%_Bonnes_Reponses_Num_M3': 'M3 (%)',
                '%_Bonnes_Reponses_Num_M4': 'M4 (%)',
                'Évolution M4 vs M1 (pts)': 'Δ M4 vs M1',
                'Évolution M4 vs M2 (pts)': 'Δ M4 vs M2',
                'Évolution M4 vs M3 (pts)': 'Δ M4 vs M3'
            })
            
            def style_delta(val):
                return f'color: {"#d62728" if val < 0 else "#2ca02c" if val > 0 else "gray"}; font-weight: bold;'
            
            styled_df_comp = df_display_comp.style.map(style_delta, subset=['Δ M4 vs M1', 'Δ M4 vs M2', 'Δ M4 vs M3']).format({
                'M1 (%)': "{:.1f}", 'M2 (%)': "{:.1f}", 'M3 (%)': "{:.1f}", 'M4 (%)': "{:.1f}",
                'Δ M4 vs M1': "{:+.1f}", 'Δ M4 vs M2': "{:+.1f}", 'Δ M4 vs M3': "{:+.1f}"
            })
            
            st.dataframe(styled_df_comp, width="stretch", height=600, hide_index=True)

# ==================================================
# ONGLET 7 : ANALYSE DES JUSTIFICATIONS (M3)
# ==================================================
elif choix_page == MENU_JUSTIF:
    st.title("🔎 Analyse des Justifications (M3)")
    st.markdown("Cet onglet permet de confronter la réponse humaine, la prédiction de la Méthode 3 (M3) et le **raisonnement textuel généré par le modèle** pour expliquer sa réponse.")
    
    if not os.path.exists(CHEMIN_JUSTIF):
        st.warning(f"Le fichier des justifications est introuvable à l'emplacement : `{CHEMIN_JUSTIF}`")
    elif df_rep_m3.empty:
        st.warning("Les données du Modèle 3 (Méthode 3) ne sont pas chargées, impossible de faire la comparaison.")
    else:
        try:
            df_justif = pd.read_json(CHEMIN_JUSTIF)
            df_justif.columns = [str(c).lower().strip() for c in df_justif.columns]
            
            # Alignement des index
            col_id_j = 'no_rg' if 'no_rg' in df_justif.columns else df_justif.columns[0]
            df_justif['id_clean'] = df_justif[col_id_j].apply(nettoyer_id_global)
            df_justif = df_justif[df_justif['id_clean'] != "inconnu"].drop_duplicates(subset=['id_clean'])
            df_justif.set_index('id_clean', inplace=True)
            
            # --- FILTRES AVANCÉS ---
            st.subheader("🔍 Filtres de recherche")
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                list_sections_j = ["Toutes les sections"] + sorted(list(df_stats_m3['Section_Nom'].unique()))
                sel_section_j = st.selectbox("🗂️ Filtrer par section :", list_sections_j, key="justif_section")
                
                # Option de tri des variables
                tri_variables = st.selectbox(
                    "↕️ Trier les variables par :", 
                    ["Plus d'erreurs en premier", "Moins d'erreurs en premier", "Alphabétique"]
                )
            
            with col_f2:
                # 1. On filtre les stats selon la section choisie
                if sel_section_j != "Toutes les sections":
                    df_stats_f = df_stats_m3[df_stats_m3['Section_Nom'] == sel_section_j]
                else:
                    df_stats_f = df_stats_m3.copy()
                    
                # 2. On garde uniquement les variables présentes dans la correction
                df_stats_f = df_stats_f[df_stats_f['Variable'].isin(df_cor.columns)]
                
                # 3. On applique le tri sur le DataFrame des stats
                if tri_variables == "Plus d'erreurs en premier":
                    df_stats_f = df_stats_f.sort_values(by='Nb_Mauvaises_Reponses', ascending=False)
                elif tri_variables == "Moins d'erreurs en premier":
                    df_stats_f = df_stats_f.sort_values(by='Nb_Mauvaises_Reponses', ascending=True)
                else:
                    df_stats_f = df_stats_f.sort_values(by='Variable', ascending=True)
                    
                # 4. On crée les options avec le nombre d'erreurs visible !
                options_vars = []
                for _, r in df_stats_f.iterrows():
                    # --- On adapte le texte au mode (Global ou Strict) ---
                    if "mode_calcul" in locals() and mode_calcul == "🎯 Strict (Humain ET LLM ont répondu)" and 'Nb_Repondu_Par_Les_Deux' in r:
                        # En mode strict, les erreurs sont les questions répondues par les deux MOINS les bonnes réponses communes
                        nb_err = int(r['Nb_Repondu_Par_Les_Deux']) - int(r['Nb_Bonnes_Reponses_Communes'])
                    else:
                        # En mode global, on prend la colonne classique
                        nb_err = int(r['Nb_Mauvaises_Reponses']) if pd.notna(r['Nb_Mauvaises_Reponses']) else 0
                        
                    options_vars.append(f"{r['Variable']} ({nb_err} erreurs)")
                
                var_sel_brut = st.selectbox("1️⃣ Choisir une variable à analyser :", options_vars)
                
                # 5. On extrait le vrai nom de la variable (on enlève " (XX erreurs)")
                var_sel = var_sel_brut.split(' (')[0] if var_sel_brut else None
                
            with col_f3:
                tri_dossier = st.selectbox("↕️ Trier par n° de dossier :", ["Croissant", "Décroissant"])
                st.write("") 
                filtre_erreurs = st.checkbox("⚠️ Afficher uniquement les dossiers avec une erreur (Humain ≠ M3)", value=True)
                
            if var_sel:
                # Affichage de la modalité
                row_stats = df_stats_m3[df_stats_m3['Variable'] == var_sel].iloc[0]
                with st.expander(f"📖 Modalités et instructions pour la question : {var_sel}", expanded=True):
                    st.code(charger_dictionnaire_variable(var_sel, row_stats['Section_Code']), language="text")

                # Création du DataFrame de fusion
                df_compare = pd.DataFrame(index=df_cor.index)
                
                col_dossier_nom = 'no_rg' if 'no_rg' in df_rep_m3.columns else df_rep_m3.columns[0]
                df_compare['Dossier'] = extraire_colonne_securisee(df_rep_m3, col_dossier_nom, df_cor.index)
                
                df_compare['Humain'] = extraire_colonne_securisee(df_cor, var_sel, df_cor.index)
                df_compare['M3 (Réponse)'] = extraire_colonne_securisee(df_rep_m3, var_sel, df_cor.index)
                
                # Chercher la justification dans le JSON
                if var_sel in df_justif.columns:
                    df_compare['Justification M3'] = df_justif[var_sel].reindex(df_cor.index).fillna("Non trouvée dans le fichier")
                else:
                    df_compare['Justification M3'] = "La variable n'est pas documentée dans le fichier de justifications."
                    
                # --- Application du filtre Strict global ---
                if "mode_calcul" in locals() and mode_calcul == "🎯 Strict (Humain ET LLM ont répondu)":
                    df_compare = df_compare[
                        (df_compare['Humain'] != "nan") & 
                        (df_compare['M3 (Réponse)'] != "nan")
                    ]
                    st.info("Filtre Strict actif : Les dossiers où l'humain ou M3 n'ont pas répondu (nan) sont masqués.")
                    
                # Application du filtre des erreurs
                if filtre_erreurs:
                    df_compare = df_compare[df_compare['Humain'] != df_compare['M3 (Réponse)']]
                    
                # Application du tri
                df_compare = df_compare.sort_values(by='Dossier', ascending=(tri_dossier == "Croissant"))
                    
                st.markdown(f"**{len(df_compare)} dossiers affichés.**")
                
                # --- AFFICHAGE AVEC RETOUR À LA LIGNE AUTO ---
                df_affichage = df_compare.set_index('Dossier')
                st.table(df_affichage)
                
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier de justifications : {e}")

# ==================================================
# ONGLET 8 : CENTRE DE DIAGNOSTIC (DEBUG)
# ==================================================
elif choix_page == MENU_DEBUG:
    st.title("🛠️ Centre de Diagnostic & Debugging")
    st.markdown("Ce panneau analyse la structure brute de tes données **avant** tout alignement automatique pour détecter les anomalies de ton pipeline.")
    
    st.info("ℹ️ **Note sur le Modèle 4 (Hybride) :** M4 est généré dynamiquement à la volée en mémoire en combinant M3 (base de défaut), M2 (pour un sous-ensemble spécifique de variables) et en appliquant un redressement à 100 % pour les 7 variables dont la correction humaine initiale était erronée. Il ne nécessite aucun fichier JSON physique supplémentaire sur le disque.")
    
    diag = get_debug_diagnostics(
        CHEMIN_EXCEL_CORRIGE, CHEMIN_GENERE_M1, CHEMIN_GENERE_M2, CHEMIN_GENERE_M3, 
        CHEMIN_STATS_M1, CHEMIN_STATS_M2, CHEMIN_STATS_M3
    )
    
    st.subheader("1. Audit de l'alignement des Dossiers (ID & Doublons)")
    st.write("Résout les écarts de type *« Pourquoi ai-je 110 réponses pour 99 documents ? »*.")
    
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.metric("Doublons Excel Humain", len(diag["doublons_humain"]), help="Nombre de lignes qui ont un numéro RG/ID en double dans l'Excel.")
        if diag["doublons_humain"]: st.error(f"**IDs :** {', '.join(map(str, set(diag['doublons_humain'])))}")
        else: st.success("Aucun doublon d'ID.")
            
    with col_d2:
        st.metric("Doublons LLM M1", len(diag["doublons_m1"]))
        if diag["doublons_m1"]: st.error(f"**IDs :** {', '.join(map(str, set(diag['doublons_m1'])))}")
        else: st.success("Aucun doublon d'ID.")

    with col_d3:
        st.metric("Doublons LLM M2", len(diag["doublons_m2"]))
        if diag["doublons_m2"]: st.error(f"**IDs :** {', '.join(map(str, set(diag['doublons_m2'])))}")
        else: st.success("Aucun doublon d'ID.")

    with col_d4:
        st.metric("Doublons LLM M3", len(diag["doublons_m3"]))
        if diag["doublons_m3"]: st.error(f"**IDs :** {', '.join(map(str, set(diag['doublons_m3'])))}")
        else: st.success("Aucun doublon d'ID.")
            
    with st.expander("👻 Enquêter sur les Dossiers Fantômes et Manquants", expanded=True):
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.markdown("#### Mode 1 (Texte Complet)")
            st.write(f"**Fantômes (en JSON, hors Excel) :** `{len(diag['fantomes_m1'])}`")
            if diag['fantomes_m1']: st.code("\n".join(map(str, diag['fantomes_m1'])))
            st.write(f"**Ratés (en Excel, hors JSON) :** `{len(diag['manquants_m1'])}`")
            if diag['manquants_m1']: st.code("\n".join(map(str, diag['manquants_m1'])))
                
        with c_m2:
            st.markdown("#### Mode 2 (Texte Découpé)")
            st.write(f"**Fantômes :** `{len(diag['fantomes_m2'])}`")
            if diag['fantomes_m2']: st.code("\n".join(map(str, diag['fantomes_m2'])))
            st.write(f"**Ratés :** `{len(diag['manquants_m2'])}`")
            if diag['manquants_m2']: st.code("\n".join(map(str, diag['manquants_m2'])))

        with c_m3:
            st.markdown("#### Mode 3 (Méthode 3)")
            st.write(f"**Fantômes :** `{len(diag['fantomes_m3'])}`")
            if diag['fantomes_m3']: st.code("\n".join(map(str, diag['fantomes_m3'])))
            st.write(f"**Ratés :** `{len(diag['manquants_m3'])}`")
            if diag['manquants_m3']: st.code("\n".join(map(str, diag['manquants_m3'])))

    st.divider()

    st.subheader("2. Audit du Schéma et des Colonnes")
    st.write("Vérifie si le LLM respecte rigoureusement la typologie des colonnes de l'Excel.")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(f"**📉 Variables dans l'Excel ignorées par le LLM M1 (`{len(diag['cols_manquantes_m1'])}`)**")
        if diag['cols_manquantes_m1']:
            st.dataframe(pd.DataFrame({"Colonnes Manquantes": diag['cols_manquantes_m1']}), height=200, hide_index=True)
        else: st.success("Toutes les colonnes de l'Excel sont présentes en JSON !")
            
    with col_c2:
        st.markdown(f"**📈 Variables inventées par le LLM M1 (absentes de l'Excel) (`{len(diag['cols_inventees_m1'])}`)**")
        if diag['cols_inventees_m1']:
            st.dataframe(pd.DataFrame({"Colonnes Inventées (Hallucination de clé)": diag['cols_inventees_m1']}), height=200, hide_index=True)
        else: st.success("Le LLM n'a inventé aucune clé hors schéma.")

    st.divider()

    st.subheader("3. Alertes sur les Faillites de Prompt (Précision = 0 %)")
    st.write("Les variables listées ci-dessous ont un taux d'erreur de 100 %. Cela indique généralement une **incohérence de typage** (ex: le LLM écrit `'Oui'` alors que l'Excel attend `'1'`) ou une question mal formulée.")
    
    if not df_stats_active.empty:
        df_faillites = df_stats_active[df_stats_active['%_Bonnes_Reponses_Num'] == 0.0]
        if not df_faillites.empty:
            st.dataframe(
                df_faillites[['Section_Nom', 'Variable', 'Libellé', 'Nb_Reponses_Fournies', 'Nb_Mauvaises_Reponses']], 
                width="stretch", hide_index=True
            )
        else:
            st.success("🎉 Excellente nouvelle : Aucune variable n'a une précision de 0 % !")

    st.divider()

    st.subheader("4. Statut des Fichiers Physiques")
    if diag["fichiers_inaccessibles"]:
        st.error(f"⚠️ `{len(diag['fichiers_inaccessibles'])}` fichier(s) source n'ont pas pu être lus par l'application :")
        for f_err in diag["fichiers_inaccessibles"]:
            st.markdown(f"- ❌ `{f_err}`")
    else:
        st.success("✅ Tous les fichiers JSON de résultats, Excel corrigés, et fichiers `.txt` de questions sont accessibles sur le disque.")