# -*- coding: utf-8 -*-

"""
Pipeline statistique automatique.

Détecte automatiquement :
- analyse par groupes ;
- analyse globale.

Ne contient aucune statistique :
il orchestre uniquement stats_engine.py.
"""

from pathlib import Path
import pandas as pd


from src.stats_engine import (
    detect_analysis_mode,
    prepare_analysis_groups,
    correlations_by_group,
    bootstrap_ci_by_group,
    leave_one_out,
    homogeneity_of_slopes,
    compute_si_and_classification,
    dual_filter,
    top_candidates,
)


def run_statistics_pipeline(csv_path):

    csv_path = Path(csv_path)

    df = pd.read_csv(csv_path)

    df, mode = prepare_analysis_groups(
        df
    )


    result = {
        "file": str(csv_path),
        "mode": mode,
        "data": df,
    }


    # --------------------------------------------------
    # Analyses communes
    # --------------------------------------------------

    result["classification"] = (
        compute_si_and_classification(df)
    )


    result["top_candidates"] = (
        top_candidates(
            result["classification"]
        )
    )


    dual_valides, dual_exclus = dual_filter(
        result["classification"]
    )

    result["dual_filter"] = {
        "candidates": dual_valides,
        "excluded_absolute": dual_exclus,
        "threshold_percentile": 50.0,
        "threshold_mexr": -8.289,
    }


    # --------------------------------------------------
    # Analyses dépendantes du mode
    # --------------------------------------------------

    result["correlations"] = (
        correlations_by_group(df)
    )


    result["bootstrap"] = (
        bootstrap_ci_by_group(df)
    )


    if mode == "GROUPES":

        result["leave_one_out"] = (
            leave_one_out(df)
        )

        result["homogeneity"] = (
            homogeneity_of_slopes(df)
        )


    else:

        result["leave_one_out"] = None
        result["homogeneity"] = None


    return result
