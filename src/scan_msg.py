"""
Script d'extraction de pièces jointes PDF depuis des courriels Outlook (.msg).

Dans le cadre du pipeline de traitement des ordonnances de protection (JAF), 
les documents numérisés sont souvent reçus par e-mail. Ce script utilitaire permet 
d'automatiser l'extraction des fichiers PDF contenus dans ces messages 
avant de les transmettre aux étapes d'OCR et d'anonymisation.
"""

import os
import extract_msg

# --- À MODIFIER ---
DOSSIER_SOURCE = r"scan_msg" # Le dossier contenant vos .msg
DOSSIER_DESTINATION = r"scan_pdf" # Le dossier où extraire les PDF
# -----------------

def extraire_pdfs_des_messages(dossier_source: str, dossier_destination: str) -> None:
    """
    Parcourt un répertoire contenant des fichiers d'emails Outlook (.msg) 
    et extrait automatiquement toutes les pièces jointes au format PDF.

    Parameters
    ----------
    dossier_source : str
        Le chemin d'accès au répertoire contenant les fichiers sources au format .msg.
    dossier_destination : str
        Le chemin d'accès au répertoire où les fichiers PDF extraits 
        seront sauvegardés. Le dossier est créé automatiquement s'il n'existe pas.

    Returns
    -------
    None
        La fonction ne retourne rien mais sauvegarde directement 
        les fichiers extraits sur le disque et affiche un compte-rendu dans la console.
    """
    # Créer le dossier de destination s'il n'existe pas déjà
    os.makedirs(dossier_destination, exist_ok=True)

    compteur = 0

    # Parcourir tous les fichiers du dossier source
    for nom_fichier in os.listdir(dossier_source):
        if nom_fichier.lower().endswith('.msg'):
            chemin_complet = os.path.join(dossier_source, nom_fichier)
            
            try:
                # Ouvrir le fichier .msg
                msg = extract_msg.Message(chemin_complet)
                
                # Parcourir les pièces jointes du mail
                for piece_jointe in msg.attachments:
                    # Vérifier s'il y a un nom de fichier et si c'est un PDF
                    if piece_jointe.longFilename and piece_jointe.longFilename.lower().endswith('.pdf'):
                        # Sauvegarder le PDF dans le dossier de destination
                        piece_jointe.save(customPath=dossier_destination)
                        compteur += 1
                        print(f"Extrait : {piece_jointe.longFilename}")
                        
                msg.close()
                
            except Exception as e:
                print(f"Erreur lors de la lecture de {nom_fichier} : {e}")

    print(f"\nTerminé ! {compteur} fichier(s) PDF extrait(s) avec succès.")


if __name__ == "__main__":
    extraire_pdfs_des_messages(DOSSIER_SOURCE, DOSSIER_DESTINATION)