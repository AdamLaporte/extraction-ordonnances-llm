"""
Script d'analyse économétrique brute (naïve) pour évaluer l'impact géographique des cours d'appel.

Ce module charge les réponses des ordonnances, nettoie les noms des tribunaux judiciaires 
pour leur associer la cour d'appel compétente via un fichier de correspondances, 
puis effectue une régression logistique brute sans variables de contrôle ni sélection de 
caractéristiques (Elastic Net), en conservant l'ensemble des cours d'appel dans le modèle.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
import warnings

# Désactiver les avertissements non critiques
warnings.filterwarnings("ignore")

def clean_tj_name(tj_name):
    """
    Nettoie et standardise le nom d'un tribunal judiciaire pour faciliter la correspondance géographique.

    Parameters
    ----------
    tj_name : str
        Le nom brut du tribunal judiciaire.

    Returns
    -------
    str
        Le nom nettoyé en minuscules, sans tirets, et débarrassé des préfixes 
        "tribunal judiciaire d'", "tribunal judiciaire de" ou "tribunal judiciaire du".
    """
    s = str(tj_name).lower().replace('-', ' ')
    s = s.replace("tribunal judiciaire d'", "")
    s = s.replace("tribunal judiciaire de ", "")
    s = s.replace("tribunal judiciaire du ", "le ") # Pour "le puy en velay" et "le mans"
    return s.strip()

def lancer_analyse_brute(fichier_reponses, fichier_competences, export_excel, nom_var_dep):
    """
    Exécute une analyse économétrique brute (naïve) de type régression logistique.

    La fonction fusionne les données de réponses avec la table des compétences territoriales, 
    génère les variables muettes (dummies) pour chaque cour d'appel, ajuste un modèle 
    de régression logistique, calcule les odds ratios et les effets marginaux (en points de pourcentage), 
    et exporte l'intégralité des résultats dans un fichier Excel.

    Parameters
    ----------
    fichier_reponses : str
        Chemin vers le fichier Excel contenant les réponses des ordonnances.
    fichier_competences : str
        Chemin vers le fichier CSV de correspondance des compétences territoriales.
    export_excel : str
        Chemin de destination pour l'exportation des résultats au format Excel.
    nom_var_dep : str
        Le nom de la variable dépendante (à expliquer) dans le jeu de données.

    Returns
    -------
    None
    """
    # ==========================================
    # 1. CHARGEMENT ET NETTOYAGE DES DONNÉES
    # ==========================================
    print("Chargement des données...")
    df = pd.read_excel(fichier_reponses, engine='openpyxl')

    df['l_com_loc'] = df['l_com_loc'].astype(str).str.lower().str.replace('-', ' ')

    try:
        df_mapping_geo = pd.read_csv(fichier_competences, sep=';', encoding='latin-1')
    except FileNotFoundError:
        print(f"⚠️ Fichier {fichier_competences} introuvable.")
        df_mapping_geo = pd.DataFrame(columns=['Tribunal judiciaire compétent', "Cour d'Appel compétente"])

    if not df_mapping_geo.empty:
        df_mapping_geo['ville_propre'] = df_mapping_geo['Tribunal judiciaire compétent'].apply(clean_tj_name)
        mapping_unique = df_mapping_geo[['ville_propre', "Cour d'Appel compétente"]].drop_duplicates()
        
        df = df.merge(mapping_unique, left_on='l_com_loc', right_on='ville_propre', how='left')
        df = df.rename(columns={"Cour d'Appel compétente": "cour_appel"})
    else:
        df['cour_appel'] = "inconnue"

    df['cour_appel'] = df['cour_appel'].fillna("inconnue")

    # Modèle brut : uniquement la variable dépendante et la cour d'appel
    colonnes_a_garder = [nom_var_dep, 'cour_appel']

    df_analyse = df[colonnes_a_garder].copy()
    df_analyse = df_analyse.dropna(subset=[nom_var_dep])

    y = df_analyse[nom_var_dep].astype(float)
    X = df_analyse[['cour_appel']]

    # Dummies pour la cour d'appel
    X = pd.get_dummies(X, drop_first=True).astype(float)

    print(f"Échantillon prêt : {len(df_analyse)} dossiers analysables.")
    
    # ==========================================
    # 2. ANALYSE ÉCONOMÉTRIQUE (SANS ELASTIC NET)
    # ==========================================
    print("Lancement de la régression brute (toutes les cours d'appel sont forcées)...\n")
    X_selected = sm.add_constant(X)

    try:
        logit_model = sm.Logit(y, X_selected)
        resultats = logit_model.fit(disp=False)
        
        odds_ratios = pd.DataFrame({
            "Odds Ratio": np.exp(resultats.params),
            "Variation des chances (%)": (np.exp(resultats.params) - 1) * 100,
            "IC bas (2.5%)": np.exp(resultats.conf_int()[0]),
            "IC haut (97.5%)": np.exp(resultats.conf_int()[1]),
            "p-value": resultats.pvalues
        })
        
        try:
            margeff = resultats.get_margeff(at='overall')
            df_effets = pd.DataFrame({"Impact probabilité (Points de %)": margeff.margeff * 100}, index=resultats.params.index.drop('const'))
            odds_ratios = odds_ratios.join(df_effets)
        except Exception as e:
            print(f"\nNote : Le calcul des effets marginaux n'a pas pu aboutir ({e}).")

        # Mise en forme : on supprime la constante et on trie
        or_finaux = odds_ratios.drop('const').sort_values(by="Odds Ratio", ascending=False).round(4)
        
        # ON NE FILTRE PLUS PAR P-VALUE pour voir toutes les zones géographiques
        
        or_finaux.to_excel(export_excel)
        print(f"✅ Terminé ! Le tableau BRUT a été sauvegardé dans : {export_excel}")
        print("💡 ATTENTION : Ce tableau contient des valeurs non-significatives (regardez la colonne p-value).")

    except np.linalg.LinAlgError:
        print("\nERREUR CRITIQUE : Matrice singulière.")
    except Exception as e:
        print(f"\nUne erreur inattendue est survenue : {e}")

# ==============================================================================
if __name__ == "__main__":
    
    FICHIER_REPONSES_EXCEL = "data/1_raw/opvc_reponses.xlsx"
    FICHIER_COMPETENCES_CSV = "test/competences-territoriales.csv"
    EXPORT_RESULTATS_EXCEL = "test/Resultats_Econometrie_Ordonnances_Lieu_Brut.xlsx"
    NOM_VARIABLE_DEPENDANTE = "accord"
    
    lancer_analyse_brute(
        fichier_reponses=FICHIER_REPONSES_EXCEL,
        fichier_competences=FICHIER_COMPETENCES_CSV,
        export_excel=EXPORT_RESULTATS_EXCEL,
        nom_var_dep=NOM_VARIABLE_DEPENDANTE
    )