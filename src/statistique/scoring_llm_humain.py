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
        Le chemin d'accès au rapport binaire.
    dossier_sortie : str
        Le répertoire de destination pour sauvegarder les scores.
    nom_fichier_sortie : str, optional
        Le nom du fichier JSON de sortie (default is "scores_par_variable.json").

    Returns
    -------
    dict or None
        Le dictionnaire contenant les résultats agrégés par variable, ou None en cas d'erreur.
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
    Calcule le taux de réussite (moyenne des 1) pour chaque fichier
    à partir du rapport binaire fichier_par_fichier.json.

    Permet d'isoler les fichiers "à problème" (source dégradée) pour revue humaine.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Le chemin d'accès au rapport binaire.
    dossier_sortie : str
        Le répertoire de destination pour sauvegarder les scores.
    nom_fichier_sortie : str, optional
        Le nom du fichier JSON de sortie (default is "scores_par_fichier.json").
    seuil_alerte : float, optional
        Le seuil de réussite en dessous duquel un dossier est signalé (default is 0.5).

    Returns
    -------
    dict or None
        Le dictionnaire contenant les scores évalués par fichier, ou None en cas d'erreur.
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


def modelisation_statistique(chemin_rapport_binaire, chemin_reponses_humain, dossier_sortie,
                              colonnes_metadata, variable_cible=None,
                              nom_fichier_sortie="modelisation_statistique.json"):
    """
    Croise la matrice de résultats binaires avec des variables métier utilisées
    comme proxies de "qualité du dossier" (ex: an_saisine, typ_jur, nv_duraff...),
    puis exécute une régression logistique pour évaluer leur influence sur le
    risque d'erreur du LLM.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Le chemin vers rapport_binaire_fichier_par_fichier.json.
    chemin_reponses_humain : str
        Le fichier JSON humain (source de vérité) pour les métadonnées.
    dossier_sortie : str
        Le répertoire de destination du fichier de modélisation.
    colonnes_metadata : list of str
        Liste des noms de colonnes à utiliser comme variables explicatives.
    variable_cible : str, optional
        Nom d'une variable précise du rapport binaire à expliquer (default is None).
    nom_fichier_sortie : str, optional
        Le nom du fichier de sortie JSON (default is "modelisation_statistique.json").

    Returns
    -------
    dict or None
        Les résultats de la modélisation statistique, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DE LA MODÉLISATION STATISTIQUE ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None
    if not os.path.exists(chemin_reponses_humain):
        logging.error(f"Fichier de métadonnées (humain) introuvable : {chemin_reponses_humain}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        # --- Chargement du rapport binaire ---
        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df_bin = pd.DataFrame(data)

        if "id_fichier" not in df_bin.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None
        df_bin = df_bin.set_index("id_fichier")

        # --- Définition de la cible ---
        if variable_cible:
            if variable_cible not in df_bin.columns:
                logging.error(f"Variable cible '{variable_cible}' absente du rapport binaire.")
                return None
            y = df_bin[variable_cible].astype(int)
            libelle_cible = f"échec sur '{variable_cible}'"
        else:
            colonnes_variables = [c for c in df_bin.columns]
            score_global = df_bin[colonnes_variables].mean(axis=1)
            # Cible binaire : fichier "à problème" si score global < 0.5
            y = (score_global < 0.5).astype(int)
            libelle_cible = "échec global du fichier (score < 50%)"

        # --- Chargement des métadonnées depuis le fichier humain ---
        df_meta = pd.read_json(chemin_reponses_humain)

        def get_col_id(df):
            for col in df.columns:
                if str(col).strip().lower() == 'no_rg':
                    return col
            return df.columns[0]

        def nettoyer_id(val):
            if pd.isna(val):
                return "inconnu"
            s = str(val).strip()
            if s.endswith('.0'):
                s = s[:-2]
            for ext in ['.txt', '.json', '.xlsx']:
                if s.lower().endswith(ext):
                    s = s[:-len(ext)]
            s = s.replace(" ", "")
            return s.lower()

        col_id_meta = get_col_id(df_meta)
        df_meta['id_clean'] = df_meta[col_id_meta].apply(nettoyer_id)
        df_meta = df_meta[df_meta['id_clean'] != "inconnu"]
        df_meta = df_meta.drop_duplicates(subset=['id_clean'], keep='first').set_index('id_clean')

        colonnes_presentes = [c for c in colonnes_metadata if c in df_meta.columns]
        colonnes_absentes = [c for c in colonnes_metadata if c not in df_meta.columns]
        if colonnes_absentes:
            logging.warning(f"Colonnes de métadonnées introuvables et ignorées : {colonnes_absentes}")
        if not colonnes_presentes:
            logging.error("Aucune des colonnes_metadata demandées n'existe dans le fichier humain.")
            return None

        X = df_meta[colonnes_presentes].copy()

        # Conversion en numérique quand c'est possible, sinon encodage catégoriel simple
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")
            if X[col].isna().all():
                # Colonne non numérique -> on la réencode via l'original en catégorie
                X[col] = pd.read_json(chemin_reponses_humain)[col].astype("category").cat.codes

        # --- Alignement X / y sur les mêmes id_fichier ---
        df_avant_dropna = X.join(y.rename("cible"), how="inner")
        nb_avant = len(df_avant_dropna)
        if nb_avant > 0:
            nb_na_par_col = df_avant_dropna.isna().sum()
            if nb_na_par_col.sum() > 0:
                logging.warning(f"Valeurs manquantes par colonne avant dropna (sur {nb_avant} lignes) :")
                for col, nb_na in nb_na_par_col.items():
                    if nb_na > 0:
                        logging.warning(f"  - {col} : {nb_na} manquantes")
        df_final = df_avant_dropna.dropna()

        if len(df_final) < 10:
            logging.error(f"Pas assez d'observations après alignement ({len(df_final)}) pour une régression fiable.")
            return None

        X_final = df_final[colonnes_presentes]
        y_final = df_final["cible"]

        if y_final.nunique() < 2:
            logging.error("La variable cible n'a qu'une seule classe (pas d'erreurs ou pas de succès) : régression impossible.")
            return None

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_final)

        modele = LogisticRegression(max_iter=1000)
        modele.fit(X_scaled, y_final)

        # Odds ratios : exp(coefficient) -> facteur multiplicatif du risque d'erreur
        import math
        resultat = {
            "cible": libelle_cible,
            "nb_observations": len(df_final),
            "taux_erreur_base": round(y_final.mean(), 4),
            "variables_ignorees": colonnes_absentes,
            "coefficients": [
                {
                    "variable": col,
                    "coefficient": round(coef, 4),
                    "odds_ratio": round(math.exp(coef), 4)
                }
                for col, coef in zip(colonnes_presentes, modele.coef_[0])
            ],
            "accuracy_train": round(modele.score(X_scaled, y_final), 4)
        }

        # Tri par force d'effet (valeur absolue du coefficient)
        resultat["coefficients"] = sorted(resultat["coefficients"], key=lambda d: abs(d["coefficient"]), reverse=True)

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info(f"Cible : {libelle_cible} | {len(df_final)} observations | taux d'erreur de base : {resultat['taux_erreur_base'] * 100:.1f}%")
        for c in resultat["coefficients"]:
            sens = "augmente" if c["coefficient"] > 0 else "diminue"
            logging.info(f"  - {c['variable']} : odds ratio {c['odds_ratio']} ({sens} le risque d'erreur)")

        logging.info(f"✅ Modélisation statistique générée : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors de la modélisation statistique : {e}")
        return None

    finally:
        logging.info("--- FIN DE LA MODÉLISATION STATISTIQUE ---\n")


def modelisation_statistique_statsmodels(chemin_rapport_binaire, chemin_reponses_humain, dossier_sortie,
                                          colonnes_metadata, variable_cible=None,
                                          nom_fichier_sortie="modelisation_statistique_statsmodels.json"):
    """
    Identique à modelisation_statistique(), mais utilise statsmodels (sm.Logit) pour
    obtenir en plus : p-values, intervalles de confiance à 95% et le résumé complet
    du modèle. Nécessite `pip install statsmodels`.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Le chemin vers rapport_binaire_fichier_par_fichier.json.
    chemin_reponses_humain : str
        Le fichier JSON humain (source de vérité) pour les métadonnées.
    dossier_sortie : str
        Le répertoire de destination du fichier de modélisation.
    colonnes_metadata : list of str
        Liste des noms de colonnes à utiliser comme variables explicatives.
    variable_cible : str, optional
        Nom d'une variable précise du rapport binaire à expliquer (default is None).
    nom_fichier_sortie : str, optional
        Le nom du fichier de sortie JSON (default is "modelisation_statistique_statsmodels.json").

    Returns
    -------
    dict or None
        Les résultats de la modélisation statistique avancée, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DE LA MODÉLISATION STATISTIQUE (statsmodels) ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None
    if not os.path.exists(chemin_reponses_humain):
        logging.error(f"Fichier de métadonnées (humain) introuvable : {chemin_reponses_humain}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)
    chemin_resume_txt = os.path.join(dossier_sortie, nom_fichier_sortie.replace(".json", ".txt"))

    try:
        import statsmodels.api as sm
    except ImportError:
        logging.error("statsmodels n'est pas installé. Lance : pip install statsmodels")
        return None

    try:
        import math

        # --- Chargement du rapport binaire ---
        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df_bin = pd.DataFrame(data)

        if "id_fichier" not in df_bin.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None
        df_bin = df_bin.set_index("id_fichier")

        # --- Définition de la cible ---
        if variable_cible:
            if variable_cible not in df_bin.columns:
                logging.error(f"Variable cible '{variable_cible}' absente du rapport binaire.")
                return None
            y = df_bin[variable_cible].astype(int)
            libelle_cible = f"échec sur '{variable_cible}'"
        else:
            score_global = df_bin[df_bin.columns].mean(axis=1)
            y = (score_global < 0.5).astype(int)
            libelle_cible = "échec global du fichier (score < 50%)"

        # --- Chargement des métadonnées ---
        df_meta_brut = pd.read_json(chemin_reponses_humain)

        def get_col_id(df):
            for col in df.columns:
                if str(col).strip().lower() == 'no_rg':
                    return col
            return df.columns[0]

        def nettoyer_id(val):
            if pd.isna(val):
                return "inconnu"
            s = str(val).strip()
            if s.endswith('.0'):
                s = s[:-2]
            for ext in ['.txt', '.json', '.xlsx']:
                if s.lower().endswith(ext):
                    s = s[:-len(ext)]
            s = s.replace(" ", "")
            return s.lower()

        col_id_meta = get_col_id(df_meta_brut)
        df_meta = df_meta_brut.copy()
        df_meta['id_clean'] = df_meta[col_id_meta].apply(nettoyer_id)
        df_meta = df_meta[df_meta['id_clean'] != "inconnu"]
        df_meta = df_meta.drop_duplicates(subset=['id_clean'], keep='first').set_index('id_clean')

        colonnes_presentes = [c for c in colonnes_metadata if c in df_meta.columns]
        colonnes_absentes = [c for c in colonnes_metadata if c not in df_meta.columns]
        if colonnes_absentes:
            logging.warning(f"Colonnes de métadonnées introuvables et ignorées : {colonnes_absentes}")
        if not colonnes_presentes:
            logging.error("Aucune des colonnes_metadata demandées n'existe dans le fichier humain.")
            return None

        X = df_meta[colonnes_presentes].copy()
        for col in X.columns:
            X_num = pd.to_numeric(X[col], errors="coerce")
            if X_num.notna().sum() == 0:
                # Non numérique -> encodage catégoriel
                X[col] = X[col].astype("category").cat.codes
            else:
                X[col] = X_num

        # --- Alignement X / y ---
        df_avant_dropna = X.join(y.rename("cible"), how="inner")
        nb_avant = len(df_avant_dropna)
        if nb_avant > 0:
            nb_na_par_col = df_avant_dropna.isna().sum()
            if nb_na_par_col.sum() > 0:
                logging.warning(f"Valeurs manquantes par colonne avant dropna (sur {nb_avant} lignes) :")
                for col, nb_na in nb_na_par_col.items():
                    if nb_na > 0:
                        logging.warning(f"  - {col} : {nb_na} manquantes")
        df_final = df_avant_dropna.dropna()

        if len(df_final) < 10:
            logging.error(f"Pas assez d'observations après alignement ({len(df_final)}) pour une régression fiable.")
            return None

        X_final = df_final[colonnes_presentes].astype(float)
        y_final = df_final["cible"].astype(float)

        if y_final.nunique() < 2:
            logging.error("La variable cible n'a qu'une seule classe : régression impossible.")
            return None

        # Standardisation (facilite l'interprétation et la convergence)
        moyennes = X_final.mean()
        ecarts_types = X_final.std(ddof=0)

        colonnes_constantes = ecarts_types[ecarts_types == 0].index.tolist()
        if colonnes_constantes:
            logging.warning(
                f"Colonne(s) constante(s) sur ces {len(df_final)} dossiers (aucune variance, retirée(s) du modèle) : "
                f"{colonnes_constantes}"
            )
            X_final = X_final.drop(columns=colonnes_constantes)
            moyennes = moyennes.drop(index=colonnes_constantes)
            ecarts_types = ecarts_types.drop(index=colonnes_constantes)

        if X_final.shape[1] == 0:
            logging.error("Toutes les colonnes de métadonnées sont constantes : aucune variable exploitable.")
            return None

        X_std = (X_final - moyennes) / ecarts_types
        X_std = sm.add_constant(X_std)

        modele = sm.Logit(y_final, X_std).fit(disp=0)

        params = modele.params
        conf = modele.conf_int(alpha=0.05)
        conf.columns = ["ic_bas", "ic_haut"]
        pvalues = modele.pvalues

        coefficients = []
        for var in X_std.columns:
            if var == "const":
                continue
            coefficients.append({
                "variable": var,
                "coefficient": round(float(params[var]), 4),
                "odds_ratio": round(math.exp(params[var]), 4),
                "p_value": round(float(pvalues[var]), 4),
                "significatif_5pct": bool(pvalues[var] < 0.05),
                "ic_95_odds_ratio": [
                    round(math.exp(conf.loc[var, "ic_bas"]), 4),
                    round(math.exp(conf.loc[var, "ic_haut"]), 4)
                ]
            })

        coefficients = sorted(coefficients, key=lambda d: d["p_value"])

        resultat = {
            "cible": libelle_cible,
            "nb_observations": len(df_final),
            "taux_erreur_base": round(float(y_final.mean()), 4),
            "variables_ignorees": colonnes_absentes,
            "pseudo_r2_mcfadden": round(float(modele.prsquared), 4),
            "log_likelihood": round(float(modele.llf), 4),
            "coefficients": coefficients
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        with open(chemin_resume_txt, "w", encoding="utf-8") as f:
            f.write(str(modele.summary()))

        logging.info(f"Cible : {libelle_cible} | {len(df_final)} obs. | pseudo-R² McFadden : {resultat['pseudo_r2_mcfadden']}")
        for c in coefficients:
            marque = "***significatif***" if c["significatif_5pct"] else "non significatif"
            sens = "augmente" if c["coefficient"] > 0 else "diminue"
            logging.info(
                f"  - {c['variable']} : OR={c['odds_ratio']} "
                f"(IC95%: {c['ic_95_odds_ratio']}), p={c['p_value']} [{marque}] -> {sens} le risque d'erreur"
            )

        logging.info(f"✅ Modélisation statsmodels générée : '{chemin_sortie}' (résumé complet : '{chemin_resume_txt}')")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors de la modélisation statsmodels : {e}")
        return None

    finally:
        logging.info("--- FIN DE LA MODÉLISATION STATISTIQUE (statsmodels) ---\n")


def diagnostiquer_alignement_ids(chemin_rapport_binaire, chemin_reponses_humain):
    """
    Compare les identifiants présents dans le rapport binaire et ceux du fichier humain.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    chemin_reponses_humain : str
        Chemin vers le fichier source de vérité humain.

    Returns
    -------
    set
        L'ensemble des identifiants communs (intersection).
    """
    with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
        data = json.load(f)
    ids_rapport = set(pd.DataFrame(data)["id_fichier"].astype(str))

    df_meta = pd.read_json(chemin_reponses_humain)

    def get_col_id(df):
        for col in df.columns:
            if str(col).strip().lower() == 'no_rg':
                return col
        return df.columns[0]

    def nettoyer_id(val):
        if pd.isna(val):
            return "inconnu"
        s = str(val).strip()
        if s.endswith('.0'):
            s = s[:-2]
        for ext in ['.txt', '.json', '.xlsx']:
            if s.lower().endswith(ext):
                s = s[:-len(ext)]
        s = s.replace(" ", "")
        return s.lower()

    col_id = get_col_id(df_meta)
    ids_meta = set(df_meta[col_id].apply(nettoyer_id))

    intersection = ids_rapport & ids_meta

    print(f"Nb ids dans le rapport binaire : {len(ids_rapport)}")
    print(f"Nb ids recalculés depuis le fichier humain : {len(ids_meta)}")
    print(f"Nb ids communs (intersection) : {len(intersection)}")
    print(f"Colonne id détectée dans le fichier humain : '{col_id}'")
    print(f"\nExemples d'ids côté rapport binaire : {list(ids_rapport)[:5]}")
    print(f"Exemples d'ids côté fichier humain    : {list(ids_meta)[:5]}")

    if len(intersection) == 0 and ids_rapport and ids_meta:
        exemple_rapport = list(ids_rapport)[0]
        exemple_meta = list(ids_meta)[0]
        print(f"\n⚠️  Aucun id en commun. Compare le format :")
        print(f"   rapport : {repr(exemple_rapport)}")
        print(f"   humain  : {repr(exemple_meta)}")
        print("   -> Vérifie s'il s'agit d'une casse différente, d'un zéro de tête, "
              "d'un séparateur, ou si le fichier humain a été modifié depuis la génération du rapport.")

    return intersection


def verifier_completude_colonnes(chemin_rapport_binaire, chemin_reponses_humain, colonnes_candidates):
    """
    Affiche le taux de complétude restreint aux identifiants présents dans le rapport binaire.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    chemin_reponses_humain : str
        Chemin vers le fichier source de vérité humain.
    colonnes_candidates : list of str
        Liste des colonnes dont on souhaite vérifier la complétude.

    Returns
    -------
    None
    """
    with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
        data = json.load(f)
    ids_rapport = set(pd.DataFrame(data)["id_fichier"].astype(str))

    df_meta = pd.read_json(chemin_reponses_humain)

    def get_col_id(df):
        for col in df.columns:
            if str(col).strip().lower() == 'no_rg':
                return col
        return df.columns[0]

    def nettoyer_id(val):
        if pd.isna(val):
            return "inconnu"
        s = str(val).strip()
        if s.endswith('.0'):
            s = s[:-2]
        for ext in ['.txt', '.json', '.xlsx']:
            if s.lower().endswith(ext):
                s = s[:-len(ext)]
        s = s.replace(" ", "")
        return s.lower()

    col_id = get_col_id(df_meta)
    df_meta['id_clean'] = df_meta[col_id].apply(nettoyer_id)
    df_meta = df_meta.drop_duplicates(subset=['id_clean'], keep='first').set_index('id_clean')

    df_subset = df_meta.loc[df_meta.index.intersection(ids_rapport)]
    n = len(df_subset)

    print(f"Complétude des colonnes candidates sur les {n} dossiers évalués :")
    for col in colonnes_candidates:
        if col not in df_subset.columns:
            print(f"  - {col} : COLONNE INTROUVABLE")
            continue
        nb_rempli = df_subset[col].notna().sum()
        # On considère aussi les chaînes vides / "nan" comme manquantes
        nb_rempli_reel = df_subset[col].apply(
            lambda v: pd.notna(v) and str(v).strip().lower() not in ["", "nan", "none", "nc"]
        ).sum()
        taux = nb_rempli_reel / n if n else 0
        statut = "✅" if taux > 0.7 else ("⚠️" if taux > 0.2 else "❌")
        print(f"  {statut} {col} : {nb_rempli_reel}/{n} renseignés ({taux * 100:.0f}%)")


def agreger_scores_par_famille(chemin_rapport_binaire, dossier_sortie,
                                suffixes=None, prefixes=None,
                                nom_fichier_sortie="scores_par_famille.json"):
    """
    Regroupe les variables du rapport binaire par famille et calcule le taux de réussite moyen.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    dossier_sortie : str
        Répertoire de destination pour sauvegarder les scores par famille.
    suffixes : list of str, optional
        Liste des suffixes à détecter (default is None).
    prefixes : list of str, optional
        Liste des préfixes à détecter (default is None).
    nom_fichier_sortie : str, optional
        Nom du fichier JSON en sortie (default is "scores_par_famille.json").

    Returns
    -------
    dict or None
        Les scores agrégés par famille, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DE L'AGRÉGATION PAR FAMILLE DE VARIABLES ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)

    suffixes = suffixes or ["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    prefixes = prefixes or []

    try:
        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None

        colonnes_variables = [c for c in df.columns if c != "id_fichier"]

        # Association variable -> liste de familles auxquelles elle appartient
        familles_par_variable = {}
        for var in colonnes_variables:
            familles = []
            for suf in suffixes:
                if var.lower().endswith(suf.lower()):
                    familles.append(suf)
            for pre in prefixes:
                if var.lower().startswith(pre.lower()):
                    familles.append(pre)
            if not familles:
                familles = ["_autres"]
            familles_par_variable[var] = familles

        # Regroupement des variables par famille
        variables_par_famille = {}
        for var, familles in familles_par_variable.items():
            for fam in familles:
                variables_par_famille.setdefault(fam, []).append(var)

        # Calcul du score moyen par famille (moyenne sur toutes les cellules de toutes les
        # variables de la famille, tous fichiers confondus)
        resultat_familles = {}
        for fam, variables in variables_par_famille.items():
            valeurs = df[variables].values.flatten()
            taux = float(pd.Series(valeurs).mean())
            resultat_familles[fam] = {
                "nb_variables": len(variables),
                "nb_observations": len(valeurs),
                "taux_reussite_moyen": round(taux, 4),
                "variables": sorted(variables)
            }

        # Tri du pire au meilleur
        resultat_familles = dict(
            sorted(resultat_familles.items(), key=lambda kv: kv[1]["taux_reussite_moyen"])
        )

        resultat = {
            "nb_fichiers": len(df),
            "nb_variables_totales": len(colonnes_variables),
            "familles": resultat_familles
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info("Taux de réussite moyen par famille (du pire au meilleur) :")
        for fam, info in resultat_familles.items():
            logging.info(
                f"  - {fam} : {info['taux_reussite_moyen'] * 100:.1f}% "
                f"({info['nb_variables']} variables, {info['nb_observations']} cellules évaluées)"
            )

        logging.info(f"✅ Scores par famille générés : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors de l'agrégation par famille : {e}")
        return None

    finally:
        logging.info("--- FIN DE L'AGRÉGATION PAR FAMILLE DE VARIABLES ---\n")


def _wilson_ci(nb_succes, n, alpha=0.05):
    """
    Calcule l'intervalle de confiance de Wilson pour une proportion binomiale.

    Parameters
    ----------
    nb_succes : int
        Nombre de succès.
    n : int
        Nombre total d'observations.
    alpha : float, optional
        Seuil de signification (default is 0.05).

    Returns
    -------
    tuple of float
        La borne basse et la borne haute de l'intervalle de confiance.
    """
    from scipy.stats import norm

    if n == 0:
        return 0.0, 1.0

    z = norm.ppf(1 - alpha / 2)
    p_hat = nb_succes / n
    denom = 1 + z ** 2 / n
    centre = p_hat + z ** 2 / (2 * n)
    marge = z * ((p_hat * (1 - p_hat) / n + z ** 2 / (4 * n ** 2)) ** 0.5)
    borne_basse = (centre - marge) / denom
    borne_haute = (centre + marge) / denom
    return max(0.0, borne_basse), min(1.0, borne_haute)


def intervalles_confiance_familles(chemin_rapport_binaire, dossier_sortie,
                                    suffixes=None, prefixes=None, alpha=0.05,
                                    nom_fichier_sortie="ic_scores_par_famille.json"):
    """
    Calcule les intervalles de confiance de Wilson à 95% pour chaque famille de variables.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    dossier_sortie : str
        Répertoire de destination pour sauvegarder les résultats.
    suffixes : list of str, optional
        Liste des suffixes à détecter (default is None).
    prefixes : list of str, optional
        Liste des préfixes à détecter (default is None).
    alpha : float, optional
        Seuil d'erreur pour l'intervalle (default is 0.05).
    nom_fichier_sortie : str, optional
        Nom du fichier JSON en sortie (default is "ic_scores_par_famille.json").

    Returns
    -------
    dict or None
        Les intervalles de confiance calculés, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DU CALCUL DES INTERVALLES DE CONFIANCE ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)

    suffixes = suffixes or ["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    prefixes = prefixes or []

    try:
        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None

        colonnes_variables = [c for c in df.columns if c != "id_fichier"]

        # --- IC par variable ---
        ic_par_variable = {}
        for var in colonnes_variables:
            serie = df[var].dropna()
            n = len(serie)
            nb_succes = int(serie.sum())
            taux = nb_succes / n if n else 0.0
            basse, haute = _wilson_ci(nb_succes, n, alpha)
            ic_par_variable[var] = {
                "taux_reussite": round(taux, 4),
                "n": n,
                "ic_basse": round(basse, 4),
                "ic_haute": round(haute, 4),
                "largeur_ic": round(haute - basse, 4)
            }

        # --- Regroupement par famille (même logique que agreger_scores_par_famille) ---
        familles_par_variable = {}
        for var in colonnes_variables:
            familles = []
            for suf in suffixes:
                if var.lower().endswith(suf.lower()):
                    familles.append(suf)
            for pre in prefixes:
                if var.lower().startswith(pre.lower()):
                    familles.append(pre)
            if not familles:
                familles = ["_autres"]
            familles_par_variable[var] = familles

        variables_par_famille = {}
        for var, familles in familles_par_variable.items():
            for fam in familles:
                variables_par_famille.setdefault(fam, []).append(var)

        ic_par_famille = {}
        for fam, variables in variables_par_famille.items():
            valeurs = pd.Series(df[variables].values.flatten()).dropna()
            n = len(valeurs)
            nb_succes = int(valeurs.sum())
            taux = nb_succes / n if n else 0.0
            basse, haute = _wilson_ci(nb_succes, n, alpha)
            ic_par_famille[fam] = {
                "nb_variables": len(variables),
                "taux_reussite": round(taux, 4),
                "n_observations": n,
                "ic_basse": round(basse, 4),
                "ic_haute": round(haute, 4),
                "largeur_ic": round(haute - basse, 4)
            }

        ic_par_famille = dict(sorted(ic_par_famille.items(), key=lambda kv: kv[1]["taux_reussite"]))

        resultat = {
            "methode": "Wilson score interval",
            "alpha": alpha,
            "niveau_confiance": f"{(1 - alpha) * 100:.0f}%",
            "ic_par_famille": ic_par_famille,
            "ic_par_variable": ic_par_variable
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info(f"IC de Wilson à {(1 - alpha) * 100:.0f}% par famille :")
        for fam, info in ic_par_famille.items():
            logging.info(
                f"  - {fam} : {info['taux_reussite'] * 100:.1f}% "
                f"[{info['ic_basse'] * 100:.1f}% ; {info['ic_haute'] * 100:.1f}%] "
                f"(n={info['n_observations']})"
            )

        logging.info(f"✅ Intervalles de confiance générés : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du calcul des IC : {e}")
        return None

    finally:
        logging.info("--- FIN DU CALCUL DES INTERVALLES DE CONFIANCE ---\n")


def comparer_deux_familles(chemin_rapport_binaire, famille_a, famille_b, dossier_sortie,
                            suffixes=None, prefixes=None,
                            nom_fichier_sortie="comparaison_familles.json"):
    """
    Compare statistiquement deux familles de variables sur les mêmes dossiers à l'aide d'un test de Wilcoxon.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    famille_a : str
        Première famille de variables à comparer.
    famille_b : str
        Seconde famille de variables à comparer.
    dossier_sortie : str
        Répertoire de destination pour sauvegarder la comparaison.
    suffixes : list of str, optional
        Liste des suffixes à détecter (default is None).
    prefixes : list of str, optional
        Liste des préfixes à détecter (default is None).
    nom_fichier_sortie : str, optional
        Nom du fichier JSON en sortie (default is "comparaison_familles.json").

    Returns
    -------
    dict or None
        Les résultats de la comparaison statistique, ou None en cas d'erreur.
    """
    logging.info(f"--- DÉBUT DE LA COMPARAISON '{famille_a}' vs '{famille_b}' ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)

    suffixes = suffixes or ["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    prefixes = prefixes or []

    try:
        from scipy.stats import wilcoxon

        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None
        df = df.set_index("id_fichier")

        colonnes_variables = list(df.columns)

        def variables_de_famille(fam):
            if fam.startswith("_"):
                return [v for v in colonnes_variables if v.lower().endswith(fam.lower())]
            return [v for v in colonnes_variables if v.lower().startswith(fam.lower())]

        vars_a = variables_de_famille(famille_a)
        vars_b = variables_de_famille(famille_b)

        if not vars_a or not vars_b:
            logging.error(f"Aucune variable trouvée pour '{famille_a}' ou '{famille_b}'.")
            return None

        # Score par dossier pour chaque famille (moyenne des variables de la famille,
        # NaN ignorés dossier par dossier)
        score_a = df[vars_a].mean(axis=1)
        score_b = df[vars_b].mean(axis=1)

        # On ne garde que les dossiers où les deux scores sont calculables
        communs = score_a.dropna().index.intersection(score_b.dropna().index)
        score_a = score_a.loc[communs]
        score_b = score_b.loc[communs]

        diff = score_a - score_b

        # Wilcoxon échoue si toutes les différences sont nulles -> on gère le cas
        if (diff == 0).all():
            stat, p_value = None, 1.0
        else:
            stat, p_value = wilcoxon(score_a, score_b, zero_method="wilcox")

        resultat = {
            "famille_a": famille_a,
            "famille_b": famille_b,
            "nb_dossiers_compares": len(communs),
            "score_moyen_a": round(float(score_a.mean()), 4),
            "score_moyen_b": round(float(score_b.mean()), 4),
            "ecart_points": round(float((score_a.mean() - score_b.mean()) * 100), 2),
            "test": "Wilcoxon signé (apparié, sur scores par dossier)",
            "statistique": float(stat) if stat is not None else None,
            "p_value": float(p_value),
            "significatif_a_5pct": bool(p_value < 0.05)
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        verdict = "significativement différente de" if resultat["significatif_a_5pct"] else \
            "pas significativement différente de (au seuil 5%)"
        logging.info(
            f"{famille_a} ({resultat['score_moyen_a'] * 100:.1f}%) est {verdict} "
            f"{famille_b} ({resultat['score_moyen_b'] * 100:.1f}%) — p={p_value:.4g}"
        )
        logging.info(f"✅ Comparaison générée : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors de la comparaison des familles : {e}")
        return None

    finally:
        logging.info(f"--- FIN DE LA COMPARAISON '{famille_a}' vs '{famille_b}' ---\n")


def test_anova_familles(chemin_rapport_binaire, dossier_sortie,
                         suffixes=None, prefixes=None,
                         nom_fichier_sortie="kruskal_wallis_familles.json"):
    """
    Exécute un test de Kruskal-Wallis pour évaluer si les taux de réussite diffèrent globalement entre les familles.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    dossier_sortie : str
        Répertoire de destination pour sauvegarder le test.
    suffixes : list of str, optional
        Liste des suffixes à détecter (default is None).
    prefixes : list of str, optional
        Liste des préfixes à détecter (default is None).
    nom_fichier_sortie : str, optional
        Nom du fichier JSON en sortie (default is "kruskal_wallis_familles.json").

    Returns
    -------
    dict or None
        Les résultats du test global, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DU TEST DE KRUSKAL-WALLIS SUR LES FAMILLES ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)

    suffixes = suffixes or ["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    prefixes = prefixes or []

    try:
        from scipy.stats import kruskal

        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None
        df = df.set_index("id_fichier")

        colonnes_variables = list(df.columns)

        familles_par_variable = {}
        for var in colonnes_variables:
            familles = []
            for suf in suffixes:
                if var.lower().endswith(suf.lower()):
                    familles.append(suf)
            for pre in prefixes:
                if var.lower().startswith(pre.lower()):
                    familles.append(pre)
            if not familles:
                familles = ["_autres"]
            familles_par_variable[var] = familles

        variables_par_famille = {}
        for var, familles in familles_par_variable.items():
            for fam in familles:
                variables_par_famille.setdefault(fam, []).append(var)

        # Un score par dossier et par famille (matrice longue : famille / score)
        scores_par_famille = {}
        for fam, variables in variables_par_famille.items():
            scores_par_famille[fam] = df[variables].mean(axis=1).dropna()

        groupes = list(scores_par_famille.keys())
        echantillons = [scores_par_famille[g].values for g in groupes]

        stat, p_value = kruskal(*echantillons)

        resultat = {
            "test": "Kruskal-Wallis",
            "familles_testees": groupes,
            "statistique_H": round(float(stat), 4),
            "p_value": float(p_value),
            "significatif_a_5pct": bool(p_value < 0.05),
            "interpretation": (
                "Au moins une famille diffère significativement des autres."
                if p_value < 0.05 else
                "Aucune différence globale significative détectée entre familles."
            )
        }

        # --- Post-hoc de Dunn si significatif et si le package est dispo ---
        if p_value < 0.05:
            try:
                import scikit_posthocs as sp

                long_df = pd.concat(
                    [pd.DataFrame({"score": s.values, "famille": fam})
                     for fam, s in scores_par_famille.items()],
                    ignore_index=True
                )
                dunn = sp.posthoc_dunn(long_df, val_col="score", group_col="famille",
                                        p_adjust="bonferroni")
                resultat["post_hoc_dunn_bonferroni"] = dunn.round(4).to_dict()
            except ImportError:
                logging.warning(
                    "scikit-posthocs non installé -> post-hoc de Dunn sauté "
                    "(pip install scikit-posthocs pour l'activer)."
                )
                resultat["post_hoc_dunn_bonferroni"] = None

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info(f"Kruskal-Wallis : H={stat:.4f}, p={p_value:.4g} -> {resultat['interpretation']}")
        logging.info(f"✅ Résultat du test généré : '{chemin_sortie}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du test de Kruskal-Wallis : {e}")
        return None

    finally:
        logging.info("--- FIN DU TEST DE KRUSKAL-WALLIS SUR LES FAMILLES ---\n")


def clustering_co_echec_variables(chemin_rapport_binaire, dossier_sortie,
                                   nb_clusters=None, seuil_distance=None,
                                   nom_fichier_sortie="clustering_variables.json",
                                   nom_dendrogramme="dendrogramme_variables.png"):
    """
    Exécute un clustering hiérarchique des variables selon leur pattern de co-échec.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    dossier_sortie : str
        Répertoire de destination pour sauvegarder le clustering.
    nb_clusters : int, optional
        Nombre de clusters souhaité (default is None).
    seuil_distance : float, optional
        Seuil de distance pour la coupe du dendrogramme (default is None).
    nom_fichier_sortie : str, optional
        Nom du fichier JSON en sortie (default is "clustering_variables.json").
    nom_dendrogramme : str, optional
        Nom du fichier image PNG du dendrogramme (default is "dendrogramme_variables.png").

    Returns
    -------
    dict or None
        Les résultats du clustering, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DU CLUSTERING DES VARIABLES PAR CO-ÉCHEC ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)
    chemin_dendro = os.path.join(dossier_sortie, nom_dendrogramme)

    try:
        import numpy as np
        from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
        from scipy.spatial.distance import squareform
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None
        df = df.set_index("id_fichier")

        # Exclusion des variables constantes (corrélation phi non définie)
        variables = [c for c in df.columns if df[c].nunique(dropna=True) > 1]
        exclues = [c for c in df.columns if c not in variables]
        if exclues:
            logging.info(f"{len(exclues)} variable(s) constante(s) exclue(s) du clustering.")

        matrice_phi = df[variables].corr()  # Pearson sur du binaire = phi
        matrice_phi = matrice_phi.fillna(0.0)

        # Distance = 1 - corrélation, symétrisée et diagonale forcée à 0
        distance = 1 - matrice_phi.values
        distance = (distance + distance.T) / 2
        np.fill_diagonal(distance, 0.0)
        distance = np.clip(distance, 0, None)

        condensed = squareform(distance, checks=False)
        Z = linkage(condensed, method="average")

        seuil = seuil_distance if seuil_distance is not None else (None if nb_clusters else 0.5)
        if nb_clusters:
            labels = fcluster(Z, t=nb_clusters, criterion="maxclust")
        else:
            labels = fcluster(Z, t=seuil, criterion="distance")

        clusters = {}
        for var, lab in zip(variables, labels):
            clusters.setdefault(int(lab), []).append(var)

        # Dendrogramme
        plt.figure(figsize=(14, max(6, len(variables) * 0.12)))
        dendrogram(Z, labels=variables, orientation="left", leaf_font_size=6)
        plt.title("Clustering hiérarchique des variables (co-échec, distance = 1 - phi)")
        plt.xlabel("Distance (1 - corrélation phi)")
        plt.tight_layout()
        plt.savefig(chemin_dendro, dpi=150)
        plt.close()

        resultat = {
            "nb_variables_clusterisees": len(variables),
            "variables_exclues_constantes": exclues,
            "methode_linkage": "average",
            "critere_decoupage": "maxclust" if nb_clusters else "distance",
            "parametre_decoupage": nb_clusters if nb_clusters else seuil,
            "nb_clusters_obtenus": len(clusters),
            "clusters": {
                str(k): sorted(v) for k, v in
                sorted(clusters.items(), key=lambda kv: -len(kv[1]))
            },
            "dendrogramme": chemin_dendro
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info(f"{len(clusters)} cluster(s) de variables détecté(s).")
        for k, v in sorted(clusters.items(), key=lambda kv: -len(kv[1]))[:10]:
            logging.info(f"  - cluster {k} ({len(v)} variables) : {v[:6]}{'...' if len(v) > 6 else ''}")

        logging.info(f"✅ Clustering des variables généré : '{chemin_sortie}'")
        logging.info(f"✅ Dendrogramme sauvegardé : '{chemin_dendro}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du clustering des variables : {e}")
        return None

    finally:
        logging.info("--- FIN DU CLUSTERING DES VARIABLES PAR CO-ÉCHEC ---\n")


def clustering_dossiers(chemin_rapport_binaire, dossier_sortie,
                         nb_clusters=3, nom_fichier_sortie="clustering_dossiers.json",
                         nom_graphique="pca_dossiers.png"):
    """
    Exécute un clustering des dossiers (KMeans) combiné à une réduction de dimension PCA.

    Parameters
    ----------
    chemin_rapport_binaire : str
        Chemin vers le rapport binaire.
    dossier_sortie : str
        Répertoire de destination pour sauvegarder le clustering.
    nb_clusters : int, optional
        Nombre de clusters (default is 3).
    nom_fichier_sortie : str, optional
        Nom du fichier JSON en sortie (default is "clustering_dossiers.json").
    nom_graphique : str, optional
        Nom du fichier image PNG de la PCA (default is "pca_dossiers.png").

    Returns
    -------
    dict or None
        Les résultats du clustering des dossiers, ou None en cas d'erreur.
    """
    logging.info("--- DÉBUT DU CLUSTERING DES DOSSIERS ---")

    if not os.path.exists(chemin_rapport_binaire):
        logging.error(f"Rapport binaire introuvable : {chemin_rapport_binaire}")
        return None

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)
    chemin_graph = os.path.join(dossier_sortie, nom_graphique)

    try:
        import numpy as np
        from sklearn.decomposition import PCA
        from sklearn.cluster import KMeans
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        with open(chemin_rapport_binaire, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if "id_fichier" not in df.columns:
            logging.error("Colonne 'id_fichier' absente du rapport binaire.")
            return None
        df = df.set_index("id_fichier")

        # Variables constantes retirées (n'apportent rien à un clustering par distance)
        variables = [c for c in df.columns if df[c].nunique(dropna=True) > 1]
        X = df[variables].fillna(df[variables].mean()).values

        if len(df) < nb_clusters:
            logging.error(f"Pas assez de dossiers ({len(df)}) pour {nb_clusters} clusters.")
            return None

        kmeans = KMeans(n_clusters=nb_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)

        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(X)

        df_out = pd.DataFrame({
            "id_fichier": df.index,
            "cluster": labels,
            "score_global": df[variables].mean(axis=1).values,
            "pca_1": coords[:, 0],
            "pca_2": coords[:, 1]
        })

        # Scatter plot
        plt.figure(figsize=(9, 7))
        scatter = plt.scatter(df_out["pca_1"], df_out["pca_2"], c=df_out["cluster"],
                               cmap="tab10", s=60, edgecolor="k")
        for _, row in df_out.iterrows():
            plt.annotate(str(row["id_fichier"]), (row["pca_1"], row["pca_2"]),
                         fontsize=6, alpha=0.7)
        plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}% variance)")
        plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}% variance)")
        plt.title("Clustering des dossiers (PCA à titre de visualisation, KMeans sur données complètes)")
        plt.legend(*scatter.legend_elements(), title="Cluster")
        plt.tight_layout()
        plt.savefig(chemin_graph, dpi=150)
        plt.close()

        resume_clusters = {}
        for c in sorted(df_out["cluster"].unique()):
            sous = df_out[df_out["cluster"] == c]
            resume_clusters[str(int(c))] = {
                "nb_dossiers": len(sous),
                "score_global_moyen": round(float(sous["score_global"].mean()), 4),
                "ids_fichiers": sous["id_fichier"].tolist()
            }

        resultat = {
            "nb_dossiers": len(df),
            "nb_variables_utilisees": len(variables),
            "nb_clusters": nb_clusters,
            "variance_expliquee_pca_2d": round(float(pca.explained_variance_ratio_.sum()), 4),
            "clusters": resume_clusters,
            "graphique": chemin_graph
        }

        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=4)

        logging.info(f"{nb_clusters} cluster(s) de dossiers (variance PCA 2D expliquée : "
                     f"{resultat['variance_expliquee_pca_2d'] * 100:.1f}%) :")
        for c, info in resume_clusters.items():
            logging.info(f"  - cluster {c} : {info['nb_dossiers']} dossiers, "
                         f"score moyen {info['score_global_moyen'] * 100:.1f}%")

        logging.info(f"✅ Clustering des dossiers généré : '{chemin_sortie}'")
        logging.info(f"✅ Graphique PCA sauvegardé : '{chemin_graph}'")
        return resultat

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du clustering des dossiers : {e}")
        return None

    finally:
        logging.info("--- FIN DU CLUSTERING DES DOSSIERS ---\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    chemin_rapport = "data/3_final/compare_results/rapport_binaire_fichier_par_fichier.json"
    chemin_humain = "data/1_raw/opvc_reponses_json.json"
    dossier_sortie = "data/3_final/resultats"

    scoring_par_variable(chemin_rapport, dossier_sortie)
    scoring_par_fichier(chemin_rapport, dossier_sortie, seuil_alerte=0.5)

    # Agrégation par famille : commence par les suffixes que tu connais.
    # Une variable peut appartenir à plusieurs familles (ex: "phys_dem_denonc"
    # compte à la fois dans "_dem" et "_denonc").
    agreger_scores_par_famille(
        chemin_rapport, dossier_sortie,
        suffixes=["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    )

    # Diagnostic : à lancer en premier si tu as 0 observations après alignement
    diagnostiquer_alignement_ids(chemin_rapport, chemin_humain)

    # Vérifie la complétude de tes candidates AVANT de les mettre dans colonnes_a_tester.
    # Élargis cette liste avec toutes les variables que tu envisages de tester.
    verifier_completude_colonnes(chemin_rapport, chemin_humain,
                                  ["an_saisine", "nv_duraff", "typ_jur", "tgd",
                                   "dept_res_dem", "nv_gpe_BAR", "hc_opvc"])

    # Exemple : on teste si l'année de saisine, la durée de l'affaire et le type
    # de juridiction influencent le risque d'erreur global du LLM sur un dossier.
    # -> Adapte cette liste à ce qui a du sens pour toi parmi tes 465 variables.
    # an_saisine et typ_jur sont vides pour ces 96 dossiers (cf. diagnostic) -> retirées.
    # Garde uniquement des colonnes que tu sais renseignées pour TES fichiers évalués.
    colonnes_a_tester = ["nv_duraff", "tgd"]

    # IMPORTANT : sans variable_cible, la cible par défaut est "score < 50%",
    # qui peut n'avoir qu'une seule classe si ton LLM performe globalement bien.
    # -> Choisis une variable qui a un vrai mélange de 0 et de 1 dans
    #    scores_par_variable.json (ex: taux_reussite entre 10% et 90%).
    #    ÉVITE les variables à 0% ou 100% de réussite : colonne constante = régression impossible.
    variable_a_expliquer = "mp_presence"  # <-- à adapter (11.5% de réussite, donc mélange 0/1)

    # Version scikit-learn (toujours disponible, mais sans p-values)
    modelisation_statistique(chemin_rapport, chemin_humain, dossier_sortie, colonnes_a_tester,
                              variable_cible=variable_a_expliquer)

    # Version statsmodels (nécessite : pip install statsmodels), avec p-values et IC 95%
    modelisation_statistique_statsmodels(chemin_rapport, chemin_humain, dossier_sortie, colonnes_a_tester,
                                          variable_cible=variable_a_expliquer)

    # --- Nouvelles analyses (robustes avec 96 dossiers) ---

    # 1. Intervalles de confiance de Wilson sur chaque taux (famille + variable)
    intervalles_confiance_familles(
        chemin_rapport, dossier_sortie,
        suffixes=["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    )

    # 2. Comparaison statistique de deux familles précises (Wilcoxon apparié,
    #    car mêmes 96 dossiers évalués sur les deux familles -> données appariées)
    comparer_deux_familles(chemin_rapport, "_denonc", "_dec", dossier_sortie)

    # 5. Kruskal-Wallis global sur les 7 familles + post-hoc de Dunn si significatif
    #    (pip install scikit-posthocs pour activer le post-hoc)
    test_anova_familles(
        chemin_rapport, dossier_sortie,
        suffixes=["_dem", "_def", "_retenu", "_denonc", "_repdef", "_dec", "_pos"]
    )

    # 3. Clustering hiérarchique des 313 variables par pattern de co-échec
    #    (dendrogramme PNG + regroupement en clusters, seuil de distance par défaut 0.5)
    clustering_co_echec_variables(chemin_rapport, dossier_sortie, seuil_distance=0.5)

    # 4. Clustering des 96 dossiers (PCA pour visualiser + KMeans pour regrouper)
    #    -> adapte nb_clusters après avoir regardé le dendrogramme/l'inertie si besoin
    clustering_dossiers(chemin_rapport, dossier_sortie, nb_clusters=3)