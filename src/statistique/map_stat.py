"""
Script de génération de cartes choroplèthes pour l'analyse des décisions judiciaires.

Ce module permet de visualiser l'impact régional des cours d'appel sur la probabilité 
d'accord des décisions de justice. Il fusionne les résultats d'un modèle économétrique (Excel) 
avec les contours géographiques des ressorts (GeoJSON) pour produire une carte thématique 
centrée sur la France métropolitaine.
"""

import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import unicodedata
import warnings

# Désactiver les avertissements non critiques liés à la géométrie
warnings.filterwarnings("ignore")

def generer_carte_probabilite(fichier_excel, fichier_geojson, export_carte):
    """
    Génère et sauvegarde une carte géographique illustrant l'impact des cours d'appel 
    sur la probabilité de décision.

    La fonction lit les résultats statistiques, normalise les noms des cours pour 
    effectuer une jointure avec les données géographiques, et trace une carte avec une 
    échelle de couleurs divergente centrée sur zéro (coolwarm).

    Parameters
    ----------
    fichier_excel : str
        Le chemin d'accès au fichier Excel contenant les résultats (indexés par le nom de la variable).
    fichier_geojson : str
        Le chemin d'accès au fichier GeoJSON contenant les contours géographiques des cours d'appel.
    export_carte : str
        Le chemin de destination où l'image de la carte générée sera sauvegardée (ex: .png).

    Returns
    -------
    None
    """
    print("Chargement des résultats Excel...")
    
    # On charge l'Excel (index_col=0 pour que les noms des variables soient l'index)
    df_or = pd.read_excel(fichier_excel, index_col=0)
    
    # Isoler uniquement les lignes concernant les cours d'appel
    df_map_ca = df_or[df_or.index.str.startswith('cour_appel_')].copy()
    
    if df_map_ca.empty:
        print("⚠️ Aucune cour d'appel trouvée dans le fichier Excel.")
        return

    # Fonction pour standardiser les noms et forcer la jointure
    def normaliser_nom(nom):
        """
        Standardise le nom d'une cour d'appel pour garantir le succès de la jointure 
        entre le tableau de données et le fichier géographique.

        Parameters
        ----------
        nom : str
            Le nom brut de la cour d'appel.

        Returns
        -------
        str
            Le nom nettoyé en minuscules, sans accents, sans tirets, sans apostrophes, 
            et sans préfixes inutiles (ex: "cour d appel de"). Retourne une chaîne vide si la valeur est nulle.
        """
        if pd.isna(nom): return ""
        # 1. Minuscules, suppression des tirets et apostrophes
        nom = str(nom).lower().strip().replace('-', ' ').replace("'", " ")
        # 2. Suppression des accents
        nom = ''.join(c for c in unicodedata.normalize('NFD', nom) if unicodedata.category(c) != 'Mn')
        # 3. Nettoyage des préfixes "cour d appel de/d"
        nom = nom.replace("cour d appel de ", "").replace("cour d appel d ", "")
        return nom.strip()

    # Création de la clé de jointure côté résultats
    df_map_ca['nom_cour'] = df_map_ca.index.str.replace('cour_appel_', '')
    df_map_ca['cour_appel_join'] = df_map_ca['nom_cour'].apply(normaliser_nom)
    
    print("Chargement du GeoJSON et jointure...")
    carte_ca = gpd.read_file(fichier_geojson)
    
    # Création de la clé de jointure côté carte
    carte_ca['cour_appel_join'] = carte_ca['cour_appel'].apply(normaliser_nom)
    
    # Jointure
    carte_resultats_ca = carte_ca.merge(df_map_ca, on='cour_appel_join', how='left')
    
    # Colonne que l'on veut tracer sur la carte
    colonne_a_tracer = "Impact probabilité (Points de %)"
    
    # --- ASTUCE VISUELLE : Centrage des couleurs sur 0 ---
    # On cherche la valeur absolue la plus haute (ex: 8.17)
    # pour que l'échelle aille de -8.17 à +8.17, garantissant que le 0 est au milieu (blanc)
    max_val = carte_resultats_ca[colonne_a_tracer].abs().max()
    vmin = -max_val
    vmax = max_val

    # Génération du graphique
    fig1, ax1 = plt.subplots(1, 1, figsize=(12, 10))
    
    # Focus sur la France métropolitaine pour éviter l'effet "dé-zoom" des DOM-TOM
    ax1.set_xlim(-6, 10)
    ax1.set_ylim(41, 52)

    # Création de la carte
    carte_resultats_ca.plot(
        column=colonne_a_tracer, 
        ax=ax1, 
        legend=True, 
        cmap='coolwarm', 
        edgecolor='grey', 
        linewidth=0.8,
        vmin=vmin,
        vmax=vmax,
        missing_kwds={'color': '#f2f2f2', 'label': 'Non significatif / Données absentes'},
        legend_kwds={'label': "Impact sur la probabilité d'accord (Points de %)", 'orientation': "horizontal", 'shrink': 0.6, 'pad': 0.05}
    )
    
    ax1.set_title("Impact régional sur la probabilité de la décision\n(Uniquement cours d'appel statistiquement significatives)", fontsize=16)
    ax1.set_axis_off()
    
    # Sauvegarder la carte
    plt.savefig(export_carte, dpi=300, bbox_inches='tight')
    print(f"✅ Carte générée avec succès : {export_carte}")

# ==============================================================================
# PARAMÈTRES
# ==============================================================================
if __name__ == "__main__":
    
    # Chemins à renseigner selon ton environnement
    FICHIER_RESULTATS_EXCEL = "test/Resultats_Econometrie_Ordonnances_Lieu_Brut.xlsx"
    FICHIER_CONTOURS_GEOJSON = "test/sortie_ca.geojson"
    EXPORT_NOUVELLE_CARTE = "test/Carte_Cours_Appel_Probabilite_Lieu.png"
    
    generer_carte_probabilite(
        fichier_excel=FICHIER_RESULTATS_EXCEL,
        fichier_geojson=FICHIER_CONTOURS_GEOJSON,
        export_carte=EXPORT_NOUVELLE_CARTE
    )