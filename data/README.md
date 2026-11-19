# Données

**Aucune donnée n'est fournie dans ce dépôt.** Le pipeline a été développé sur des ordonnances de protection
réelles, rendues par des juges aux affaires familiales et transmises par le ministère de la Justice. Ces documents
sont **privés** : ils contiennent des données personnelles sensibles (violences conjugales, situation familiale,
enfants) et ne peuvent pas être diffusés, même sous forme anonymisée ou partielle.

Le code est publié avec l'accord du ministère, à la condition de ne contenir aucun document privé.

## Arborescence attendue

Pour exécuter le pipeline sur vos propres documents, créez l'arborescence suivante :

```
data/
├── 1_raw/                   # documents sources
│   ├── scan_pdf/            # PDF scannés
│   ├── opvc_better_ocr/     # textes OCR structurés (JSON)
│   ├── opvc_ano/            # textes anonymisés (.txt)
│   └── opvc_reponses.xlsx   # grille de correction humaine (une ligne par dossier)
├── 2_interim/               # JSON produits par le LLM, section par section
└── 3_final/                 # base consolidée, rapports de comparaison, statistiques
```

Les données géographiques utilisées pour les cartes (départements, ressorts des cours d'appel) sont publiques :
`src/statistique/generer_geojson_ca.py` les récupère depuis l'API Géo de l'État (geo.api.gouv.fr).
