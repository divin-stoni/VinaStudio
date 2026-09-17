"""
statistics_pipeline.py

Chef d'orchestre des analyses statistiques STONI.

Détermine automatiquement :
- mode GLOBAL (CSV sans groupe)
- mode GROUPES (CSV avec colonne groupe)

Le moteur scientifique reste dans stats_engine.py.
"""

import pandas as pd

from . import stats_engine as se


def _infer_affinity_columns(df):
    if "dg_mexb" in df.columns and "dg_mexr" in df.columns:
        return "dg_mexb", "dg_mexr"
    candidates = [
        column for column in df.columns
        if str(column).startswith("dg_")
        and column not in {"dg_pump", "dg_repressor"}
    ]
    if "dg_pump" in df.columns and "dg_repressor" in df.columns:
        return "dg_pump", "dg_repressor"
    if len(candidates) >= 2:
        return candidates[0], candidates[1]
    raise ValueError(
        "Le CSV doit contenir deux colonnes d'affinité ΔG pour "
        "l'analyse à double sélectivité."
    )


def run_statistics_pipeline(df):
    """
    Lance les analyses adaptées au type de données.

    Retourne :
    {
        "mode": GLOBAL/GROUPES,
        "correlations": ...,
        "si": ...,
        "bootstrap": ...,
        ...
    }
    """

    results = {}
    x_col, y_col = _infer_affinity_columns(df)
    results["affinity_columns"] = {"pump": x_col, "repressor": y_col}

    # -------------------------------------------------
    # Détection du mode
    # -------------------------------------------------

    mode = se.detect_analysis_mode(df)

    results["mode"] = mode


    # -------------------------------------------------
    # Analyse commune GLOBAL
    # -------------------------------------------------

    results["correlations"] = se.correlations_by_group(
        df, x_col=x_col, y_col=y_col
    )

    results["si"] = se.compute_si_and_classification(
        df, x_col=x_col, y_col=y_col
    )
    results["permutation"] = se.permutation_test_by_group(
        df, x_col=x_col, y_col=y_col
    )


    # -------------------------------------------------
    # Analyses supplémentaires uniquement GROUPES
    # -------------------------------------------------

    if mode == "GROUPES":

        results["bootstrap"] = se.bootstrap_ci_by_group(
            df, x_col=x_col, y_col=y_col
        )

        results["leave_one_out"] = se.leave_one_out(
            df, x_col=x_col, y_col=y_col
        )

        results["partial_correlation"] = se.partial_correlation(
            df, x_col=x_col, y_col=y_col
        )[0]

        model, coef = se.multiple_regression(
            df, y_col=y_col, predictors=(x_col, "MW", "LogP")
        )

        results["regression_model"] = model

        results["regression_table"] = coef


        results["slope_test"] = se.homogeneity_of_slopes(
            df, x_col=x_col, y_col=y_col
        )


    else:

        results["bootstrap"] = None
        results["leave_one_out"] = None
        results["partial_correlation"] = None
        results["regression_model"] = None
        results["regression_table"] = None
        results["slope_test"] = None


    return results



def run_statistics_file(path):

    """
    Version pratique :
    prend directement un CSV.
    """

    df = pd.read_csv(path)

    return run_statistics_pipeline(df)
