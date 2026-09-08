# -*- coding: utf-8 -*-
"""
interaction_analyzer.py

Analyse géométrique des interactions ligand-récepteur
à partir des poses AutoDock Vina.

Analyse :
- contacts ligand-récepteur ;
- résidus à proximité du ligand ;
- distances minimales ;
- contacts hydrogène potentiels ;
- contacts hydrophobes approximatifs ;
- export CSV.

Aucune dépendance externe obligatoire.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import csv
import math
import re


# ================================================================
# CONFIGURATION
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECEPTOR = (
    PROJECT_ROOT
    / "docking/receptor/3W9J.pdbqt"
)

HITS_CSV = (
    PROJECT_ROOT
    / "docking/results/batch_vina_engine/selected_hits.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "docking/results/batch_vina_engine/interaction_analysis"
)


# ================================================================
# STRUCTURES
# ================================================================

@dataclass
class Atom:
    """Atome extrait d'un fichier PDB/PDBQT."""

    name: str
    residue: str
    residue_id: str
    chain: str

    x: float
    y: float
    z: float

    atom_type: str


@dataclass
class Contact:
    """Contact ligand-récepteur."""

    ligand_atom: str
    receptor_atom: str

    residue: str
    residue_id: str
    chain: str

    distance: float
    interaction_type: str


# ================================================================
# LECTURE PDBQT
# ================================================================

def parse_pdbqt(path: Path) -> list[Atom]:
    """
    Lit les lignes ATOM/HETATM d'un PDBQT.
    """

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

                name = line[12:16].strip()
                residue = line[17:20].strip()
                chain = line[21].strip() or "-"
                residue_id = line[22:26].strip()

                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])

                atom_type = (
                    line[77:79].strip()
                    if len(line) >= 79
                    else ""
                )

                atoms.append(
                    Atom(
                        name=name,
                        residue=residue,
                        residue_id=residue_id,
                        chain=chain,
                        x=x,
                        y=y,
                        z=z,
                        atom_type=atom_type,
                    )
                )

            except (ValueError, IndexError):
                continue

    return atoms


# ================================================================
# DISTANCE
# ================================================================

def distance(a: Atom, b: Atom) -> float:
    """Distance euclidienne entre deux atomes."""

    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


# ================================================================
# TYPE D'INTERACTION
# ================================================================

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

DONOR_ACCEPTOR_ELEMENTS = {
    "N",
    "O",
    "S",
}


def classify_interaction(
    ligand_atom: Atom,
    receptor_atom: Atom,
    dist: float,
) -> str:
    """
    Classification géométrique simple.

    Attention :
    ce n'est pas une identification complète des liaisons
    hydrogène ou interactions π. Une analyse chimique plus
    poussée pourra être ajoutée ultérieurement.
    """

    receptor_residue = receptor_atom.residue

    ligand_element = (
        ligand_atom.atom_type.upper()
        [:1]
    )

    receptor_element = (
        receptor_atom.atom_type.upper()
        [:1]
    )

    # ------------------------------------------------------------
    # Contact très proche
    # ------------------------------------------------------------

    if dist <= 3.5:

        if (
            ligand_element in DONOR_ACCEPTOR_ELEMENTS
            and receptor_element in DONOR_ACCEPTOR_ELEMENTS
        ):
            return "Polar/H-bond candidate"

        if receptor_residue in HYDROPHOBIC_RESIDUES:
            return "Hydrophobic candidate"

        return "Close contact"

    # ------------------------------------------------------------
    # Contact hydrophobe
    # ------------------------------------------------------------

    if (
        dist <= 4.5
        and receptor_residue in HYDROPHOBIC_RESIDUES
    ):
        return "Hydrophobic contact"

    return "Contact"


# ================================================================
# ANALYSE D'UNE POSE
# ================================================================

def analyze_pose(
    ligand_path: Path,
    receptor_atoms: list[Atom],
    cutoff: float = 4.5,
) -> list[Contact]:

    ligand_atoms = parse_pdbqt(
        ligand_path
    )

    contacts = []

    for ligand_atom in ligand_atoms:

        for receptor_atom in receptor_atoms:

            dist = distance(
                ligand_atom,
                receptor_atom,
            )

            if dist > cutoff:
                continue

            interaction_type = classify_interaction(
                ligand_atom,
                receptor_atom,
                dist,
            )

            contacts.append(
                Contact(
                    ligand_atom=ligand_atom.name,
                    receptor_atom=receptor_atom.name,
                    residue=receptor_atom.residue,
                    residue_id=receptor_atom.residue_id,
                    chain=receptor_atom.chain,
                    distance=dist,
                    interaction_type=interaction_type,
                )
            )

    return contacts


# ================================================================
# RÉDUCTION DES CONTACTS
# ================================================================

def summarize_contacts(
    contacts: list[Contact],
) -> list[dict]:

    summary = {}

    for contact in contacts:

        key = (
            contact.residue,
            contact.residue_id,
            contact.chain,
        )

        if key not in summary:

            summary[key] = {
                "residue": contact.residue,
                "residue_id": contact.residue_id,
                "chain": contact.chain,
                "min_distance": contact.distance,
                "n_contacts": 0,
                "interaction_types": set(),
            }

        entry = summary[key]

        entry["min_distance"] = min(
            entry["min_distance"],
            contact.distance,
        )

        entry["n_contacts"] += 1

        entry["interaction_types"].add(
            contact.interaction_type
        )

    results = []

    for entry in summary.values():

        results.append(
            {
                "residue": entry["residue"],
                "residue_id": entry["residue_id"],
                "chain": entry["chain"],
                "min_distance": round(
                    entry["min_distance"],
                    3,
                ),
                "n_contacts": entry["n_contacts"],
                "interaction_types": "; ".join(
                    sorted(
                        entry["interaction_types"]
                    )
                ),
            }
        )

    results.sort(
        key=lambda x: x["min_distance"]
    )

    return results


# ================================================================
# CHARGEMENT DES HITS
# ================================================================

def load_hits(
    csv_path: Path,
) -> list[dict]:

    hits = []

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:
            hits.append(row)

    return hits


# ================================================================
# EXPORT
# ================================================================

def export_summary(
    molecule: str,
    summary: list[dict],
    output_path: Path,
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "molecule",
        "residue",
        "residue_id",
        "chain",
        "min_distance",
        "n_contacts",
        "interaction_types",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in summary:

            writer.writerow(
                {
                    "molecule": molecule,
                    **row,
                }
            )


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 70)
    print("INTERACTION ANALYZER — TEST")
    print("=" * 70)

    print()
    print(
        f"Récepteur : {RECEPTOR}"
    )

    print(
        f"Hits CSV  : {HITS_CSV}"
    )

    if not RECEPTOR.exists():

        print(
            "[ERREUR] Récepteur introuvable."
        )

        return 1

    if not HITS_CSV.exists():

        print(
            "[ERREUR] selected_hits.csv introuvable."
        )

        return 1

    # ------------------------------------------------------------
    # RÉCEPTEUR
    # ------------------------------------------------------------

    receptor_atoms = parse_pdbqt(
        RECEPTOR
    )

    print()
    print(
        f"[OK] Atomes récepteur : "
        f"{len(receptor_atoms)}"
    )

    if not receptor_atoms:

        print(
            "[ERREUR] Aucun atome détecté."
        )

        return 1

    # ------------------------------------------------------------
    # HITS
    # ------------------------------------------------------------

    hits = load_hits(
        HITS_CSV
    )

    print(
        f"[OK] Hits chargés : "
        f"{len(hits)}"
    )

    # ------------------------------------------------------------
    # ANALYSE
    # ------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for hit in hits:

        molecule = (
            hit.get("molecule")
            or ""
        )

        affinity = (
            hit.get("affinity")
            or ""
        )

        pose_path = (
            hit.get("output_pdbqt")
            or ""
        )

        pose = Path(
            pose_path
        )

        print()
        print("-" * 70)
        print(
            f"{molecule}"
        )
        print(
            f"Affinité : "
            f"{affinity} kcal/mol"
        )

        if not pose.exists():

            print(
                "[ERREUR] Pose PDBQT introuvable : "
                f"{pose}"
            )

            continue

        contacts = analyze_pose(
            pose,
            receptor_atoms,
            cutoff=4.5,
        )

        summary = summarize_contacts(
            contacts
        )

        print(
            f"Contacts atomiques : "
            f"{len(contacts)}"
        )

        print(
            f"Résidus en contact : "
            f"{len(summary)}"
        )

        print()
        print(
            "TOP RÉSIDUS"
        )

        print("-" * 70)

        for row in summary[:15]:

            print(
                f"{row['residue']:<4} "
                f"{row['residue_id']:>4} "
                f"{row['chain']} | "
                f"{row['min_distance']:5.2f} Å | "
                f"{row['interaction_types']}"
            )

        output_file = (
            OUTPUT_DIR
            / f"{molecule}_interactions.csv"
        )

        export_summary(
            molecule,
            summary,
            output_file,
        )

        print()
        print(
            f"[OK] Export : "
            f"{output_file}"
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
