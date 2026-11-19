"""
Script principal d'extraction d'informations par Modèle de Langage (LLM).

Ce module interroge le LLM pour extraire les informations clés des ordonnances de protection 
de façon structurée, en validant la sortie avec des schémas Pydantic. Il gère 
différentes variantes de traitement (texte complet, texte découpé, OCR amélioré) 
et produit les résultats dans les répertoires intermédiaires correspondants, avec ou 
sans les justifications du modèle.
"""

from __future__ import annotations
import asyncio
import instructor
import openai
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import sys
import json
import time
import argparse
import importlib
from tqdm.asyncio import tqdm_asyncio 
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any

# Configuration du logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pipeline.log", encoding="utf-8")
    ]
)

# ==========================================
#      DÉFINITION DES PARAMÈTRES ET CHEMINS
# ==========================================

CHEMIN_SCRIPT = Path(__file__).resolve()
RACINE_PROJET = CHEMIN_SCRIPT.parent.parent if CHEMIN_SCRIPT.parent.name == "scripts" else CHEMIN_SCRIPT.parent

DOSSIER_ARCHIVES = RACINE_PROJET / "src"
sys.path.append(str(DOSSIER_ARCHIVES))
load_dotenv(dotenv_path=RACINE_PROJET / ".env")

WEBUI_BASE_URL = os.getenv("WEBUI_BASE_URL")
WEBUI_API_KEY = os.getenv("WEBUI_API_KEY")
MODEL_NAME = os.getenv("WEBUI_MODEL")

if not WEBUI_BASE_URL or not WEBUI_API_KEY:
    sys.stderr.write("❌ WEBUI_BASE_URL ou WEBUI_API_KEY manquant(e). Ajoutez-les dans le .env.\n")
    sys.exit(1)

client = instructor.from_openai(
    openai.AsyncOpenAI(
        api_key=WEBUI_API_KEY,
        base_url=WEBUI_BASE_URL.rstrip("/") + "/v1",
    ),
    mode=instructor.Mode.JSON,
)

# ==========================================
#          FONCTIONS UTILITAIRES
# ==========================================

def wrap_schema_with_justifications(schema_class):
    """
    Crée dynamiquement un schéma Pydantic qui englobe le schéma cible 
    tout en exigeant du LLM qu'il fournisse un dictionnaire de justifications.

    Parameters
    ----------
    schema_class : type[BaseModel]
        La classe Pydantic de base représentant la structure des données à extraire.

    Returns
    -------
    type[BaseModel]
        Une nouvelle classe Pydantic contenant les données extraites sous la clé 
        `donnees_extraites` et les citations textuelles sous `justifications`.
    """
    class SchemaAvecJustifications(BaseModel):
        donnees_extraites: schema_class = Field(
            ..., 
            description="L'objet contenant EXACTEMENT l'ensemble des informations extraites selon le schéma de base demandé."
        )
        justifications: dict[str, str] = Field(
            ..., 
            description="Un dictionnaire liant le nom exact de CHAQUE champ extrait à la citation précise du texte justifiant ce choix. S'il n'y a pas de justification explicite, indiquer 'Aucune mention explicite'."
        )
    return SchemaAvecJustifications

async def extraire_infos(contenu: dict, question: str, schema_class, max_retries: int = 3):
    """
    Interroge le modèle de langage (LLM) pour extraire des informations structurées 
    à partir du texte fourni, en validant la sortie avec le schéma Pydantic.

    Parameters
    ----------
    contenu : dict
        Le contenu du document à analyser (contient la clé 'texte' ou le JSON découpé).
    question : str
        Le prompt ou la liste de questions définissant les attentes de l'extraction.
    schema_class : type[BaseModel]
        La classe Pydantic définissant la structure de données attendue en sortie.
    max_retries : int, optional
        Le nombre maximum de tentatives en cas d'échec de l'API ou de non-respect du schéma (default is 3).

    Returns
    -------
    BaseModel
        Un objet Pydantic instancié contenant les données extraites et validées.

    Raises
    ------
    ValueError
        Si le LLM échoue à renvoyer une réponse valide et conforme au schéma après toutes les tentatives.
    """
    for attempt in range(max_retries):
        try:
            # Ajout d'une consigne stricte sur la nécessité de justifier
            system_msg = """Role Assignment: Tu es un greffier expert en droit de la famille au Ministère de la Justice français. Ta tâche est de coder une décision de justice avec une précision absolue.
            Ambiguity Clarification: Si une information est ambiguë, implicite, ou n'est pas EXPLICITEMENT écrite noir sur blanc dans le texte, tu as l'interdiction de la déduire. Tu dois utiliser la valeur 'X' ou 'None' prévue pour les cas non renseignés. Ne présume jamais rien.
            Justification Obligatoire: Pour CHAQUE information que tu extrais, tu dois fournir la citation ou le passage exact du texte qui t'a permis de prendre ta décision dans l'espace 'justifications' demandé.
            
            ⚠️ INSTRUCTION CRITIQUE DE FORMATTAGE ⚠️ : 
            Tu communiques exclusivement avec des machines. Ta réponse DOIT COMMENCER DIRECTEMENT par le caractère { et SE TERMINER DIRECTEMENT par le caractère }. 
            Tu as l'interdiction absolue d'ajouter du texte avant ou après le JSON.
            Tu as l'interdiction absolue d'utiliser des balises Markdown (comme ```json).
            Tu as l'interdiction absolue d'échapper les apostrophes avec un antislash. Écris "l'ordonnance" et non "l\'ordonnance". Le JSON n'a pas besoin d'échapper les apostrophes simples.
            Renvoie uniquement le JSON brut."""

            if "texte" in contenu:
                user_msg = f"Voici le texte à analyser :\n{contenu['texte']}\n{question}"
            else:
                user_msg = f"Voici un extrait de fichier JSON : {contenu}. {question}"

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
            
            return await client.chat.completions.create(
                model=MODEL_NAME,
                response_model=schema_class, 
                messages=messages,
                max_retries=max_retries,
                temperature=0.0,
            )
        except Exception as err:
            logging.error(f"❌ Tentative {attempt+1}/{max_retries} échouée : {err}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    raise ValueError("Aucune réponse valide après toutes les tentatives")

def importer_fichier(chemin_fichier: str | Path) -> dict:
    """
    Charge le contenu d'un fichier JSON ou texte.

    Parameters
    ----------
    chemin_fichier : str or Path
        Le chemin vers le fichier à importer.

    Returns
    -------
    dict
        Un dictionnaire contenant les données du JSON, ou un dictionnaire 
        avec une clé 'texte' pour les fichiers bruts (.txt).

    Raises
    ------
    Exception
        Si le fichier ne peut pas être lu ou décodé.
    """
    chemin_str = str(chemin_fichier)
    try:
        if chemin_str.lower().endswith('.json'):
            with open(chemin_str, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(chemin_str, "r", encoding="utf-8") as f:
                return {"texte": f.read()}
    except Exception as e:
        logging.error(f"❌ Erreur lors de la lecture de {chemin_str}: {str(e)}")
        raise

def exporter_json(data, chemin_sortie: Path) -> None:
    """
    Exporte un objet Pydantic au format JSON sur le disque.

    Parameters
    ----------
    data : BaseModel
        L'objet Pydantic contenant les données à exporter.
    chemin_sortie : Path
        Le chemin de destination du fichier JSON.

    Returns
    -------
    None
    """
    try:
        with chemin_sortie.open("w", encoding="utf-8") as f:
            json.dump(data.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"❌ Impossible d'écrire {chemin_sortie}: {e}")
        raise

async def traiter_un_fichier(nom: str, dossier_entree: Path, dossier_sortie_base: Path, dossier_sortie_justif: Path, question: str, schema_class, semaphore: asyncio.Semaphore, section: str, mode: str, contenu_deja_charge: dict | None = None) -> tuple[bool, str, any]:
    """
    Traite un fichier individuel : lecture, ciblage de section, requête au LLM, et 
    sauvegarde des résultats intermédiaires dans `data/2_interim/` (avec et sans justifications).

    Parameters
    ----------
    nom : str
        Le nom du fichier à traiter.
    dossier_entree : Path
        Le chemin vers le dossier contenant les fichiers sources bruts.
    dossier_sortie_base : Path
        Le chemin vers le dossier où sauvegarder le JSON sans justifications.
    dossier_sortie_justif : Path
        Le chemin vers le dossier où sauvegarder le JSON avec justifications.
    question : str
        La question ou le prompt à soumettre au LLM.
    schema_class : type[BaseModel]
        La classe Pydantic représentant la structure attendue de la section.
    semaphore : asyncio.Semaphore
        Le sémaphore pour limiter le nombre de requêtes concurrentes à l'API LLM.
    section : str
        L'identifiant de la section à extraire (ex: 'a_procedure', 'b_profil_social').
    mode : str
        Le mode d'extraction (ex: 'llm_par_partie' cible une clé précise du JSON, sinon traitement intégral).
    contenu_deja_charge : dict, optional
        Le contenu du fichier s'il a déjà été chargé en mémoire (cas d'un méga-JSON).

    Returns
    -------
    tuple
        (succes, nom_fichier, message_ou_chemin_sortie) : 
        succes (bool) indique si l'extraction a réussi, 
        nom_fichier (str) est le nom du document, 
        message_ou_chemin_sortie (str ou Path) est le chemin de sortie ou le message d'erreur.
    """
    try:
        if contenu_deja_charge is not None:
            contenu_complet = contenu_deja_charge
        else:
            chemin_complet = dossier_entree / nom
            contenu_complet = importer_fichier(chemin_complet)
        
        # --- LOGIQUE DE CIBLAGE SELON LE MODE ---
        cle_cible = None
        if mode == "llm_par_partie" and isinstance(contenu_complet, dict):
            mapping_sections = {
                "a_procedure": "Identification_Procedure",
                "b_profil_social": "Identification_Procedure",
                "c_violences_denoncees": "Pretentions_Demandes",
                "d_demandes": "Pretentions_Demandes",
                "e_reponses_sur_violences": "Pretentions_Demandes",
                "f_reponses_sur_demandes": "Pretentions_Demandes",
                "g_violences_retenues_jaf": "Motifs_Juge",
                "h_decision_jaf": "Decisions_Finales",
                "i_bracelet_anti_rapprochement": "Decisions_Finales"
            }
            
            cle_cible = mapping_sections.get(section)
            
            if cle_cible and cle_cible in contenu_complet:
                contenu_a_envoyer = {"texte": contenu_complet[cle_cible]}
            else:
                contenu_a_envoyer = contenu_complet
        else:
            contenu_a_envoyer = contenu_complet
        
        # Génération du Schéma Englobant pour forcer les justifications
        SchemaEnglobant = wrap_schema_with_justifications(schema_class)

        async with semaphore:
            if mode == "llm_par_partie" and cle_cible and isinstance(contenu_complet, dict) and cle_cible in contenu_complet:
                info_ciblage = f"Ciblage: {cle_cible}"
            elif mode == "llm_better_ocr":
                info_ciblage = "Better OCR (Pages)"
            else:
                info_ciblage = "Texte Complet"

            logging.info(f"⏳ [Envoi au LLM] -> {nom} ({info_ciblage})") 
            data_wrapper = await extraire_infos(contenu_a_envoyer, question, SchemaEnglobant)
            logging.info(f"🟢 [Réponse reçue] <- {nom}") 

        # ==========================================
        # GESTION DES DEUX DOSSIERS DE SORTIE
        # ==========================================
        
        # 1. Dossier Normal (Données Pures)
        data_base = data_wrapper.donnees_extraites
        data_base.NO_CMPST = os.path.splitext(nom)[0]
        sortie_base_path = dossier_sortie_base / f"{data_base.NO_CMPST}.json"
        exporter_json(data_base, sortie_base_path)

        # 2. Dossier Avec Justifications (Données Pures + Citations)
        data_justif_dict = data_wrapper.model_dump(mode="json")
        data_justif_dict["NO_CMPST"] = data_base.NO_CMPST # On force le NO_CMPST à la racine pour la clarté
        sortie_justif_path = dossier_sortie_justif / f"{data_base.NO_CMPST}.json"
        
        with sortie_justif_path.open("w", encoding="utf-8") as f:
            json.dump(data_justif_dict, f, ensure_ascii=False, indent=2)

        return True, nom, sortie_base_path
        
    except Exception as exc:
        logging.error(f"❌ Erreur sur {nom} : {exc}")
        return False, nom, str(exc)

async def lancer_qcm_adhoc(question: str, choix_possibles: list[str], dossier_entree: str, dossier_sortie: str):
    """
    Exécute un QCM ad-hoc sur l'ensemble des documents d'un dossier.
    Ce mode possède déjà son propre système de justification native.

    Parameters
    ----------
    question : str
        La question unique à poser au LLM sur les documents.
    choix_possibles : list of str
        Liste des réponses possibles parmi lesquelles le LLM doit choisir.
    dossier_entree : str
        Chemin vers le dossier contenant les fichiers sources à analyser.
    dossier_sortie : str
        Chemin vers le dossier de destination pour sauvegarder les réponses et les statistiques.

    Returns
    -------
    None
    """
    chemin_entree = Path(dossier_entree) if Path(dossier_entree).is_absolute() else RACINE_PROJET / dossier_entree
    chemin_sortie = Path(dossier_sortie) if Path(dossier_sortie).is_absolute() else RACINE_PROJET / dossier_sortie
    chemin_sortie.mkdir(parents=True, exist_ok=True)
    
    ChoixLiteral = Literal[tuple(choix_possibles)]
    
    class SchemaQCM(BaseModel):
        numero_reponse: int = Field(
            ..., 
            description=f"L'index de la réponse choisie (de 1 à {len(choix_possibles)})"
        )
        reponse_choisie: ChoixLiteral = Field(
            ..., 
            description="Le texte exact de la réponse qui correspond le mieux au document parmi les choix imposés."
        )
        justification: str = Field(
            ..., 
            description="Courte citation ou explication tirée strictement du texte justifiant ce choix."
        )

    liste_choix_str = "\n".join([f"{i+1}. {choix}" for i, choix in enumerate(choix_possibles)])
    prompt_qcm = (
        f"QUESTION : {question}\n\n"
        f"CHOIX POSSIBLES :\n{liste_choix_str}\n\n"
        "INSTRUCTION : Analyse le texte et choisis la réponse la plus adéquate parmi les choix possibles. "
        "Renvoie le numéro de la réponse (ex: 1, 2, 3...) dans 'numero_reponse' et le libellé exact dans 'reponse_choisie'."
    )

    if not chemin_entree.exists():
        logging.error(f"❌ Le dossier source '{chemin_entree}' est introuvable.")
        return

    fichiers = [f for f in os.listdir(chemin_entree) if f.lower().endswith(('.json', '.txt'))]
    fichiers.sort()
    
    logging.info(f"⏳ Lancement du QCM sur {len(fichiers)} documents. Mode de concurrence : 5.")
    semaphore = asyncio.Semaphore(5)
    
    async def traiter_qcm_fichier(nom_fichier: str):
        chemin_fichier = chemin_entree / nom_fichier
        try:
            contenu = importer_fichier(chemin_fichier)
            async with semaphore:
                data = await extraire_infos(contenu, prompt_qcm, SchemaQCM)
            return True, os.path.splitext(nom_fichier)[0], data
        except Exception as e:
            logging.error(f"❌ Échec QCM sur {nom_fichier} : {e}")
            return False, os.path.splitext(nom_fichier)[0], None

    taches = [traiter_qcm_fichier(f) for f in fichiers]

    start_time = time.time()
    resultats = await tqdm_asyncio.gather(*taches, desc="🧠 Traitement QCM")
    end_time = time.time()
    
    duree_totale = end_time - start_time
    temps_moyen = duree_totale / len(fichiers) if fichiers else 0

    liste_reponses_docs = []
    compteur_choix = {choix: 0 for choix in choix_possibles}
    total_reussis = 0
    
    for succes, nom_doc, data in resultats:
        if succes and data:
            total_reussis += 1
            liste_reponses_docs.append({
                "numero_doc": nom_doc,
                "numero_reponse": data.numero_reponse,
                "reponse_choisie": data.reponse_choisie,
                "justification": data.justification
            })
            if data.reponse_choisie in compteur_choix:
                compteur_choix[data.reponse_choisie] += 1
            else:
                compteur_choix[data.reponse_choisie] = 1

    statistiques = {
        "question": question,
        "total_documents_analyses": len(fichiers),
        "total_extractions_reussies": total_reussis,
        "repartition_comptages": {},
        "repartition_pourcentages": {}
    }
    
    for choix, count in compteur_choix.items():
        pourcentage = (count / total_reussis * 100) if total_reussis > 0 else 0
        statistiques["repartition_comptages"][choix] = count
        statistiques["repartition_pourcentages"][choix] = f"{round(pourcentage, 2)} %"

    fichier_reponses_path = chemin_sortie / "qcm_reponses_par_document.json"
    fichier_stats_path = chemin_sortie / "qcm_statistiques.json"
    
    with open(fichier_reponses_path, "w", encoding="utf-8") as f:
        json.dump(liste_reponses_docs, f, ensure_ascii=False, indent=2)
        
    with open(fichier_stats_path, "w", encoding="utf-8") as f:
        json.dump(statistiques, f, ensure_ascii=False, indent=2)

    logging.info("✅ QCM TERMINÉ AVEC SUCCÈS !")
    logging.info(f"📄 Fichier des réponses par document : {fichier_reponses_path}")
    logging.info(f"📊 Fichier des statistiques : {fichier_stats_path}")
    
    print("\n--- 📈 RÉSULTATS RAPIDES ---")
    if duree_totale >= 60:
        minutes = int(duree_totale // 60)
        secondes = int(duree_totale % 60)
        print(f"⏱️  Temps total d'extraction : {minutes}m {secondes}s (soit ~{temps_moyen:.2f} s/doc)")
    else:
        print(f"⏱️  Temps total d'extraction : {duree_totale:.2f} secondes (soit ~{temps_moyen:.2f} s/doc)")
    print("-" * 28)

# ==========================================
# MISE À JOUR DE TRAITER_DOSSIER ET MAIN 
# ==========================================

async def traiter_dossier(dossier_entree: Path, dossier_sortie_base: Path, dossier_sortie_justif: Path, question: str, schema_class, section: str, mode: str, max_concurrent: int = 10, fichiers_specifiques: list[str] | None = None) -> tuple[list[Path], list[str]]:
    """
    Orchestre le traitement asynchrone d'un dossier entier de documents.

    Ignore automatiquement les fichiers qui ont déjà été traités et fusionnés.

    Parameters
    ----------
    dossier_entree : Path
        Dossier contenant les fichiers sources (ou un JSON global unique).
    dossier_sortie_base : Path
        Dossier cible pour les résultats JSON classiques.
    dossier_sortie_justif : Path
        Dossier cible pour les résultats avec justifications (données et citations séparées).
    question : str
        Le prompt associé à la section.
    schema_class : type[BaseModel]
        La classe Pydantic pour structurer la réponse.
    section : str
        Le nom de la section juridique en cours de traitement.
    mode : str
        Variante d'extraction (ex: 'llm_par_partie', 'llm_better_ocr').
    max_concurrent : int, optional
        Nombre de requêtes parallèles au LLM (default is 10).
    fichiers_specifiques : list of str, optional
        Liste restreinte de noms de fichiers à traiter (default is None).

    Returns
    -------
    tuple
        (reussis, en_echec) : listes respectives des fichiers traités avec succès et des fichiers en échec.
    """
    if not dossier_entree.exists():
        logging.error(f"❌ Le chemin source '{dossier_entree}' n'existe pas.")
        return [], []

    contenu_global = None
    if dossier_entree.is_file() and dossier_entree.suffix.lower() == '.json':
        logging.info("📄 Mode Méga-JSON détecté. Chargement en mémoire...")
        with open(dossier_entree, "r", encoding="utf-8") as f:
            contenu_global = json.load(f)
        fichiers_bruts = list(contenu_global.keys())
    else:
        logging.info("📂 Mode dossier classique détecté.")
        fichiers_bruts = [f for f in os.listdir(dossier_entree) if f.lower().endswith(('.json', '.txt'))]
    
    fichiers_bruts.sort()

    if fichiers_specifiques:
        fichiers_cibles = [f for f in fichiers_bruts if os.path.splitext(f)[0] in fichiers_specifiques]
        logging.info(f"🎯 Mode CIBLÉ activé : Vérification de {len(fichiers_cibles)} fichier(s) spécifique(s).")
    else:
        fichiers_cibles = fichiers_bruts
        logging.info(f"📦 Mode COMPLET : Vérification de tous les fichiers ({len(fichiers_cibles)} documents).")

    if mode == "llm_par_partie":
        suffixe = "_bis"
    elif mode == "llm_better_ocr":
        suffixe = "_better_ocr"
    else:
        suffixe = ""

    dossier_final_fusion = dossier_sortie_base.parent / f"JSON__final{suffixe}"
    
    fichiers_a_traiter = []
    for f in fichiers_cibles:
        nom_sans_ext = os.path.splitext(f)[0]
        chemin_fusion = dossier_final_fusion / f"{nom_sans_ext}_fusion.json"
        
        # On vérifie seulement si le dossier de base est fait pour skipper (les deux sont censés se générer en même temps)
        chemin_section_deja_fait = dossier_sortie_base / f"{nom_sans_ext}.json"
        
        if chemin_fusion.exists():
            logging.info(f"⏭️ Ignoré : '{nom_sans_ext}' est déjà entièrement fusionné.")
        elif chemin_section_deja_fait.exists():
            logging.info(f"⏭️ Ignoré : '{nom_sans_ext}' a déjà été extrait pour la section {section}.")
        else:
            fichiers_a_traiter.append(f)

    if not fichiers_a_traiter:
        logging.warning("⚠️ Aucun fichier restant à traiter (tous sont déjà faits).")
        return [], []

    semaphore = asyncio.Semaphore(max_concurrent)
    
    taches = [
        traiter_un_fichier(
            nom=nom, 
            dossier_entree=dossier_entree, 
            dossier_sortie_base=dossier_sortie_base, 
            dossier_sortie_justif=dossier_sortie_justif,
            question=question, 
            schema_class=schema_class, 
            semaphore=semaphore, 
            section=section, 
            mode=mode,
            contenu_deja_charge=contenu_global[nom] if contenu_global else None 
        )
        for nom in fichiers_a_traiter
    ]

    print("\n") 
    resultats = await tqdm_asyncio.gather(*taches, desc=f"⏳ Traitement {dossier_sortie_base.name.replace('JSON_', '')}")
    print("\n") 

    reussis = [donnee for succes, nom, donnee in resultats if succes]
    en_echec = [nom for succes, nom, donnee in resultats if not succes]

    return reussis, en_echec

async def main(section: str, dossier_entree: str | Path, fichiers_specifiques: list[str] | None = None, mode: str = "llm_par_partie") -> int:
    """
    Point d'entrée de l'extraction par le LLM pour une section donnée.

    Détermine le dossier de sortie intermédiaire (dans `data/2_interim/`) selon 
    la méthode de traitement choisie (ex: standard, découpé ou better OCR), charge 
    les schémas Pydantic et prompts associés, et lance le traitement asynchrone.

    Parameters
    ----------
    section : str
        Le nom du bloc juridique à extraire (ex: 'c_violences_denoncees'). 
        Sert à retrouver le schéma Pydantic et la question correspondante.
    dossier_entree : str or Path
        Le chemin vers les fichiers d'entrée bruts ou intermédiaires.
    fichiers_specifiques : list of str, optional
        Liste d'IDs de fichiers pour ne traiter qu'une sélection (default is None).
    mode : str, optional
        Variante du pipeline, dicte le ciblage et le nommage du dossier (default is "llm_par_partie").

    Returns
    -------
    int
        0 si l'exécution est un succès complet ou partiel (fichiers générés), 
        1 en cas d'erreur de configuration (schéma manquant, prompt introuvable).
    """
    logging.info(f"🚀 Initialisation pour la section : {section} (Mode : {mode})")

    chemin_entree = Path(dossier_entree) if Path(dossier_entree).is_absolute() else RACINE_PROJET / dossier_entree

    try:
        module_schema = importlib.import_module(f"schemas.{section}")
        SchemaClass = module_schema.Schema
    except ModuleNotFoundError:
        logging.error(f"❌ Le fichier de schéma schemas/{section}.py est introuvable à la racine.")
        return 1
    except AttributeError:
        logging.error(f"❌ La classe 'Schema' n'a pas été trouvée dans schemas/{section}.py.")
        return 1

    chemin_question = RACINE_PROJET / "prompts" / f"{section}.txt"
    try:
        with open(chemin_question, "r", encoding="utf-8") as f:
            question = f.read()
    except FileNotFoundError:
        logging.error(f"❌ Le fichier question {chemin_question} est introuvable.")
        return 1

    if mode == "llm_par_partie":
        suffixe = "_bis"
    elif mode == "llm_better_ocr":
        suffixe = "_better_ocr"
    else:
        suffixe = ""

    # Création des deux dossiers de destination
    dossier_sortie_par_defaut = RACINE_PROJET / "data" / "2_interim" / f"JSON_{section}{suffixe}"
    dossier_sortie_base = Path(os.getenv("OUTPUT_DIR", dossier_sortie_par_defaut))
    dossier_sortie_justif = Path(str(dossier_sortie_base) + "_avec_justification")

    dossier_sortie_base.mkdir(parents=True, exist_ok=True)
    dossier_sortie_justif.mkdir(parents=True, exist_ok=True)

    logging.info(f"📂 Dossier source : {chemin_entree}")
    logging.info(f"📁 Dossier de destination NORMAL : {dossier_sortie_base}")
    logging.info(f"🗂️  Dossier de destination JUSTIFIÉ : {dossier_sortie_justif}")

    json_files, echec = await traiter_dossier(chemin_entree, dossier_sortie_base, dossier_sortie_justif, question, SchemaClass, section, mode, max_concurrent=1, fichiers_specifiques=fichiers_specifiques)

    logging.info(f"📊 {len(json_files)} fichiers JSON ont été créés avec succès en version normale ET version justifiée.")
    if echec:
        logging.warning(f"⚠️ {len(echec)} fichiers en échec : {', '.join(echec)}")
    else:
        logging.info("✅ Tous les fichiers ciblés ont été traités avec succès.")
    
    return 0