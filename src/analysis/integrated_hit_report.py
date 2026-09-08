#!/usr/bin/env python3

import csv
import os
import re
import statistics

BASE = os.path.expanduser("~/MexAB_MexR_Analyzer_BETA")
RESULTS = os.path.join(BASE, "docking/results/batch_vina_engine")

HITS_CSV = os.path.join(RESULTS, "selected_hits.csv")
CONVERGENCE_CSV = os.path.join(RESULTS, "pose_convergence/pose_convergence.csv")
INTERACTION_DIR = os.path.join(RESULTS, "interaction_analysis")
STRUCTURAL_DIR = os.path.join(RESULTS, "structural_validation")

OUTPUT_DIR = os.path.join(RESULTS, "integrated_report")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "integrated_hit_report.csv")
OUTPUT_TXT = os.path.join(OUTPUT_DIR, "integrated_hit_report.txt")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_column(row, names):
    for name in names:
        if name in row:
            return row[name]
    return ""


def load_convergence():
    if not os.path.exists(CONVERGENCE_CSV):
        return {}

    data = {}

    for row in read_csv(CONVERGENCE_CSV):
        data[row["molecule"]] = row

    return data


def load_interactions(molecule):
    path = os.path.join(
        INTERACTION_DIR,
        f"{molecule}_interactions.csv"
    )

    if not os.path.exists(path):
        return []

    return read_csv(path)


def load_structural(molecule):
    path = os.path.join(
        STRUCTURAL_DIR,
        f"{molecule}_structural_validation.csv"
    )

    if not os.path.exists(path):
        return []

    return read_csv(path)


def classify_convergence(value):
    value = value.lower()

    if "bonne" in value:
        return "Bonne"

    if "modérée" in value or "moderee" in value:
        return "Modérée"

    if "faible" in value:
        return "Faible"

    return value


def count_interaction_types(rows):
    polar = 0
    hydrophobic = 0
    close = 0

    residues = set()

    for row in rows:

        residue = (
            find_column(
                row,
                ["residue", "residue_id", "residue_label"]
            )
        )

        if residue:
            residues.add(residue)

        description = " ".join(
            str(v) for v in row.values()
        ).lower()

        if "polar" in description or "h-bond" in description:
            polar += 1

        if "hydrophobic" in description:
            hydrophobic += 1

        if "close contact" in description:
            close += 1

    return len(residues), polar, hydrophobic, close


def calculate_robustness(row):
    """
    Score indicatif de synthèse.
    Ce score n'est PAS un score expérimental ni une prédiction
    d'activité biologique.
    """

    score = 0.0

    affinity = float(row["affinity"])

    # Affinité : contribution plafonnée
    if affinity <= -11:
        score += 40
    elif affinity <= -10:
        score += 35
    elif affinity <= -9:
        score += 30
    elif affinity <= -8:
        score += 20
    else:
        score += 10

    # Convergence
    convergence = row["convergence"]

    if convergence == "Bonne":
        score += 25
    elif convergence == "Modérée":
        score += 15
    else:
        score += 5

    # Résidus en contact
    residues = int(row["structural_residues"])

    if residues >= 30:
        score += 20
    elif residues >= 20:
        score += 15
    elif residues >= 10:
        score += 10
    else:
        score += 5

    # Interactions polaires candidates
    polar = int(row["polar_candidates"])

    if polar >= 5:
        score += 10
    elif polar >= 2:
        score += 7
    elif polar >= 1:
        score += 4

    # Hydrophobes
    hydrophobic = int(row["hydrophobic_candidates"])

    if hydrophobic >= 5:
        score += 5
    elif hydrophobic >= 2:
        score += 3

    return round(score, 2)


def main():

    print("=" * 78)
    print("INTEGRATED HIT REPORT — TEST")
    print("=" * 78)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(HITS_CSV):
        print("[ERREUR] selected_hits.csv introuvable")
        return

    hits = read_csv(HITS_CSV)
    convergence = load_convergence()

    print()
    print(f"[OK] Hits chargés : {len(hits)}")

    results = []

    for hit in hits:

        molecule = hit["molecule"]

        affinity = float(hit["affinity"])

        conv = convergence.get(molecule, {})

        interaction_rows = load_interactions(molecule)
        structural_rows = load_structural(molecule)

        interaction_residues, polar, hydrophobic, close = \
            count_interaction_types(interaction_rows)

        structural_residue_count = len({
            find_column(
                row,
                ["residue", "residue_id", "residue_label"]
            )
            for row in structural_rows
            if find_column(
                row,
                ["residue", "residue_id", "residue_label"]
            )
        })

        if structural_residue_count == 0:
            structural_residue_count = len(structural_rows)

        convergence_label = classify_convergence(
            conv.get("convergence", "Inconnue")
        )

        result = {
            "rank": hit["rank"],
            "molecule": molecule,
            "group": hit.get("group", ""),
            "affinity": affinity,

            "n_modes": conv.get("n_modes", ""),
            "best_score": conv.get("best_score", ""),
            "second_best": conv.get("second_best", ""),
            "delta_best_second": conv.get(
                "delta_best_second",
                ""
            ),

            "mean_score": conv.get("mean_score", ""),
            "median_score": conv.get("median_score", ""),
            "std_score": conv.get("std_score", ""),

            "modes_within_0_5": conv.get(
                "modes_within_0_5",
                ""
            ),

            "modes_within_1_0": conv.get(
                "modes_within_1_0",
                ""
            ),

            "convergence": convergence_label,

            "interaction_residues": interaction_residues,
            "structural_residues": structural_residue_count,

            "polar_candidates": polar,
            "hydrophobic_candidates": hydrophobic,
            "close_contacts": close,
        }

        result["robustness_score"] = calculate_robustness(result)

        results.append(result)

    # Classement intégré
    results.sort(
        key=lambda x: (
            -x["robustness_score"],
            x["affinity"]
        )
    )

    for i, result in enumerate(results, start=1):
        result["integrated_rank"] = i

    fields = [
        "integrated_rank",
        "rank",
        "molecule",
        "group",
        "affinity",
        "n_modes",
        "best_score",
        "second_best",
        "delta_best_second",
        "mean_score",
        "median_score",
        "std_score",
        "modes_within_0_5",
        "modes_within_1_0",
        "convergence",
        "interaction_residues",
        "structural_residues",
        "polar_candidates",
        "hydrophobic_candidates",
        "close_contacts",
        "robustness_score"
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(results)

    # Rapport lisible
    with open(
        OUTPUT_TXT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("=" * 78 + "\n")
        f.write("RAPPORT INTÉGRÉ DES HITS — MexAB/MexR\n")
        f.write("=" * 78 + "\n\n")

        f.write(
            "IMPORTANT : le score de robustesse est un indicateur "
            "informatif interne.\n"
        )
        f.write(
            "Il ne constitue pas une prédiction expérimentale "
            "d'activité biologique.\n\n"
        )

        for result in results:

            f.write("-" * 78 + "\n")
            f.write(
                f"RANG INTÉGRÉ : {result['integrated_rank']}\n"
            )
            f.write(
                f"Molécule : {result['molecule']}\n"
            )
            f.write(
                f"Affinité : {result['affinity']:.3f} kcal/mol\n"
            )

            f.write(
                f"Convergence : {result['convergence']}\n"
            )

            f.write(
                f"Modes : {result['n_modes']}\n"
            )

            f.write(
                f"Delta meilleur/2e : "
                f"{result['delta_best_second']} kcal/mol\n"
            )

            f.write(
                f"Modes ≤0.5 kcal/mol : "
                f"{result['modes_within_0_5']}\n"
            )

            f.write(
                f"Modes ≤1.0 kcal/mol : "
                f"{result['modes_within_1_0']}\n"
            )

            f.write(
                f"Résidus interactions : "
                f"{result['interaction_residues']}\n"
            )

            f.write(
                f"Résidus validation structurale : "
                f"{result['structural_residues']}\n"
            )

            f.write(
                f"Interactions polaires candidates : "
                f"{result['polar_candidates']}\n"
            )

            f.write(
                f"Contacts hydrophobes candidats : "
                f"{result['hydrophobic_candidates']}\n"
            )

            f.write(
                f"Close contacts : "
                f"{result['close_contacts']}\n"
            )

            f.write(
                f"SCORE DE ROBUSTESSE : "
                f"{result['robustness_score']}/100\n"
            )

            f.write("\n")

        f.write("=" * 78 + "\n")
        f.write("CLASSEMENT FINAL INTÉGRÉ\n")
        f.write("=" * 78 + "\n\n")

        for result in results:
            f.write(
                f"{result['integrated_rank']}. "
                f"{result['molecule']} | "
                f"{result['affinity']:.3f} kcal/mol | "
                f"{result['convergence']} | "
                f"Robustesse = "
                f"{result['robustness_score']}/100\n"
            )

    print()
    print("=" * 78)
    print("CLASSEMENT INTÉGRÉ")
    print("=" * 78)

    for result in results:

        print(
            f"{result['integrated_rank']:2d}. "
            f"{result['molecule']:<40} "
            f"{result['affinity']:7.3f} kcal/mol | "
            f"{result['convergence']:<10} | "
            f"{result['robustness_score']:5.1f}/100"
        )

    print()
    print(f"[OK] CSV : {OUTPUT_CSV}")
    print(f"[OK] Rapport texte : {OUTPUT_TXT}")

    print()
    print("=" * 78)
    print("RAPPORT INTÉGRÉ TERMINÉ")
    print("=" * 78)


if __name__ == "__main__":
    main()
