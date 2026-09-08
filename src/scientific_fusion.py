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
    output_dir="reference_data"
):

    input_csv = Path(input_csv)
    output_dir = Path(output_dir)

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

    df = apply_column_mapping(
        df,
        verbose=True
    )

    required = [
        "molecule",
        "dg_mexb",
        "dg_mexr",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {missing}"
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


    out["dg_mexb"] = (
        pd.to_numeric(
            df["dg_mexb"],
            errors="coerce"
        )
    )

    out["dg_mexr"] = (
        pd.to_numeric(
            df["dg_mexr"],
            errors="coerce"
        )
    )


    out["indice_selectivite"] = (
        out["dg_mexr"]
        -
        out["dg_mexb"]
    )


    out = out.dropna(
        subset=[
            "dg_mexb",
            "dg_mexr"
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
            "dg_mexb",
            "dg_mexr",
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
