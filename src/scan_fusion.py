"""
Script utilitaire de fusion de documents PDF scannés page par page.

Ce script permet de reconstituer des ordonnances de protection (OPVC) complètes 
à partir d'un lot de pages individuelles numérisées en vrac. Il se base sur 
une liste prédéfinie indiquant le nombre de pages attendu pour chaque document 
afin de reconstruire les fichiers d'origine avant traitement.
"""

import os
from pypdf import PdfWriter, PdfReader

# --- À MODIFIER ---
DOSSIER_SOURCE = r"scan_non_fusion"
DOSSIER_DESTINATION = r"scan_fusion"

# Insérez ici votre liste complète de nombres de pages
TAILLES_DOCUMENTS = [6, 5, 5, 10, 7, 6, 6, 5, 11, 7, 5, 4, 4, 4, 3, 5, 7, 5, 4, 4, 6, 8, 4, 6, 4, 5, 5, 8, 8, 4, 9, 8, 6, 4, 9, 3, 6, 5, 5, 3, 4]
# -----------------

def fusionner_pdfs(dossier_src, dossier_dest, tailles):
    """
    Reconstitue les documents PDF multi-pages à partir de pages individuelles.

    Parcourt un dossier contenant des pages PDF uniques triées chronologiquement, 
    les regroupe selon les longueurs spécifiées dans la liste `tailles`, et 
    sauvegarde les documents fusionnés dans le dossier de destination.

    Parameters
    ----------
    dossier_src : str
        Le chemin du répertoire contenant les pages PDF individuelles en vrac.
    dossier_dest : str
        Le chemin du répertoire où seront sauvegardés les PDF complets reconstitués.
    tailles : list of int
        La liste séquentielle du nombre de pages composant chaque document 
        (ex: [6, 5] signifie que le 1er document fait 6 pages, le 2ème en fait 5, etc.).

    Returns
    -------
    None
    """
    os.makedirs(dossier_dest, exist_ok=True)

    # 1. Lister et trier les fichiers pour respecter l'ordre chronologique de votre capture d'écran
    fichiers = [f for f in os.listdir(dossier_src) if f.lower().endswith('.pdf')]
    fichiers.sort()

    # 2. Petite vérification de sécurité
    total_pages_prevues = sum(tailles)
    if total_pages_prevues != len(fichiers):
        print(f"ATTENTION : Votre liste demande {total_pages_prevues} pages au total, "
              f"mais le dossier contient {len(fichiers)} fichiers PDF.")
        print("Le script va quand même essayer de tourner, mais vérifiez votre liste.")
        print("-" * 50)

    index_fichier_courant = 0
    doc_index = 1

    print("Début de la reconstruction...")

    # 3. Boucle sur votre liste de tailles
    for nb_pages in tailles:
        writer = PdfWriter()
        
        # On "pioche" le nombre de fichiers demandé dans la liste globale
        fichiers_du_doc = fichiers[index_fichier_courant : index_fichier_courant + nb_pages]
        
        # Sécurité : si on arrive à la fin des fichiers plus tôt que prévu
        if not fichiers_du_doc:
            print("Il n'y a plus de fichiers à traiter.")
            break
            
        try:
            # On fusionne ces fichiers spécifiques
            for nom_fichier in fichiers_du_doc:
                chemin_complet = os.path.join(dossier_src, nom_fichier)
                reader = PdfReader(chemin_complet)
                
                # Bien qu'ils fassent 1 page, on boucle sur les pages par précaution
                for page in reader.pages:
                    writer.add_page(page)
            
            # On sauvegarde le document terminé
            chemin_sauvegarde = os.path.join(dossier_dest, f"Document_Complet_{doc_index}.pdf")
            with open(chemin_sauvegarde, "wb") as f_out:
                writer.write(f_out)
                
            print(f"-> Sauvegardé : Document_Complet_{doc_index}.pdf (constitué de {len(fichiers_du_doc)} pages)")
            
        except Exception as e:
            print(f"Erreur lors de la création du document {doc_index} : {e}")
            
        # On décale notre index pour le document suivant
        index_fichier_courant += nb_pages
        doc_index += 1

    print(f"\nTerminé ! {doc_index - 1} documents ont été reconstruits avec succès.")

if __name__ == "__main__":
    fusionner_pdfs(DOSSIER_SOURCE, DOSSIER_DESTINATION, TAILLES_DOCUMENTS)