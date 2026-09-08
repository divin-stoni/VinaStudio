#!/usr/bin/env python3

import csv
import os
import re
import statistics

BASE = os.path.expanduser("~/MexAB_MexR_Analyzer_BETA")

HITS_CSV = os.path.join(
    BASE,
    "docking/results/batch_vina_engine/selected_hits.csv"
)

INDIVIDUAL_DIR = os.path.join(
    BASE,
    "docking/results/batch_vina_engine/individual"
)

OUTPUT_DIR = os.path.join(
    BASE,
    "docking/results/batch_vina_engine/pose_convergence"
)

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "pose_convergence.csv"
)


def load_hits():
    hits = []

    with open(HITS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            hits.append({
                "rank": int(row["rank"]),
                "molecule": row["molecule"],
                "affinity": float(row["affinity"]),
                "output_pdbqt": row["output_pdbqt"]
            })

    return hits


def extract_scores(pdbqt_file):
    scores = []

    with open(pdbqt_file, "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(
                r"REMARK VINA RESULT:\s+(-?\d+(?:\.\d+)?)",
                line
            )

            if match:
                scores.append(float(match.group(1)))

    return scores


def convergence_label(scores):
    if len(scores) < 2:
        return "Insuffisant"

    best = scores[0]
    delta2 = abs(scores[1] - best)

    within_05 = sum(
        1 for s in scores
        if abs(s - best) <= 0.5
    )

    within_10 = sum(
        1 for s in scores
        if abs(s - best) <= 1.0
    )

    if delta2 <= 0.5 and within_05 >= 3:
        return "Bonne convergence"

    if delta2 <= 1.0 and within_10 >= 3:
        return "Convergence modérée"

    return "Convergence faible"


def main():

    print("=" * 70)
    print("POSE CONVERGENCE ANALYZER — TEST")
    print("=" * 70)

    print()
    print(f"Hits CSV : {HITS_CSV}")

    if not os.path.exists(HITS_CSV):
        print("[ERREUR] selected_hits.csv introuvable")
        return

    hits = load_hits()

    print(f"[OK] Hits chargés : {len(hits)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []

    for hit in hits:

        molecule = hit["molecule"]

        pdbqt_file = os.path.join(
            INDIVIDUAL_DIR,
            molecule + "_out.pdbqt"
        )

        print()
        print("-" * 70)
        print(molecule)
        print("-" * 70)

        if not os.path.exists(pdbqt_file):
            print(f"[ERREUR] Fichier introuvable : {pdbqt_file}")
            continue

        scores = extract_scores(pdbqt_file)

        if not scores:
            print("[ERREUR] Aucun score Vina trouvé")
            continue

        best = min(scores)

        # Scores triés du meilleur au moins bon
        sorted_scores = sorted(scores)

        second = sorted_scores[1] if len(sorted_scores) >= 2 else None

        delta_best_second = (
            abs(second - best)
            if second is not None
            else None
        )

        mean_score = statistics.mean(scores)
        median_score = statistics.median(scores)

        std_score = (
            statistics.stdev(scores)
            if len(scores) >= 2
            else 0.0
        )

        within_05 = sum(
            1 for s in scores
            if abs(s - best) <= 0.5
        )

        within_10 = sum(
            1 for s in scores
            if abs(s - best) <= 1.0
        )

        convergence = convergence_label(scores)

        print(f"Nombre de modes       : {len(scores)}")
        print(f"Meilleur score        : {best:.3f} kcal/mol")
        print(f"2e meilleur score     : {second:.3f} kcal/mol")
        print(f"Delta meilleur/2e     : {delta_best_second:.3f} kcal/mol")
        print(f"Moyenne               : {mean_score:.3f} kcal/mol")
        print(f"Médiane               : {median_score:.3f} kcal/mol")
        print(f"Écart-type            : {std_score:.3f} kcal/mol")
        print(f"Modes ≤ 0.5 kcal/mol  : {within_05}/{len(scores)}")
        print(f"Modes ≤ 1.0 kcal/mol  : {within_10}/{len(scores)}")
        print(f"Convergence           : {convergence}")

        print()
        print("SCORES")
        for i, score in enumerate(scores, start=1):
            delta = abs(score - best)
            print(
                f"  Mode {i:2d} : {score:8.3f} kcal/mol"
                f" | Δ meilleur = {delta:.3f}"
            )

        results.append({
            "rank": hit["rank"],
            "molecule": molecule,
            "csv_affinity": hit["affinity"],
            "n_modes": len(scores),
            "best_score": best,
            "second_best": second,
            "delta_best_second": delta_best_second,
            "mean_score": mean_score,
            "median_score": median_score,
            "std_score": std_score,
            "modes_within_0_5": within_05,
            "modes_within_1_0": within_10,
            "convergence": convergence
        })

    if results:

        fields = [
            "rank",
            "molecule",
            "csv_affinity",
            "n_modes",
            "best_score",
            "second_best",
            "delta_best_second",
            "mean_score",
            "median_score",
            "std_score",
            "modes_within_0_5",
            "modes_within_1_0",
            "convergence"
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

        print()
        print("=" * 70)
        print("RÉSUMÉ DE CONVERGENCE")
        print("=" * 70)

        for r in results:
            print(
                f"{r['molecule']:<40} "
                f"{r['best_score']:7.3f} | "
                f"Δ2 = {r['delta_best_second']:.3f} | "
                f"{r['modes_within_0_5']}/"
                f"{r['n_modes']} à ≤0.5 | "
                f"{r['convergence']}"
            )

        print()
        print(f"[OK] Résultats exportés : {OUTPUT_CSV}")

    print()
    print("=" * 70)
    print("ANALYSE DE CONVERGENCE TERMINÉE")
    print("=" * 70)


if __name__ == "__main__":
    main()
