# -*- coding: utf-8 -*-

"""
structural_validator.py

Validation structurale des interactions ligand-récepteur.

Objectifs :
- analyser les distances ligand-récepteur ;
- identifier les contacts rapprochés ;
- proposer des candidats aux liaisons hydrogène ;
- identifier les contacts hydrophobes ;
- produire un résumé par ligand ;
- exporter les résultats CSV.

Les interactions sont qualifiées de candidates :
elles doivent être confirmées par inspection structurale
avec ChimeraX ou Discovery Studio.
"""

from __future__ import annotations

from pathlib import Path
import csv
import math
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECEPTOR = (
    PROJECT_ROOT
    / "docking/receptor/3W9J.pdbqt"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "docking/results/batch_vina_engine"
)

HITS_CSV = (
    RESULTS_DIR / "selected_hits.csv"
)

OUTPUT_DIR = (
    RESULTS_DIR / "structural_validation"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------------------
# ATOME
# ---------------------------------------------------------------------

class Atom:
    def __init__(
        self,
        serial: int,
        name: str,
        residue: str,
        resnum: int,
        chain: str,
        x: float,
        y: float,
        z: float,
        element: str,
    ):
        self.serial = serial
        self.name = name
        self.residue = residue
        self.resnum = resnum
        self.chain = chain
        self.x = x
        self.y = y
        self.z = z
        self.element = element.upper()


# ---------------------------------------------------------------------
# LECTURE PDBQT
# ---------------------------------------------------------------------

def read_pdbqt(path: Path) -> list[Atom]:

    atoms = []

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:

        for line in handle:

            if not (
                line.startswith("ATOM")
                or line.startswith("HETATM")
            ):
                continue

            try:

                serial = int(line[6:11].strip())

                name = line[12:16].strip()

                residue = line[17:20].strip()

                chain = line[21].strip() or "?"

                resnum = int(
                    line[22:26].strip()
                )

                x = float(
                    line[30:38].strip()
                )

                y = float(
                    line[38:46].strip()
                )

                z = float(
                    line[46:54].strip()
                )

                # Dans PDBQT, le type AutoDock
                # est généralement à la fin.
                ad_type = (
                    line[77:79].strip()
                    if len(line) >= 79
                    else ""
                )

                if ad_type:
                    element = ad_type
                else:
                    element = name[0]

                atoms.append(
                    Atom(
                        serial,
                        name,
                        residue,
                        resnum,
                        chain,
                        x,
                        y,
                        z,
                        element,
                    )
                )

            except (
                ValueError,
                IndexError,
            ):
                continue

    return atoms


# ---------------------------------------------------------------------
# DISTANCE
# ---------------------------------------------------------------------

def distance(a: Atom, b: Atom) -> float:

    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


# ---------------------------------------------------------------------
# CLASSIFICATION
# ---------------------------------------------------------------------

HYDROPHOBIC_RESIDUES = {
    "ALA",
    "VAL",
    "LEU",
    "ILE",
    "MET",
    "PHE",
    "TRP",
    "PRO",
}

POLAR_RESIDUES = {
    "SER",
    "THR",
    "ASN",
    "GLN",
    "TYR",
    "CYS",
}

CHARGED_RESIDUES = {
    "ASP",
    "GLU",
    "LYS",
    "ARG",
    "HIS",
}


def classify_interaction(
    ligand_atom: Atom,
    receptor_atom: Atom,
    d: float,
) -> str:

    residue = receptor_atom.residue

    if d <= 2.2:
        return "Close contact / H-bond candidate"

    if (
        residue in POLAR_RESIDUES
        or residue in CHARGED_RESIDUES
    ):

        if d <= 3.5:
            return "Polar interaction candidate"

    if (
        residue in HYDROPHOBIC_RESIDUES
        and d <= 4.0
    ):

        return "Hydrophobic contact candidate"

    if d <= 4.0:
        return "Van der Waals/contact candidate"

    return "Other"


# ---------------------------------------------------------------------
# ANALYSE D'UN LIGAND
# ---------------------------------------------------------------------

def analyze_ligand(
    receptor_atoms: list[Atom],
    ligand_atoms: list[Atom],
    ligand_name: str,
) -> list[dict]:

    interactions = []

    for ligand_atom in ligand_atoms:

        for receptor_atom in receptor_atoms:

            d = distance(
                ligand_atom,
                receptor_atom,
            )

            # On conserve uniquement les contacts
            # suffisamment proches.
            if d > 4.0:
                continue

            interaction = classify_interaction(
                ligand_atom,
                receptor_atom,
                d,
            )

            interactions.append(
                {
                    "molecule": ligand_name,
                    "ligand_atom": ligand_atom.name,
                    "ligand_serial": ligand_atom.serial,
                    "receptor_atom": receptor_atom.name,
                    "residue": receptor_atom.residue,
                    "resnum": receptor_atom.resnum,
                    "chain": receptor_atom.chain,
                    "distance_A": round(d, 3),
                    "interaction": interaction,
                }
            )

    interactions.sort(
        key=lambda x: x["distance_A"]
    )

    return interactions


# ---------------------------------------------------------------------
# RESIDUS UNIQUES
# ---------------------------------------------------------------------

def summarize_residues(
    interactions: list[dict],
) -> list[dict]:

    residues = {}

    for row in interactions:

        key = (
            row["residue"],
            row["resnum"],
            row["chain"],
        )

        if key not in residues:

            residues[key] = {
                "residue": row["residue"],
                "resnum": row["resnum"],
                "chain": row["chain"],
                "min_distance_A": row["distance_A"],
                "n_contacts": 0,
                "interaction_types": set(),
            }

        item = residues[key]

        item["n_contacts"] += 1

        item["min_distance_A"] = min(
            item["min_distance_A"],
            row["distance_A"],
        )

        item["interaction_types"].add(
            row["interaction"]
        )

    output = []

    for item in residues.values():

        output.append(
            {
                "residue": item["residue"],
                "resnum": item["resnum"],
                "chain": item["chain"],
                "min_distance_A": item[
                    "min_distance_A"
                ],
                "n_contacts": item[
                    "n_contacts"
                ],
                "interaction_types": "; ".join(
                    sorted(
                        item["interaction_types"]
                    )
                ),
            }
        )

    output.sort(
        key=lambda x: x["min_distance_A"]
    )

    return output


# ---------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------

def export_csv(
    path: Path,
    rows: list[dict],
):

    if not rows:
        return

    fieldnames = list(rows[0].keys())

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

        writer.writerows(rows)


# ---------------------------------------------------------------------
# HIT CSV
# ---------------------------------------------------------------------

def load_hits() -> list[dict]:

    if not HITS_CSV.exists():

        raise FileNotFoundError(
            f"CSV introuvable : {HITS_CSV}"
        )

    with HITS_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        return list(
            csv.DictReader(handle)
        )


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    print("=" * 70)
    print("STRUCTURAL VALIDATOR — TEST")
    print("=" * 70)

    print()
    print(
        f"Récepteur : {RECEPTOR}"
    )

    print(
        f"Hits CSV  : {HITS_CSV}"
    )

    # --------------------------------------------------------------
    # RECEPTEUR
    # --------------------------------------------------------------

    if not RECEPTOR.exists():

        print(
            f"[ERREUR] Récepteur introuvable."
        )

        return 1

    receptor_atoms = read_pdbqt(
        RECEPTOR
    )

    print()
    print(
        f"[OK] Atomes récepteur : "
        f"{len(receptor_atoms)}"
    )

    # --------------------------------------------------------------
    # HITS
    # --------------------------------------------------------------

    try:

        hits = load_hits()

    except Exception as exc:

        print(
            f"[ERREUR] {exc}"
        )

        return 1

    print(
        f"[OK] Hits chargés : "
        f"{len(hits)}"
    )

    # --------------------------------------------------------------
    # ANALYSE
    # --------------------------------------------------------------

    all_residue_rows = []

    for hit in hits:

        molecule = hit["molecule"]

        affinity = hit.get(
            "affinity",
            "",
        )

        output_pdbqt = Path(
            hit["output_pdbqt"]
        )

        print()
        print("-" * 70)
        print(molecule)
        print(
            f"Affinité : {affinity} kcal/mol"
        )

        if not output_pdbqt.exists():

            print(
                "[ERREUR] PDBQT ligand "
                "introuvable."
            )

            continue

        ligand_atoms = read_pdbqt(
            output_pdbqt
        )

        # Le PDBQT de sortie contient plusieurs
        # MODEL. Ici on prend tous les ATOM.
        # Pour une validation finale, il faudra
        # travailler spécifiquement sur le MODEL 1.
        interactions = analyze_ligand(
            receptor_atoms,
            ligand_atoms,
            molecule,
        )

        residues = summarize_residues(
            interactions
        )

        print(
            f"Contacts : "
            f"{len(interactions)}"
        )

        print(
            f"Résidus en contact : "
            f"{len(residues)}"
        )

        print()
        print("TOP RÉSIDUS")
        print("-" * 70)

        for residue in residues[:15]:

            print(
                f"{residue['residue']:>3} "
                f"{residue['resnum']:4d}"
                f"({residue['chain']}) | "
                f"{residue['min_distance_A']:5.2f} Å | "
                f"{residue['interaction_types']}"
            )

            row = dict(residue)

            row["molecule"] = molecule

            all_residue_rows.append(row)

        # ----------------------------------------------------------
        # EXPORT INDIVIDUEL
        # ----------------------------------------------------------

        output_file = (
            OUTPUT_DIR
            / f"{molecule}_structural_validation.csv"
        )

        export_csv(
            output_file,
            residues,
        )

        print()
        print(
            f"[OK] Export : {output_file}"
        )

    # --------------------------------------------------------------
    # EXPORT GLOBAL
    # --------------------------------------------------------------

    global_file = (
        OUTPUT_DIR
        / "all_structural_interactions.csv"
    )

    export_csv(
        global_file,
        all_residue_rows,
    )

    print()
    print("=" * 70)
    print("VALIDATION STRUCTURALE TERMINÉE")
    print("=" * 70)

    print(
        f"Résultats : {OUTPUT_DIR}"
    )

    print(
        f"CSV global : {global_file}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
