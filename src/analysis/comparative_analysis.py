# -*- coding: utf-8 -*-

"""
comparative_analysis.py

Comparaison des empreintes d'interaction des hits de docking.

Entrées :
    docking/results/batch_vina_engine/interaction_analysis/*_interactions.csv

Sorties :
    - résidus communs aux 3 hits ;
    - résidus communs à 2 hits ;
    - résidus spécifiques ;
    - tableau comparatif CSV.

Aucune dépendance externe.
"""

from __future__ import annotations

from pathlib import Path
import csv


# ================================================================
# CONFIGURATION
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "docking/results/batch_vina_engine/"
      "interaction_analysis"
)

OUTPUT_DIR = INPUT_DIR / "comparative"


# ================================================================
# LECTURE
# ================================================================

def load_interactions(
    path: Path,
) -> dict:

    interactions = {}

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:

            key = (
                row["residue"],
                row["residue_id"],
                row["chain"],
            )

            distance = float(
                row["min_distance"]
            )

            interactions[key] = {
                "residue": row["residue"],
                "residue_id": row["residue_id"],
                "chain": row["chain"],
                "min_distance": distance,
                "n_contacts": int(
                    row["n_contacts"]
                ),
                "interaction_types": (
                    row["interaction_types"]
                ),
            }

    return interactions


# ================================================================
# DÉCOUVERTE DES HITS
# ================================================================

def discover_files() -> dict:

    files = sorted(
        INPUT_DIR.glob(
            "*_interactions.csv"
        )
    )

    hits = {}

    for path in files:

        name = path.name.replace(
            "_interactions.csv",
            "",
        )

        hits[name] = path

    return hits


# ================================================================
# COMPARAISON
# ================================================================

def compare(
    datasets: dict,
) -> dict:

    names = list(datasets.keys())

    residue_sets = {
        name: set(
            datasets[name].keys()
        )
        for name in names
    }

    all_residues = set().union(
        *residue_sets.values()
    )

    common_all = set.intersection(
        *residue_sets.values()
    )

    common_two = set()

    for residue in all_residues:

        count = sum(
            residue in residue_sets[name]
            for name in names
        )

        if count == 2:
            common_two.add(residue)

    specific = {}

    for name in names:

        others = set().union(
            *[
                residue_sets[other]
                for other in names
                if other != name
            ]
        )

        specific[name] = (
            residue_sets[name] - others
        )

    return {
        "names": names,
        "sets": residue_sets,
        "all_residues": all_residues,
        "common_all": common_all,
        "common_two": common_two,
        "specific": specific,
    }


# ================================================================
# FORMATAGE
# ================================================================

def residue_label(
    residue,
) -> str:

    res, number, chain = residue

    return (
        f"{res}{number}"
        f"({chain})"
    )


# ================================================================
# EXPORT RÉSIDUS COMMUNS
# ================================================================

def export_common(
    comparison: dict,
) -> Path:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        OUTPUT_DIR
        / "common_residues.csv"
    )

    names = comparison["names"]

    fieldnames = [
        "residue",
        *names,
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.writer(
            handle
        )

        writer.writerow(
            fieldnames
        )

        for residue in sorted(
            comparison["all_residues"],
            key=lambda x: (
                x[2],
                int(x[1])
                if x[1].isdigit()
                else 99999,
            ),
        ):

            row = [
                residue_label(residue)
            ]

            for name in names:

                data = comparison[
                    "sets"
                ][name]

                row.append(
                    "YES"
                    if residue in data
                    else "NO"
                )

            writer.writerow(row)

    return path


# ================================================================
# EXPORT DÉTAILLÉ
# ================================================================

def export_detailed(
    datasets: dict,
) -> Path:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        OUTPUT_DIR
        / "comparative_interactions.csv"
    )

    names = list(datasets.keys())

    fieldnames = [
        "residue",
        "residue_id",
        "chain",
    ]

    for name in names:

        fieldnames.extend(
            [
                f"{name}_present",
                f"{name}_distance",
                f"{name}_contacts",
                f"{name}_interaction_types",
            ]
        )

    all_residues = set().union(
        *[
            set(data.keys())
            for data in datasets.values()
        ]
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for residue in sorted(
            all_residues,
            key=lambda x: (
                x[2],
                int(x[1])
                if x[1].isdigit()
                else 99999,
            ),
        ):

            row = {
                "residue": residue[0],
                "residue_id": residue[1],
                "chain": residue[2],
            }

            for name in names:

                data = datasets[name].get(
                    residue
                )

                prefix = f"{name}_"

                if data:

                    row[
                        prefix + "present"
                    ] = "YES"

                    row[
                        prefix + "distance"
                    ] = f"{data['min_distance']:.3f}"

                    row[
                        prefix + "contacts"
                    ] = data["n_contacts"]

                    row[
                        prefix + "interaction_types"
                    ] = data[
                        "interaction_types"
                    ]

                else:

                    row[
                        prefix + "present"
                    ] = "NO"

                    row[
                        prefix + "distance"
                    ] = ""

                    row[
                        prefix + "contacts"
                    ] = ""

                    row[
                        prefix + "interaction_types"
                    ] = ""

            writer.writerow(row)

    return path


# ================================================================
# RAPPORT
# ================================================================

def print_report(
    comparison: dict,
) -> None:

    names = comparison["names"]

    print()
    print("=" * 70)
    print("ANALYSE COMPARATIVE DES INTERACTIONS")
    print("=" * 70)

    print()
    print("HITS ANALYSÉS")
    print("-" * 70)

    for name in names:

        count = len(
            comparison["sets"][name]
        )

        print(
            f"- {name} : "
            f"{count} résidus"
        )

    # ------------------------------------------------------------
    # COMMUNS AUX 3
    # ------------------------------------------------------------

    common_all = comparison[
        "common_all"
    ]

    print()
    print(
        "RÉSIDUS COMMUNS AUX 3 HITS"
    )

    print("-" * 70)

    if common_all:

        for residue in sorted(
            common_all,
            key=lambda x: (
                int(x[1])
                if x[1].isdigit()
                else 99999
            ),
        ):

            print(
                f"  {residue_label(residue)}"
            )

        print(
            f"\nNombre : "
            f"{len(common_all)}"
        )

    else:

        print(
            "Aucun résidu commun aux 3 hits."
        )

    # ------------------------------------------------------------
    # COMMUNS À 2
    # ------------------------------------------------------------

    common_two = comparison[
        "common_two"
    ]

    print()
    print(
        "RÉSIDUS COMMUNS À EXACTEMENT 2 HITS"
    )

    print("-" * 70)

    if common_two:

        for residue in sorted(
            common_two,
            key=lambda x: (
                int(x[1])
                if x[1].isdigit()
                else 99999
            ),
        ):

            present_in = [
                name
                for name in names
                if residue
                in comparison["sets"][name]
            ]

            print(
                f"  {residue_label(residue)}"
                f" → {', '.join(present_in)}"
            )

    else:

        print(
            "Aucun résidu commun à exactement 2 hits."
        )

    # ------------------------------------------------------------
    # SPÉCIFIQUES
    # ------------------------------------------------------------

    print()
    print(
        "RÉSIDUS SPÉCIFIQUES"
    )

    print("-" * 70)

    for name in names:

        specific = comparison[
            "specific"
        ][name]

        print()
        print(
            f"{name}"
        )

        if specific:

            labels = [
                residue_label(r)
                for r in sorted(
                    specific,
                    key=lambda x: (
                        int(x[1])
                        if x[1].isdigit()
                        else 99999
                    ),
                )
            ]

            print(
                "  "
                + ", ".join(labels)
            )

            print(
                f"  Nombre : "
                f"{len(specific)}"
            )

        else:

            print(
                "  Aucun résidu spécifique."
            )


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 70)
    print("COMPARATIVE ANALYSIS — TEST")
    print("=" * 70)

    print()
    print(
        f"Dossier : {INPUT_DIR}"
    )

    if not INPUT_DIR.exists():

        print(
            "[ERREUR] Dossier d'analyse introuvable."
        )

        return 1

    files = discover_files()

    print(
        f"[OK] Fichiers détectés : "
        f"{len(files)}"
    )

    if not files:

        print(
            "[ERREUR] Aucun fichier *_interactions.csv."
        )

        return 1

    datasets = {}

    for name, path in files.items():

        try:

            datasets[name] = (
                load_interactions(path)
            )

            print(
                f"  - {name} : "
                f"{len(datasets[name])} résidus"
            )

        except Exception as exc:

            print(
                f"[ERREUR] {name} : {exc}"
            )

    if len(datasets) < 2:

        print(
            "[ERREUR] Au moins deux hits sont nécessaires."
        )

        return 1

    comparison = compare(
        datasets
    )

    print_report(
        comparison
    )

    # ------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------

    common_file = export_common(
        comparison
    )

    detailed_file = export_detailed(
        datasets
    )

    print()
    print(
        "[OK] Résidus communs exportés :"
    )

    print(
        f"     {common_file}"
    )

    print()
    print(
        "[OK] Analyse détaillée exportée :"
    )

    print(
        f"     {detailed_file}"
    )

    print()
    print("=" * 70)
    print("ANALYSE TERMINÉE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
