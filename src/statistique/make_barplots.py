"""
Script de génération de graphiques (barplots) pour l'analyse économétrique.

Ce script lit les résultats d'un modèle logistique depuis un fichier Excel,
sépare les variables régionales (cours d'appel) des autres caractéristiques,
et génère deux graphiques en barres horizontales illustrant l'impact 
de chaque variable sur la probabilité d'obtention (en points de pourcentage).
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ----------------------------------------------------------------------
# 1. Chargement et préparation des données
# ----------------------------------------------------------------------
file = "test/Resultats_Econometrie_Ordonnances.xlsx"
df = pd.read_excel(file, sheet_name="Sheet1").rename(columns={"Unnamed: 0": "variable"})
impact_col = "Impact probabilité (Points de %)"

is_region = df["variable"].str.startswith("cour_appel_")
df_region = df[is_region].copy()
df_other = df[~is_region].copy()

# Libellés région : on isole le nom de la ville
def clean_region(v):
    """
    Nettoie le nom de la variable régionale pour n'isoler que le nom de la ville.

    Parameters
    ----------
    v : str
        Le nom brut de la variable contenant le préfixe de la cour d'appel.

    Returns
    -------
    str
        Le nom nettoyé de la cour d'appel.
    """
    return (v.replace("cour_appel_Cour d'Appel de ", "")
              .replace("cour_appel_Cour d'Appel d'", ""))

df_region["label"] = df_region["variable"].apply(clean_region)
# Libellés autres variables : underscores -> espaces, lisibilité
df_other["label"] = df_other["variable"].str.replace("_", " ")

# Tri ascendant -> le plus fort effet positif se retrouve en haut du barh
df_region = df_region.sort_values(impact_col, ascending=True).reset_index(drop=True)
df_other = df_other.sort_values(impact_col, ascending=True).reset_index(drop=True)

COLOR_POS = "#1B7A3D"   # vert : effet positif
COLOR_NEG = "#C0392B"   # rouge : effet négatif
GRAY = "#6B6B6B"

def fr_num(x, signed=True):
    """
    Formate un nombre décimal au format français (remplacement du point par une virgule).

    Parameters
    ----------
    x : float
        Le nombre décimal à formater.
    signed : bool, optional
        Indique si le signe (positif ou négatif) doit être affiché explicitement (default is True).

    Returns
    -------
    str
        Le nombre formaté sous forme de chaîne de caractères.
    """
    s = f"{x:+.1f}" if signed else f"{x:.1f}"
    return s.replace(".", ",")

# ----------------------------------------------------------------------
# 2. Fonction de tracé
# ----------------------------------------------------------------------
def make_barplot(data, title, subtitle, filename, note):
    """
    Génère et sauvegarde un graphique en barres horizontales (barplot) 
    illustrant l'impact des variables sur la probabilité étudiée.

    Les barres sont colorées en vert pour un effet positif et en rouge 
    pour un effet négatif. Le graphique inclut les valeurs numériques formatées 
    et une légende explicative disposée sous l'axe.

    Parameters
    ----------
    data : pandas.DataFrame
        Le DataFrame contenant les données à tracer (incluant les colonnes "label" et d'impact).
    title : str
        Le titre principal du graphique.
    subtitle : str
        Le sous-titre explicatif affiché sous le titre.
    filename : str
        Le chemin et le nom du fichier de destination pour sauvegarder l'image.
    note : str
        Le texte de la note de bas de page (ex: précisions statistiques).

    Returns
    -------
    None
    """
    n = len(data)
    fig, ax = plt.subplots(figsize=(10, max(3.2, 0.62 * n + 1.6)))

    colors = [COLOR_POS if v >= 0 else COLOR_NEG for v in data[impact_col]]
    bars = ax.barh(data["label"], data[impact_col], color=colors,
                    edgecolor="white", height=0.62, zorder=3)

    ax.axvline(0, color="#333333", linewidth=0.9, zorder=2)

    ax.set_xlabel("Impact sur la probabilité (points de %)", fontsize=11, color="#333333")
    ax.set_title(title, fontsize=15, fontweight="bold", loc="left", pad=34, color="#1a1a1a")
    ax.text(0, 1.045, subtitle, transform=ax.transAxes, fontsize=10,
            color=GRAY, ha="left", va="bottom")

    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(axis="y", length=0, labelsize=10.5)
    ax.tick_params(axis="x", labelsize=9.5, colors="#555555")
    ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    ax.set_axisbelow(True)

    xmax_abs = data[impact_col].abs().max()
    offset = xmax_abs * 0.025
    for bar, v in zip(bars, data[impact_col]):
        y = bar.get_y() + bar.get_height() / 2
        if v >= 0:
            ax.text(v + offset, y, fr_num(v), va="center", ha="left",
                     fontsize=9.5, fontweight="bold", color=COLOR_POS)
        else:
            ax.text(v - offset, y, fr_num(v), va="center", ha="right",
                     fontsize=9.5, fontweight="bold", color=COLOR_NEG)

    xmin, xmax = ax.get_xlim()
    pad = (xmax - xmin) * 0.14
    ax.set_xlim(xmin - pad, xmax + pad)

    legend_elems = [
        Patch(facecolor=COLOR_POS, label="Effet positif — augmente la probabilité"),
        Patch(facecolor=COLOR_NEG, label="Effet négatif — diminue la probabilité"),
    ]
# On déplace la légende en dessous, centrée, et sur 2 colonnes
    ax.legend(
        handles=legend_elems, 
        loc="upper center", 
        bbox_to_anchor=(0.5, -0.15), 
        ncol=2, 
        frameon=False, 
        fontsize=9.5
    )

# On augmente "bottom" (ex: 0.22 au lieu de 0.16) pour laisser la place à la légende
    fig.subplots_adjust(bottom=0.22, top=0.86, left=0.30, right=0.96)
    fig.text(0.02, 0.02, note, fontsize=8, color="#8a8a8a", ha="left")

    plt.savefig(filename, dpi=200, facecolor="white")
    plt.close()
    print(f"OK -> {filename}  ({n} variables)")


# ----------------------------------------------------------------------
# 3. Génération des deux graphiques
# ----------------------------------------------------------------------
make_barplot(
    df_region,
    "Effet des cours d'appel sur la probabilité d'obtention",
    "Écart de probabilité par rapport à la cour d'appel de référence (variable catégorielle)",
    "test/barplot_1_regions_cours_appel.png",
    "Note : effets marginaux (points de %) issus d'un modèle logistique. Les 6 cours affichées sont statistiquement significatives (p < 0,05).",
)

make_barplot(
    df_other,
    "Effet des autres variables sur la probabilité d'obtention",
    "Caractéristiques des faits et des parties (hors variables géographiques)",
    "test/barplot_2_autres_variables.png",
    "Note : effets marginaux (points de %) issus d'un modèle logistique. Les 12 variables affichées sont statistiquement significatives (p < 0,05).",
)

print("\nTerminé.")