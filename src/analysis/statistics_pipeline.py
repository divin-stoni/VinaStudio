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
    permutation_test_by_group,
)


def _infer_affinity_columns(df):
    if "dg_mexb" in df.columns and "dg_mexr" in df.columns:
        return "dg_mexb", "dg_mexr"
    if "dg_pump" in df.columns and "dg_repressor" in df.columns:
        return "dg_pump", "dg_repressor"
    candidates = [column for column in df.columns if str(column).startswith("dg_")]
    if len(candidates) >= 2:
        return candidates[0], candidates[1]
    raise ValueError(
        "Le CSV doit contenir deux colonnes d'affinité ΔG pour l'analyse."
    )


def _receptor_labels(csv_path, x_col, y_col):
    """Noms des deux recepteurs : fichier meta de la fusion, sinon defauts."""
    labels = {"x": None, "y": None}
    try:
        import json

        meta_path = Path(csv_path).parent / "scores_fusionnes_meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pump = meta.get("pump") or {}
            repressor = meta.get("repressor") or {}
            # Le fichier meta ne sert que s'il decrit bien ces colonnes.
            if pump.get("column") == x_col and repressor.get("column") == y_col:
                labels["x"] = pump.get("label")
                labels["y"] = repressor.get("label")
    except Exception:
        pass
    defaults = {
        "dg_mexb": "MexB",
        "dg_mexr": "MexR",
        "dg_pump": "Pompe",
        "dg_repressor": "Répresseur",
    }
    labels["x"] = labels["x"] or defaults.get(x_col, str(x_col))
    labels["y"] = labels["y"] or defaults.get(y_col, str(y_col))
    return labels


def run_statistics_pipeline(csv_path):

    csv_path = Path(csv_path)

    df = pd.read_csv(csv_path)

    df, mode = prepare_analysis_groups(
        df
    )
    x_col, y_col = _infer_affinity_columns(df)


    result = {
        "file": str(csv_path),
        "mode": mode,
        "data": df,
        "affinity_columns": {"pump": x_col, "repressor": y_col},
    }


    # --------------------------------------------------
    # Analyses communes
    # --------------------------------------------------

    result["classification"] = (
        compute_si_and_classification(df, x_col=x_col, y_col=y_col)
    )

    # patch-libelles : noms des recepteurs (fusion -> meta -> pipeline -> figures)
    result["labels"] = _receptor_labels(csv_path, x_col, y_col)
    for _frame in (result["classification"], df):
        _frame.attrs["x_label"] = result["labels"]["x"]
        _frame.attrs["y_label"] = result["labels"]["y"]


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
        correlations_by_group(df, x_col=x_col, y_col=y_col)
    )


    result["bootstrap"] = (
        bootstrap_ci_by_group(df, x_col=x_col, y_col=y_col)
    )

    result["permutation"] = permutation_test_by_group(
        df, x_col=x_col, y_col=y_col
    )


    if mode == "GROUPES":

        result["leave_one_out"] = (
            leave_one_out(df, x_col=x_col, y_col=y_col)
        )

        result["homogeneity"] = (
            homogeneity_of_slopes(df, x_col=x_col, y_col=y_col)
        )


    else:

        result["leave_one_out"] = leave_one_out(df, x_col=x_col, y_col=y_col)  # patch-familles : LOO aussi en mode global
        result["homogeneity"] = None


    return result
