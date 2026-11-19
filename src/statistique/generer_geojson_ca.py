#!/usr/bin/env python3
"""
Génère un GeoJSON des ressorts des cours d'appel par dissolution des
contours départementaux, à partir de la table de correspondance
CA <-> départements (Tableau IV du Code de l'organisation judiciaire).

PRÉREQUIS
---------
1. pip install geopandas shapely --break-system-packages
2. Un fichier de contours départementaux avec un champ de code INSEE
   département (ex. "code" ou "INSEE_DEP"). Sources possibles :
   - IGN ADMIN EXPRESS (data.gouv.fr, "Contours...IGN")
   - API découpage administratif : https://geo.api.gouv.fr/departements?format=geojson&geometry=contour
   - Répertoire GitHub gregoiredavid/france-geojson (departements.geojson)
   Ce fichier doit couvrir la métropole + DROM ; les COM (Nouvelle-Calédonie,
   Polynésie française, Wallis-et-Futuna, Saint-Pierre-et-Miquelon) n'ont
   pas de maille "département" dans Admin Express -> à traiter séparément
   (cf. section COM_ET_TSA plus bas).

USAGE
-----
python3 generer_geojson_ca.py contours_departements.geojson ca_ressort_departements.json sortie_ca.geojson
"""

import sys
import json

def main():
    """
    Point d'entrée principal du script générant les ressorts des cours d'appel.
    
    Cette fonction s'appuie sur GeoPandas pour charger les contours géographiques, 
    détecter automatiquement la colonne correspondant au code du département, 
    et fusionner (dissoudre) les géométries départementales selon la table de 
    correspondance fournie en argument.

    Parameters
    ----------
    Aucun paramètre explicite. Les arguments sont lus depuis la ligne de commande (sys.argv) :
    sys.argv[1] : str
        Chemin vers le fichier GeoJSON des contours départementaux.
    sys.argv[2] : str
        Chemin vers le fichier JSON de mapping (Cours d'appel <-> départements).
    sys.argv[3] : str
        Chemin vers le fichier GeoJSON de destination pour la sauvegarde.

    Returns
    -------
    None
        Le script génère directement le fichier GeoJSON en sortie et affiche 
        le résultat de l'opération dans la console, y compris les éventuels 
        départements manquants (souvent DROM/COM).

    Raises
    ------
    SystemExit
        Si le nombre d'arguments fournis est incorrect ou si la colonne 
        identifiant le code du département n'a pas pu être détectée 
        parmi les candidats possibles ("code", "INSEE_DEP", etc.).
    """
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    contours_path, mapping_path, sortie_path = sys.argv[1:4]

    import geopandas as gpd

    gdf = gpd.read_file(contours_path)

    # Détection automatique de la colonne de code département
    candidats = ["code", "INSEE_DEP", "code_insee", "insee_dep", "CODE_DEPT", "code_departement"]
    col_code = next((c for c in candidats if c in gdf.columns), None)
    if col_code is None:
        raise SystemExit(
            f"Impossible de trouver la colonne de code département parmi {list(gdf.columns)}. "
            "Renseignez-la manuellement dans le script (variable col_code)."
        )

    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    features = []
    manquants_globaux = []

    for ca in mapping["cours_appel"]:
        nom = ca["nom"]
        deps = ca["departements"]
        sous_gdf = gdf[gdf[col_code].isin(deps)]

        trouves = set(sous_gdf[col_code].unique())
        manquants = set(deps) - trouves
        if manquants:
            manquants_globaux.append((nom, sorted(manquants)))

        if sous_gdf.empty:
            # Probablement un DROM/COM absent du fichier de contours fourni
            continue

        geom = sous_gdf.geometry.union_all() if hasattr(sous_gdf.geometry, "union_all") \
            else sous_gdf.geometry.unary_union

        features.append({
            "type": "Feature",
            "properties": {
                "cour_appel": nom,
                "departements": deps,
                "source": "Tableau IV COJ (Légifrance) + contours départementaux fournis en entrée",
            },
            "geometry": geom.__geo_interface__,
        })

    if manquants_globaux:
        print("ATTENTION - départements absents du fichier de contours fourni :")
        for nom, deps in manquants_globaux:
            print(f"  - {nom}: {deps}")
        print("Ces territoires (souvent DROM/COM) doivent être ajoutés séparément.\n")

    fc = {"type": "FeatureCollection", "features": features}

    with open(sortie_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)

    print(f"Écrit {len(features)} ressorts de cour d'appel dans {sortie_path}")


if __name__ == "__main__":
    main()