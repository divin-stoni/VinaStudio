#!/usr/bin/env python3

import json
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "environment.json"

LIGAND_FILE = (
    PROJECT_ROOT
    / "docking"
    / "results"
    / "batch_vina_engine"
    / "individual"
    / "Vilazodone_CID_6918314_out.pdbqt"
)

RECEPTOR_FILE = (
    PROJECT_ROOT
    / "docking"
    / "receptor"
    / "3W9J.pdbqt"
)


class PoseManager:

    def __init__(self):
        self.ligand_file = LIGAND_FILE
        self.receptor_file = RECEPTOR_FILE
        self.chimerax_path = self._load_chimerax_path()
        self.poses = []

    # ================================================================
    # CHIMERAX
    # ================================================================

    def _load_chimerax_path(self):

        if not CONFIG_FILE.exists():
            raise RuntimeError(
                f"Configuration introuvable : {CONFIG_FILE}"
            )

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as handle:

            config = json.load(handle)

        chimerax = config.get(
            "tools",
            {}
        ).get(
            "chimerax",
            {}
        )

        if chimerax.get("status") != "READY":
            raise RuntimeError(
                "ChimeraX n'est pas disponible."
            )

        path = chimerax.get("path")

        if not path:
            raise RuntimeError(
                "Chemin ChimeraX absent."
            )

        if not Path(path).exists():
            raise RuntimeError(
                f"ChimeraX introuvable : {path}"
            )

        return path

    # ================================================================
    # LECTURE DES POSES
    # ================================================================

    def load_poses(self):

        if not self.ligand_file.exists():
            raise FileNotFoundError(
                f"Fichier ligand introuvable : "
                f"{self.ligand_file}"
            )

        self.poses = []

        current_pose = None

        with open(
            self.ligand_file,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as handle:

            for line in handle:

                stripped = line.strip()

                model_match = re.match(
                    r"^MODEL\s+(\d+)",
                    stripped,
                    re.IGNORECASE
                )

                if model_match:

                    pose_number = int(
                        model_match.group(1)
                    )

                    current_pose = {
                        "pose": pose_number,
                        "score": None
                    }

                    self.poses.append(
                        current_pose
                    )

                    continue

                if current_pose is None:
                    continue

                score_match = re.search(
                    r"VINA RESULT:\s*"
                    r"(-?\d+(?:\.\d+)?)",
                    stripped,
                    re.IGNORECASE
                )

                if score_match:

                    current_pose["score"] = float(
                        score_match.group(1)
                    )

        return self.poses

    # ================================================================
    # RECHERCHE D'UNE POSE
    # ================================================================

    def get_pose(self, pose_number):

        if not self.poses:
            self.load_poses()

        for pose in self.poses:

            if pose["pose"] == pose_number:
                return pose

        return None

    # ================================================================
    # MEILLEURE POSE
    # ================================================================

    def best_pose(self):

        if not self.poses:
            self.load_poses()

        valid = [
            pose
            for pose in self.poses
            if pose["score"] is not None
        ]

        if not valid:
            return None

        return min(
            valid,
            key=lambda pose: pose["score"]
        )

    # ================================================================
    # EXTRACTION POSE
    # ================================================================

    def extract_pose(self, pose_number):

        pose = self.get_pose(
            pose_number
        )

        if pose is None:
            raise ValueError(
                f"Pose {pose_number} introuvable."
            )

        output_directory = (
            PROJECT_ROOT
            / "docking"
            / "results"
            / "batch_vina_engine"
            / "selected_poses"
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file = (
            output_directory
            / (
                f"Vilazodone_pose_"
                f"{pose_number}.pdbqt"
            )
        )

        inside_pose = False
        found_pose = False
        lines = []

        model_pattern = re.compile(
            rf"^MODEL\s+{pose_number}\s*$",
            re.IGNORECASE
        )

        next_model_pattern = re.compile(
            r"^MODEL\s+\d+",
            re.IGNORECASE
        )

        with open(
            self.ligand_file,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as handle:

            for line in handle:

                stripped = line.strip()

                if model_pattern.match(
                    stripped
                ):

                    inside_pose = True
                    found_pose = True
                    lines.append(line)
                    continue

                if (
                    inside_pose
                    and next_model_pattern.match(
                        stripped
                    )
                ):
                    break

                if inside_pose:

                    lines.append(line)

                    if stripped.upper() == "ENDMDL":
                        break

        if not found_pose:

            raise RuntimeError(
                f"Impossible d'extraire "
                f"la pose {pose_number}."
            )

        if not lines:

            raise RuntimeError(
                f"La pose {pose_number} "
                f"ne contient aucune donnée."
            )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as handle:

            handle.writelines(lines)

        return output_file

    # ================================================================
    # VISUALISATION
    # ================================================================

    def visualize_pose(self, pose_number):

        pose = self.get_pose(
            pose_number
        )

        if pose is None:
            raise ValueError(
                f"Pose {pose_number} introuvable."
            )

        pose_file = self.extract_pose(
            pose_number
        )

        commands = [

            f'open "{self.receptor_file}"',

            f'open "{pose_file}"',

            "hide #1 atoms",

            "show #1 cartoons",

            "show #2 atoms",

            "show #2 bonds",

            "view"
        ]

        command_args = [
            self.chimerax_path,
            "--start",
            "default"
        ]

        for command in commands:

            command_args.extend(
                [
                    "--cmd",
                    command
                ]
            )

        process = subprocess.Popen(
            command_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return {
            "pid": process.pid,
            "pose": pose_number,
            "score": pose["score"],
            "file": str(pose_file)
        }

    # ================================================================
    # RÉSUMÉ
    # ================================================================

    def summary(self):

        if not self.poses:
            self.load_poses()

        best = self.best_pose()

        return {
            "number_of_poses": len(
                self.poses
            ),
            "best_pose": (
                best["pose"]
                if best
                else None
            ),
            "best_score": (
                best["score"]
                if best
                else None
            )
        }


def main():

    print("=" * 70)
    print(
        "MEXAB/MEXR ANALYZER — POSE MANAGER"
    )
    print("=" * 70)

    try:

        manager = PoseManager()

        print()
        print("FICHIER PDBQT")
        print("-" * 70)
        print(
            f"Ligand : "
            f"{manager.ligand_file}"
        )

        poses = manager.load_poses()

        print()
        print("POSES DÉTECTÉES")
        print("-" * 70)

        for pose in poses:

            if pose["score"] is None:

                score_text = "INCONNU"

            else:

                score_text = (
                    f"{pose['score']:8.3f} "
                    f"kcal/mol"
                )

            print(
                f"Pose {pose['pose']:2d} : "
                f"{score_text}"
            )

        summary = manager.summary()

        print()
        print("RÉSUMÉ")
        print("-" * 70)

        print(
            f"Nombre de poses : "
            f"{summary['number_of_poses']}"
        )

        print(
            f"Meilleure pose  : "
            f"{summary['best_pose']}"
        )

        print(
            f"Meilleur score  : "
            f"{summary['best_score']:.3f} "
            f"kcal/mol"
        )

        print()
        print(
            "TEST VISUALISATION — POSE 1"
        )
        print("-" * 70)

        result = manager.visualize_pose(1)

        print(
            "[OK] ChimeraX lancé."
        )

        print(
            f"[OK] PID : "
            f"{result['pid']}"
        )

        print(
            f"[OK] Pose : "
            f"{result['pose']}"
        )

        print(
            f"[OK] Score : "
            f"{result['score']:.3f} kcal/mol"
        )

        print(
            f"[OK] Fichier créé : "
            f"{result['file']}"
        )

        print()
        print(
            "[OK] Récepteur affiché en cartoon."
        )

        print(
            "[OK] Pose affichée automatiquement."
        )

        print(
            "[OK] Atomes et liaisons du ligand activés."
        )

    except Exception as exc:

        print()
        print(
            f"[ERREUR] {exc}"
        )

    print()
    print("=" * 70)
    print(
        "TEST POSE MANAGER TERMINÉ"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
