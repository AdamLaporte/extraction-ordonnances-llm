import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# ==========================================
#     CONFIGURATION ET CONSTANTES
# ==========================================
st.set_page_config(
    page_title="Analytics OPVC — Contenu M4", 
    page_icon="📊", 
    layout="wide"
)

# Chemins des fichiers sources M2 et M3 nécessaires pour générer M4
CHEMIN_GENERE_M2 = "data/3_final/resultats_final/database_finale_bis.json"
CHEMIN_GENERE_M3 = "data/3_final/resultats_final/database_finale_better_ocr.json"
CHEMIN_LIBELLES = "data/1_raw/nom_des_variables.xlsx"

SECTIONS_MAPPING = {
    "a": "Procédure d'identification", "b": "Profil social", "c": "Violences dénoncées",
    "d": "Demandes", "e": "Réponses sur violences", "f": "Réponses sur demandes",
    "g": "Violences retenues JAF", "h": "Décision JAF", "i": "Bracelet anti-rapprochement"
}

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

# ==========================================
#     FONCTIONS UTILITAIRES DE CHARGEMENT
# ==========================================
@st.cache_data
def charger_metadata():
    """
    Charge les libellés humains des variables et leurs modalités de réponses explicites
    à partir des fichiers de questions (.txt) et du fichier Excel du projet.

    Parameters
    ----------
    Aucun

    Returns
    -------
    tuple
        (dict, dict, dict)
        Le premier élément (mapping_sections) associe chaque variable à son code de section.
        Le deuxième élément (libelles_questions) associe chaque variable à sa question complète.
        Le troisième élément (dict_modalites) associe chaque variable à ses modalités de réponse (codes et libellés).
    """
    mapping_sections = {}
    libelles_questions = {}
    dict_modalites = {}
    
    fichiers_sections = {
        "a": "a_procedure.txt", "b": "b_profil_social.txt", "c": "c_violences_denoncees.txt",
        "d": "d_demandes.txt", "e": "e_reponses_sur_violences.txt", "f": "f_reponses_sur_demandes.txt",
        "g": "g_violences_retenues_jaf.txt", "h": "h_decision_jaf.txt", "i": "i_bracelet_anti_rapprochement.txt"
    }
    
    for code, fichier in fichiers_sections.items():
        chemin = os.path.join("docs_et_archives", "questions", fichier)
        if os.path.exists(chemin):
            with open(chemin, 'r', encoding='utf-8') as f:
                contenu = f.read()
                matches = re.findall(r"^([A-Z0-9_]+)\s*:\s*(.*?)(?=\n[A-Z0-9_]+\s*:|\Z)", contenu, re.MULTILINE | re.DOTALL)
                for var, desc in matches:
                    var_l = var.lower().strip()
                    mapping_sections[var_l] = code
                    
                    lignes = [l.strip() for l in desc.strip().split('\n') if l.strip()]
                    if not lignes:
                        libelles_questions[var_l] = var.upper()
                        continue
                        
                    lib_lignes = []
                    mods = {}
                    
                    for l in lignes:
                        m = re.match(r"^([0-9]+|[A-Za-z]{1,3})\s*[-–:.)]\s*(.+)$", l)
                        if m:
                            code_mod = m.group(1).strip()
                            texte_complet = l.strip()
                            mods[code_mod] = texte_complet
                            mods[code_mod.lower()] = texte_complet
                            mods[code_mod.upper()] = texte_complet
                            if code_mod.isdigit():
                                mods[f"{code_mod}.0"] = texte_complet
                        else:
                            if not mods:
                                lib_lignes.append(l)
                                
                    libelles_questions[var_l] = " ".join(lib_lignes).strip()
                    if not libelles_questions[var_l]:
                        libelles_questions[var_l] = lignes[0]
                        
                    dict_modalites[var_l] = mods
                    
    if os.path.exists(CHEMIN_LIBELLES):
        try:
            df_lib = pd.read_excel(CHEMIN_LIBELLES)
            if len(df_lib.columns) >= 2:
                for _, r in df_lib.iterrows():
                    v = str(r.iloc[0]).lower().strip()
                    l = str(r.iloc[1]).strip()
                    if v != "nan" and l != "nan" and v not in libelles_questions:
                        libelles_questions[v] = l
        except Exception:
            pass
            
    return mapping_sections, libelles_questions, dict_modalites

def normaliser_valeur(val):
    """
    Nettoie les valeurs brutes pour uniformiser les calculs statistiques.

    Cette fonction gère les valeurs nulles ou manquantes et supprime les 
    décimales superflues (comme ".0") pour faciliter l'agrégation.

    Parameters
    ----------
    val : str, int, float ou NaN
        La valeur brute issue de la base de données à traiter.

    Returns
    -------
    str
        La valeur nettoyée ou "Non renseigné / Absent" si la valeur est considérée comme nulle.
    """
    if pd.isna(val): return "Non renseigné / Absent"
    s = str(val).strip()
    if s.lower() in ["nan", "none", "", "<na>", "null", "nat"]:
        return "Non renseigné / Absent"
    if s.endswith(".0"): 
        return s[:-2]
    return s

def enrichir_valeur(val, var_name, dict_modalites):
    """
    Associe le numéro ou le code de la réponse à son libellé explicatif complet.

    Parameters
    ----------
    val : str ou int
        La valeur ou le code brut de la réponse.
    var_name : str
        Le nom de la variable concernée.
    dict_modalites : dict
        Dictionnaire global contenant les mappings code -> libellé pour l'ensemble des variables.

    Returns
    -------
    str
        Le libellé explicite de la modalité, ou la valeur d'origine sous forme de chaîne 
        si aucune correspondance n'est trouvée.
    """
    if val == "Non renseigné / Absent":
        return val
    var_l = str(var_name).lower().strip()
    val_str = str(val).strip()
    if var_l in dict_modalites:
        mods = dict_modalites[var_l]
        if val_str in mods:
            return mods[val_str]
        if val_str.endswith(".0") and val_str[:-2] in mods:
            return mods[val_str[:-2]]
    return val_str

@st.cache_data
def load_and_build_m4(path_m2, path_m3):
    """
    Génère la base de données M4 en mémoire à partir des données de M3 et M2.

    Cette fonction initialise la base avec les prédictions du Modèle 3, 
    puis remplace les données de certaines variables spécifiques par les 
    résultats du Modèle 2 (définies dans VARS_M2_IN_M4). Elle applique également 
    un nettoyage des identifiants et des valeurs.

    Parameters
    ----------
    path_m2 : str
        Chemin vers le fichier source JSON contenant les résultats du Modèle 2.
    path_m3 : str
        Chemin vers le fichier source JSON contenant les résultats du Modèle 3.

    Returns
    -------
    tuple
        (pandas.DataFrame, list)
        Le premier élément est la base de données consolidée et nettoyée du Modèle 4.
        Le second élément est la liste des colonnes de variables à nettoyer.
    """
    if not os.path.exists(path_m3):
        st.error(f"❌ Fichier source introuvable : {path_m3}")
        st.stop()
        
    df_m3 = pd.read_json(path_m3)
    df_m2 = pd.read_json(path_m2) if os.path.exists(path_m2) else pd.DataFrame()
    
    df_m3.columns = [str(c).lower().strip() for c in df_m3.columns]
    if not df_m2.empty:
        df_m2.columns = [str(c).lower().strip() for c in df_m2.columns]
        
    def clean_id(df):
        col_id = 'no_rg' if 'no_rg' in df.columns else df.columns[0]
        df['id_clean'] = df[col_id].astype(str).str.replace(' ', '').str.lower()
        return df.drop_duplicates(subset=['id_clean'], keep='first').set_index('id_clean', drop=False)

    df_m4 = clean_id(df_m3).copy()
    if not df_m2.empty:
        df_m2 = clean_id(df_m2)
        for var in VARS_M2_IN_M4:
            var_l = var.lower().strip()
            if var_l in df_m2.columns:
                df_m4[var_l] = df_m2[var_l].reindex(df_m4.index)
                
    cols_a_nettoyer = [c for c in df_m4.columns if c not in ['id_clean', 'no_rg', 'no_cmpst']]
    for c in cols_a_nettoyer:
        df_m4[c] = df_m4[c].apply(normaliser_valeur)
        
    return df_m4, cols_a_nettoyer

# ==========================================
#     CHARGEMENT ET INITIALISATION
# ==========================================
df_m4, cols_variables = load_and_build_m4(CHEMIN_GENERE_M2, CHEMIN_GENERE_M3)
mapping_sec, libelles_vars, dict_mods = charger_metadata()

# ==========================================
#     NAVIGATION & FILTRES LATÉRAUX
# ==========================================
st.sidebar.title("🧭 Menu Statistique")

st.sidebar.markdown("### 🗂️ Navigation")
page = st.sidebar.radio(
    "Choisir une vue :",
    [
        "📈 Synthèse & Tendances",
        "📊 Statistiques par Question",
        "🔄 Croisement de Variables",
        "📑 Vue d'ensemble par Section",
        "📄 Explorateur de Dossier"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ Options d'affichage")
masquer_non_renseigne = st.sidebar.checkbox("Masquer les « Non renseigné » dans les graphiques", value=False)
masquer_peu_renseigne = st.sidebar.checkbox("Masquer les questions peu renseignées (> 25 réponses requis)", value=False)

# -------------------------------------------------------------------------
# FILTRAGE DYNAMIQUE DES VARIABLES
# -------------------------------------------------------------------------
if masquer_peu_renseigne:
    cols_variables_actives = [
        c for c in cols_variables 
        if (df_m4[c] != "Non renseigné / Absent").sum() > 25
    ]
else:
    cols_variables_actives = cols_variables.copy()

st.title("📊 Analytics du Contenu Juridique — Modèle 4")
st.caption(f"Analyse statistique descriptive portant sur **{len(df_m4)} dossiers** de justice et **{len(cols_variables_actives)} variables affichées** (sur {len(cols_variables)} au total).")

# ==================================================
# ONGLET 1 : SYNTHÈSE & TENDANCES
# ==================================================
if page == "📈 Synthèse & Tendances":
    st.subheader("🌟 Chiffres clés de la base de données")
    
    total_cellules = len(df_m4) * len(cols_variables)
    cellules_remplies = sum((df_m4[c] != "Non renseigné / Absent").sum() for c in cols_variables)
    taux_remplissage = (cellules_remplies / total_cellules) * 100 if total_cellules > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Dossiers (Ordonnances)", len(df_m4))
    c2.metric("Questions actives", f"{len(cols_variables_actives)} / {len(cols_variables)}")
    c3.metric("Taux global de renseignement", f"{taux_remplissage:.1f} %", help="Pourcentage moyen de questions ayant trouvé une réponse explicite dans le texte (sur l'ensemble de la base).")
    
    st.divider()
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("📍 Top 10 — Départements des Demandeurs")
        if 'dept_res_dem' in df_m4.columns:
            df_dept = df_m4['dept_res_dem'].value_counts().reset_index()
            df_dept.columns = ['Département', 'Nombre de dossiers']
            df_dept['Département'] = df_dept['Département'].astype(str)
            if masquer_non_renseigne:
                df_dept = df_dept[df_dept['Département'] != "Non renseigné / Absent"]
            fig_dept = px.bar(
                df_dept.head(10), x='Nombre de dossiers', y='Département', orientation='h',
                color='Nombre de dossiers', color_continuous_scale='Blues',
                text='Nombre de dossiers'
            )
            fig_dept.update_yaxes(type='category')
            fig_dept.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, height=350)
            st.plotly_chart(fig_dept, width="stretch")
        else:
            st.info("Variable `dept_res_dem` non disponible.")

    with col_g2:
        st.subheader("📍 Top 10 — Départements des Défendeurs")
        if 'dept_res_def' in df_m4.columns:
            df_dept_def = df_m4['dept_res_def'].value_counts().reset_index()
            df_dept_def.columns = ['Département', 'Nombre de dossiers']
            df_dept_def['Département'] = df_dept_def['Département'].astype(str)
            if masquer_non_renseigne:
                df_dept_def = df_dept_def[df_dept_def['Département'] != "Non renseigné / Absent"]
            fig_dept_def = px.bar(
                df_dept_def.head(10), x='Nombre de dossiers', y='Département', orientation='h',
                color='Nombre de dossiers', color_continuous_scale='Purples',
                text='Nombre de dossiers'
            )
            fig_dept_def.update_yaxes(type='category')
            fig_dept_def.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, height=350)
            st.plotly_chart(fig_dept_def, width="stretch")
        else:
            st.info("Variable `dept_res_def` non disponible.")

    st.divider()
    st.subheader("⚖️ Proportions clés sur la procédure")
    
    cols_prop = [c for c in ['mp_presence', 'divorce_ok_def', 'violence_repete_retenu', 'aj_dem_ok'] if c in cols_variables_actives]
    if cols_prop:
        grid_cols = st.columns(len(cols_prop))
        for idx, col_name in enumerate(cols_prop):
            with grid_cols[idx]:
                lib = libelles_vars.get(col_name, col_name)
                st.markdown(f"**{col_name.upper()} : {lib}**")
                
                serie_enrichie = df_m4[col_name].apply(lambda x: enrichir_valeur(x, col_name, dict_mods))
                counts = serie_enrichie.value_counts()
                
                if masquer_non_renseigne and "Non renseigné / Absent" in counts:
                    counts = counts.drop("Non renseigné / Absent")
                fig_pie = px.pie(values=counts.values, names=counts.index, hole=0.4)
                fig_pie.update_layout(margin=dict(t=10, b=20, l=10, r=10), height=240, showlegend=True)
                st.plotly_chart(fig_pie, width="stretch")
    else:
        st.info("ℹ️ Les proportions clés sont masquées par les filtres actifs (moins de 25 réponses valides).")

# ==================================================
# ONGLET 2 : STATISTIQUES PAR QUESTION (QCM)
# ==================================================
elif page == "📊 Statistiques par Question":
    st.subheader("🔍 Analyse détaillée par variable (Questionnaire)")
    st.markdown("Sélectionnez une question pour afficher la **répartition enrichie des réponses**, le **pourcentage exact** et la **distribution graphique**.")
    
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        sections_dispos = ["Toutes les sections"] + [SECTIONS_MAPPING[k] for k in sorted(SECTIONS_MAPPING.keys())]
        choix_sec = st.selectbox("🗂️ Filtrer par section :", sections_dispos)
        
    vars_filtrees = cols_variables_actives
    if choix_sec != "Toutes les sections":
        code_sec_cible = [k for k, v in SECTIONS_MAPPING.items() if v == choix_sec][0]
        vars_filtrees = [v for v in cols_variables_actives if mapping_sec.get(v) == code_sec_cible]
        
    with col_f2:
        def format_var_option(v):
            lib = libelles_vars.get(v, "Pas de libellé disponible")
            return f"{v.upper()} : {lib}"
            
        var_selected = st.selectbox("📌 Choisir la question à analyser :", sorted(vars_filtrees), format_func=format_var_option)
        
    st.divider()
    
    if var_selected:
        libelle_complet = libelles_vars.get(var_selected, "Libellé non défini.")
        sec_code = mapping_sec.get(var_selected, "autre")
        sec_nom = SECTIONS_MAPPING.get(sec_code, "Autre / Général")
        
        st.markdown(f"#### 📑 `{var_selected.upper()} : {libelle_complet}`")
        st.info(f"**Section juridique :** {sec_nom}")
        
        serie_valeurs = df_m4[var_selected].apply(lambda x: enrichir_valeur(x, var_selected, dict_mods))
        
        if masquer_non_renseigne:
            serie_valeurs = serie_valeurs[serie_valeurs != "Non renseigné / Absent"]
            
        df_stats_qcm = serie_valeurs.value_counts().reset_index()
        df_stats_qcm.columns = ['Modalité de réponse (Numéro et Libellé)', 'Nombre de dossiers']
        
        df_stats_qcm['Modalité de réponse (Numéro et Libellé)'] = df_stats_qcm['Modalité de réponse (Numéro et Libellé)'].astype(str)
        
        total_rep = df_stats_qcm['Nombre de dossiers'].sum()
        df_stats_qcm['Pourcentage (%)'] = (df_stats_qcm['Nombre de dossiers'] / total_rep * 100).round(2) if total_rep > 0 else 0
        
        df_stats_qcm['Texte_Affichage'] = [f"{p:.1f}%" for p in df_stats_qcm['Pourcentage (%)']]
        
        col_tab, col_chart = st.columns([1, 1])
        
        with col_tab:
            st.markdown("##### 📋 Tableau de distribution")
            st.dataframe(
                df_stats_qcm[['Modalité de réponse (Numéro et Libellé)', 'Nombre de dossiers', 'Pourcentage (%)']]\
                .style.background_gradient(subset=['Pourcentage (%)'], cmap='Blues')\
                .format({'Pourcentage (%)': "{:.2f} %"}),
                width="stretch", hide_index=True, height=350
            )
            st.caption(f"**Total pris en compte :** {total_rep} dossier(s).")
            
        with col_chart:
            st.markdown("##### 📊 Visualisation graphique")
            if len(df_stats_qcm) <= 6:
                fig_qcm = px.pie(
                    df_stats_qcm, values='Nombre de dossiers', names='Modalité de réponse (Numéro et Libellé)',
                    hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel
                )
            else:
                df_bar = df_stats_qcm.head(15).copy()
                
                fig_qcm = px.bar(
                    df_bar, x='Nombre de dossiers', y='Modalité de réponse (Numéro et Libellé)', orientation='h',
                    color='Nombre de dossiers', color_continuous_scale='Teal',
                    text='Texte_Affichage'
                )
                fig_qcm.update_yaxes(type='category')
                fig_qcm.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
                
            fig_qcm.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400)
            st.plotly_chart(fig_qcm, width="stretch")
            
        with st.expander("🔎 Voir les dossiers associés à une modalité spécifique", expanded=False):
            mod_choisie = st.selectbox("Sélectionner une réponse :", df_stats_qcm['Modalité de réponse (Numéro et Libellé)'].tolist())
            col_id = 'no_rg' if 'no_rg' in df_m4.columns else df_m4.index.name
            
            dossiers_associes = df_m4[df_m4[var_selected].apply(lambda x: enrichir_valeur(x, var_selected, dict_mods)).astype(str) == str(mod_choisie)][col_id].tolist()
            st.write(f"**{len(dossiers_associes)} dossier(s)** ont pour réponse *« {mod_choisie} »* :")
            st.code(", ".join(map(str, dossiers_associes)))
    else:
        st.warning("⚠️ Aucune variable ne correspond aux critères actuels.")

# ==================================================
# ONGLET 3 : CROISEMENT DE VARIABLES
# ==================================================
elif page == "🔄 Croisement de Variables":
    st.subheader("🔄 Croisement et corrélation entre deux variables")
    st.markdown("Explorez les relations directes entre deux questions (par exemple : *vérifier la proportion de décisions JAF favorables selon la consommation d'alcool du demandeur*).")
    
    if len(cols_variables_actives) >= 2:
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            var_A = st.selectbox("📌 Variable 1 (Axe principal / Condition) :", sorted(cols_variables_actives), format_func=lambda v: f"{v.upper()} : {libelles_vars.get(v, '—')}", key="var_a")
        with col_sel2:
            idx_b = 1 if len(cols_variables_actives) > 1 else 0
            var_B = st.selectbox("🎯 Variable 2 (À croiser / Résultat) :", sorted(cols_variables_actives), index=idx_b, format_func=lambda v: f"{v.upper()} : {libelles_vars.get(v, '—')}", key="var_b")
            
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            mode_pct = st.radio("Mode de calcul du tableau :", [
                "Pourcentage par ligne (Profil = 100%)", 
                "Pourcentage par colonne (Résultat = 100%)", 
                "Pourcentage global", 
                "Nombre de dossiers (Brut)"
            ], horizontal=False)
        with col_opt2:
            ignorer_vides = st.checkbox("Masquer les dossiers avec « Non renseigné / Absent » pour ces 2 variables", value=True)
            type_graph = st.radio("Type de graphique :", [
                "Barres empilées (100%)", 
                "Barres groupées (Effectifs)", 
                "Camembert (Répartition)"
            ], horizontal=True)

        if var_A and var_B:
            st.divider()
            lib_A = libelles_vars.get(var_A, "—")
            lib_B = libelles_vars.get(var_B, "—")
            st.markdown(f"#### 📊 Croisement : `{var_A.upper()}` ✖️ `{var_B.upper()}`")
            st.caption(f"**Variable 1 (Condition) :** {lib_A}  \n**Variable 2 (Résultat) :** {lib_B}")
            
            ser_A = df_m4[var_A].apply(lambda x: enrichir_valeur(x, var_A, dict_mods)).astype(str)
            ser_B = df_m4[var_B].apply(lambda x: enrichir_valeur(x, var_B, dict_mods)).astype(str)
            
            df_croise_raw = pd.DataFrame({var_A: ser_A, var_B: ser_B})
            
            if ignorer_vides:
                df_croise_raw = df_croise_raw[
                    (df_croise_raw[var_A] != "Non renseigné / Absent") & 
                    (df_croise_raw[var_B] != "Non renseigné / Absent")
                ]
                
            if df_croise_raw.empty:
                st.warning("⚠️ Aucun dossier disponible pour ce croisement avec les filtres actuels.")
            else:
                if mode_pct == "Pourcentage par ligne (Profil = 100%)":
                    tab = pd.crosstab(df_croise_raw[var_A], df_croise_raw[var_B], normalize='index') * 100
                    fmt_str = "{:.1f} %"
                    cmap = "Blues"
                elif mode_pct == "Pourcentage par colonne (Résultat = 100%)":
                    tab = pd.crosstab(df_croise_raw[var_A], df_croise_raw[var_B], normalize='columns') * 100
                    fmt_str = "{:.1f} %"
                    cmap = "Greens"
                elif mode_pct == "Pourcentage global":
                    tab = pd.crosstab(df_croise_raw[var_A], df_croise_raw[var_B], normalize='all') * 100
                    fmt_str = "{:.1f} %"
                    cmap = "Purples"
                else:
                    tab = pd.crosstab(df_croise_raw[var_A], df_croise_raw[var_B], margins=True, margins_name="Total")
                    fmt_str = "{:.0f}"
                    cmap = "YlOrRd"
                
                # --> SECTION 1 : LE TABLEAU EN HAUT SUR TOUTE LA LARGEUR
                st.markdown("##### 📋 Tableau de contingence")
                st.dataframe(
                    tab.style.background_gradient(cmap=cmap).format(fmt_str),
                    width="stretch"
                )
                st.caption(f"**Total de dossiers analysés pour ce croisement :** {len(df_croise_raw)}")
                
                st.markdown("---")

                # --> SECTION 2 : LE GRAPHIQUE EN DESSOUS SUR TOUTE LA LARGEUR
                st.markdown("##### 📈 Visualisation comparative")
                
                if type_graph == "Barres empilées (100%)":
                    df_plot = pd.crosstab(df_croise_raw[var_A], df_croise_raw[var_B], normalize='index').reset_index()
                    df_plot_melt = df_plot.melt(id_vars=var_A, value_name="Proportion", var_name=var_B)
                    df_plot_melt['Pourcentage (%)'] = (df_plot_melt['Proportion'] * 100).round(1)
                    df_plot_melt['Texte_Affichage'] = df_plot_melt['Pourcentage (%)'].apply(lambda x: f"{x:.1f}%" if x > 4 else "")
                    
                    fig = px.bar(
                        df_plot_melt, x=var_A, y="Pourcentage (%)", color=var_B,
                        text="Texte_Affichage", barmode="stack",
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    fig.update_xaxes(type='category')
                    fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=500, legend=dict(orientation="h", y=-0.25))
                    
                elif type_graph == "Barres groupées (Effectifs)":
                    df_plot = df_croise_raw.groupby([var_A, var_B]).size().reset_index(name="Nombre de dossiers")
                    fig = px.bar(
                        df_plot, x=var_A, y="Nombre de dossiers", color=var_B,
                        text="Nombre de dossiers", barmode="group",
                        color_discrete_sequence=px.colors.qualitative.Vivid
                    )
                    fig.update_xaxes(type='category')
                    fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=500, legend=dict(orientation="h", y=-0.25))
                    
                else: # --> TYPE CAMEMBERT (RÉPARTITION EN SOUS-GRAPHIQUES)
                    df_plot = df_croise_raw.groupby([var_A, var_B]).size().reset_index(name="Nombre de dossiers")
                    fig = px.pie(
                        df_plot, values="Nombre de dossiers", names=var_B, facet_col=var_A,
                        facet_col_wrap=3, hole=0.3,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    # SUPPRESSION DU TEXTE DE LA VARIABLE DANS LES CAMEMBERTS : On ne garde que le pourcentage et on grossit un peu le chiffre
                    fig.update_traces(textposition='inside', textinfo='percent', textfont=dict(size=14))
                    
                    # AGRANDISSEMENT ET NETTOYAGE DES NOMS DES VARIABLES AU-DESSUS DE CHAQUE CAMEMBERT
                    # (On retire le préfixe "variable_A = " pour ne laisser que le nom clair de la modalité, en grosse police)
                    fig.for_each_annotation(lambda a: a.update(
                        text=a.text.split("=")[-1].strip() if "=" in a.text else a.text,
                        font=dict(size=16, color="#1f77b4")
                    ))
                    
                    # Hauteur adaptable selon le nombre de diagrammes créés
                    nb_facets = len(df_croise_raw[var_A].unique())
                    calc_height = 450 if nb_facets <= 3 else (350 * ((nb_facets // 3) + 1))
                    
                    # AGRANDISSEMENT DE LA LÉGENDE
                    fig.update_layout(
                        margin=dict(t=50, b=20, l=10, r=10), 
                        height=calc_height, 
                        legend=dict(
                            orientation="h", 
                            y=-0.15,
                            font=dict(size=14) # Légende plus grande et plus lisible
                        )
                    )
                    
                st.plotly_chart(fig, width="stretch")
    else:
        st.warning("⚠️ Pas assez de variables actives (>25 réponses) pour réaliser un croisement.")

# ==================================================
# ONGLET 4 : VUE D'ENSEMBLE PAR SECTION
# ==================================================
elif page == "📑 Vue d'ensemble par Section":
    st.subheader("📑 Synthèse et complétude par section juridique")
    st.markdown("Ce tableau récapitule pour chaque variable **sa réponse la plus fréquente (enrichie du libellé)** et **son taux de présence** dans les dossiers.")
    
    resume_list = []
    for var in cols_variables_actives:
        serie = df_m4[var]
        serie_valide = serie[serie != "Non renseigné / Absent"]
        
        nb_valide = len(serie_valide)
        pct_renseigne = (nb_valide / len(df_m4) * 100)
        
        if nb_valide > 0:
            mode_val_brute = serie_valide.mode().iloc[0]
            mode_val_enrichie = enrichir_valeur(mode_val_brute, var, dict_mods)
            mode_count = (serie_valide == mode_val_brute).sum()
            pct_mode = (mode_count / nb_valide * 100)
        else:
            mode_val_enrichie = "N/A (100% absent)"
            pct_mode = 0.0
            
        sec_code = mapping_sec.get(var, "autre")
        lib_q = libelles_vars.get(var, "—")
        
        resume_list.append({
            "Section": SECTIONS_MAPPING.get(sec_code, "Autre"),
            "Question (Nom : Libellé)": f"{var.upper()} : {lib_q}",
            "Taux de renseignement": pct_renseigne,
            "Réponse majoritaire (Mode)": str(mode_val_enrichie)[:70],
            "Fréquence du Mode": pct_mode
        })
        
    df_resume = pd.DataFrame(resume_list)
    
    if not df_resume.empty:
        filtre_sec_tab = st.multiselect(
            "Filtrer le tableau par section :", 
            sorted(df_resume['Section'].unique()), 
            default=sorted(df_resume['Section'].unique())
        )
        
        df_resume_affich = df_resume[df_resume['Section'].isin(filtre_sec_tab)]
        
        st.dataframe(
            df_resume_affich.style.background_gradient(subset=['Taux de renseignement'], cmap='Greens', vmin=0, vmax=100)\
            .background_gradient(subset=['Fréquence du Mode'], cmap='Blues', vmin=0, vmax=100)\
            .format({'Taux de renseignement': "{:.1f} %", 'Fréquence du Mode': "{:.1f} %"}),
            width="stretch", hide_index=True, height=600
        )
    else:
        st.warning("⚠️ Aucune variable active à afficher dans cette vue.")

# ==================================================
# ONGLET 5 : EXPLORATEUR DE DOSSIER
# ==================================================
elif page == "📄 Explorateur de Dossier":
    st.subheader("📄 Fiche descriptive complète d'une ordonnance")
    st.markdown("Consultez l'intégralité des réponses extraites par le **Modèle 4** pour un document précis, avec les intitulés clairs.")
    
    col_id_name = 'no_rg' if 'no_rg' in df_m4.columns else df_m4.columns[0]
    liste_dossiers = sorted(df_m4[col_id_name].astype(str).unique())
    
    dossier_sel = st.selectbox("📂 Sélectionner le numéro du dossier (RG) :", liste_dossiers)
    
    if dossier_sel:
        row_dossier = df_m4[df_m4[col_id_name].astype(str) == dossier_sel].iloc[0]
        
        dict_par_section = {sec_nom: [] for sec_nom in SECTIONS_MAPPING.values()}
        dict_par_section["Autre / Général"] = []
        
        for var in cols_variables_actives:
            val_ext = row_dossier[var]
            if masquer_non_renseigne and val_ext == "Non renseigné / Absent":
                continue
            sec_code = mapping_sec.get(var, "autre")
            sec_nom = SECTIONS_MAPPING.get(sec_code, "Autre / Général")
            lib = libelles_vars.get(var, "—")
            
            val_enrichie = enrichir_valeur(val_ext, var, dict_mods)
            
            dict_par_section[sec_nom].append({
                "Question": f"{var.upper()} : {lib}", 
                "Réponse extraite (Code & Libellé)": val_enrichie
            })
            
        for sec_nom, items in dict_par_section.items():
            if items:
                with st.expander(f"📑 {sec_nom} ({len(items)} réponses)", expanded=True):
                    df_sec_dossier = pd.DataFrame(items)
                    
                    def colorier_reponse(val):
                        if val == "Non renseigné / Absent":
                            return "color: #9aa0a6; font-style: italic;"
                        return "font-weight: bold; color: #1a73e8;"
                        
                    st.dataframe(
                        df_sec_dossier.style.map(colorier_reponse, subset=['Réponse extraite (Code & Libellé)']),
                        width="stretch", hide_index=True
                    )