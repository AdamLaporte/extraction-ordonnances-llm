import pandas as pd
import json
import logging
import os


def scoring_par_variable(chemin_rapport_binaire, dossier_sortie, nom_fichier_sortie="scores_par_variable.json"):
    """
    Calcule le taux de réussite (moyenne des 1) pour chaque variable à partir du rapport binaire.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Le chemin d'accès au rapport binaire (fichier_par_fichier.json) généré précédemment.
    dossier_sortie : str
        Le chemin du dossier où le fichier de résultat sera enregistré.
    nom_fichier_sortie : str, optional
        Le nom du fichier JSON généré en sortie (default is "scores_par_variable.json").

    Returns
    -------
    dict or None
        Un dictionnaire contenant le nombre de fichiers évalués, le score global moyen, 
        et les détails (taux de réussite, nombre d'erreurs) par variable. Retourne None en cas d'erreur.
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


def scoring_par_fichier(chemin_rapport_binaire, dossier_sortie, nom_fichier_sortie="scores_par_fichier.json",
                         seuil_alerte=0.5):
    """
    Calcule le taux de réussite (moyenne des 1) pour chaque fichier afin d'isoler les documents "à problème".

    Parameters
    ----------
    chemin_rapport_binaire : str
        Le chemin d'accès au rapport binaire (fichier_par_fichier.json) contenant les données évaluées.
    dossier_sortie : str
        Le chemin du dossier de destination pour le rapport généré.
    nom_fichier_sortie : str, optional
        Le nom du fichier JSON de sortie (default is "scores_par_fichier.json").
    seuil_alerte : float, optional
        Le seuil de réussite en dessous duquel un fichier est signalé pour une revue humaine (default is 0.5).

    Returns
    -------
    dict or None
        Un dictionnaire contenant le nombre de fichiers évalués, le nombre de fichiers sous le seuil d'alerte, 
        et la liste des scores par identifiant de fichier. Retourne None en cas d'erreur.
    """
    logging.info("--- DÉBUT DU SCORING PAR FICHIER ---")

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

        colonnes_variables = [c for c in df.columns if c != "id_fichier"]

        # Score par ligne (fichier) : moyenne des 1 sur toutes les variables
        df["score_fichier"] = df[colonnes_variables].mean(axis=1)
        df["nb_erreurs"] = (1 - df[colonnes_variables]).sum(axis=1).astype(int)

        df_trie = df.sort_values("score_fichier")

        fichiers_a_revoir = df_trie[df_trie["score_fichier"] < seuil_alerte]

        resultat = {
            "nb_fichiers_evalues": len(df),
            "seuil_alerte": seuil_alerte,
            "nb_fichiers_sous_seuil": len(fichiers_a_revoir),
            "scores_par_fichier": [
                {
                    "id_fichier": row["id_fichier"],
                    "taux_reussite": round(row["score_fichier"], 4),
                    "nb_erreurs": int(row["nb_erreurs"])
                }
                for _, row in df_trie.iterrows()
            ]
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info(f"{len(fichiers_a_revoir)} fichier(s) sous le seuil de {seuil_alerte * 100:.0f}% :")
        for _, row in fichiers_a_revoir.iterrows():
            logging.info(f"  - {row['id_fichier']} : {row['score_fichier'] * 100:.1f}% ({row['nb_erreurs']} erreurs)")

        logging.info(f"✅ Scores par fichier générés : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du scoring par fichier : {e}")
        return None

    finally:
        logging.info("--- FIN DU SCORING PAR FICHIER ---\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    chemin_rapport = "data/3_final/compare_results/rapport_binaire_fichier_par_fichier.json"
    dossier_sortie = "data/3_final/resultats"

    scoring_par_variable(chemin_rapport, dossier_sortie)
    scoring_par_fichier(chemin_rapport, dossier_sortie, seuil_alerte=0.5)