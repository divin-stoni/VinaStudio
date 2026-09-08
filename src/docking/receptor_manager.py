# -*- coding: utf-8 -*-
"""
receptor_manager.py

Gestion et validation du récepteur destiné au docking AutoDock Vina.

Responsabilités :
- vérifier l'existence du récepteur PDBQT ;
- vérifier son format ;
- analyser les lignes ATOM/HETATM ;
- vérifier les charges et types atomiques AutoDock ;
- compter les atomes ;
- détecter les résidus ;
- fournir un résumé exploitable par le moteur de docking.

Aucune dépendance externe.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import re


# ======================================================================
# STRUCTURES DE DONNÉES
# ======================================================================

@dataclass
class ReceptorAtom:
    """Informations minimales sur un atome PDBQT."""

    record: str
    atom_name: str
    residue_name: str
    chain: str
    residue_number: str
    x: float
    y: float
    z: float
    charge: Optional[float]
    atom_type: str


@dataclass
class ReceptorInfo:
    """Résumé du récepteur PDBQT."""

    path: str
    exists: bool = False
    is_file: bool = False
    valid_extension: bool = False

    n_atoms: int = 0
    n_residues: int = 0
    n_chains: int = 0

    n_atoms_with_charge: int = 0
    n_atoms_without_charge: int = 0

    n_atoms_with_type: int = 0
    n_atoms_without_type: int = 0

    atom_types: list[str] | None = None
    chains: list[str] | None = None

    valid: bool = False
    errors: list[str] | None = None
    warnings: list[str] | None = None

    def to_dict(self) -> dict:
        """Convertit les informations en dictionnaire."""

        return asdict(self)


# ======================================================================
# GESTIONNAIRE DU RÉCEPTEUR
# ======================================================================

class ReceptorManager:
    """Gestionnaire du récepteur PDBQT."""

    def __init__(self, receptor_path: str | Path):
        self.path = Path(receptor_path).expanduser().resolve()

    # ==================================================================
    # EXISTENCE
    # ==================================================================

    def exists(self) -> bool:
        """Vérifie que le récepteur existe."""

        return self.path.exists()

    def is_file(self) -> bool:
        """Vérifie que le chemin correspond à un fichier."""

        return self.path.is_file()

    def has_valid_extension(self) -> bool:
        """Vérifie l'extension PDBQT."""

        return self.path.suffix.lower() == ".pdbqt"

    # ==================================================================
    # LECTURE
    # ==================================================================

    def read_text(self) -> str:
        """Lit le fichier PDBQT."""

        return self.path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    # ==================================================================
    # PARSING ATOMES
    # ==================================================================

    @staticmethod
    def _parse_atom_line(line: str) -> Optional[ReceptorAtom]:
        """
        Analyse une ligne ATOM/HETATM PDBQT.

        Le format PDBQT reprend la structure PDB avec :
        - coordonnées X/Y/Z ;
        - charge partielle ;
        - type atomique AutoDock.
        """

        if not (
            line.startswith("ATOM")
            or line.startswith("HETATM")
        ):
            return None

        # --------------------------------------------------------------
        # Format fixe PDB/PDBQT
        # --------------------------------------------------------------

        try:
            record = line[0:6].strip()
            atom_name = line[12:16].strip()
            residue_name = line[17:20].strip()
            chain = line[21:22].strip()
            residue_number = line[22:26].strip()

            x = float(line[30:38].strip())
            y = float(line[38:46].strip())
            z = float(line[46:54].strip())

        except (ValueError, IndexError):
            return None

        # --------------------------------------------------------------
        # Charge et type atomique
        #
        # PDBQT standard :
        # charge vers les colonnes 71-76
        # type vers la fin de la ligne
        # --------------------------------------------------------------

        charge: Optional[float] = None
        atom_type = ""

        # Tentative charge par colonnes fixes
        if len(line) >= 76:
            charge_text = line[70:76].strip()

            try:
                if charge_text:
                    charge = float(charge_text)
            except ValueError:
                charge = None

        # Le type AutoDock est généralement le dernier champ.
        fields = line.split()

        if fields:
            candidate = fields[-1].strip()

            # Types AutoDock courants.
            if re.match(
                r"^[A-Za-z][A-Za-z0-9_+\-]*$",
                candidate,
            ):
                atom_type = candidate

        return ReceptorAtom(
            record=record,
            atom_name=atom_name,
            residue_name=residue_name,
            chain=chain,
            residue_number=residue_number,
            x=x,
            y=y,
            z=z,
            charge=charge,
            atom_type=atom_type,
        )

    def parse_atoms(self) -> list[ReceptorAtom]:
        """Retourne tous les atomes ATOM/HETATM valides."""

        if not self.exists() or not self.is_file():
            return []

        atoms: list[ReceptorAtom] = []

        try:
            text = self.read_text()
        except OSError:
            return []

        for line in text.splitlines():
            atom = self._parse_atom_line(line)

            if atom is not None:
                atoms.append(atom)

        return atoms

    # ==================================================================
    # RÉSIDUS
    # ==================================================================

    def get_residues(
        self,
        atoms: Optional[list[ReceptorAtom]] = None,
    ) -> list[tuple[str, str, str]]:
        """
        Retourne les résidus uniques.

        Format :
            (chaîne, nom_résidu, numéro_résidu)
        """

        if atoms is None:
            atoms = self.parse_atoms()

        residues: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        for atom in atoms:
            key = (
                atom.chain,
                atom.residue_name,
                atom.residue_number,
            )

            if key not in seen:
                seen.add(key)
                residues.append(key)

        return residues

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def validate(self) -> ReceptorInfo:
        """Analyse et valide le récepteur."""

        info = ReceptorInfo(
            path=str(self.path),
            errors=[],
            warnings=[],
            atom_types=[],
            chains=[],
        )

        # --------------------------------------------------------------
        # Vérifications de base
        # --------------------------------------------------------------

        info.exists = self.exists()

        if not info.exists:
            info.errors.append(
                f"Fichier introuvable : {self.path}"
            )
            return info

        info.is_file = self.is_file()

        if not info.is_file:
            info.errors.append(
                f"Le chemin n'est pas un fichier : {self.path}"
            )
            return info

        info.valid_extension = self.has_valid_extension()

        if not info.valid_extension:
            info.errors.append(
                "Le récepteur doit avoir l'extension .pdbqt."
            )
            return info

        # --------------------------------------------------------------
        # Parsing
        # --------------------------------------------------------------

        atoms = self.parse_atoms()

        info.n_atoms = len(atoms)

        if info.n_atoms == 0:
            info.errors.append(
                "Aucun atome ATOM/HETATM valide détecté."
            )
            return info

        # --------------------------------------------------------------
        # Résidus
        # --------------------------------------------------------------

        residues = self.get_residues(atoms)

        info.n_residues = len(residues)

        # --------------------------------------------------------------
        # Chaînes
        # --------------------------------------------------------------

        chains = sorted(
            {
                atom.chain if atom.chain else "_"
                for atom in atoms
            }
        )

        info.chains = chains
        info.n_chains = len(chains)

        # --------------------------------------------------------------
        # Charges
        # --------------------------------------------------------------

        info.n_atoms_with_charge = sum(
            atom.charge is not None
            for atom in atoms
        )

        info.n_atoms_without_charge = (
            info.n_atoms - info.n_atoms_with_charge
        )

        # --------------------------------------------------------------
        # Types AutoDock
        # --------------------------------------------------------------

        info.n_atoms_with_type = sum(
            bool(atom.atom_type)
            for atom in atoms
        )

        info.n_atoms_without_type = (
            info.n_atoms - info.n_atoms_with_type
        )

        atom_types = sorted(
            {
                atom.atom_type
                for atom in atoms
                if atom.atom_type
            }
        )

        info.atom_types = atom_types

        # --------------------------------------------------------------
        # Avertissements
        # --------------------------------------------------------------

        if info.n_atoms_without_charge > 0:
            info.warnings.append(
                f"{info.n_atoms_without_charge} atome(s) "
                "sans charge détectée."
            )

        if info.n_atoms_without_type > 0:
            info.warnings.append(
                f"{info.n_atoms_without_type} atome(s) "
                "sans type AutoDock détecté."
            )

        # --------------------------------------------------------------
        # Validation finale
        # --------------------------------------------------------------

        info.valid = len(info.errors) == 0

        return info

    # ==================================================================
    # RÉSUMÉ
    # ==================================================================

    def summary(self) -> str:
        """Retourne un résumé textuel du récepteur."""

        info = self.validate()

        lines = [
            "=" * 70,
            "GESTIONNAIRE DU RÉCEPTEUR — TEST",
            "=" * 70,
            "",
            f"Fichier          : {info.path}",
            f"Existe           : {info.exists}",
            f"Fichier valide   : {info.is_file}",
            f"Extension PDBQT  : {info.valid_extension}",
            "",
            f"Nombre d'atomes  : {info.n_atoms}",
            f"Nombre de résidus: {info.n_residues}",
            f"Nombre de chaînes: {info.n_chains}",
            "",
            f"Avec charge      : {info.n_atoms_with_charge}",
            f"Sans charge      : {info.n_atoms_without_charge}",
            f"Avec type AD     : {info.n_atoms_with_type}",
            f"Sans type AD     : {info.n_atoms_without_type}",
            "",
            f"Chaînes          : {info.chains}",
            f"Types atomiques  : {info.atom_types}",
            "",
            f"Validation       : "
            f"{'OK' if info.valid else 'ERREUR'}",
        ]

        if info.errors:
            lines.append("")
            lines.append("Erreurs :")

            for error in info.errors:
                lines.append(f"  - {error}")

        if info.warnings:
            lines.append("")
            lines.append("Avertissements :")

            for warning in info.warnings:
                lines.append(f"  - {warning}")

        lines.append("=" * 70)

        return "\n".join(lines)


# ======================================================================
# TEST
# ======================================================================

def main() -> None:
    """Test du gestionnaire de récepteur."""

    project_root = Path(
        __file__
    ).resolve().parents[2]

    receptor = (
        project_root
        / "docking"
        / "receptor"
        / "3W9J.pdbqt"
    )

    manager = ReceptorManager(receptor)

    print(manager.summary())

    # --------------------------------------------------------------
    # Affichage des premiers atomes
    # --------------------------------------------------------------

    atoms = manager.parse_atoms()

    print()
    print("=" * 70)
    print("APERÇU DES ATOMES")
    print("=" * 70)

    for atom in atoms[:10]:
        print(
            f"{atom.record:6s} "
            f"{atom.atom_name:4s} "
            f"{atom.residue_name:3s} "
            f"{atom.chain or '_':1s} "
            f"{atom.residue_number:4s} | "
            f"X={atom.x:8.3f} "
            f"Y={atom.y:8.3f} "
            f"Z={atom.z:8.3f} | "
            f"charge={atom.charge!s:>7s} | "
            f"type={atom.atom_type}"
        )

    if len(atoms) > 10:
        print(
            f"... {len(atoms) - 10} autre(s) atome(s)"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
