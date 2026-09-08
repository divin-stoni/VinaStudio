# -*- coding: utf-8 -*-

from pathlib import Path
import csv
import math
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIR = (
    PROJECT_ROOT
    / "docking/results/batch_vina_engine"
)

HITS_CSV = RESULTS_DIR / "selected_hits.csv"
INDIVIDUAL_DIR = RESULTS_DIR / "individual"


CENTER = (
    34.12,
    16.29,
    -58.71,
)

SIZE = (
    26.0,
    26.0,
    26.0,
)


def load_hits():

    hits = []

    with HITS_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:

            hits.append(row)

    return hits


def parse_pose_file(path):

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    models = text.split("MODEL ")

    parsed_models = []

    for block in models[1:]:

        lines = block.splitlines()

        model_number = None
        affinity = None
        atoms = []

        first_line = lines[0].strip()

        try:
            model_number = int(first_line)
        except ValueError:
            continue

        for line in lines:

            if line.startswith(
                "REMARK VINA RESULT:"
            ):

                parts = line.split()

                if len(parts) >= 5:

                    try:
                        affinity = float(parts[3])
                    except ValueError:
                        pass

            if line.startswith("ATOM"):

                try:

                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])

                    atoms.append(
                        (x, y, z)
                    )

                except ValueError:
                    pass

        parsed_models.append(
            {
                "model": model_number,
                "affinity": affinity,
                "atoms": atoms,
            }
        )

    return parsed_models


def distance_to_center(
    atoms,
):

    if not atoms:
        return None

    cx = sum(
        atom[0]
        for atom in atoms
    ) / len(atoms)

    cy = sum(
        atom[1]
        for atom in atoms
    ) / len(atoms)

    cz = sum(
        atom[2]
        for atom in atoms
    ) / len(atoms)

    dx = cx - CENTER[0]
    dy = cy - CENTER[1]
    dz = cz - CENTER[2]

    distance = math.sqrt(
        dx * dx
        + dy * dy
        + dz * dz
    )

    return (
        cx,
        cy,
        cz,
        distance,
    )


def main():

    print("=" * 70)
    print("POSE VALIDATOR — TEST")
    print("=" * 70)

    print()
    print(
        f"Hits CSV : {HITS_CSV}"
    )

    if not HITS_CSV.exists():

        print(
            "[ERREUR] selected_hits.csv introuvable."
        )

        return 1

    hits = load_hits()

    print(
        f"[OK] Hits chargés : {len(hits)}"
    )

    print()
    print(
        "BOÎTE DE DOCKING"
    )

    print("-" * 70)

    print(
        f"Centre : "
        f"({CENTER[0]}, "
        f"{CENTER[1]}, "
        f"{CENTER[2]})"
    )

    print(
        f"Taille : "
        f"({SIZE[0]}, "
        f"{SIZE[1]}, "
        f"{SIZE[2]})"
    )

    for hit in hits:

        molecule = hit["molecule"]

        output = (
            INDIVIDUAL_DIR
            / f"{molecule}_out.pdbqt"
        )

        print()
        print("-" * 70)
        print(molecule)
        print("-" * 70)

        if not output.exists():

            print(
                "[ERREUR] PDBQT introuvable : "
                f"{output}"
            )

            continue

        models = parse_pose_file(
            output
        )

        print(
            f"[OK] Fichier : "
            f"{output.name}"
        )

        print(
            f"[OK] Nombre de modèles : "
            f"{len(models)}"
        )

        if not models:

            print(
                "[ERREUR] Aucun modèle détecté."
            )

            continue

        model1 = models[0]

        print()
        print(
            "POSE 1"
        )

        print(
            f"Score PDBQT : "
            f"{model1['affinity']}"
        )

        print(
            f"Score CSV   : "
            f"{hit.get('affinity')}"
        )

        print(
            f"Nombre d'atomes : "
            f"{len(model1['atoms'])}"
        )

        geometry = distance_to_center(
            model1["atoms"]
        )

        if geometry:

            cx, cy, cz, distance = geometry

            print()
            print(
                "CENTRE GÉOMÉTRIQUE DU LIGAND"
            )

            print(
                f"X : {cx:.3f}"
            )

            print(
                f"Y : {cy:.3f}"
            )

            print(
                f"Z : {cz:.3f}"
            )

            print(
                f"Distance au centre "
                f"de la boîte : "
                f"{distance:.3f} Å"
            )

        print()
        print(
            "SCORES DES MODES"
        )

        for model in models:

            print(
                f"  Mode {model['model']:2d} : "
                f"{model['affinity']}"
            )

    print()
    print("=" * 70)
    print("VALIDATION DES POSES TERMINÉE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
