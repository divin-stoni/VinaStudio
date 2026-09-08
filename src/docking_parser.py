# -*- coding: utf-8 -*-
"""
docking_parser.py

Parser des résultats AutoDock Vina 1.2.x.

Responsabilités :
- lire un fichier log Vina ;
- extraire les paramètres principaux ;
- extraire les modes de docking ;
- récupérer la meilleure affinité ;
- récupérer le nombre de modes ;
- fournir des structures Python simples au moteur de docking.

Aucune dépendance externe.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Optional


@dataclass
class DockingMode:
    """Un mode de docking Vina."""

    mode: int
    affinity: float
    rmsd_lb: float
    rmsd_ub: float


@dataclass
class VinaResult:
    """Résultat complet d'un docking Vina."""

    success: bool
    version: Optional[str] = None
    scoring_function: Optional[str] = None
    receptor: Optional[str] = None
    ligand: Optional[str] = None

    center_x: Optional[float] = None
    center_y: Optional[float] = None
    center_z: Optional[float] = None

    size_x: Optional[float] = None
    size_y: Optional[float] = None
    size_z: Optional[float] = None

    exhaustiveness: Optional[int] = None
    cpu: Optional[int] = None
    seed: Optional[int] = None

    modes: list[DockingMode] | None = None

    error: Optional[str] = None

    @property
    def best_mode(self) -> Optional[DockingMode]:
        """Retourne le meilleur mode selon l'affinité Vina."""
        if not self.modes:
            return None

        return min(self.modes, key=lambda x: x.affinity)

    @property
    def best_affinity(self) -> Optional[float]:
        """Retourne la meilleure affinité."""
        best = self.best_mode
        return best.affinity if best else None

    @property
    def n_modes(self) -> int:
        """Nombre de modes détectés."""
        return len(self.modes or [])

    def to_dict(self) -> dict:
        """Convertit le résultat en dictionnaire."""
        data = asdict(self)

        data["best_affinity"] = self.best_affinity
        data["best_mode"] = (
            self.best_mode.mode
            if self.best_mode is not None
            else None
        )
        data["n_modes"] = self.n_modes

        # On conserve les modes détaillés séparément.
        data["modes"] = [
            asdict(mode)
            for mode in (self.modes or [])
        ]

        return data


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

_RE_VERSION = re.compile(
    r"AutoDock Vina\s+v([0-9]+(?:\.[0-9]+)+)",
    re.IGNORECASE,
)

_RE_SCORING = re.compile(
    r"Scoring function\s*:\s*(\S+)",
    re.IGNORECASE,
)

_RE_RECEPTOR = re.compile(
    r"Rigid receptor\s*:\s*(.+)",
    re.IGNORECASE,
)

_RE_LIGAND = re.compile(
    r"Ligand\s*:\s*(.+)",
    re.IGNORECASE,
)

_RE_GRID_CENTER = re.compile(
    r"Grid center\s*:\s*X\s+([-+0-9.eE]+)\s+"
    r"Y\s+([-+0-9.eE]+)\s+"
    r"Z\s+([-+0-9.eE]+)",
    re.IGNORECASE,
)

_RE_GRID_SIZE = re.compile(
    r"Grid size\s*:\s*X\s+([-+0-9.eE]+)\s+"
    r"Y\s+([-+0-9.eE]+)\s+"
    r"Z\s+([-+0-9.eE]+)",
    re.IGNORECASE,
)

_RE_EXHAUSTIVENESS = re.compile(
    r"Exhaustiveness\s*:\s*(\d+)",
    re.IGNORECASE,
)

_RE_CPU = re.compile(
    r"CPU\s*:\s*(\d+)",
    re.IGNORECASE,
)

_RE_SEED = re.compile(
    r"random seed\s*:\s*(\d+)",
    re.IGNORECASE,
)

# Exemple Vina :
#
# 1       -7.329          0          0
# 2       -7.271      2.183      4.879
#
_RE_MODE = re.compile(
    r"^\s*(\d+)\s+"
    r"([-+]?\d+(?:\.\d+)?)\s+"
    r"([-+]?\d+(?:\.\d+)?)\s+"
    r"([-+]?\d+(?:\.\d+)?)\s*$"
)


def _float(value: str) -> float:
    """Conversion float robuste."""
    return float(value.strip())


def parse_vina_log(log_path: str | Path) -> VinaResult:
    """
    Analyse un fichier log AutoDock Vina.

    Parameters
    ----------
    log_path:
        Chemin du fichier log.

    Returns
    -------
    VinaResult
    """

    path = Path(log_path)

    if not path.exists():
        return VinaResult(
            success=False,
            error=f"Fichier log introuvable : {path}",
            modes=[],
        )

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return VinaResult(
            success=False,
            error=f"Impossible de lire le log : {exc}",
            modes=[],
        )

    result = VinaResult(
        success=False,
        modes=[],
    )

    for line in text.splitlines():

        match = _RE_VERSION.search(line)
        if match:
            result.version = match.group(1)
            continue

        match = _RE_SCORING.search(line)
        if match:
            result.scoring_function = match.group(1)
            continue

        match = _RE_RECEPTOR.search(line)
        if match:
            result.receptor = match.group(1).strip()
            continue

        match = _RE_LIGAND.search(line)
        if match:
            result.ligand = match.group(1).strip()
            continue

        match = _RE_GRID_CENTER.search(line)
        if match:
            result.center_x = _float(match.group(1))
            result.center_y = _float(match.group(2))
            result.center_z = _float(match.group(3))
            continue

        match = _RE_GRID_SIZE.search(line)
        if match:
            result.size_x = _float(match.group(1))
            result.size_y = _float(match.group(2))
            result.size_z = _float(match.group(3))
            continue

        match = _RE_EXHAUSTIVENESS.search(line)
        if match:
            result.exhaustiveness = int(match.group(1))
            continue

        match = _RE_CPU.search(line)
        if match:
            result.cpu = int(match.group(1))
            continue

        match = _RE_SEED.search(line)
        if match:
            result.seed = int(match.group(1))
            continue

        match = _RE_MODE.match(line)
        if match:
            try:
                mode = DockingMode(
                    mode=int(match.group(1)),
                    affinity=_float(match.group(2)),
                    rmsd_lb=_float(match.group(3)),
                    rmsd_ub=_float(match.group(4)),
                )

                result.modes.append(mode)

            except ValueError:
                pass

    # Un docking valide doit avoir au moins un mode.
    if result.modes:
        result.success = True
    else:
        result.success = False

        if "error" not in text.lower():
            result.error = (
                "Aucun mode de docking détecté dans le fichier log."
            )
        else:
            result.error = (
                "AutoDock Vina semble avoir signalé une erreur."
            )

    return result


def parse_vina_text(text: str) -> VinaResult:
    """
    Variante utile pour les tests unitaires.

    Analyse directement le texte d'un log Vina sans créer de fichier.
    """

    result = VinaResult(
        success=False,
        modes=[],
    )

    for line in text.splitlines():

        match = _RE_VERSION.search(line)
        if match:
            result.version = match.group(1)
            continue

        match = _RE_SCORING.search(line)
        if match:
            result.scoring_function = match.group(1)
            continue

        match = _RE_RECEPTOR.search(line)
        if match:
            result.receptor = match.group(1).strip()
            continue

        match = _RE_LIGAND.search(line)
        if match:
            result.ligand = match.group(1).strip()
            continue

        match = _RE_GRID_CENTER.search(line)
        if match:
            result.center_x = _float(match.group(1))
            result.center_y = _float(match.group(2))
            result.center_z = _float(match.group(3))
            continue

        match = _RE_GRID_SIZE.search(line)
        if match:
            result.size_x = _float(match.group(1))
            result.size_y = _float(match.group(2))
            result.size_z = _float(match.group(3))
            continue

        match = _RE_EXHAUSTIVENESS.search(line)
        if match:
            result.exhaustiveness = int(match.group(1))
            continue

        match = _RE_CPU.search(line)
        if match:
            result.cpu = int(match.group(1))
            continue

        match = _RE_SEED.search(line)
        if match:
            result.seed = int(match.group(1))
            continue

        match = _RE_MODE.match(line)
        if match:
            try:
                result.modes.append(
                    DockingMode(
                        mode=int(match.group(1)),
                        affinity=_float(match.group(2)),
                        rmsd_lb=_float(match.group(3)),
                        rmsd_ub=_float(match.group(4)),
                    )
                )
            except ValueError:
                pass

    result.success = bool(result.modes)

    if not result.success:
        result.error = "Aucun mode de docking détecté."

    return result


def extract_best_affinity(log_path: str | Path) -> Optional[float]:
    """Raccourci : retourne uniquement le meilleur score."""

    result = parse_vina_log(log_path)

    if not result.success:
        return None

    return result.best_affinity


def extract_modes(log_path: str | Path) -> list[DockingMode]:
    """Raccourci : retourne les modes de docking."""

    result = parse_vina_log(log_path)
    return result.modes or []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyse un fichier log AutoDock Vina."
    )

    parser.add_argument(
        "log",
        help="Fichier .log produit par Vina",
    )

    args = parser.parse_args()

    result = parse_vina_log(args.log)

    print("=" * 70)
    print("ANALYSE LOG AUTODOCK VINA")
    print("=" * 70)

    print(f"Succès           : {result.success}")
    print(f"Version Vina     : {result.version}")
    print(f"Scoring          : {result.scoring_function}")
    print(f"Récepteur        : {result.receptor}")
    print(f"Ligand           : {result.ligand}")
    print(f"Exhaustiveness   : {result.exhaustiveness}")
    print(f"Seed             : {result.seed}")
    print(f"Nombre de modes  : {result.n_modes}")
    print(f"Meilleur mode    : {result.best_mode.mode if result.best_mode else None}")
    print(f"Meilleure aff.   : {result.best_affinity}")

    if result.error:
        print(f"Erreur           : {result.error}")

    print("\nModes :")

    for mode in result.modes or []:
        print(
            f"  {mode.mode:2d} | "
            f"{mode.affinity:8.3f} kcal/mol | "
            f"RMSD LB {mode.rmsd_lb:6.3f} | "
            f"RMSD UB {mode.rmsd_ub:6.3f}"
        )
