# -*- coding: utf-8 -*-

"""
Fusion des résultats docking MexB + MexR.
"""

from pathlib import Path
import pandas as pd


def fuse_docking_results(
    mexb_csv,
    mexr_csv,
    output_csv
):

    mexb = pd.read_csv(mexb_csv)
    mexr = pd.read_csv(mexr_csv)


    mexb = mexb[
        [
            "molecule",
            "ligand_file",
            "groupe",
            "best_affinity",
        ]
    ].rename(
        columns={
            "best_affinity":
            "best_affinity_mexb"
        }
    )


    mexr = mexr[
        [
            "molecule",
            "best_affinity",
        ]
    ].rename(
        columns={
            "best_affinity":
            "best_affinity_mexr"
        }
    )


    merged = pd.merge(
        mexb,
        mexr,
        on="molecule",
        how="outer"
    )


    Path(output_csv).parent.mkdir(
        parents=True,
        exist_ok=True
    )


    merged.to_csv(
        output_csv,
        index=False
    )


    return output_csv



if __name__ == "__main__":

    out = fuse_docking_results(
        "docking/results/batch_vina_engine/MexB/docking_results.csv",
        "docking/results/batch_vina_engine/MexR/docking_results.csv",
        "docking/results/batch_vina_engine/docking_results_MexB_MexR.csv"
    )

    print(out)
