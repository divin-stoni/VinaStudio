"""
scientific_fusion.py

Conversion des résultats de docking MexB/MexR
vers des fichiers scientifiques exploitables
par le moteur statistique.

Entrée :
    docking_results_MexB_MexR.csv

Sorties :
    reference_data/scores_fusionnes.csv
    reference_data/scores_fusionnes_global.csv
"""

from pathlib import Path
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

from src.column_matcher import apply_column_mapping


def _target_slug(name: str) -> str:
    return "".join(
        char.lower() if char.isalnum() else "_"
        for char in str(name)
    ).strip("_")


def _find_affinity_columns(df, pair_roles=None):
    columns = list(df.columns)
    if "dg_mexb" in columns and "dg_mexr" in columns:
        return "dg_mexb", "dg_mexr", "MexB", "MexR"

    role_names = pair_roles or {}
    pump_name = role_names.get("pump")
    repressor_name = role_names.get("repressor")

    def candidates_for(target):
        slug = _target_slug(target)
        return [
            column for column in columns
            if _target_slug(column).endswith(slug)
            and any(token in _target_slug(column) for token in (
                "bestaffinity", "affinity", "dg", "delta",
            ))
        ]

    if pump_name and repressor_name:
        pump = candidates_for(pump_name)
        repressor = candidates_for(repressor_name)
        if pump and repressor:
            return pump[0], repressor[0], pump_name, repressor_name

    discovered = [
        column for column in columns
        if any(token in _target_slug(column) for token in (
            "bestaffinity", "affinity", "dg", "delta",
        ))
        and not _target_slug(column).startswith(("status", "duration"))
    ]
    if len(discovered) >= 2:
        return discovered[0], discovered[1], discovered[0], discovered[1]

    raise ValueError(
        "Deux colonnes d'affinité de cibles sont nécessaires pour "
        "l'analyse à double sélectivité."
    )


def detect_groups(df, group_col="groupe"):
    """
    Détection des vrais groupes.
    Un groupe vide n'est pas considéré.
    """

    if group_col not in df.columns:
        return False

    values = (
        df[group_col]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values != ""
    ]

    return len(values.unique()) > 0


def create_scientific_scores(
    input_csv,
    output_dir=None,
    pair_roles=None,
):

    input_csv = Path(input_csv)
    output_dir = (
        input_csv.parent / "scientific_analysis"
        if output_dir is None
        else Path(output_dir)
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    df = pd.read_csv(
        input_csv
    )

    # --------------------------------------------------
    # NORMALISATION AUTOMATIQUE DES COLONNES SCIENTIFIQUES
    # --------------------------------------------------

    df = apply_column_mapping(df, verbose=True, required=["molecule"])
    pump_col, repressor_col, pump_name, repressor_name = _find_affinity_columns(
        df, pair_roles=pair_roles
    )


    out = pd.DataFrame()

    out["molecule"] = (
        df["molecule"]
        .astype(str)
    )

    if detect_groups(df):

        out["groupe"] = (
            df["groupe"]
            .fillna("SANS_GROUPE")
            .astype(str)
            .str.strip()
        )

        out.loc[
            out["groupe"] == "",
            "groupe"
        ] = "SANS_GROUPE"

    else:

        out["groupe"] = "SANS_GROUPE"


    pump_output_col = "dg_mexb" if pump_name == "MexB" else "dg_pump"
    repressor_output_col = "dg_mexr" if repressor_name == "MexR" else "dg_repressor"
    out[pump_output_col] = (
        pd.to_numeric(
            df[pump_col],
            errors="coerce"
        )
    )

    out[repressor_output_col] = (
        pd.to_numeric(
            df[repressor_col],
            errors="coerce"
        )
    )


    out["indice_selectivite"] = (
        out[repressor_output_col]
        -
        out[pump_output_col]
    )


    out = out.dropna(
        subset=[
            pump_output_col,
            repressor_output_col,
        ]
    )


    # -------------------------
    # fichier avec groupes
    # -------------------------

    grouped_csv = (
        output_dir /
        "scores_fusionnes.csv"
    )

    out.to_csv(
        grouped_csv,
        index=False
    )


    # -------------------------
    # fichier global
    # -------------------------

    global_out = out[
        [
            "molecule",
            pump_output_col,
            repressor_output_col,
            "indice_selectivite"
        ]
    ]


    global_csv = (
        output_dir /
        "scores_fusionnes_global.csv"
    )


    global_out.to_csv(
        global_csv,
        index=False
    )


    return grouped_csv, global_csv



if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print(
            "Usage : python scientific_fusion.py fichier.csv"
        )
        raise SystemExit(1)


    grouped, global_csv = create_scientific_scores(
        sys.argv[1]
    )


    print()
    print("Créé :")
    print(grouped)
    print(global_csv)
