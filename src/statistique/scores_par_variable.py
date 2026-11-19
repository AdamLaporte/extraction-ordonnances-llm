import pandas as pd
import json
import logging
import os


def scoring_par_variable(chemin_rapport_binaire, dossier_sortie, nom_fichier_sortie="scores_par_variable.json"):
    """
    Calcule le taux de réussite (moyenne des 1) pour chaque variable
    à partir du rapport binaire fichier_par_fichier.json.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Le chemin d'accès au rapport binaire contenant les données de comparaison.
    dossier_sortie : str
        Le chemin du répertoire où sauvegarder le fichier JSON de résultats.
    nom_fichier_sortie : str, optional
        Le nom du fichier JSON généré en sortie (default is "scores_par_variable.json").

    Returns
    -------
    dict or None
        Un dictionnaire contenant les statistiques agrégées des scores par variable, 
        ou None si une erreur survient.
    """
    logging.info("--- DÉBUT DU SCORING PAR VARIABLE ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)

    try:
        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)

        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None

        # On isole uniquement les colonnes de variables (tout sauf l'id)
        colonnes_variables = [c for c in df.columns if c != "id_fichier"]

        # Moyenne (taux de réussite) par variable, triée du pire au meilleur
        scores = df[colonnes_variables].mean().sort_values()

        nb_fichiers = len(df)

        resultat = {
            "nb_fichiers_evalues": nb_fichiers,
            "score_global_moyen": round(df[colonnes_variables].mean().mean(), 4),
            "scores_par_variable": {
                var: {
                    "taux_reussite": round(score, 4),
                    "nb_erreurs": int((1 - score) * nb_fichiers)
                }
                for var, score in scores.items()
            }
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        # Petit résumé lisible dans les logs
        logging.info(f"Score global moyen : {resultat['score_global_moyen'] * 100:.1f}%")
        logging.info("Variables les plus problématiques :")
        for var, info in list(resultat["scores_par_variable"].items())[:5]:
            logging.info(f"  - {var} : {info['taux_reussite'] * 100:.1f}% ({info['nb_erreurs']} erreurs)")

        logging.info(f"✅ Scores par variable générés : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du scoring par variable : {e}")
        return None

    finally:
        logging.info("--- FIN DU SCORING PAR VARIABLE ---\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    chemin_rapport = "data/3_final/compare_results/rapport_binaire_fichier_par_fichier.json"
    dossier_sortie = "data/3_final/resultats"

    scoring_par_variable(chemin_rapport, dossier_sortie)