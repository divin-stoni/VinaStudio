# -*- coding: utf-8 -*-
"""
config_manager.py

Gestion centralisée de la configuration du docking AutoDock Vina.

Responsabilités :
- stocker les paramètres du docking ;
- vérifier l'existence du récepteur ;
- vérifier l'existence du dossier de ligands ;
- vérifier les paramètres de la grid box ;
- vérifier les paramètres Vina ;
- fournir une configuration simple au reste du projet.

Aucune dépendance externe.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import shutil


@dataclass
class DockingConfig:
    """Configuration complète d'un docking AutoDock Vina."""

    # ------------------------------------------------------------------
    # Chemins
    # ------------------------------------------------------------------

    project_root: Path

    receptor_path: Path
    ligands_dir: Path

    results_dir: Path

    vina_path: str = "vina"

    # ------------------------------------------------------------------
    # Grid box
    # ------------------------------------------------------------------

    center_x: float = 34.12
    center_y: float = 16.29
    center_z: float = -58.71

    size_x: float = 26.0
    size_y: float = 26.0
    size_z: float = 26.0

    # ------------------------------------------------------------------
    # Paramètres Vina
    # ------------------------------------------------------------------

    exhaustiveness: int = 32
    num_modes: int = 9
    energy_range: float = 3.0
    seed: int = 2024

    # ------------------------------------------------------------------
    # Divers
    # ------------------------------------------------------------------

    cpu: int = 0
    scoring_function: str = "vina"

    def __post_init__(self) -> None:
        """Normalise les chemins après création."""

        self.project_root = Path(self.project_root).expanduser().resolve()
        self.receptor_path = Path(self.receptor_path).expanduser().resolve()
        self.ligands_dir = Path(self.ligands_dir).expanduser().resolve()
        self.results_dir = Path(self.results_dir).expanduser().resolve()

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def validate(self) -> tuple[bool, list[str]]:
        """
        Vérifie la cohérence de la configuration.

        Returns
        -------
        tuple
            (validation_ok, liste_des_erreurs)
        """

        errors: list[str] = []

        # --------------------------------------------------------------
        # Récepteur
        # --------------------------------------------------------------

        if not self.receptor_path.exists():
            errors.append(
                f"Récepteur introuvable : {self.receptor_path}"
            )

        elif not self.receptor_path.is_file():
            errors.append(
                f"Le récepteur n'est pas un fichier : "
                f"{self.receptor_path}"
            )

        elif self.receptor_path.suffix.lower() != ".pdbqt":
            errors.append(
                f"Le récepteur doit être au format PDBQT : "
                f"{self.receptor_path}"
            )

        # --------------------------------------------------------------
        # Ligands
        # --------------------------------------------------------------

        if not self.ligands_dir.exists():
            errors.append(
                f"Dossier des ligands introuvable : {self.ligands_dir}"
            )

        elif not self.ligands_dir.is_dir():
            errors.append(
                f"Le chemin des ligands n'est pas un dossier : "
                f"{self.ligands_dir}"
            )

        # --------------------------------------------------------------
        # Grid box
        # --------------------------------------------------------------

        if self.size_x <= 0:
            errors.append("size_x doit être > 0.")

        if self.size_y <= 0:
            errors.append("size_y doit être > 0.")

        if self.size_z <= 0:
            errors.append("size_z doit être > 0.")

        # --------------------------------------------------------------
        # Exhaustiveness
        # --------------------------------------------------------------

        if self.exhaustiveness < 1:
            errors.append(
                "exhaustiveness doit être >= 1."
            )

        # --------------------------------------------------------------
        # Nombre de modes
        # --------------------------------------------------------------

        if self.num_modes < 1:
            errors.append(
                "num_modes doit être >= 1."
            )

        # --------------------------------------------------------------
        # Energy range
        # --------------------------------------------------------------

        if self.energy_range < 0:
            errors.append(
                "energy_range doit être >= 0."
            )

        # --------------------------------------------------------------
        # Seed
        # --------------------------------------------------------------

        if self.seed < 0:
            errors.append(
                "seed doit être >= 0."
            )

        # --------------------------------------------------------------
        # CPU
        # --------------------------------------------------------------

        if self.cpu < 0:
            errors.append(
                "cpu doit être >= 0."
            )

        # --------------------------------------------------------------
        # Scoring function
        # --------------------------------------------------------------

        allowed_scoring = {
            "vina",
            "ad4",
            "vinardo",
        }

        if self.scoring_function.lower() not in allowed_scoring:
            errors.append(
                "scoring_function doit être l'un de : "
                "vina, ad4, vinardo."
            )

        # --------------------------------------------------------------
        # Vina
        # --------------------------------------------------------------

        vina_executable = shutil.which(self.vina_path)

        if vina_executable is None:
            errors.append(
                f"Executable Vina introuvable : {self.vina_path}"
            )

        return len(errors) == 0, errors

    # ==================================================================
    # LIGANDS
    # ==================================================================

    def get_ligands(self) -> list[Path]:
        """
        Retourne tous les ligands PDBQT du dossier.

        Returns
        -------
        list[Path]
            Liste triée des fichiers PDBQT.
        """

        if not self.ligands_dir.exists():
            return []

        return sorted(
            path
            for path in self.ligands_dir.glob("*.pdbqt")
            if path.is_file()
        )

    def count_ligands(self) -> int:
        """Retourne le nombre de ligands disponibles."""

        return len(self.get_ligands())

    # ==================================================================
    # RÉSULTATS
    # ==================================================================

    def prepare_results_directory(self) -> Path:
        """
        Crée le dossier de résultats s'il n'existe pas.

        Returns
        -------
        Path
            Dossier de résultats.
        """

        self.results_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return self.results_dir

    # ==================================================================
    # VINA COMMAND
    # ==================================================================

    def vina_arguments(self) -> list[str]:
        """
        Construit les arguments Vina communs à tous les dockings.

        Les chemins du récepteur et les paramètres de la boîte sont
        centralisés ici.
        """

        return [
            "--receptor",
            str(self.receptor_path),

            "--center_x",
            str(self.center_x),

            "--center_y",
            str(self.center_y),

            "--center_z",
            str(self.center_z),

            "--size_x",
            str(self.size_x),

            "--size_y",
            str(self.size_y),

            "--size_z",
            str(self.size_z),

            "--exhaustiveness",
            str(self.exhaustiveness),

            "--num_modes",
            str(self.num_modes),

            "--energy_range",
            str(self.energy_range),

            "--seed",
            str(self.seed),

            "--verbosity",
            "1",
        ]

    # ==================================================================
    # DICTIONNAIRE
    # ==================================================================

    def to_dict(self) -> dict:
        """Convertit la configuration en dictionnaire."""

        data = asdict(self)

        # Path n'est pas directement pratique pour JSON/CSV.
        for key in (
            "project_root",
            "receptor_path",
            "ligands_dir",
            "results_dir",
        ):
            data[key] = str(data[key])

        return data

    # ==================================================================
    # AFFICHAGE
    # ==================================================================

    def display(self) -> None:
        """Affiche la configuration de manière lisible."""

        print("=" * 70)
        print("CONFIGURATION DOCKING — AUTODOCK VINA")
        print("=" * 70)

        print(f"Projet           : {self.project_root}")
        print(f"Récepteur        : {self.receptor_path}")
        print(f"Ligands          : {self.ligands_dir}")
        print(f"Résultats        : {self.results_dir}")
        print(f"Vina             : {self.vina_path}")

        print()
        print("Grid box")
        print("-" * 70)
        print(
            f"Centre           : "
            f"({self.center_x}, "
            f"{self.center_y}, "
            f"{self.center_z})"
        )

        print(
            f"Taille           : "
            f"({self.size_x}, "
            f"{self.size_y}, "
            f"{self.size_z})"
        )

        print()
        print("Paramètres Vina")
        print("-" * 70)
        print(f"Scoring          : {self.scoring_function}")
        print(f"Exhaustiveness   : {self.exhaustiveness}")
        print(f"Nombre de modes  : {self.num_modes}")
        print(f"Energy range     : {self.energy_range}")
        print(f"Seed             : {self.seed}")
        print(f"CPU              : {self.cpu}")

        print()
        print(f"Nombre de ligands : {self.count_ligands()}")

        print("=" * 70)


# ======================================================================
# CONFIGURATION PAR DÉFAUT DU PROJET
# ======================================================================

def create_default_config() -> DockingConfig:
    """
    Crée la configuration correspondant à l'architecture actuelle
    de MexAB_MexR_Analyzer_BETA.
    """

    project_root = Path(
        __file__
    ).resolve().parents[2]

    return DockingConfig(
        project_root=project_root,

        receptor_path=(
            project_root
            / "docking"
            / "receptor"
            / "3W9J.pdbqt"
        ),

        ligands_dir=(
            project_root
            / "docking"
            / "ligands"
            / "prepared"
        ),

        results_dir=(
            project_root
            / "docking"
            / "results"
            / "batch_src"
        ),

        vina_path="vina",

        center_x=34.12,
        center_y=16.29,
        center_z=-58.71,

        size_x=26.0,
        size_y=26.0,
        size_z=26.0,

        exhaustiveness=32,
        num_modes=9,
        energy_range=3.0,
        seed=2024,

        cpu=0,
        scoring_function="vina",
    )


# ======================================================================
# TEST
# ======================================================================

def main() -> None:
    """Test du gestionnaire de configuration."""

    config = create_default_config()

    config.display()

    print()
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    valid, errors = config.validate()

    if valid:
        print("[OK] Configuration valide.")
    else:
        print("[ERREUR] Configuration invalide.")

        for error in errors:
            print(f"  - {error}")

    print()
    print("=" * 70)
    print("LIGANDS")
    print("=" * 70)

    ligands = config.get_ligands()

    if ligands:
        for ligand in ligands:
            print(f"  - {ligand.name}")
    else:
        print("  Aucun ligand PDBQT trouvé.")

    print()
    print(f"Nombre total : {config.count_ligands()}")

    print()
    print("=" * 70)
    print("ARGUMENTS VINA")
    print("=" * 70)

    print(" ".join(config.vina_arguments()))

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
