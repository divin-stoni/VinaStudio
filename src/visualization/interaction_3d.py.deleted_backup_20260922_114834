#!/usr/bin/env python3

import csv
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHIMERAX = "/usr/lib/ucsf-chimerax/bin/ChimeraX"

RECEPTOR = (
    PROJECT_ROOT
    / "docking"
    / "receptor"
    / "3W9J.pdbqt"
)

POSE = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "selected_poses"
    / "Vilazodone_pose_1.pdbqt"
)

INTERACTIONS = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "interaction_analysis"
    / "Vilazodone_CID_6918314_interactions.csv"
)


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
                row["min_distance"] = float(row["min_distance"])
            except (ValueError, TypeError):
                continue

            interactions.append(row)

    return interactions


def interaction_color(interaction_type):

    text = interaction_type.lower()

    if "hydrophobic" in text and "polar" in text:
        return "purple"

    if "polar" in text or "h-bond" in text:
        return "cyan"

    if "hydrophobic" in text:
        return "gold"

    if "close contact" in text:
        return "white"

    if "contact" in text:
        return "lightgray"

    return "white"


def clean_label_text(interaction_type):

    text = interaction_type.lower()

    has_polar = (
        "polar" in text
        or "h-bond" in text
    )

    has_hydrophobic = (
        "hydrophobic" in text
    )

    has_close = (
        "close contact" in text
    )

    has_contact = (
        "contact" in text
    )

    parts = []

    if has_polar:
        parts.append("Polar/H-bond")

    if has_hydrophobic:
        parts.append("Hydrophobic")

    if has_close and not parts:
        parts.append("Close contact")

    elif has_contact and not parts:
        parts.append("Contact")

    if not parts:
        parts.append("Interaction")

    return " + ".join(parts)


def build_commands(interactions):

    commands = []

    # ============================================================
    # OUVERTURE
    # ============================================================

    commands.append(
        f'open "{RECEPTOR}"'
    )

    commands.append(
        f'open "{POSE}"'
    )

    # ============================================================
    # STRUCTURE GÉNÉRALE
    # ============================================================

    commands.append(
        "hide #1 atoms"
    )

    commands.append(
        "show #1 cartoons"
    )

    commands.append(
        "show #2 atoms"
    )

    commands.append(
        "show #2 bonds"
    )

    commands.append(
        "style #2 stick"
    )

    # ============================================================
    # RÉSIDUS INTERACTIFS
    # ============================================================

    for index, interaction in enumerate(
        interactions,
        start=1
    ):

        residue = interaction["residue"]
        residue_id = interaction["residue_id"]
        chain = interaction["chain"]

        min_distance = interaction["min_distance"]

        interaction_type = interaction[
            "interaction_types"
        ]

        color = interaction_color(
            interaction_type
        )

        type_label = clean_label_text(
            interaction_type
        )

        residue_spec = (
            f"#1/{chain}:{residue_id}"
        )

        # --------------------------------------------------------
        # AFFICHAGE DU RÉSIDU
        # --------------------------------------------------------

        commands.append(
            f"show {residue_spec} atoms"
        )

        commands.append(
            f"show {residue_spec} bonds"
        )

        commands.append(
            f"style {residue_spec} stick"
        )

        commands.append(
            f"color {residue_spec} {color}"
        )

        # --------------------------------------------------------
        # LABEL DU RÉSIDU
        # --------------------------------------------------------

        residue_label = (
            f"{residue} {residue_id}"
        )

        commands.append(
            f'label {residue_spec} residues '
            f'text "{residue_label}" '
            f'color {color} '
            f'height 1.0'
        )

        # --------------------------------------------------------
        # LABEL DE L'INTERACTION
        # --------------------------------------------------------

        interaction_label = (
            f"{residue} {residue_id} | "
            f"{min_distance:.2f} Å | "
            f"{type_label}"
        )

        print(
            f"[{index:02d}] "
            f"{residue} {residue_id} "
            f"| {min_distance:.2f} Å "
            f"| {interaction_type}"
        )

        # --------------------------------------------------------
        # LABEL DÉTAILLÉ
        #
        # Le label est placé sur le résidu.
        # Cela permet d'afficher directement :
        #
        # GLN 46 | 1.92 Å | Polar/H-bond
        #
        # sans utiliser la commande distance.
        # --------------------------------------------------------

        commands.append(
            f'label {residue_spec} residues '
            f'text "{interaction_label}" '
            f'color {color} '
            f'height 0.7'
        )

    # ============================================================
    # VUE
    # ============================================================

    commands.append(
        "select #2"
    )

    commands.append(
        "view sel"
    )

    commands.append(
        "select clear"
    )

    return commands


def launch_chimerax(commands):

    command_string = "; ".join(commands)

    process = subprocess.Popen(
        [
            CHIMERAX,
            "--cmd",
            command_string
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    return process


def main():

    print("=" * 70)
    print("MEXAB/MEXR ANALYZER — INTERACTION 3D")
    print("=" * 70)

    print()
    print("FICHIERS")
    print("-" * 70)

    print(
        f"Récepteur    : {RECEPTOR}"
    )

    print(
        f"Pose         : {POSE}"
    )

    print(
        f"Interactions : {INTERACTIONS}"
    )

    # ============================================================
    # VÉRIFICATIONS
    # ============================================================

    print()
    print("VÉRIFICATION")
    print("-" * 70)

    for filename in (
        RECEPTOR,
        POSE,
        INTERACTIONS
    ):

        if not filename.exists():

            print(
                f"[ERREUR] Fichier introuvable : "
                f"{filename}"
            )

            return

    print(
        "[OK] Tous les fichiers sont disponibles."
    )

    # ============================================================
    # LECTURE CSV
    # ============================================================

    print()
    print("LECTURE DES INTERACTIONS")
    print("-" * 70)

    interactions = load_interactions(
        INTERACTIONS
    )

    print(
        f"[OK] {len(interactions)} interactions chargées."
    )

    print()
    print("INTERACTIONS")
    print("-" * 70)

    for index, interaction in enumerate(
        interactions,
        start=1
    ):

        residue = interaction["residue"]
        residue_id = interaction["residue_id"]
        chain = interaction["chain"]
        distance = interaction["min_distance"]
        interaction_type = interaction[
            "interaction_types"
        ]

        print(
            f"{index:02d}. "
            f"{residue} {residue_id} "
            f"(chaîne {chain}) "
            f"— {distance:.2f} Å "
            f"— {interaction_type}"
        )

    # ============================================================
    # COMMANDES
    # ============================================================

    print()
    print("PRÉPARATION")
    print("-" * 70)

    commands = build_commands(
        interactions
    )

    print(
        f"[OK] {len(commands)} commandes ChimeraX préparées."
    )

    # ============================================================
    # LANCEMENT
    # ============================================================

    print()
    print("LANCEMENT")
    print("-" * 70)

    try:

        process = launch_chimerax(
            commands
        )

        print(
            f"[OK] ChimeraX lancé."
        )

        print(
            f"[OK] PID : {process.pid}"
        )

        print(
            "[OK] Récepteur chargé."
        )

        print(
            "[OK] Pose chargée."
        )

        print(
            "[OK] Résidus interactifs affichés."
        )

        print(
            "[OK] Noms des résidus affichés."
        )

        print(
            "[OK] Distances du CSV affichées."
        )

        print(
            "[OK] Types d'interactions affichés."
        )

        print(
            "[OK] Vue 3D configurée."
        )

    except Exception as exc:

        print()
        print(
            f"[ERREUR] {exc}"
        )

    print()
    print("=" * 70)
    print("TEST INTERACTION 3D TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    main()
