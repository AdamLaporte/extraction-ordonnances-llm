# 📖 Documentation Technique & Guide d'Utilisation — Pipeline OPVC (JAF)

## 1. Vue d'ensemble du projet

Ce projet automatise l'extraction, la structuration et l'analyse statistique des Ordonnances de Protection (OPVC) rendues par les Juges aux Affaires Familiales (JAF). Il transforme des documents juridiques PDF bruts et non structurés en une base de données exploitable, en s'appuyant sur des techniques de reconnaissance optique de caractères (OCR) et des Modèles de Langage (LLM) contraints par des schémas stricts (Pydantic). La protection des données personnelles est au cœur de l'architecture.

---

## 2. Architecture et Cycle de vie de la donnée

Le traitement d'un document suit un cheminement logique en plusieurs étapes :

* **Acquisition & Préparation :** Les documents reçus (souvent par mail) sont extraits, fusionnés si besoin, puis convertis de PDF en texte via OCR.


* **Anonymisation :** Les textes passent par un modèle de détection d'entités (NER) pour masquer les prénoms et sécuriser les données.


* **Segmentation :** Les textes longs sont découpés en blocs logiques (Procédure, Motifs, Décision) via des expressions régulières pour faciliter le travail du LLM.


* **Extraction LLM :** Le modèle lit les textes et extrait les informations selon des questions précises (prompts), en générant un fichier JSON structuré et, optionnellement, ses justifications.


* **Consolidation :** Les JSON individuels sont fusionnés pour créer une base de données tabulaire propre.


* **Évaluation & Statistiques :** La base LLM est comparée à une correction humaine pour calculer des scores de fiabilité, puis analysée statistiquement et géographiquement.



---

## 3. Le Dictionnaire des Fichiers

Voici la cartographie des scripts pour comprendre rapidement qui fait quoi.

### ⚙️ Cœur du Pipeline (Dossier `src/` ou racine)

| Fichier | Catégorie | Rôle principal |
| --- | --- | --- |
| **`main.py`** | Orchestration | Le chef d'orchestre en ligne de commande. Lance l'extraction LLM, la fusion, la consolidation et la comparaison en une seule commande.

 |
| **`llm_pydantic_opvc_2021.py`** | Extraction | Contient la logique d'appel à l'API LLM (via Instructor/OpenAI), force le format de sortie via Pydantic et gère les justifications.

 |
| **`decoupe_opvc_regex.py`** | Traitement Texte | Segmente le texte brut d'une ordonnance en 4 parties distinctes à l'aide d'expressions régulières.

 |
| **`jointure_json.py`** | Consolidation | Fusionne les résultats JSON des différentes sections (a_procedure, b_profil_social...) en un seul fichier par dossier.

 |
| **`json_to_database.py`** | Consolidation | Applique les règles métiers de cohérence et compile tous les JSON en une base de données tabulaire finale.

 |
| **`compare_database.py`** | Évaluation | Aligne la base générée par le LLM avec le fichier Excel de correction humaine pour repérer les erreurs et les bonus.

 |

### 📄 Préparation des documents et OCR

| Fichier | Catégorie | Rôle principal |
| --- | --- | --- |
| **`scan_msg.py`** | Ingestion | Extrait automatiquement les pièces jointes PDF depuis des e-mails Outlook (`.msg`).

 |
| **`scan_fusion.py`** | Ingestion | Reconstitue des documents PDF complets à partir d'un lot de pages scannées en vrac.

 |
| **`ocr.py`** | OCR | Convertit les PDF en texte brut à l'aide de Tesseract (avec prétraitement d'image).

 |
| **`better_ocr.py`** | OCR | Alternative plus performante utilisant OpenCV (anti-fluo) et PaddleOCR pour l'extraction de texte.

 |
| **`anonymize_json_better.py`** | Sécurité | Utilise GLiNER pour détecter et masquer les prénoms dans les textes bruts (chunking intelligent).

 |
| **`recup_numero_RG.py`** | Utilitaire | Extrait le Numéro de Répertoire Général (N° RG) des fichiers textes et harmonise le nommage des fichiers.

 |
| **`renommer_doc.py`** | Utilitaire | Renomme en masse les fichiers JSON issus de l'OCR en utilisant leur N° RG.

 |

### 📈 Analyse Statistique et Économétrie

| Fichier | Catégorie | Rôle principal |
| --- | --- | --- |
| **`scores_par_fichier.py`** / **`scores_par_variable.py`** | Scoring | Calcule les taux de réussite par variable et par document à partir du rapport de comparaison binaire.

 |
| **`scoring_llm_humain.py`** | Scoring Avancé | Regroupe les calculs de scores, génère des intervalles de confiance, des tests statistiques (Kruskal-Wallis) et des modélisations logistiques.

 |
| **`statistique_jaf.py`** | Économétrie | Exécute une régression logistique pour évaluer l'impact géographique des cours d'appel sur la décision finale.

 |
| **`make_barplots.py`** | Visualisation | Génère les graphiques en barres pour illustrer les résultats des modèles économétriques.

 |
| **`generer_geojson_ca.py`** | Cartographie | Crée les contours géographiques des cours d'appel à partir des départements.

 |
| **`map_stat.py`** | Cartographie | Génère une carte choroplèthe de la France illustrant l'impact régional des décisions de justice.

 |

### 🖥️ Interfaces Utilisateur (Dossier `apps/`)

| Fichier | Catégorie | Rôle principal |
| --- | --- | --- |
| **`question.py`** | Interface | L'interface graphique (GUI) permettant de piloter l'extraction, avec barre de progression et mode QCM libre.

 |
| **`comparaison.py`** | Dashboard | Un tableau de bord complet comparant la performance des différents modèles (M1 à M4) face à l'humain.

 |
| **`resultat.py`** | Dashboard | Un explorateur de base de données présentant des statistiques descriptives et le croisement de variables.

 |

---

## 4. Guide de Démarrage Rapide

**Étape 1 : Installation de l'environnement**
Il est impératif d'utiliser un environnement virtuel isolé.

```bash
python -m venv env
source env/bin/activate  # Sous Windows : env\Scripts\activate
pip install -r requirements.txt

```

**Étape 2 : Configuration des Clés API**
Le projet nécessite une connexion à un modèle de langage. Tu dois créer un fichier `.env` à la racine du projet contenant :

```env
WEBUI_BASE_URL=https://ton-url-api.com
WEBUI_API_KEY=ta_cle_api_secrete
WEBUI_MODEL=nom_du_modele_utilise

```

**Étape 3 : Exécution du Pipeline de bout en bout**
Pour lancer le traitement sur un lot de documents, utilise le point d'entrée principal en ligne de commande :

```bash
python main.py

```

Le menu interactif te demandera de choisir le mode d'extraction (texte complet, texte découpé, etc.) et gérera toute la chaîne, de la requête LLM à la comparaison avec la base humaine.

**Étape 4 : Utilisation des interfaces graphiques (Dashboards)**
Pour visualiser les résultats, enquêter sur les erreurs du modèle ou lancer des extractions de manière plus visuelle, utilise Streamlit :

```bash
streamlit run apps/comparaison.py
# ou
streamlit run apps/question.py

```

---

## 5. Règle d'or : Confidentialité des Données

Ce projet manipule des données judiciaires hautement sensibles. **En aucun cas le dossier `data/` (contenant les PDF bruts, les scans ou les JSON non anonymisés) ne doit être partagé ou commité sur un dépôt de code (Git)**. Utilise toujours le script `anonymize_json_better.py` pour nettoyer les textes avant de réaliser des exports ou des tests en dehors de l'environnement sécurisé.
