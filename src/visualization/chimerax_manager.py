#!/usr/bin/env python3

import json
import os
import subprocess
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "environment.json"


class ChimeraXManager:
    """
    Gestionnaire UCSF ChimeraX.

    ChimeraX est utilisé comme moteur graphique externe.

    Modes :
        GUI      : ouverture interactive de ChimeraX.
        HEADLESS : génération automatisée d'images/exports.
    """

    def __init__(self):
        self.chimerax_path = self._load_chimerax_path()
        self.process = None

    # ================================================================
    # CONFIGURATION
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
                f"Exécutable ChimeraX introuvable : {path}"
            )

        return path

    # ================================================================
    # MODE GUI
    # ================================================================

    def launch_gui(self, commands=None):
        """
        Lance ChimeraX dans une fenêtre graphique.

        Les commandes sont transmises au démarrage.
        """

        command_args = [
            self.chimerax_path,
            "--start",
            "default"
        ]

        if commands:
            for command in commands:
                command_args.extend([
                    "--cmd",
                    command
                ])

        self.process = subprocess.Popen(
            command_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return self.process.pid

    # ================================================================
    # MODE HEADLESS
    # ================================================================

    def run_headless(self, commands, timeout=60):
        """
        Exécute ChimeraX sans interface.

        Utilisé ultérieurement pour :
            - génération d'images ;
            - exports ;
            - rapports ;
            - visualisations automatisées.
        """

        if isinstance(commands, str):
            commands = [commands]

        command_string = "; ".join(commands)

        result = subprocess.run(
            [
                self.chimerax_path,
                "--nogui",
                "--cmd",
                command_string
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout
        )

        return result.returncode, result.stdout

    # ================================================================
    # OUVERTURE D'UNE STRUCTURE
    # ================================================================

    def open_structure_gui(self, structure_file):

        structure_file = Path(structure_file).resolve()

        if not structure_file.exists():
            raise FileNotFoundError(
                f"Structure introuvable : {structure_file}"
            )

        command = f'open "{structure_file}"'

        return self.launch_gui([command])

    # ================================================================
    # OUVERTURE D'UNE POSE
    # ================================================================

    def open_pose_gui(
        self,
        receptor_file,
        ligand_file,
        pose=1
    ):
        """
        Ouvre une pose spécifique d'un docking.

        pose=1 correspond à MODEL 1 du fichier PDBQT.
        """

        receptor_file = Path(receptor_file).resolve()
        ligand_file = Path(ligand_file).resolve()

        if not receptor_file.exists():
            raise FileNotFoundError(
                f"Récepteur introuvable : {receptor_file}"
            )

        if not ligand_file.exists():
            raise FileNotFoundError(
                f"Ligand introuvable : {ligand_file}"
            )

        commands = [
            # --------------------------------------------------------
            # Récepteur
            # --------------------------------------------------------
            f'open "{receptor_file}"',

            # --------------------------------------------------------
            # Ligand
            # --------------------------------------------------------
            f'open "{ligand_file}"',

            # --------------------------------------------------------
            # Représentation du récepteur
            # --------------------------------------------------------
            "hide #1 atoms",
            "show #1 cartoon",

            # --------------------------------------------------------
            # Représentation du ligand
            # --------------------------------------------------------
            "show #2 atoms",
            "show #2 sticks",

            # --------------------------------------------------------
            # Sélection de la pose demandée
            # --------------------------------------------------------
            f"select #2.{pose}",

            # --------------------------------------------------------
            # Affichage explicite des atomes de la pose
            # --------------------------------------------------------
            f"show #2.{pose} atoms",
            f"show #2.{pose} sticks",

            # --------------------------------------------------------
            # Centrage
            # --------------------------------------------------------
            f"view #2.{pose}",

            # --------------------------------------------------------
            # Désélection
            # --------------------------------------------------------
            "select clear"
        ]

        return self.launch_gui(commands)

    # ================================================================
    # OUVERTURE DU COMPLEXE
    # ================================================================

    def open_complex_gui(
        self,
        receptor_file,
        ligand_file,
        pose=1
    ):
        """
        Ouvre automatiquement un complexe récepteur-ligand.

        Pose par défaut :
            MODEL 1

        Le récepteur est affiché en cartoon.
        Le ligand est affiché en sticks et atoms.
        """

        receptor_file = Path(receptor_file).resolve()
        ligand_file = Path(ligand_file).resolve()

        if not receptor_file.exists():
            raise FileNotFoundError(
                f"Récepteur introuvable : {receptor_file}"
            )

        if not ligand_file.exists():
            raise FileNotFoundError(
                f"Ligand introuvable : {ligand_file}"
            )

        commands = [

            # ========================================================
            # OUVERTURE
            # ========================================================

            f'open "{receptor_file}"',
            f'open "{ligand_file}"',

            # ========================================================
            # RÉCEPTEUR
            # ========================================================

            "hide #1 atoms",
            "show #1 cartoon",

            # ========================================================
            # LIGAND
            # ========================================================

            "show #2 atoms",
            "show #2 sticks",

            # ========================================================
            # POSE
            # ========================================================

            f"select #2.{pose}",

            f"show #2.{pose} atoms",
            f"show #2.{pose} sticks",

            # ========================================================
            # VUE
            # ========================================================

            f"view #2.{pose}",

            # ========================================================
            # NETTOYAGE
            # ========================================================

            "select clear"
        ]

        return self.launch_gui(commands)

    # ================================================================
    # STATUT
    # ================================================================

    def status(self):

        running = False

        if self.process is not None:
            running = self.process.poll() is None

        return {
            "engine": "UCSF ChimeraX",
            "path": self.chimerax_path,
            "ready": True,
            "process_running": running,
            "pid": self.process.pid if self.process else None
        }


# ====================================================================
# TEST
# ====================================================================

def main():

    print("=" * 70)
    print("MEXAB/MEXR ANALYZER — CHIMERAX MANAGER")
    print("=" * 70)

    manager = ChimeraXManager()

    print()
    print("ChimeraX")
    print("-" * 70)
    print(f"Path   : {manager.chimerax_path}")
    print("Status : READY")

    receptor = (
        PROJECT_ROOT
        / "docking"
        / "receptor"
        / "3W9J.pdbqt"
    )

    ligand = (
        PROJECT_ROOT
        / "docking"
        / "results"
        / "batch_vina_engine"
        / "individual"
        / "Vilazodone_CID_6918314_out.pdbqt"
    )

    print()
    print("TEST OUVERTURE COMPLEXE — POSE 1")
    print("-" * 70)

    if not receptor.exists():
        print(f"[ERREUR] Récepteur absent : {receptor}")
        return

    if not ligand.exists():
        print(f"[ERREUR] Ligand absent : {ligand}")
        return

    try:

        pid = manager.open_complex_gui(
            receptor,
            ligand,
            pose=1
        )

        print("[OK] ChimeraX lancé.")
        print(f"[OK] PID : {pid}")

        time.sleep(3)

        status = manager.status()

        print()
        print("STATUT")
        print("-" * 70)
        print(f"Processus actif : {status['process_running']}")
        print(f"PID             : {status['pid']}")

        if status["process_running"]:

            print()
            print("[OK] ChimeraX fonctionne.")
            print("[OK] Récepteur chargé.")
            print("[OK] Ligand chargé.")
            print("[OK] Pose 1 demandée.")
            print("[OK] Affichage automatique activé.")

        else:

            print()
            print("[ATTENTION] ChimeraX s'est fermé rapidement.")

    except Exception as exc:

        print()
        print(f"[ERREUR] {exc}")

    print()
    print("=" * 70)
    print("TEST CHIMERAX TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    main()
