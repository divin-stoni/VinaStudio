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

    # -------------------------------------------------
    # Détection du mode
    # -------------------------------------------------

    mode = se.detect_analysis_mode(df)

    results["mode"] = mode


    # -------------------------------------------------
    # Analyse commune GLOBAL
    # -------------------------------------------------

    results["correlations"] = se.correlations_by_group(df)

    results["si"] = se.compute_si_and_classification(df)


    # -------------------------------------------------
    # Analyses supplémentaires uniquement GROUPES
    # -------------------------------------------------

    if mode == "GROUPES":

        results["bootstrap"] = se.bootstrap_ci_by_group(df)

        results["leave_one_out"] = se.leave_one_out(df)

        results["partial_correlation"] = se.partial_correlation(df)[0]

        model, coef = se.multiple_regression(df)

        results["regression_model"] = model

        results["regression_table"] = coef


        results["slope_test"] = se.homogeneity_of_slopes(df)


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
