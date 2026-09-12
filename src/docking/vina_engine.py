# -*- coding: utf-8 -*-
"""
vina_engine.py

Moteur d'exécution AutoDock Vina 1.2.x.

Fonctions :
- validation de l'environnement ;
- découverte des ligands PDBQT ;
- exécution de Vina ligand par ligand ;
- génération des PDBQT de sortie ;
- génération des logs ;
- parsing automatique des logs ;
- export du CSV complet des résultats.

Aucune dépendance externe à part Python + AutoDock Vina.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional
import csv
import shutil
import subprocess
import time
import sys


# ============================================================================
# CHEMINS DU PROJET
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# docking_parser.py est à la racine du projet
from ..docking_parser import parse_vina_log
from src.session_runtime import reset_before_docking


# ============================================================================
# RESOLUTION DE L'EXECUTABLE VINA (PATCH WINDOWS PACKAGE)
# ============================================================================

def resolve_vina_executable() -> str:
    """
    Determine le chemin de l'executable Vina a utiliser.

    - Si l'application tourne en executable package (PyInstaller)
      ET qu'un binaire vina embarque existe, on l'utilise
      directement (docking/bin/vina.exe sur Windows,
      docking/bin/vina sur Linux).
    - Sinon (execution normale en Python), on garde le
      comportement historique : "vina" recherche dans le PATH
      systeme.
    """
    from src.tools.runtime_env import configure_bundled_runtime
    configure_bundled_runtime()

    if getattr(sys, "frozen", False):
        if sys.platform.startswith("linux"):
            bundled = PROJECT_ROOT / "docking" / "bin" / "vina"
        else:
            bundled = PROJECT_ROOT / "docking" / "bin" / "vina.exe"

        if bundled.exists():
            return str(bundled)

    return "vina"


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class VinaConfig:
    """Configuration complète d'AutoDock Vina."""

    vina_executable: str = field(default_factory=resolve_vina_executable)

    receptor: Path = (
        PROJECT_ROOT / "docking/receptor/3W9J.pdbqt"
    )

    ligands_dir: Path = (
        PROJECT_ROOT / "docking/ligands/prepared"
    )

    results_dir: Path = (
        PROJECT_ROOT / "docking/results/batch_vina_engine"
    )

    # Grid box
    center_x: float = 34.12
    center_y: float = 16.29
    center_z: float = -58.71

    size_x: float = 26.0
    size_y: float = 26.0
    size_z: float = 26.0

    # Vina
    exhaustiveness: int = 32
    num_modes: int = 9
    energy_range: float = 3.0

    seed: int = 2024
    cpu: int = 0
    verbosity: int = 1


# ============================================================================
# PROFILS DE CIBLES
# ============================================================================

def create_target_config(
    target: str,
    results_root: Optional[Path] = None,
) -> VinaConfig:
    """
    Crée une configuration Vina correspondant à une cible biologique.

    Cibles supportées :
        MexB
        MexR

    Le profil MexB conserve exactement les paramètres historiques
    du moteur actuel.

    Le profil MexR utilise le récepteur 1LNW et la grille validée
    précédemment dans le projet.
    """

    normalized = str(target).strip().lower()

    project_root = PROJECT_ROOT

    if results_root is None:
        results_root = (
            project_root
            / "docking"
            / "results"
            / "batch_vina_engine"
        )
    else:
        results_root = Path(results_root)

    if normalized == "mexb":
        return VinaConfig(
            vina_executable=resolve_vina_executable(),

            receptor=(
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
                results_root
                / "MexB"
            ),

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
            verbosity=1,
        )

    if normalized == "mexr":
        return VinaConfig(
            vina_executable=resolve_vina_executable(),

            receptor=(
                project_root
                / "docking"
                / "receptor"
                / "MexR"
                / "MEXR_1LNW.pdbqt"
            ),

            ligands_dir=(
                project_root
                / "docking"
                / "ligands"
                / "prepared"
            ),

            results_dir=(
                results_root
                / "MexR"
            ),

            center_x=9.11737,
            center_y=34.0078,
            center_z=3.24093,

            size_x=25.0,
            size_y=25.0,
            size_z=25.0,

            exhaustiveness=32,
            num_modes=20,
            energy_range=3.0,

            seed=42,
            cpu=8,
            verbosity=1,
        )

    raise ValueError(
        "Cible de docking inconnue : "
        f"{target!r}. Cibles disponibles : MexB, MexR."
    )


# ============================================================================
# RESULTAT INDIVIDUEL
# ============================================================================

@dataclass
class VinaDockingResult:
    """Résultat d'un docking individuel."""

    molecule: str
    ligand_file: str
    status: str
    groupe: str = ""

    best_affinity: Optional[float] = None
    best_mode: Optional[int] = None
    n_modes: int = 0

    output_pdbqt: Optional[str] = None
    log_file: Optional[str] = None

    error: Optional[str] = None
    duration_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# MOTEUR
# ============================================================================

class VinaEngine:
    """Moteur principal de docking AutoDock Vina."""

    def __init__(
        self,
        config: Optional[VinaConfig] = None,
    ):

        self.config = config or VinaConfig()

        self.config.receptor = Path(
            self.config.receptor
        )

        self.config.ligands_dir = Path(
            self.config.ligands_dir
        )

        self.config.results_dir = Path(
            self.config.results_dir
        )

        self.individual_dir = (
            self.config.results_dir / "individual"
        )

        self.logs_dir = (
            self.config.results_dir / "logs"
        )

        # Processus Vina actuellement exécuté.
        # Utilisé par le worker GUI pour permettre
        # une annulation réelle du docking.
        self._current_process = None

        self.individual_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.logs_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ========================================================================
    # ANNULATION DU PROCESSUS VINA
    # ========================================================================

    def cancel_current_process(self) -> bool:
        """
        Interrompt le processus Vina actuellement en cours.

        Retourne True si un processus actif a été interrompu,
        sinon False.
        """

        process = self._current_process

        if process is None:
            return False

        try:
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

                return True

        except Exception as exc:
            print(
                f"[ANNULATION] Erreur lors de l'arrêt de Vina : {exc}"
            )

        finally:
            if process.poll() is not None:
                self._current_process = None

        return False

    # ========================================================================
    # VERIFICATION VINA
    # ========================================================================

    def check_vina(self) -> tuple[bool, str]:

        executable = shutil.which(
            self.config.vina_executable
        )

        if executable is None:
            return (
                False,
                f"Vina introuvable : "
                f"{self.config.vina_executable}",
            )

        try:

            process = subprocess.run(
                [
                    executable,
                    "--version",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            version = (
                process.stdout.strip()
                or process.stderr.strip()
            )

            return True, version

        except Exception as exc:

            return (
                False,
                f"Erreur Vina : {exc}",
            )

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate(self) -> tuple[bool, list[str]]:

        errors = []

        # Récepteur
        if not self.config.receptor.exists():
            errors.append(
                f"Récepteur introuvable : "
                f"{self.config.receptor}"
            )

        elif self.config.receptor.suffix.lower() != ".pdbqt":
            errors.append(
                "Le récepteur doit être au format PDBQT."
            )

        # Ligands
        if not self.config.ligands_dir.exists():
            errors.append(
                f"Dossier ligands introuvable : "
                f"{self.config.ligands_dir}"
            )

        # Grid
        if self.config.size_x <= 0:
            errors.append(
                "size_x doit être > 0"
            )

        if self.config.size_y <= 0:
            errors.append(
                "size_y doit être > 0"
            )

        if self.config.size_z <= 0:
            errors.append(
                "size_z doit être > 0"
            )

        # Vina
        if self.config.exhaustiveness < 1:
            errors.append(
                "exhaustiveness doit être >= 1"
            )

        if self.config.num_modes < 1:
            errors.append(
                "num_modes doit être >= 1"
            )

        if self.config.energy_range < 0:
            errors.append(
                "energy_range doit être >= 0"
            )

        # Exécutable
        vina_ok, vina_message = self.check_vina()

        if not vina_ok:
            errors.append(vina_message)

        return len(errors) == 0, errors

    # ========================================================================
    # DECOUVERTE DES LIGANDS
    # ========================================================================

    def discover_ligands(self) -> list[Path]:

        if not self.config.ligands_dir.exists():
            return []

        return sorted(
            self.config.ligands_dir.glob("*.pdbqt")
        )

    # ========================================================================
    # CONSTRUCTION DE LA COMMANDE
    # ========================================================================

    def build_command(
        self,
        ligand: Path,
        output: Path,
    ) -> list[str]:

        # Génération automatique du fichier config Vina
        self.write_config_file()

        executable = shutil.which(
            self.config.vina_executable
        )

        if executable is None:
            executable = self.config.vina_executable

        command = [
            executable,

            "--receptor",
            str(self.config.receptor),

            "--ligand",
            str(ligand),

            "--center_x",
            str(self.config.center_x),

            "--center_y",
            str(self.config.center_y),

            "--center_z",
            str(self.config.center_z),

            "--size_x",
            str(self.config.size_x),

            "--size_y",
            str(self.config.size_y),

            "--size_z",
            str(self.config.size_z),

            "--exhaustiveness",
            str(self.config.exhaustiveness),

            "--num_modes",
            str(self.config.num_modes),

            "--energy_range",
            str(self.config.energy_range),

            "--seed",
            str(self.config.seed),

            "--out",
            str(output),

            "--verbosity",
            str(self.config.verbosity),
        ]

        if self.config.cpu > 0:

            command.extend(
                [
                    "--cpu",
                    str(self.config.cpu),
                ]
            )

        return command


    def write_config_file(self):
        """
        Génère automatiquement le fichier config.txt Vina
        correspondant à la cible active.
        """

        config_file = (
            self.config.results_dir
            / "config.txt"
        )

        config_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        content = f"""receptor = {self.config.receptor}
ligand = {self.config.ligands_dir}

center_x = {self.config.center_x}
center_y = {self.config.center_y}
center_z = {self.config.center_z}

size_x = {self.config.size_x}
size_y = {self.config.size_y}
size_z = {self.config.size_z}

exhaustiveness = {self.config.exhaustiveness}
num_modes = {self.config.num_modes}
energy_range = {self.config.energy_range}

seed = {self.config.seed}
"""

        config_file.write_text(
            content,
            encoding="utf-8"
        )

        return config_file


    # ========================================================================
    # DOCKING D'UN LIGAND
    # ========================================================================

    def dock_ligand(
        self,
        ligand: Path,
    ) -> VinaDockingResult:

        ligand = Path(ligand)

        molecule = ligand.stem

        output_file = (
            self.individual_dir
            / f"{molecule}_out.pdbqt"
        )

        log_file = (
            self.logs_dir
            / f"{molecule}.log"
        )

        print()
        print("-" * 70)
        print(f"[DOCKING] {molecule}")
        print("-" * 70)

        command = self.build_command(
            ligand,
            output_file,
        )

        print(" ".join(command))

        start = time.perf_counter()

        try:

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            # Rend le processus accessible à cancel_current_process().
            self._current_process = process

            stdout, _ = process.communicate()

            duration = (
                time.perf_counter() - start
            )

            # Le processus n'est plus actif.
            self._current_process = None

            # Sauvegarde du log
            log_file.write_text(
                stdout or "",
                encoding="utf-8",
            )

            # ------------------------------------------------------------
            # ERREUR VINA
            # ------------------------------------------------------------

            if process.returncode != 0:

                return VinaDockingResult(
                    molecule=molecule,
                    ligand_file=ligand.name,
                    status="FAILED",
                    output_pdbqt=str(
                        output_file
                    ),
                    log_file=str(log_file),
                    error=(
                        f"Vina code retour "
                        f"{process.returncode}"
                    ),
                    duration_seconds=duration,
                )

            # ------------------------------------------------------------
            # VERIFICATION PDBQT
            # ------------------------------------------------------------

            if not output_file.exists():

                return VinaDockingResult(
                    molecule=molecule,
                    ligand_file=ligand.name,
                    status="FAILED",
                    log_file=str(log_file),
                    error=(
                        "Vina terminé sans générer "
                        "le fichier PDBQT."
                    ),
                    duration_seconds=duration,
                )

            # ------------------------------------------------------------
            # PARSING
            # ------------------------------------------------------------

            parsed = parse_vina_log(
                log_file
            )

            if not parsed.success:

                return VinaDockingResult(
                    molecule=molecule,
                    ligand_file=ligand.name,
                    status="FAILED",
                    output_pdbqt=str(
                        output_file
                    ),
                    log_file=str(log_file),
                    error=(
                        parsed.error
                        or "Impossible de parser le log."
                    ),
                    duration_seconds=duration,
                )

            best = parsed.best_mode

            print(
                f"[OK] Modes obtenus : "
                f"{parsed.n_modes}"
            )

            if best is not None:

                print(
                    f"[OK] Meilleur score : "
                    f"{best.affinity:.3f} kcal/mol"
                )

            return VinaDockingResult(
                molecule=molecule,
                ligand_file=ligand.name,
                status="OK",
                best_affinity=parsed.best_affinity,
                best_mode=(
                    best.mode
                    if best is not None
                    else None
                ),
                n_modes=parsed.n_modes,
                output_pdbqt=str(
                    output_file
                ),
                log_file=str(log_file),
                duration_seconds=duration,
            )

        except Exception as exc:

            duration = (
                time.perf_counter() - start
            )

            return VinaDockingResult(
                molecule=molecule,
                ligand_file=ligand.name,
                status="FAILED",
                output_pdbqt=str(
                    output_file
                ),
                log_file=str(log_file),
                error=str(exc),
                duration_seconds=duration,
            )

    # ========================================================================
    # BATCH COMPLET
    # ========================================================================

    def run_batch(
        self,
        ligands: Optional[list[Path]] = None,
    ) -> list[VinaDockingResult]:

        if ligands is None:
            ligands = self.discover_ligands()

        print("=" * 70)
        print("BATCH DOCKING — MEXB / 3W9J")
        print("=" * 70)

        print(
            f"Nombre de ligands : {len(ligands)}"
        )

        print(
            f"Récepteur         : "
            f"{self.config.receptor.name}"
        )

        print(
            f"Exhaustiveness    : "
            f"{self.config.exhaustiveness}"
        )

        print(
            f"Seed              : "
            f"{self.config.seed}"
        )

        print()

        if not ligands:
            print(
                "[ERREUR] Aucun ligand PDBQT trouvé."
            )
            return []

        results: list[VinaDockingResult] = []

        total_start = time.perf_counter()

        for index, ligand in enumerate(
            ligands,
            start=1,
        ):

            # =============================================================
            # SESSION PROPRE — nouveau docking
            # =============================================================
            reset_before_docking()

            print(
                f"[{index}/{len(ligands)}] "
                f"{ligand.name}"
            )

            result = self.dock_ligand(
                ligand
            )

            results.append(result)

        total_duration = (
            time.perf_counter()
            - total_start
        )

        # ------------------------------------------------------------
        # EXPORT CSV
        # ------------------------------------------------------------

        csv_path = self.export_csv(
            results
        )

        # ------------------------------------------------------------
        # RESUME
        # ------------------------------------------------------------

        success_count = sum(
            result.status == "OK"
            for result in results
        )

        failed_count = (
            len(results) - success_count
        )

        print()
        print("=" * 70)
        print("BATCH DOCKING TERMINE")
        print("=" * 70)

        print(
            f"Total       : {len(results)}"
        )

        print(
            f"Réussis     : {success_count}"
        )

        print(
            f"Échecs      : {failed_count}"
        )

        print(
            f"Durée       : "
            f"{total_duration:.2f} secondes"
        )

        print(
            f"Résultats   : "
            f"{self.config.results_dir}"
        )

        print(
            f"CSV         : {csv_path}"
        )

        print("=" * 70)

        return results

    # ========================================================================
    # EXPORT CSV
    # ========================================================================

    def export_csv(
        self,
        results: list[VinaDockingResult],
    ) -> Path:

        self.config.results_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        csv_path = (
            self.config.results_dir
            / "docking_results.csv"
        )

        fieldnames = [
            "molecule",
            "ligand_file",
            "groupe",
            "status",
            "best_affinity",
            "best_mode",
            "n_modes",
            "output_pdbqt",
            "log_file",
            "error",
            "duration_seconds",
        ]

        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for result in results:

                writer.writerow(
                    result.to_dict()
                )

        return csv_path


# ============================================================================
# CAMPAGNE DOUBLE MEXB / MEXR
# ============================================================================

def export_combined_csv(
    mexb_results: list[VinaDockingResult],
    mexr_results: list[VinaDockingResult],
    output_path: str | Path,
) -> Path:
    """
    Fusionne les résultats MexB et MexR par molécule.

    Chaque molécule apparaît sur une seule ligne.

    Les résultats individuels restent conservés dans :
        .../MexB/docking_results.csv
        .../MexR/docking_results.csv
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mexb_by_molecule = {}

    for result in mexb_results:
        molecule = str(
            result.molecule
        ).strip()

        if not molecule:
            raise ValueError(
                "Un résultat MexB possède un nom de molécule vide."
            )

        if molecule in mexb_by_molecule:
            raise ValueError(
                "Doublon de molécule détecté dans les résultats MexB : "
                + molecule
            )

        mexb_by_molecule[molecule] = result

    mexr_by_molecule = {}

    for result in mexr_results:
        molecule = str(
            result.molecule
        ).strip()

        if not molecule:
            raise ValueError(
                "Un résultat MexR possède un nom de molécule vide."
            )

        if molecule in mexr_by_molecule:
            raise ValueError(
                "Doublon de molécule détecté dans les résultats MexR : "
                + molecule
            )

        mexr_by_molecule[molecule] = result

    molecules = sorted(
        set(mexb_by_molecule)
        | set(mexr_by_molecule)
    )

    fieldnames = [
        "molecule",
        "ligand_file",
        "groupe",

        "status_mexb",
        "best_affinity_mexb",
        "best_mode_mexb",
        "n_modes_mexb",
        "output_pdbqt_mexb",
        "log_file_mexb",
        "error_mexb",
        "duration_seconds_mexb",

        "status_mexr",
        "best_affinity_mexr",
        "best_mode_mexr",
        "n_modes_mexr",
        "output_pdbqt_mexr",
        "log_file_mexr",
        "error_mexr",
        "duration_seconds_mexr",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for molecule in molecules:

            mexb = mexb_by_molecule.get(
                molecule
            )

            mexr = mexr_by_molecule.get(
                molecule
            )

            reference = (
                mexb
                if mexb is not None
                else mexr
            )

            row = {
                "molecule": molecule,
                "ligand_file": (
                    reference.ligand_file
                    if reference is not None
                    else ""
                ),
                "groupe": (
                    (
                        mexb.groupe
                        if mexb is not None
                        else ""
                    )
                    or (
                        mexr.groupe
                        if mexr is not None
                        else ""
                    )
                ),

                "status_mexb": (
                    mexb.status
                    if mexb is not None
                    else "NOT_RUN"
                ),
                "best_affinity_mexb": (
                    mexb.best_affinity
                    if mexb is not None
                    else ""
                ),
                "best_mode_mexb": (
                    mexb.best_mode
                    if mexb is not None
                    else ""
                ),
                "n_modes_mexb": (
                    mexb.n_modes
                    if mexb is not None
                    else ""
                ),
                "output_pdbqt_mexb": (
                    mexb.output_pdbqt
                    if mexb is not None
                    else ""
                ),
                "log_file_mexb": (
                    mexb.log_file
                    if mexb is not None
                    else ""
                ),
                "error_mexb": (
                    mexb.error
                    if mexb is not None
                    else "Résultat MexB absent."
                ),
                "duration_seconds_mexb": (
                    mexb.duration_seconds
                    if mexb is not None
                    else ""
                ),

                "status_mexr": (
                    mexr.status
                    if mexr is not None
                    else "NOT_RUN"
                ),
                "best_affinity_mexr": (
                    mexr.best_affinity
                    if mexr is not None
                    else ""
                ),
                "best_mode_mexr": (
                    mexr.best_mode
                    if mexr is not None
                    else ""
                ),
                "n_modes_mexr": (
                    mexr.n_modes
                    if mexr is not None
                    else ""
                ),
                "output_pdbqt_mexr": (
                    mexr.output_pdbqt
                    if mexr is not None
                    else ""
                ),
                "log_file_mexr": (
                    mexr.log_file
                    if mexr is not None
                    else ""
                ),
                "error_mexr": (
                    mexr.error
                    if mexr is not None
                    else "Résultat MexR absent."
                ),
                "duration_seconds_mexr": (
                    mexr.duration_seconds
                    if mexr is not None
                    else ""
                ),
            }

            writer.writerow(
                row
            )

    return output_path


def run_dual_batch(
    ligands: Optional[list[Path]] = None,
    ligand_groups: Optional[dict[str, str]] = None,
    results_root: Optional[Path] = None,
    progress_callback=None,
):
    """
    Exécute une campagne successive MexB + MexR.

    Pour chaque ligand :

        1. docking MexB
        2. docking MexR

    Puis :

        - export CSV MexB ;
        - export CSV MexR ;
        - export CSV fusionné par molécule.

    Parameters
    ----------
    ligands:
        Liste explicite des ligands PDBQT.

        Si None, les ligands du dossier préparé du profil MexB
        sont utilisés.

    ligand_groups:
        Mapping :
            chemin absolu du ligand -> groupe.

    results_root:
        Racine de sortie.
        Par défaut :
            docking/results/batch_vina_engine

    progress_callback:
        Fonction optionnelle appelée sous la forme :

            progress_callback(
                current,
                total,
                target,
                ligand_name,
            )
    """

    ligand_groups = (
        ligand_groups
        or {}
    )

    if results_root is None:
        results_root = (
            PROJECT_ROOT
            / "docking"
            / "results"
            / "batch_vina_engine"
        )
    else:
        results_root = Path(
            results_root
        ).expanduser().resolve()

    # ------------------------------------------------------------------
    # PROFILS
    # ------------------------------------------------------------------

    mexb_config = create_target_config(
        "MexB",
        results_root,
    )

    mexr_config = create_target_config(
        "MexR",
        results_root,
    )

    mexb_engine = VinaEngine(
        mexb_config
    )

    mexr_engine = VinaEngine(
        mexr_config
    )

    # ------------------------------------------------------------------
    # LIGANDS
    # ------------------------------------------------------------------

    if ligands is None:
        ligands = mexb_engine.discover_ligands()

    ligands = [
        Path(ligand)
        for ligand in ligands
    ]

    if not ligands:
        raise RuntimeError(
            "Aucun ligand PDBQT disponible pour la campagne double."
        )

    # ------------------------------------------------------------------
    # VERIFICATION DES DOUBLONS
    # ------------------------------------------------------------------

    molecule_names = {}

    for ligand in ligands:

        molecule = ligand.stem

        if molecule in molecule_names:
            raise ValueError(
                "Deux ligands portent le même identifiant moléculaire : "
                f"{molecule}\n"
                f"1 : {molecule_names[molecule]}\n"
                f"2 : {ligand}"
            )

        molecule_names[molecule] = ligand

    # ------------------------------------------------------------------
    # VALIDATION DES DEUX MOTEURS AVANT DE COMMENCER
    # ------------------------------------------------------------------

    mexb_valid, mexb_errors = (
        mexb_engine.validate()
    )

    if not mexb_valid:
        raise RuntimeError(
            "Configuration MexB invalide.\n\n"
            + "\n".join(
                mexb_errors
            )
        )

    mexr_valid, mexr_errors = (
        mexr_engine.validate()
    )

    if not mexr_valid:
        raise RuntimeError(
            "Configuration MexR invalide.\n\n"
            + "\n".join(
                mexr_errors
            )
        )

    print("=" * 70)
    print("CAMPAGNE DOUBLE — MEXB + MEXR")
    print("=" * 70)

    print(
        f"Nombre de ligands : {len(ligands)}"
    )

    print(
        f"MexB              : "
        f"{mexb_config.receptor.name}"
    )

    print(
        f"MexR              : "
        f"{mexr_config.receptor.name}"
    )

    print()

    # ------------------------------------------------------------------
    # RESULTATS
    # ------------------------------------------------------------------

    mexb_results: list[VinaDockingResult] = []
    mexr_results: list[VinaDockingResult] = []

    total_steps = (
        len(ligands) * 2
    )

    current_step = 0

    # ------------------------------------------------------------------
    # DOCKING SUCCESSIF
    # ------------------------------------------------------------------

    for ligand in ligands:

        molecule = ligand.stem

        group = ligand_groups.get(
            str(
                ligand.resolve()
            ),
            "",
        )

        # ==============================================================
        # MEXB
        # ==============================================================

        current_step += 1

        if progress_callback is not None:
            progress_callback(
                current_step,
                total_steps,
                "MexB",
                ligand.name,
            )

        print()
        print(
            f"[{current_step}/{total_steps}] "
            f"MexB — {molecule}"
        )

        mexb_result = mexb_engine.dock_ligand(
            ligand
        )

        mexb_result.groupe = group

        mexb_results.append(
            mexb_result
        )

        # ==============================================================
        # MEXR
        # ==============================================================

        current_step += 1

        if progress_callback is not None:
            progress_callback(
                current_step,
                total_steps,
                "MexR",
                ligand.name,
            )

        print()
        print(
            f"[{current_step}/{total_steps}] "
            f"MexR — {molecule}"
        )

        mexr_result = mexr_engine.dock_ligand(
            ligand
        )

        mexr_result.groupe = group

        mexr_results.append(
            mexr_result
        )

    # ------------------------------------------------------------------
    # EXPORTS INDIVIDUELS
    # ------------------------------------------------------------------

    mexb_csv = mexb_engine.export_csv(
        mexb_results
    )

    mexr_csv = mexr_engine.export_csv(
        mexr_results
    )

    # ------------------------------------------------------------------
    # EXPORT COMBINE
    # ------------------------------------------------------------------

    combined_dir = (
        results_root
        / "combined"
    )

    combined_csv = (
        combined_dir
        / "docking_results_MexB_MexR.csv"
    )

    export_combined_csv(
        mexb_results,
        mexr_results,
        combined_csv,
    )

    # ------------------------------------------------------------------
    # STATISTIQUES
    # ------------------------------------------------------------------

    mexb_success = sum(
        result.status == "OK"
        for result in mexb_results
    )

    mexr_success = sum(
        result.status == "OK"
        for result in mexr_results
    )

    mexb_failed = (
        len(mexb_results)
        - mexb_success
    )

    mexr_failed = (
        len(mexr_results)
        - mexr_success
    )

    dual_success = sum(
        mexb.status == "OK"
        and mexr.status == "OK"
        for mexb, mexr in zip(
            mexb_results,
            mexr_results,
        )
    )

    print()
    print("=" * 70)
    print("CAMPAGNE DOUBLE TERMINEE")
    print("=" * 70)

    print(
        f"MexB : "
        f"{mexb_success}/{len(mexb_results)} réussi(s) "
        f"| {mexb_failed} échec(s)"
    )

    print(
        f"MexR : "
        f"{mexr_success}/{len(mexr_results)} réussi(s) "
        f"| {mexr_failed} échec(s)"
    )

    print(
        f"Double réussite : "
        f"{dual_success}/{len(ligands)}"
    )

    print()
    print(
        f"CSV MexB      : {mexb_csv}"
    )

    print(
        f"CSV MexR      : {mexr_csv}"
    )

    print(
        f"CSV combiné   : {combined_csv}"
    )

    print("=" * 70)

    return {
        "mexb_results": mexb_results,
        "mexr_results": mexr_results,
        "mexb_csv": mexb_csv,
        "mexr_csv": mexr_csv,
        "combined_csv": combined_csv,
    }



# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    print("=" * 70)
    print("VINA ENGINE — BATCH COMPLET")
    print("=" * 70)

    config = VinaConfig()

    engine = VinaEngine(
        config
    )

    # ========================================================================
    # VALIDATION
    # ========================================================================

    valid, errors = engine.validate()

    print()
    print("VALIDATION")
    print("-" * 70)

    if not valid:

        print(
            "[ERREUR] Configuration invalide."
        )

        for error in errors:
            print(f"  - {error}")

        return 1

    print(
        "[OK] Configuration valide."
    )

    # ========================================================================
    # VINA
    # ========================================================================

    vina_ok, vina_version = (
        engine.check_vina()
    )

    print()
    print("VINA")
    print("-" * 70)
    print(vina_version)

    if not vina_ok:
        return 1

    # ========================================================================
    # LIGANDS
    # ========================================================================

    ligands = engine.discover_ligands()

    print()
    print("LIGANDS")
    print("-" * 70)

    for ligand in ligands:
        print(
            f"  - {ligand.name}"
        )

    print(
        f"\nNombre total : {len(ligands)}"
    )

    if not ligands:

        print(
            "[ERREUR] Aucun ligand PDBQT trouvé."
        )

        return 1

    # ========================================================================
    # BATCH COMPLET
    # ========================================================================

    print()
    print("=" * 70)
    print("LANCEMENT DU BATCH COMPLET")
    print("=" * 70)

    results = engine.run_batch(
        ligands
    )

    # ========================================================================
    # VERIFICATION
    # ========================================================================

    success_count = sum(
        result.status == "OK"
        for result in results
    )

    failed_count = (
        len(results) - success_count
    )

    print()
    print("=" * 70)
    print("VERIFICATION FINALE")
    print("=" * 70)

    print(
        f"Dockings réussis : "
        f"{success_count}/{len(results)}"
    )

    print(
        f"Dockings échoués : "
        f"{failed_count}/{len(results)}"
    )

    csv_path = (
        config.results_dir
        / "docking_results.csv"
    )

    print(
        f"CSV disponible   : "
        f"{csv_path}"
    )

    print("=" * 70)

    if failed_count == 0 and success_count > 0:
        print(
            "BATCH TERMINE AVEC SUCCES."
        )
        return 0

    if success_count > 0:
        print(
            "BATCH TERMINE AVEC DES ECHECS."
        )
        return 0

    print(
        "AUCUN DOCKING N'A REUSSI."
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
