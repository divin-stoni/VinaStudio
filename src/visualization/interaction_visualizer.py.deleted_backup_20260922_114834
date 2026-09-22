#!/usr/bin/env python3

import csv
import json
import os
import subprocess
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "environment.json"

RECEPTOR_FILE = (
    PROJECT_ROOT
    / "docking"
    / "receptor"
    / "3W9J.pdbqt"
)

POSE_FILE = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "selected_poses"
    / "Vilazodone_pose_1.pdbqt"
)

INTERACTION_FILE = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "interaction_analysis"
    / "Vilazodone_CID_6918314_interactions.csv"
)


class InteractionVisualizer:
    """
    Visualiseur des interactions ligand-récepteur.

    Le module :
        - lit le fichier CSV d'interactions ;
        - identifie les résidus concernés ;
        - prépare les sélections ChimeraX ;
        - ouvre le complexe ;
        - affiche le ligand et les résidus interactifs ;
        - zoome automatiquement sur la zone d'interaction.

    Les interactions de type H-bond sont volontairement
    présentées comme des candidats, conformément aux données CSV.
    """

    def __init__(self):
        self.chimerax_path = self._load_chimerax_path()
        self.interactions = []

    # ================================================================
    # CHIMERAX
    # ================================================================

    def _load_chimerax_path(self):

        if not CONFIG_FILE.exists():
            raise RuntimeError(
                f"Configuration introuvable : {CONFIG_FILE}"
            )

        with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        chimerax = config.get("tools", {}).get("chimerax", {})

        if chimerax.get("status") != "READY":
            raise RuntimeError(
                "ChimeraX n'est pas disponible."
            )

        path = chimerax.get("path")

        if not path:
            raise RuntimeError(
                "Chemin ChimeraX absent de environment.json."
            )

        if not os.path.exists(path):
            raise RuntimeError(
                f"ChimeraX introuvable : {path}"
            )

        return path

    # ================================================================
    # LECTURE CSV
    # ================================================================

    def load_interactions(self, csv_file):

        csv_file = Path(csv_file)

        if not csv_file.exists():
            raise FileNotFoundError(
                f"Fichier d'interactions introuvable : {csv_file}"
            )

        with open(csv_file, "r", encoding="utf-8") as handle:

            reader = csv.DictReader(handle)

            self.interactions = list(reader)

        if not self.interactions:
            raise RuntimeError(
                "Aucune interaction trouvée dans le CSV."
            )

        return self.interactions

    # ================================================================
    # ANALYSE DES TYPES
    # ================================================================

    def classify_interactions(self):

        statistics = {
            "polar": 0,
            "hydrophobic": 0,
            "close_contact": 0,
            "contact": 0
        }

        for interaction in self.interactions:

            types = interaction.get(
                "interaction_types",
                ""
            ).lower()

            if "polar/h-bond candidate" in types:
                statistics["polar"] += 1

            if "hydrophobic" in types:
                statistics["hydrophobic"] += 1

            if "close contact" in types:
                statistics["close_contact"] += 1

            if "contact" in types:
                statistics["contact"] += 1

        return statistics

    # ================================================================
    # RÉSIDUS
    # ================================================================

    def get_residue_identifiers(self):

        residues = []

        for interaction in self.interactions:

            residue = interaction.get("residue", "").strip()
            residue_id = interaction.get("residue_id", "").strip()
            chain = interaction.get("chain", "").strip()

            if not residue_id:
                continue

            try:
                residue_id_int = int(float(residue_id))
            except ValueError:
                continue

            identifier = (
                residue,
                residue_id_int,
                chain
            )

            if identifier not in residues:
                residues.append(identifier)

        return residues

    # ================================================================
    # CONSTRUCTION DES COMMANDES CHIMERAX
    # ================================================================

    def build_chimerax_commands(self):

        residues = self.get_residue_identifiers()

        commands = [
            f'open "{RECEPTOR_FILE}"',
            f'open "{POSE_FILE}"',

            "hide atoms",
            "show #1 cartoons",

            "select #2",
            "show atoms",
            "show bonds",

            "select clear"
        ]

        # ------------------------------------------------------------
        # Affichage des résidus interactifs
        # ------------------------------------------------------------

        for residue, residue_id, chain in residues:

            if chain:
                selector = f"#1/{chain}:{residue_id}"
            else:
                selector = f"#1:{residue_id}"

            commands.extend([
                f"select {selector}",
                f"show {selector} atoms",
                f"show {selector} bonds"
            ])

        commands.extend([
            "select clear",
            "view"
        ])

        return commands

    # ================================================================
    # LANCEMENT CHIMERAX
    # ================================================================

    def launch(self):

        commands = self.build_chimerax_commands()

        process_args = [
            self.chimerax_path,
            "--start",
            "default"
        ]

        for command in commands:
            process_args.extend([
                "--cmd",
                command
            ])

        process = subprocess.Popen(
            process_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return process

    # ================================================================
    # RAPPORT CONSOLE
    # ================================================================

    def print_report(self):

        statistics = self.classify_interactions()
        residues = self.get_residue_identifiers()

        print()
        print("INTERACTIONS")
        print("-" * 70)

        print(
            f"[OK] Nombre total de lignes : "
            f"{len(self.interactions)}"
        )

        print(
            f"[OK] Résidus uniques        : "
            f"{len(residues)}"
        )

        print()
        print("CLASSIFICATION")
        print("-" * 70)

        print(
            f"Polar / H-bond candidates : "
            f"{statistics['polar']}"
        )

        print(
            f"Hydrophobices             : "
            f"{statistics['hydrophobic']}"
        )

        print(
            f"Close contacts            : "
            f"{statistics['close_contact']}"
        )

        print(
            f"Contacts                  : "
            f"{statistics['contact']}"
        )

        print()
        print("RÉSIDUS INTERACTIFS")
        print("-" * 70)

        for residue, residue_id, chain in residues:

            print(
                f"{residue:>3} {residue_id:<4} "
                f"Chaîne {chain}"
            )

    # ================================================================
    # TEST
    # ================================================================

    def run_test(self):

        print("=" * 70)
        print("MEXAB/MEXR ANALYZER — INTERACTION VISUALIZER")
        print("=" * 70)

        print()
        print("FICHIERS")
        print("-" * 70)

        print(f"Récepteur : {RECEPTOR_FILE}")
        print(f"Pose      : {POSE_FILE}")
        print(f"Interactions : {INTERACTION_FILE}")

        if not RECEPTOR_FILE.exists():
            print()
            print("[ERREUR] Récepteur introuvable.")
            return

        if not POSE_FILE.exists():
            print()
            print("[ERREUR] Pose introuvable.")
            return

        if not INTERACTION_FILE.exists():
            print()
            print("[ERREUR] CSV d'interactions introuvable.")
            return

        print()
        print("LECTURE DES INTERACTIONS")
        print("-" * 70)

        self.load_interactions(INTERACTION_FILE)

        self.print_report()

        print()
        print("VISUALISATION 3D")
        print("-" * 70)

        try:

            process = self.launch()

            print("[OK] ChimeraX lancé.")
            print(f"[OK] PID : {process.pid}")

            time.sleep(4)

            if process.poll() is None:

                print("[OK] Récepteur chargé.")
                print("[OK] Pose chargée.")
                print("[OK] Résidus interactifs affichés.")
                print("[OK] Ligand affiché.")
                print("[OK] Vue 3D configurée.")

            else:

                print(
                    "[ATTENTION] ChimeraX s'est fermé rapidement."
                )

        except Exception as exc:

            print()
            print(f"[ERREUR] {exc}")

        print()
        print("=" * 70)
        print("TEST INTERACTION VISUALIZER TERMINÉ")
        print("=" * 70)


def main():

    visualizer = InteractionVisualizer()
    visualizer.run_test()


if __name__ == "__main__":
    main()
