"""
Script d'anonymisation des données sensibles issues des ordonnances de protection (JAF).

Ce script utilise le modèle GLiNER (Open-Vocabulary NER) pour détecter et 
masquer les prénoms (demanderesse, victime, défendeur, agresseur) au sein 
des fichiers JSON d'OCR bruts avant leur traitement par le reste du pipeline.
Il garantit la confidentialité des données personnelles conformément aux 
règles de sécurité du projet.
"""

import json
from pathlib import Path
from gliner import GLiNER
from tqdm import tqdm

# ----------------------------------------------------------------------
# Configuration des répertoires
# ----------------------------------------------------------------------
SRC_DIR = Path("data/1_raw/opvc_better_ocr_non_ano")
DST_DIR = Path("data/1_raw/opvc_better_ocr")

# Crée le répertoire de destination s’il n’existe pas
DST_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Chargement du modèle GLiNER multilingue (SOTA en Open-Vocabulary NER)
# ----------------------------------------------------------------------
print("Chargement du modèle GLiNER (urchade/gliner_multi-v2.1) …")
try:
    model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")
except Exception as e:
    raise SystemExit(f"Erreur lors du chargement du modèle : {e}")

# Définition des étiquettes cibles en langage naturel
LABELS_CIBLES = [
    "prénom de la demanderesse",
    "prénom de la victime",
    "prénom du défendeur",
    "prénom de l'agresseur"
]

# ----------------------------------------------------------------------
# Fonctions d'anonymisation de texte avec découpage (Chunking)
# ----------------------------------------------------------------------
def _apply_gliner_on_chunk(text_chunk: str) -> str:
    """
    Applique le modèle GLiNER sur un court bloc de texte pour anonymiser les entités ciblées.

    Parameters
    ----------
    text_chunk : str
        Le segment de texte brut à analyser et anonymiser.

    Returns
    -------
    str
        Le texte avec les entités détectées remplacées par la balise '[PRÉNOM]'.
        Si le texte d'origine contient moins de 3 caractères, il est retourné tel quel.
    """
    if len(text_chunk.strip()) < 3:
        return text_chunk
        
    entities = model.predict_entities(text_chunk, LABELS_CIBLES, threshold=0.4, flat_ner=True)
    # Tri par position décroissante pour ne pas décaler les index lors du remplacement
    entities_sorted = sorted(entities, key=lambda x: x["start"], reverse=True)
    
    for ent in entities_sorted:
        start = ent["start"]
        end = ent["end"]
        text_chunk = text_chunk[:start] + "[PRÉNOM]" + text_chunk[end:]
        
    return text_chunk

def anonymize_text(text: str) -> str:
    """
    Découpe intelligemment le texte pour contourner la limite de tokens du modèle (384 tokens),
    anonymise les segments, puis réassemble le texte à l'identique.

    Gère la segmentation par paragraphes et par phrases pour les blocs trop longs 
    (> 800 caractères) afin de maintenir la précision du modèle NER sans perte 
    de formatage original (sauts de ligne, ponctuation).

    Parameters
    ----------
    text : str
        Le texte complet et brut issu de l'OCR à anonymiser.

    Returns
    -------
    str
        Le texte anonymisé, avec sa structure (sauts de ligne, phrases) originale rigoureusement préservée.
    """
    if len(text.strip()) < 3:
        return text

    # 1. Découpage naturel par sauts de ligne (paragraphes de l'OCR)
    paragraphs = text.split('\n')
    anon_paragraphs = []
    
    for para in paragraphs:
        # 2. Si un paragraphe dépasse 800 caractères (~200 mots), on le découpe 
        # par phrases pour rester sous la limite technique du modèle
        if len(para) > 800:
            sentences = para.split('. ')
            anon_sentences = [_apply_gliner_on_chunk(sent) for sent in sentences]
            # Réassemblage exact des phrases avec leur point et espace
            anon_paragraphs.append('. '.join(anon_sentences))
        else:
            anon_paragraphs.append(_apply_gliner_on_chunk(para))
            
    # 3. Réassemblage exact des paragraphes avec leurs sauts de ligne
    return '\n'.join(anon_paragraphs)

# ----------------------------------------------------------------------
# Traversée récursive du JSON pour n'anonymiser que les chaînes de texte
# ----------------------------------------------------------------------
def anonymize_json_data(data):
    """
    Parcourt récursivement une structure de données (généralement issue d'un JSON) 
    et applique l'anonymisation uniquement sur les valeurs textuelles.

    Les clés des dictionnaires et les types non textuels (entiers, flottants, 
    booléens, None) sont conservés intacts pour ne pas corrompre le schéma de données.

    Parameters
    ----------
    data : dict, list, str, int, float, bool, or None
        La structure de données ou la valeur individuelle à traiter.

    Returns
    -------
    dict, list, str, int, float, bool, or None
        La structure de données nettoyée avec toutes les chaînes de caractères sensibles anonymisées.
    """
    if isinstance(data, dict):
        return {key: anonymize_json_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [anonymize_json_data(item) for item in data]
    elif isinstance(data, str):
        return anonymize_text(data)
    else:
        # Int, float, bool, None : on laisse intact
        return data

# ----------------------------------------------------------------------
# Traitement principal des fichiers *.json
# ----------------------------------------------------------------------
def main():
    """
    Point d'entrée du script pour le traitement en lot des fichiers JSON.

    Lit tous les fichiers JSON du répertoire source (`SRC_DIR`), 
    applique la procédure d'anonymisation pour protéger les données sensibles 
    afin d'éviter les fuites de données, puis sauvegarde les résultats 
    dans le répertoire de destination (`DST_DIR`).
    """
    json_files = list(SRC_DIR.glob("*.json"))
    if not json_files:
        print(f"Aucun fichier .json trouvé dans {SRC_DIR}")
        return

    print(f"Anonymisation optimisée de {len(json_files)} fichiers JSON …")
    for src_path in tqdm(json_files, unit="file"):
        try:
            # 1. Lecture du fichier JSON source
            with open(src_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # 2. Anonymisation des données
            anon_data = anonymize_json_data(raw_data)

            # 3. Écriture dans le répertoire destination
            dst_path = DST_DIR / src_path.name
            with open(dst_path, "w", encoding="utf-8") as f:
                # ensure_ascii=False garantit la bonne écriture des accents français
                json.dump(anon_data, f, ensure_ascii=False, indent=2)

        except Exception as exc:
            tqdm.write(f"⚠️ Erreur avec {src_path.name} : {exc}")

    print("✅ Fin de l’anonymisation.")

if __name__ == "__main__":
    main()