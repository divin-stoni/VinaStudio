"""
plotting.py
Génération des figures matplotlib reproduites de l'article :
scatter par famille, histogrammes SI, forest plot des corrélations,
graphique d'influence leave-one-out.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

PALETTE = {
    "ANTIDEPRESSEUR": "#4C72B0",
    "ANTIPSYCHOTIQUE": "#DD8452",
    "ANTIHISTAMINIQUE": "#55A868",
    "PHYTOMOLECULE": "#8172B2",
    "GLOBAL": "#444444",
}


def _color_for(g):
    return PALETTE.get(g, "#999999")


def fig_scatter_corr(df, x_col="dg_mexb", y_col="dg_mexr", group_col="groupe"):
    """Nuage de points ΔG(MexB) vs ΔG(MexR), couleur par famille,
    avec droites de régression par famille."""
    fig = Figure(figsize=(7, 5.5), dpi=110)
    ax = fig.add_subplot(111)
    for g in sorted(df[group_col].dropna().unique()):
        sub = df[df[group_col] == g]
        ax.scatter(sub[x_col], sub[y_col], s=28, alpha=0.75,
                   label=g, color=_color_for(g), edgecolor="white", linewidth=0.4)
        if len(sub) >= 3:
            z = np.polyfit(sub[x_col], sub[y_col], 1)
            xs = np.linspace(sub[x_col].min(), sub[x_col].max(), 50)
            ax.plot(xs, np.polyval(z, xs), color=_color_for(g), linewidth=1.4, alpha=0.85)
    ax.set_xlabel("ΔG(MexB) (kcal/mol)")
    ax.set_ylabel("ΔG(MexR) (kcal/mol)")
    ax.set_title("Corrélation ΔG(MexB) – ΔG(MexR) par famille")
    ax.legend(fontsize=8, loc="best")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def fig_histogram_si(df_classified, si_col="SI_calc", group_col="groupe"):
    fig = Figure(figsize=(7, 5), dpi=110)
    ax = fig.add_subplot(111)
    ax.hist(df_classified[si_col], bins=25, color="#4C72B0", edgecolor="white", alpha=0.9)
    seuil = df_classified.attrs.get("seuil_risque_absolu")
    ax.set_xlabel("Indice de sélectivité SI = ΔG(MexR) − ΔG(MexB)")
    ax.set_ylabel("Nombre de composés")
    ax.set_title("Distribution de l'indice de sélectivité (SI)")
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    return fig


def fig_histogram_si_by_group(df_classified, si_col="SI_calc", group_col="groupe"):
    groups = sorted(df_classified[group_col].dropna().unique())
    n = len(groups)
    fig = Figure(figsize=(9, 2.6 * ((n + 1) // 2)), dpi=110)
    for i, g in enumerate(groups, start=1):
        ax = fig.add_subplot((n + 1) // 2, 2, i)
        sub = df_classified[df_classified[group_col] == g]
        ax.hist(sub[si_col], bins=15, color=_color_for(g), edgecolor="white", alpha=0.9)
        ax.set_title(g, fontsize=9)
        ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    return fig


def fig_forest_correlations(corr_df, boot_df):
    """
    Forest plot robuste aux données insuffisantes.

    Si les DataFrames statistiques sont vides ou ne possèdent pas
    les colonnes nécessaires, un panneau informatif est affiché
    au lieu de provoquer une erreur.
    """

    required_corr = {
        "groupe",
        "r_pearson",
    }

    required_boot = {
        "groupe",
        "IC_low",
        "IC_high",
    }

    invalid_input = (
        corr_df is None
        or boot_df is None
        or corr_df.empty
        or boot_df.empty
        or not required_corr.issubset(
            set(corr_df.columns)
        )
        or not required_boot.issubset(
            set(boot_df.columns)
        )
    )

    if invalid_input:
        fig = Figure(
            figsize=(7.0, 3.0),
            dpi=110,
        )

        ax = fig.add_subplot(111)

        message = (
            "Données insuffisantes pour calculer\n"
            "les corrélations et leurs IC bootstrap.\n\n"
            "Au moins 3 molécules sont nécessaires."
        )

        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
        )

        ax.set_axis_off()

        fig.tight_layout()

        return fig

    merged = corr_df.merge(
        boot_df,
        on="groupe",
        how="inner",
    )

    if merged.empty:
        fig = Figure(
            figsize=(7.0, 3.0),
            dpi=110,
        )

        ax = fig.add_subplot(111)

        ax.text(
            0.5,
            0.5,
            "Aucune corrélation exploitable après fusion.",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
        )

        ax.set_axis_off()

        fig.tight_layout()

        return fig

    merged = merged.sort_values(
        "r_pearson"
    )

    fig = Figure(
        figsize=(
            6.5,
            0.6 * len(merged) + 1.5,
        ),
        dpi=110,
    )

    ax = fig.add_subplot(111)

    y_pos = np.arange(
        len(merged)
    )

    lower_error = (
        merged["r_pearson"]
        - merged["IC_low"]
    )

    upper_error = (
        merged["IC_high"]
        - merged["r_pearson"]
    )

    ax.errorbar(
        merged["r_pearson"],
        y_pos,
        xerr=[
            lower_error,
            upper_error,
        ],
        fmt="o",
        color="#4C72B0",
        ecolor="#4C72B0",
        capsize=4,
    )

    ax.set_yticks(
        y_pos
    )

    ax.set_yticklabels(
        merged["groupe"]
    )

    ax.axvline(
        0,
        color="grey",
        linewidth=0.8,
        linestyle="--",
    )

    ax.set_xlabel(
        "Coefficient de corrélation de Pearson (r) [IC 95%]"
    )

    ax.set_title(
        "Robustesse des corrélations par famille (bootstrap)"
    )

    ax.grid(
        alpha=0.25,
        axis="x",
    )

    fig.tight_layout()

    return fig

def fig_percentile_scatter(df_classified, si_col="SI_calc", pct_col="percentile_SI",
                            status_col="statut_risque", name_col="molecule"):
    fig = Figure(figsize=(7.5, 5.5), dpi=110)
    ax = fig.add_subplot(111)
    colors = df_classified[status_col].map(
        {"Favorable": "#55A868", "À risque (dérépression possible)": "#C44E52"})
    ax.scatter(df_classified[pct_col], df_classified[si_col], c=colors, s=26,
               alpha=0.8, edgecolor="white", linewidth=0.4)
    ax.set_xlabel("Percentile SI")
    ax.set_ylabel("Indice de sélectivité (SI)")
    ax.set_title("Classement percentile et statut de risque")
    ax.grid(alpha=0.25)
    from matplotlib.patches import Patch
    handles = [Patch(color="#55A868", label="Favorable"),
               Patch(color="#C44E52", label="À risque")]
    ax.legend(handles=handles, fontsize=8)
    fig.tight_layout()
    return fig


def fig_loo_influence(loo_df):
    fig = Figure(figsize=(6.5, 4.0), dpi=110)
    ax = fig.add_subplot(111)

    # --------------------------------------------------------------
    # Cas sans données suffisantes
    # --------------------------------------------------------------
    if loo_df is None or loo_df.empty:
        ax.text(
            0.5,
            0.5,
            "Données insuffisantes pour calculer\n"
            "l'analyse leave-one-out.",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
        )

        ax.set_title(
            "Sensibilité de la corrélation au composé le plus influent"
        )

        ax.set_xticks([])
        ax.set_yticks([])

        fig.tight_layout()
        return fig

    # --------------------------------------------------------------
    # Vérification des colonnes attendues
    # --------------------------------------------------------------
    required = {"delta_r_max", "groupe"}

    if not required.issubset(set(loo_df.columns)):
        ax.text(
            0.5,
            0.5,
            "Données leave-one-out\n"
            "non disponibles.",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
        )

        ax.set_title(
            "Sensibilité de la corrélation au composé le plus influent"
        )

        ax.set_xticks([])
        ax.set_yticks([])

        fig.tight_layout()
        return fig

    # --------------------------------------------------------------
    # Cas normal
    # --------------------------------------------------------------
    y_pos = np.arange(len(loo_df))

    ax.barh(
        y_pos,
        loo_df["delta_r_max"],
        color="#DD8452",
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(loo_df["groupe"])
    ax.axvline(
        0,
        color="grey",
        linewidth=0.8,
    )

    ax.set_xlabel(
        "Δr maximal (retrait d'un composé, leave-one-out)"
    )

    ax.set_title(
        "Sensibilité de la corrélation au composé le plus influent"
    )

    ax.grid(
        alpha=0.25,
        axis="x",
    )

    fig.tight_layout()
    return fig


def fig_prediction_mode2(df_pred, x_col="dg_mexb", y_pred_col="dg_mexr_predit",
                          y_lo_col="dg_mexr_IC95_bas", y_hi_col="dg_mexr_IC95_haut"):
    fig = Figure(figsize=(7, 5.5), dpi=110)
    ax = fig.add_subplot(111)
    order = df_pred[x_col].argsort()
    x_sorted = df_pred[x_col].values[order]
    y_sorted = df_pred[y_pred_col].values[order]
    lo_sorted = df_pred[y_lo_col].values[order]
    hi_sorted = df_pred[y_hi_col].values[order]
    ax.fill_between(x_sorted, lo_sorted, hi_sorted, color="#4C72B0", alpha=0.15,
                     label="IC 95% de prédiction")
    ax.scatter(df_pred[x_col], df_pred[y_pred_col], color="#4C72B0", s=30,
               edgecolor="white", linewidth=0.5, label="ΔG(MexR) prédit")
    ax.set_xlabel("ΔG(MexB) (kcal/mol) — observé")
    ax.set_ylabel("ΔG(MexR) (kcal/mol) — prédit")
    ax.set_title("Prédiction ΔG(MexR) à partir de ΔG(MexB) seul")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


# ================================================================
# CARTE 2D DES INTERACTIONS LIGAND–RÉCEPTEUR
# ================================================================

def make_interaction_2d_figure(interactions):
    """
    Génère une carte 2D schématique des interactions.

    Le ligand est placé au centre.
    Les résidus interactifs sont disposés autour.
    La position radiale est proportionnelle à la distance minimale.

    Cette représentation est une carte structurale simplifiée,
    et non une projection 2D exacte de la structure chimique du ligand.
    """

    import math

    figure = Figure(
        figsize=(8.5, 5.5)
    )

    ax = figure.add_subplot(111)

    ax.set_title(
        "Carte 2D des interactions ligand–MexB"
    )

    ax.set_xlabel(
        "Interaction spatiale — représentation schématique"
    )

    ax.set_ylabel(
        "Résidus du récepteur"
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    # ------------------------------------------------------------
    # Cas sans interactions
    # ------------------------------------------------------------

    if not interactions:
        ax.text(
            0.5,
            0.5,
            "Aucune interaction disponible",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

        ax.set_xticks([])
        ax.set_yticks([])

        figure.tight_layout()

        return figure

    # ------------------------------------------------------------
    # Ligand central
    # ------------------------------------------------------------

    ax.scatter(
        [0],
        [0],
        s=900,
        marker="o",
        zorder=5,
    )

    ax.text(
        0,
        0,
        "LIGAND",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        zorder=6,
    )

    # ------------------------------------------------------------
    # Résidus
    # ------------------------------------------------------------

    n = len(interactions)

    max_distance = max(
        float(
            item.get(
                "min_distance",
                1.0,
            )
        )
        for item in interactions
    )

    max_distance = max(
        max_distance,
        1.0,
    )

    radius_base = 2.4

    for index, item in enumerate(
        interactions,
        start=0,
    ):

        distance = float(
            item.get(
                "min_distance",
                0.0,
            )
        )

        angle = (
            2.0
            * math.pi
            * index
            / max(n, 1)
        )

        radius = (
            radius_base
            * (0.75 + 0.55 * distance / max_distance)
        )

        x = (
            radius
            * math.cos(angle)
        )

        y = (
            radius
            * math.sin(angle)
        )

        # --------------------------------------------------------
        # Liaison schématique
        # --------------------------------------------------------

        ax.plot(
            [0, x],
            [0, y],
            linewidth=1.2,
            zorder=1,
        )

        # --------------------------------------------------------
        # Résidu
        # --------------------------------------------------------

        ax.scatter(
            [x],
            [y],
            s=500,
            marker="s",
            zorder=4,
        )

        residue = str(
            item.get(
                "residue",
                "",
            )
        )

        residue_id = str(
            item.get(
                "residue_id",
                "",
            )
        )

        chain = str(
            item.get(
                "chain",
                "",
            )
        )

        interaction_type = str(
            item.get(
                "interaction_types",
                "",
            )
        )

        label = (
            f"{residue} {residue_id}"
            f"\n"
            f"{distance:.2f} Å"
        )

        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=8,
            zorder=6,
        )

        # --------------------------------------------------------
        # Type de l'interaction
        # --------------------------------------------------------

        type_label = (
            interaction_type
            .replace(
                "; ",
                " / ",
            )
        )

        label_x = (
            x * 0.58
        )

        label_y = (
            y * 0.58
        )

        ax.text(
            label_x,
            label_y,
            type_label,
            ha="center",
            va="center",
            fontsize=7,
            bbox=dict(
                alpha=0.75,
                pad=2,
            ),
        )

    # ------------------------------------------------------------
    # Légende descriptive
    # ------------------------------------------------------------

    ax.text(
        0.02,
        0.02,
        (
            "Représentation schématique\n"
            "Distance = distance minimale calculée\n"
            "Résidus = contacts détectés par l'analyse géométrique"
        ),
        transform=ax.transAxes,
        fontsize=7,
        va="bottom",
        ha="left",
    )

    limit = (
        radius_base
        * 1.45
    )

    ax.set_xlim(
        -limit,
        limit,
    )

    ax.set_ylim(
        -limit,
        limit,
    )

    ax.set_xticks([])
    ax.set_yticks([])

    figure.tight_layout()

    return figure
