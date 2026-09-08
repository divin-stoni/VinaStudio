#!/usr/bin/env python3

import csv
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERACTION_FILE = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "interaction_analysis"
    / "Vilazodone_CID_6918314_interactions.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "analysis"
)

SUMMARY_JSON = OUTPUT_DIR / "Vilazodone_interaction_summary.json"
SUMMARY_CSV = OUTPUT_DIR / "Vilazodone_interaction_summary.csv"


def load_interactions(filename):

    interactions = []

    with open(
        filename,
        "r",
        encoding="utf-8",
        newline=""
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:

            try:
                row["residue_id"] = int(row["residue_id"])
                row["min_distance"] = float(
                    row["min_distance"]
                )
                row["n_contacts"] = int(
                    row["n_contacts"]
                )
            except (ValueError, TypeError):
                continue

            interactions.append(row)

    return interactions


def classify_interaction(interaction_type):

    text = interaction_type.lower()

    polar = (
        "polar" in text
        or "h-bond" in text
    )

    hydrophobic = (
        "hydrophobic" in text
    )

    close = (
        "close contact" in text
    )

    contact = (
        "contact" in text
    )

    return {
        "polar": polar,
        "hydrophobic": hydrophobic,
        "close_contact": close,
        "contact": contact
    }


def calculate_summary(interactions):

    distances = [
        row["min_distance"]
        for row in interactions
    ]

    contacts = [
        row["n_contacts"]
        for row in interactions
    ]

    polar_count = 0
    hydrophobic_count = 0
    close_count = 0
    contact_count = 0

    for row in interactions:

        classification = classify_interaction(
            row["interaction_types"]
        )

        if classification["polar"]:
            polar_count += 1

        if classification["hydrophobic"]:
            hydrophobic_count += 1

        if classification["close_contact"]:
            close_count += 1

        if classification["contact"]:
            contact_count += 1

    sorted_by_distance = sorted(
        interactions,
        key=lambda x: x["min_distance"]
    )

    sorted_by_contacts = sorted(
        interactions,
        key=lambda x: x["n_contacts"],
        reverse=True
    )

    closest_residues = []

    for row in sorted_by_distance[:10]:

        closest_residues.append({
            "residue": row["residue"],
            "residue_id": row["residue_id"],
            "chain": row["chain"],
            "distance_A": row["min_distance"],
            "n_contacts": row["n_contacts"],
            "interaction_types": row[
                "interaction_types"
            ]
        })

    strongest_contacts = []

    for row in sorted_by_contacts[:10]:

        strongest_contacts.append({
            "residue": row["residue"],
            "residue_id": row["residue_id"],
            "chain": row["chain"],
            "distance_A": row["min_distance"],
            "n_contacts": row["n_contacts"],
            "interaction_types": row[
                "interaction_types"
            ]
        })

    residue_counter = Counter(
        (
            row["residue"],
            row["residue_id"]
        )
        for row in interactions
    )

    recurrent_residues = []

    for (residue, residue_id), count in (
        residue_counter.most_common()
    ):

        recurrent_residues.append({
            "residue": residue,
            "residue_id": residue_id,
            "occurrences": count
        })

    return {
        "total_interactions": len(interactions),
        "polar_hbond_candidates": polar_count,
        "hydrophobic_interactions": hydrophobic_count,
        "close_contacts": close_count,
        "contacts": contact_count,
        "minimum_distance_A": min(distances)
        if distances else None,
        "maximum_distance_A": max(distances)
        if distances else None,
        "mean_distance_A": (
            sum(distances) / len(distances)
            if distances else None
        ),
        "total_atom_contacts": sum(contacts),
        "closest_residues": closest_residues,
        "strongest_contacts": strongest_contacts,
        "recurrent_residues": recurrent_residues
    }


def save_json(summary):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        SUMMARY_JSON,
        "w",
        encoding="utf-8"
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=4,
            ensure_ascii=False
        )


def save_csv(summary):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = [
        (
            "metric",
            "value"
        ),
        (
            "total_interactions",
            summary["total_interactions"]
        ),
        (
            "polar_hbond_candidates",
            summary["polar_hbond_candidates"]
        ),
        (
            "hydrophobic_interactions",
            summary["hydrophobic_interactions"]
        ),
        (
            "close_contacts",
            summary["close_contacts"]
        ),
        (
            "contacts",
            summary["contacts"]
        ),
        (
            "minimum_distance_A",
            summary["minimum_distance_A"]
        ),
        (
            "maximum_distance_A",
            summary["maximum_distance_A"]
        ),
        (
            "mean_distance_A",
            summary["mean_distance_A"]
        ),
        (
            "total_atom_contacts",
            summary["total_atom_contacts"]
        )
    ]

    with open(
        SUMMARY_CSV,
        "w",
        encoding="utf-8",
        newline=""
    ) as handle:

        writer = csv.writer(handle)

        writer.writerows(rows)


def print_summary(summary):

    print()
    print("RÉSUMÉ SCIENTIFIQUE")
    print("-" * 70)

    print(
        f"Interactions totales        : "
        f"{summary['total_interactions']}"
    )

    print(
        f"Polar / H-bond candidates   : "
        f"{summary['polar_hbond_candidates']}"
    )

    print(
        f"Interactions hydrophobes    : "
        f"{summary['hydrophobic_interactions']}"
    )

    print(
        f"Close contacts              : "
        f"{summary['close_contacts']}"
    )

    print(
        f"Contacts                    : "
        f"{summary['contacts']}"
    )

    print(
        f"Distance minimale           : "
        f"{summary['minimum_distance_A']:.2f} Å"
    )

    print(
        f"Distance maximale           : "
        f"{summary['maximum_distance_A']:.2f} Å"
    )

    print(
        f"Distance moyenne            : "
        f"{summary['mean_distance_A']:.2f} Å"
    )

    print(
        f"Contacts atomiques totaux   : "
        f"{summary['total_atom_contacts']}"
    )

    print()
    print("TOP 10 RÉSIDUS LES PLUS PROCHES")
    print("-" * 70)

    for index, residue in enumerate(
        summary["closest_residues"],
        start=1
    ):

        print(
            f"{index:02d}. "
            f"{residue['residue']} "
            f"{residue['residue_id']} "
            f"(chaîne {residue['chain']}) "
            f"— {residue['distance_A']:.2f} Å"
        )

    print()
    print("TOP 10 CONTACTS ATOMIQUES")
    print("-" * 70)

    for index, residue in enumerate(
        summary["strongest_contacts"],
        start=1
    ):

        print(
            f"{index:02d}. "
            f"{residue['residue']} "
            f"{residue['residue_id']} "
            f"— {residue['n_contacts']} contacts "
            f"— {residue['distance_A']:.2f} Å"
        )


def main():

    print("=" * 70)
    print("MEXAB/MEXR ANALYZER — INTERACTION SUMMARY")
    print("=" * 70)

    print()
    print("FICHIER D'ENTRÉE")
    print("-" * 70)

    print(
        f"Interactions : {INTERACTION_FILE}"
    )

    if not INTERACTION_FILE.exists():

        print()
        print(
            "[ERREUR] Fichier d'interactions introuvable."
        )

        return

    print()
    print("LECTURE")
    print("-" * 70)

    interactions = load_interactions(
        INTERACTION_FILE
    )

    print(
        f"[OK] {len(interactions)} interactions chargées."
    )

    if not interactions:

        print(
            "[ERREUR] Aucune interaction exploitable."
        )

        return

    print()
    print("ANALYSE")
    print("-" * 70)

    summary = calculate_summary(
        interactions
    )

    print(
        "[OK] Analyse des interactions terminée."
    )

    print_summary(summary)

    print()
    print("EXPORT")
    print("-" * 70)

    save_json(summary)
    save_csv(summary)

    print(
        f"[OK] JSON : {SUMMARY_JSON}"
    )

    print(
        f"[OK] CSV  : {SUMMARY_CSV}"
    )

    print()
    print("=" * 70)
    print("TEST INTERACTION SUMMARY TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    main()
