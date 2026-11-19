"""
Compilation des fichiers JSON extraits en une base de données consolidée.

Ce script regroupe tous les JSON générés par l'extraction LLM en un seul fichier
global (base de données tabulaire). Il applique des règles métiers de cohérence 
pour annuler les champs dépendants si la condition maître est fausse, et 
nettoie les variables vides.
"""

import os
import json
import logging
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def appliquer_regles_hors_champ(data: dict) -> dict:
    """
    Applique TOUTES les règles métiers de cohérence globale AVANT le nettoyage.
    
    Vérifie les conditions logiques entre les variables de l'ordonnance. 
    Si la condition maître est fausse, les questions dépendantes sont 
    automatiquement mises à None.

    Parameters
    ----------
    data : dict
        Le dictionnaire contenant les paires clé-valeur extraites d'une ordonnance.

    Returns
    -------
    dict
        Le dictionnaire mis à jour avec les règles de cohérence appliquées.
    """
    def nullify(fields):
        for f in fields:
            if f in data:
                data[f] = None

    # ==========================================
    # 1. PROCEDURE
    # ==========================================
    if data.get("RENVOI") != "1":
        nullify(["RENVOI_QUI", "DA_RENVOI_AUDIENCE", "RENVOI_MOTIF_CONTRAD", "RENVOI_MOTIF_DELAI", "RENVOI_MOTIF_PIECES", "RENVOI_MOTIF_AVOCAT", "RENVOI_MOTIF_PARQUET", "RENVOI_MOTIF_INTERP", "RENVOI_MOTIF_AJ", "RENVOI_MOTIF_AUTRE"])
    if data.get("RENVOI_MOTIF_AUTRE") != "1":
        nullify(["RENVOI_MOTIF_AUTRE_DET"])
    if data.get("AUDITION_SEPARE") != "1":
        nullify(["AUDITION_SEPARE_QUI"])

    # ==========================================
    # 2. PROFIL SOCIAL
    # ==========================================
    if data.get("PAYS_NAIS_DEF") != "250":
        nullify(["VILLE_NAIS_DEF"])
    if data.get("PAYS_NAIS_DEF") == "250":
        nullify(["VILLE_NAIS_ETR_DEF"])
        
    statut_jur = data.get("STATUT_JUR_COUPLE")
    if statut_jur not in ("11", "21"):
        nullify(["AN_MARIAGE_COUPLE"])
    if statut_jur not in ("12", "22"):
        nullify(["AN_PACS_COUPLE"])
    if statut_jur not in ("11", "12"):
        nullify(["DIVORCE_ENCOURS_COUPLE"])
        
    enft = data.get("ENFT")
    if enft != "1":
        nullify(["ENFT_NB", "ENFT_MIN", "ENFT_MAJ", "ENFT_MINI_AN_NAIS"])
        
    enft_min = data.get("ENFT_MIN")
    if enft_min != "1":
        nullify(["ENFT_MIN_NB", "ENFT_MESURE_SOCIOEDUC", "ENFT_PROC_JAF"])
        
    if data.get("ENFT_MAJ") != "1":
        nullify(["ENFT_MAJ_NB"])
        
    enft_nb = data.get("ENFT_NB")
    try:
        if enft_nb is None or int(float(enft_nb)) < 2:
            nullify(["ENFT_MAXI_AN_NAIS"])
    except (ValueError, TypeError):
        nullify(["ENFT_MAXI_AN_NAIS"])

    # ==========================================
    # 3. VIOLENCES DÉNONCÉES
    # ==========================================
    if data.get("MENACE_DEM_DENONC") != "1":
        nullify(["MENACE_MORT_DEM_DENONC", "MENACE_ARME_DEM_DENONC"])
    if data.get("PSY_DEM_DENONC") != "1":
        nullify(["PSY_HARCEL_DEM_DENONC", "PSY_CONTROL_DEM_DENONC"])
        
    if enft != "1" or data.get("ENFT_HORS_UNION_DEM") != "1":
        nullify(["PHYS_ENFT_DENONC", "MENACE_ENFT_DENONC", "PSY_ENFT_DENONC", "SEXUEL_ENFT_DENONC", "ENLEVT_ENFT_DENONC"])
        
    if data.get("LOGT_TYPE_DEM") == "1":
        nullify(["VIOLENCE_DEBUT_DENONC"])
        
    if data.get("PREUV_PLAINTE_AVANT") != "1":
        nullify(["PREUV_PLAINTE_AVANT_NB"])

    # ==========================================
    # 4. DEMANDES
    # ==========================================
    if data.get("MOTIV_DEM") != "9":
        nullify(["MOTIV_DEM_DET"])
        
    if enft_min != "1":
        nullify([
            "ENFT_IEC_TOT_DEM", "ENFT_IEC_MEDIA_DEM", "ENFT_MEDIA_DEM", "ENFT_VISIT_DEM", 
            "ENFT_DVH_DEM", "ENFT_PASS_BRAS_DEM", "ENFT_RESERVE_DEM", "ENFT_REVISION_DEM", 
            "ENFT_AUTRE_DEM", "ENFT_AP_CONJ_DEM", "ENFT_AP_DEM_DEM", "ENFT_RESID_DEM_DEM", 
            "ENFT_CEE_DEM", "ENFT_SORTIE_TERR_DEM", "ENFT_EXPERT_PSY_DEM", "ENFT_INVESTIG_DEM"
        ])
        
    if data.get("ENFT_MAJ") != "1":
        nullify(["ENFT_MAJ_IEC_DEM"])
        
    if data.get("ENFT_IEC_TOT_DEM") != "1":
        nullify(["ENFT_IEC_MEDIA_SUBS_DEM"])
        
    if data.get("ENFT_IEC_MEDIA_DEM") != "1" and data.get("ENFT_MEDIA_DEM") != "1":
        nullify(["ENFT_VISIT_SUBS_DEM"])
        
    if data.get("ENFT_VISIT_SUBS_DEM") != "1":
        nullify(["ENFT_AUTRE_DEM_DET"])
        
    if data.get("ENFT_CEE_DEM") != "1":
        nullify(["ENFT_CEE_DEM_MT"])
        
    if data.get("LIEU_INTERDI_DEM") != "1":
        nullify(["LIEU_INTERDI_DOMIC_DEM", "LIEU_INTERDI_ECOLE_DEM", "LIEU_INTERDI_W_DEM"])
        
    if data.get("INTERDI_AUTRE_DEM") != "1":
        nullify(["INTERDI_AUTRE_DEM_DET"])
        
    if data.get("LOGT_AUTRE_DEM") != "1":
        nullify(["LOGT_AUTRE_DEM_DET"])
        
    if data.get("CONTRIB_MRGE_DEM") != "1":
        nullify(["CONTRIB_MRGE_DEM_MT"])

    # ==========================================
    # 5. RÉPONSES SUR VIOLENCES
    # ==========================================
    rep_violence = data.get("REP_VIOLENCE")
    if data.get("PHYS_DEM_DENONC") != "1" or rep_violence != "1": nullify(["PHYS_DEM_REPDEF"])
    if data.get("MENACE_DEM_DENONC") != "1" or rep_violence != "1": nullify(["MENACE_DEM_REPDEF"])
    if data.get("MENACE_MORT_DEM_DENONC") != "1" or rep_violence != "1": nullify(["MENACE_MORT_DEM_REPDEF"])
    if data.get("MENACE_ARME_DEM_DENONC") != "1" or rep_violence != "1": nullify(["MENACE_ARME_DEM_REPDEF"])
    if data.get("PSY_DEM_DENONC") != "1" or rep_violence != "1": nullify(["PSY_DEM_REPDEF"])
    if data.get("PSY_HARCEL_DEM_DENONC") != "1" or rep_violence != "1": nullify(["PSY_HARCEL_DEM_REPDEF"])
    if data.get("PSY_CONTROL_DEM_DENONC") != "1" or rep_violence != "1": nullify(["PSY_CONTROL_DEM_REPDEF"])
    if data.get("SEXUEL_DEM_DENONC") != "1" or rep_violence != "1": nullify(["SEXUEL_DEM_REPDEF"])
    if data.get("ECONOMIC_DEM_DENONC") != "1" or rep_violence != "1": nullify(["ECONOMIC_DEM_REPDEF"])
    if data.get("VOLPAPIER_DEM_DENONC") != "1" or rep_violence != "1": nullify(["VOLPAPIER_DEM_REPDEF"])
    if data.get("INTRUSION_DEM_DENONC") != "1" or rep_violence != "1": nullify(["INTRUSION_DEM_REPDEF"])
    if data.get("DEGRAD_DEM_DENONC") != "1" or rep_violence != "1": nullify(["DEGRAD_DEM_REPDEF"])
    if data.get("PHYS_ENFT_DENONC") != "1" or rep_violence != "1": nullify(["PHYS_ENFT_REPDEF"])
    if data.get("MENACE_ENFT_DENONC") != "1" or rep_violence != "1": nullify(["MENACE_ENFT_REPDEF"])
    if data.get("PSY_ENFT_DENONC") != "1" or rep_violence != "1": nullify(["PSY_ENFT_REPDEF"])
    if data.get("SEXUEL_ENFT_DENONC") != "1" or rep_violence != "1": nullify(["SEXUEL_ENFT_REPDEF"])
    if data.get("ENLEVT_ENFT_DENONC") != "1" or rep_violence != "1": nullify(["ENLEVT_ENFT_REPDEF"])
    if data.get("TEMOIN_ENFT_DENONC") != "1" or rep_violence != "1": nullify(["TEMOIN_ENFT_REPDEF"])
    if data.get("TEMOIN_NOUV_CONJ_DENONC") != "1" or rep_violence != "1": nullify(["TEMOIN_NOUV_CONJ_REPDEF"])
    if data.get("TEMOIN_PROCHE_DENONC") != "1" or rep_violence != "1": nullify(["TEMOIN_PROCHE_REPDEF"])
    if data.get("TEMOIN_AUTRE_DENONC") != "1" or rep_violence != "1": nullify(["TEMOIN_AUTRE_REPDEF"])
    if rep_violence != "1": nullify(["TENSION_OK_DEF", "ILLEGAL_OK_DEF", "MINIM_JUSTIF_DEF", "DIVORCE_OK_DEF"])

    # ==========================================
    # 6. RÉPONSES SUR DEMANDES
    # ==========================================
    rep_demande = data.get("REP_DEMANDE")
    cond_heberg = (
        data.get("ENFT_IEC_TOT_DEM") != "1" and data.get("ENFT_IEC_MEDIA_DEM") != "1" and 
        data.get("ENFT_MEDIA_DEM") != "1" and data.get("ENFT_VISIT_DEM") != "1" and 
        data.get("ENFT_DVH_DEM") != "1" and data.get("ENFT_PASS_BRAS_DEM") != "1" and 
        data.get("ENFT_RESERVE_DEM") != "1" and data.get("ENFT_REVISION_DEM") != "1" and 
        data.get("ENFT_AUTRE_DEM") != "1"
    )
    if cond_heberg or rep_demande != "1":
        nullify(["ENFT_HEBERG_POS"])
        
    if data.get("ENFT_PASS_BRAS_DEM") != "1" or rep_demande != "1": nullify(["ENFT_PASS_BRAS_DEF"])
    if (data.get("ENFT_AP_CONJ_DEM") != "1" and data.get("ENFT_AP_DEM_DEM") != "1") or rep_demande != "1": nullify(["ENFT_AP_POS"])
    if data.get("ENFT_RESID_DEM_DEM") != "1" or rep_demande != "1": nullify(["ENFT_RESID_DEM_POS"])
    if data.get("ENFT_RESID_DEM_POS") != "0" and data.get("ENFT_RESID_DEM_DEM") != "0": nullify(["ENFT_RESID_DEM_DEF"])
    if data.get("ENFT_CEE_DEM") != "1" or rep_demande != "1": nullify(["ENFT_CEE_DEF_MT"])
    if data.get("RESID_SEPARE_DEM") != "1" or rep_demande != "1": nullify(["RESID_SEPARE_POS"])
    if (data.get("LOGT_USAGE_DEM") != "1" and data.get("LOGT_BAIL_DEM") != "1") or rep_demande != "1": nullify(["LOGT_POS"])
    if data.get("LOGT_PEC_FRAIS_DEM") == "0" or rep_demande != "1": nullify(["LOGT_PEC_FRAIS_POS"])
    if data.get("PEC_SANITAIRE_DEM") != "1" or rep_demande != "1": nullify(["PEC_SANITAIRE_POS"])
    if data.get("CONTRIB_MRGE_DEM") != "1" or rep_demande != "1": nullify(["CONTRIB_MRGE_POS"])
    if enft_min != "1" or rep_demande != "1": nullify(["ENFT_SORTIE_TERR_DEF", "ENFT_EXPERT_PSY_DEF", "ENFT_INVESTIG_DEF"])
    if data.get("ENFT_HEBERG_POS") != "0": nullify(["ENFT_HEBERG_DEF"])
    if data.get("CONTRIB_MRGE_POS") != "2": nullify(["CONTRIB_MRGE_DEF_MT"])
    if rep_demande != "1": nullify(["ART_700_DEF"])

    # ==========================================
    # 7. VIOLENCES RETENUES JAF
    # ==========================================
    if data.get("PHYS_DEM_DENONC") != "1": nullify(["PHYS_DEM_RETENU"])
    if data.get("MENACE_DEM_DENONC") != "1": nullify(["MENACE_DEM_RETENU"])
    if data.get("MENACE_MORT_DEM_DENONC") != "1": nullify(["MENACE_MORT_DEM_RETENU"])
    if data.get("MENACE_ARME_DEM_DENONC") != "1": nullify(["MENACE_ARME_DEM_RETENU"])
    if data.get("PSY_DEM_DENONC") != "1": nullify(["PSY_DEM_RETENU"])
    if data.get("PSY_HARCEL_DEM_DENONC") != "1": nullify(["PSY_HARCEL_DEM_RETENU"])
    if data.get("PSY_CONTROL_DEM_DENONC") != "1": nullify(["PSY_CONTROL_DEM_RETENU"])
    if data.get("SEXUEL_DEM_DENONC") != "1": nullify(["SEXUEL_DEM_RETENU"])
    if data.get("ECONOMIC_DEM_DENONC") != "1": nullify(["ECONOMIC_DEM_RETENU"])
    if data.get("VOLPAPIER_DEM_DENONC") != "1": nullify(["VOLPAPIER_DEM_RETENU"])
    if data.get("INTRUSION_DEM_DENONC") != "1": nullify(["INTRUSION_DEM_RETENU"])
    if data.get("DEGRAD_DEM_DENONC") != "1": nullify(["DEGRAD_DEM_RETENU"])
    if data.get("PHYS_ENFT_DENONC") != "1": nullify(["PHYS_ENFT_RETENU"])
    if data.get("MENACE_ENFT_DENONC") != "1": nullify(["MENACE_ENFT_RETENU"])
    if data.get("PSY_ENFT_DENONC") != "1": nullify(["PSY_ENFT_RETENU"])
    if data.get("SEXUEL_ENFT_DENONC") != "1": nullify(["SEXUEL_ENFT_RETENU"])
    if data.get("ENLEVT_ENFT_DENONC") != "1": nullify(["ENLEVT_ENFT_RETENU"])
    if data.get("PRES_AUDIENCE_DEM") != "1": nullify(["NERVEUX_DEM_RETENU", "REPONSE_EVASIVE_DEM_RETENU"])
    if data.get("PRES_AUDIENCE_DEF") != "1": nullify(["NERVEUX_DEF_RETENU", "REPONSE_EVASIVE_DEF_RETENU"])
    if data.get("PASSE_VCONJ_CONDA") != "1": nullify(["PASSE_VCONJ_CONDA_NB", "PASSE_VCONJ_PRISON"])
    if data.get("PROCES_ENCOURS") != "1": nullify(["PROCES_ENCOURS_LIEN_OP", "PROCES_ENCOURS_PREVENTIVE"])

    # ==========================================
    # 8. DECISIONS JAF
    # ==========================================
    accord = data.get("ACCORD")
    if accord != "1": nullify(["OP_DUREE"])
    if data.get("ENFT_CEE_DEC") != "1": nullify(["ENFT_CEE_VIA_DEC", "ENFT_CEE_DEC_MT"])
    if data.get("CONTRIB_MRGE_DEC") != "1": nullify(["CONTRIB_MRGE_DEC_MT"])
    if data.get("ART_700_DEM_DEC") != "1" and data.get("ART_700_DEF_DEC") != "1": nullify(["ART_700_MT"])
    
    if data.get("ENFT_IEC_TOT_DEM") != "1" or accord != "1": nullify(["ENFT_IEC_TOT_DEC"])
    
    cond_iec_media_dec = (data.get("ENFT_IEC_MEDIA_DEM") != "1" and (data.get("ENFT_IEC_TOT_DEC") != "0" or data.get("ENFT_IEC_MEDIA_SUBS_DEM") != "1")) or accord != "1"
    if cond_iec_media_dec: nullify(["ENFT_IEC_MEDIA_DEC"])
    
    if (data.get("ENFT_MEDIA_DEM") != "1" and data.get("ENFT_HEBERG_DEF") != "1") or accord != "1": nullify(["ENFT_MEDIA_DEC"])
    
    cond_visit_dec = (data.get("ENFT_VISIT_DEM") != "1" and (data.get("ENFT_IEC_MEDIA_DEC") == "1" or data.get("ENFT_MEDIA_DEC") == "1" or data.get("ENFT_VISIT_SUBS_DEM") != "1") and data.get("ENFT_HEBERG_DEF") != "2") or accord != "1"
    if cond_visit_dec: nullify(["ENFT_VISIT_DEC"])
    
    if (data.get("ENFT_DVH_DEM") != "1" and data.get("ENFT_HEBERG_DEF") != "3") or accord != "1": nullify(["ENFT_DVH_DEC"])
    if (data.get("ENFT_PASS_BRAS_DEM") != "1" and data.get("ENFT_PASS_BRAS_DEF") != "3") or accord != "1": nullify(["ENFT_PASS_BRAS_DEC"])
    
    if data.get("ENFT_RESERVE_DEM") != "1" or accord != "1": nullify(["ENFT_RESERVE_DEC"])
    if data.get("ENFT_REVISION_DEM") != "1" or accord != "1": nullify(["ENFT_REVISION_DEC"])
    if data.get("ENFT_AUTRE_DEM") != "1" or accord != "1": nullify(["ENFT_AUTRE_DEC"])
    if data.get("ENFT_AP_CONJ_DEM") != "1" or accord != "1": nullify(["ENFT_AP_CONJ_DEC"])
    if data.get("ENFT_AP_DEM_DEM") != "1" or accord != "1": nullify(["ENFT_AP_DEM_DEC"])
    if data.get("ENFT_RESID_DEM_DEM") != "1" or accord != "1": nullify(["ENFT_RESID_DEM_DEC"])
    if data.get("ENFT_RESID_DEM_DEC") != "0" and (accord != "1" or data.get("ENFT_RESID_DEM_DEM") != "0"): nullify(["ENFT_RESID_DEC"])
    if data.get("ENFT_CEE_DEM") != "1" or accord != "1": nullify(["ENFT_CEE_DEC"])
    if accord != "1" or enft_min != "1": nullify(["ENFT_SORTIE_TERR_DEC", "ENFT_EXPERT_PSY_DEC", "ENFT_INVESTIG_DEC"])
    if accord != "1" or data.get("ENFT_MAJ_IEC_DEM") != "1": nullify(["ENFT_MAJ_IEC_DEC"])
    if accord != "1" or data.get("DEM_IEC_DEM") != "1": nullify(["ENFT_MAJ_IEC_DEC", "DEM_IEC_DEC"])
    if accord != "1" or data.get("NOUV_CONJ_IEC_DEM") != "1": nullify(["NOUV_CONJ_IEC_DEC"])
    if accord != "1" or data.get("AUTRE_IEC_DEM") != "1": nullify(["AUTRE_IEC_DEC"])
    if accord != "1" or data.get("ARME_INTERDI_DEM") != "1": nullify(["ARME_INTERDI_DEC"])
    if accord != "1" or data.get("LIEU_INTERDI_DEM") != "1": nullify(["LIEU_INTERDI_DEC"])
    
    lieu_interdi_dec = data.get("LIEU_INTERDI_DEC")
    if lieu_interdi_dec != "1" or data.get("LIEU_INTERDI_DOMIC_DEM") != "1": nullify(["LIEU_INTERDI_DOMIC_DEC"])
    if lieu_interdi_dec != "1" or data.get("LIEU_INTERDI_ECOLE_DEM") != "1": nullify(["LIEU_INTERDI_ECOLE_DEC"])
    if lieu_interdi_dec != "1" or data.get("LIEU_INTERDI_W_DEM") != "1": nullify(["LIEU_INTERDI_W_DEC"])
    
    if accord != "1" or data.get("INTERDI_AUTRE_DEM") != "1": nullify(["INTERDI_AUTRE_DEC"])
    if accord != "1" or data.get("RESID_SEPARE_DEM") != "1": nullify(["RESID_SEPARE_DEC"])
    if accord != "1" or data.get("ADR_INSTANCE_DEM") != "1": nullify(["ADR_INSTANCE_DEC"])
    if accord != "1" or data.get("ADR_VIE_DEM") != "1": nullify(["ADR_VIE_DEC"])
    if accord != "1" or data.get("LOGT_USAGE_DEM") != "1": nullify(["LOGT_USAGE_DEC"])
    if accord != "1" or data.get("LOGT_BAIL_DEM") != "1": nullify(["LOGT_BAIL_DEC"])
    if data.get("LOGT_PEC_FRAIS_DEM") == "0" or accord != "1": nullify(["LOGT_PEC_FRAIS_DEC"])
    if accord != "1" or data.get("EXPULS_LOGT_DEM") != "1": nullify(["EXPULS_LOGT_DEC"])
    if accord != "1" or data.get("LOGT_AUTRE_DEM") != "1": nullify(["LOGT_AUTRE_DEC"])
    if accord != "1" or data.get("PEC_SANITAIRE_DEM") != "1": nullify(["PEC_SANITAIRE_DEC"])
    if accord != "1" or data.get("CONTRIB_MRGE_DEM") != "1": nullify(["CONTRIB_MRGE_DEC"])
    if accord != "1" or data.get("ART_700_DEM") != "1": nullify(["ART_700_DEM_DEC"])
    if accord != "1" or data.get("ART_700_DEF") != "1": nullify(["ART_700_DEF_DEC"])
    if data.get("AJ_PROV_DEM") != "1": nullify(["AJ_PROV_DEM_DEC"])
    if data.get("AJ_PROV_DEF") != "1": nullify(["AJ_PROV_DEF_DEC"])

    # ==========================================
    # 9. BRACELET ANTI RAPPROCHEMENT
    # ==========================================
    bar_dem = data.get("BAR_DEM")
    bar_def = data.get("BAR_DEF")
    bar_parquet = data.get("BAR_PARQUET")
    bar_jaf = data.get("BAR_JAF")
    
    if bar_dem != "1": nullify(["BAR_POS"])
    if bar_dem != "1" and bar_def != "1": nullify(["BAR_PARQUET", "BAR_JAF"])
    if bar_parquet != "0": nullify(["BAR_PARQUET_REFUS"])
    if bar_jaf != "0": nullify(["BAR_JAF_REFUS"])
    if bar_jaf != "1": nullify(["BAR_DUREE", "BAR_DISTANCE"])

    # ==========================================
    # 10. CONDITIONS DE DATES
    # ==========================================
    da_saisine = data.get("DA_SAISINE")
    if da_saisine and str(da_saisine)[:10] < "2020-05-27":
        nullify(["DA_FIX_AUDIENCE", "FIX_AUDIENCE_NOTIF"])
        
    da_audience = data.get("DA_AUDIENCE")
    if da_audience and str(da_audience)[:10] < "2019-12-29":
        nullify(["PEC_SANITAIRE_DEM"])
        
    da_dec = data.get("DA_DEC")
    if da_dec and (str(da_dec)[:10] < "2020-05-27" or accord != "0"):
        nullify(["RENVOI_FOND"])
        
    if da_saisine and str(da_saisine)[:10] < "2019-12-29":
        nullify(["BAR_DEM", "BAR_DEF"])

    return data

def nettoyer_valeur(val):
    """
    Nettoie et uniformise une valeur extraite pour faciliter les analyses statistiques.

    Convertit la chaîne de caractères en minuscules et remplace les tirets par 
    des espaces. Retourne la valeur inchangée si elle n'est pas de type chaîne.

    Parameters
    ----------
    val : any
        La valeur à nettoyer.

    Returns
    -------
    any
        La valeur nettoyée si c'est une chaîne de caractères, sinon la valeur d'origine.
    """
    if isinstance(val, str):
        return val.lower().replace("-", " ")
    return val

def est_valeur_manquante(val):
    """
    Vérifie si une valeur extraite doit être considérée comme manquante ou nulle.

    Détecte les valeurs 'None', les structures de données vides (listes, dictionnaires),
    et les chaînes de caractères indiquant une absence d'information 
    (ex: "nan", "none", "?", "-").

    Parameters
    ----------
    val : any
        La valeur à évaluer.

    Returns
    -------
    bool
        True si la valeur est effectivement manquante ou nulle, False sinon.
    """
    if val is None: return True
    if isinstance(val, (list, dict)) and len(val) == 0: return True
    if isinstance(val, str):
        if val.strip().lower() in ["", "na", "n/a", "nan", "null", "none", "aucun", "non renseigné", "?", "-"]:
            return True
    return False

def jsons_vers_base_unique(dossier_entree, dossier_sortie, nom_fichier_sortie):
    """
    Compile tous les fichiers JSON individuels en une base de données consolidée et nettoyée.

    Parcourt le dossier d'entrée, extrait les données utiles (en isolant les 
    justifications le cas échéant), applique les règles métiers de cohérence globale, 
    nettoie les valeurs et supprime les colonnes qui ne contiennent aucune réponse 
    avant de sauvegarder la base de données finale.

    Parameters
    ----------
    dossier_entree : str
        Le chemin du répertoire contenant les fichiers JSON (généralement fusionnés par dossier).
    dossier_sortie : str
        Le répertoire de destination où sauvegarder la base de données consolidée finale.
    nom_fichier_sortie : str
        Le nom du fichier JSON final produit (ex: 'database_finale.json').

    Returns
    -------
    None
    """
    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie_complet = os.path.join(dossier_sortie, nom_fichier_sortie)

    if not os.path.exists(dossier_entree):
        logging.error(f"Le dossier source '{dossier_entree}' n'existe pas.")
        return

    fichiers_json = [f for f in os.listdir(dossier_entree) if f.lower().endswith('.json')]
    if not fichiers_json:
        logging.warning(f"Aucun fichier JSON trouvé dans '{dossier_entree}'.")
        return

    liste_donnees = []
 
    for nom_fichier in fichiers_json:
        chemin_fichier = os.path.join(dossier_entree, nom_fichier)
        try:
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                contenu = json.load(f)
                
                # --- On extrait juste les données, on ignore les justifs ---
                if isinstance(contenu, dict) and "donnees_extraites" in contenu:
                    donnees_pures = contenu["donnees_extraites"]
                    if "no_rg" in contenu:
                        donnees_pures["no_rg"] = contenu["no_rg"]
                    contenu_a_traiter = donnees_pures
                else:
                    contenu_a_traiter = contenu
                
                # --- Application des règles métier et nettoyage ---
                if isinstance(contenu_a_traiter, dict):
                    contenu_a_traiter = appliquer_regles_hors_champ(contenu_a_traiter)
                    contenu_propre = {k.lower(): nettoyer_valeur(v) for k, v in contenu_a_traiter.items()}
                    liste_donnees.append(contenu_propre)
                else:
                    liste_donnees.append(contenu_a_traiter)
                    
        except Exception as e:
            logging.error(f"Erreur lors de la lecture de {nom_fichier} : {e}")

    # --- NETTOYAGE CLASSIQUE : Suppression des variables sans réponse ---
    toutes_les_cles = set()
    for d in liste_donnees:
        if isinstance(d, dict): toutes_les_cles.update(d.keys())

    cles_a_conserver = set()
    for cle in toutes_les_cles:
        if cle == "no_rg":
            cles_a_conserver.add(cle)
            continue
        for d in liste_donnees:
            if isinstance(d, dict) and cle in d and not est_valeur_manquante(d[cle]):
                cles_a_conserver.add(cle)
                break 

    cles_supprimees = toutes_les_cles - cles_a_conserver
    if cles_supprimees:
        logging.info(f"🗑️ {len(cles_supprimees)} variable(s) sans aucune réponse supprimée(s).")

    liste_donnees_nettoyees = []
    for d in liste_donnees:
        if isinstance(d, dict):
            d_propre = {k: v for k, v in d.items() if k in cles_a_conserver}
            liste_donnees_nettoyees.append(d_propre)
        else:
            liste_donnees_nettoyees.append(d)

    # Écriture
    try:
        with open(chemin_sortie_complet, 'w', encoding='utf-8') as f_out:
            json.dump(liste_donnees_nettoyees, f_out, ensure_ascii=False, indent=4)
        logging.info(f"✅ JSON global généré avec succès dans : '{chemin_sortie_complet}' ({len(liste_donnees_nettoyees)} dossiers, {len(cles_a_conserver)} colonnes conservées)")
    except Exception as e:
        logging.error(f"Erreur lors de l'écriture du fichier JSON global : {e}")

if __name__ == "__main__":
    CHEMIN_SCRIPT = Path(__file__).resolve()
    RACINE_PROJET = CHEMIN_SCRIPT.parent.parent if CHEMIN_SCRIPT.parent.name == "scripts" else CHEMIN_SCRIPT.parent

    # Lancer sur le dossier classique
    dossier_source_classique = str(RACINE_PROJET / "data/2_interim/JSON__final")
    dossier_resultats = str(RACINE_PROJET / "data/3_final/resultats_final")
    jsons_vers_base_unique(dossier_source_classique, dossier_resultats, "database_finale.json")

    # Lancer AUSSI sur le dossier avec justifications (produira un fichier parfaitement normal)
    dossier_source_justifs = str(RACINE_PROJET / "data/2_interim/JSON__final_avec_justification")
    if os.path.exists(dossier_source_justifs):
        jsons_vers_base_unique(dossier_source_justifs, dossier_resultats, "database_finale_avec_justification.json")