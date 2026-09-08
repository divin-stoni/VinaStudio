# -*- coding: utf-8 -*-
"""
ligand_manager.py

Gestion des ligands destinés au docking AutoDock Vina.

Fonctions principales :
- découverte des ligands PDBQT ;
- gestion des ligands préparés ;
- sélection multiple ;
- attribution de groupes ;
- export/import de la sélection ;
- aucune dépendance externe.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import csv
from typing import Iterable


@dataclass
class Ligand:
    """Représente un ligand utilisable pour le docking."""

    name: str
    path: Path
    group: str = ""
    selected: bool = False

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def molecule_name(self) -> str:
        """Nom de la molécule sans extension .pdbqt."""
        return self.path.stem

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "filename": self.filename,
            "group": self.group,
            "selected": self.selected,
        }


class LigandManager:
    """
    Gestionnaire central des ligands.

    Exemple :

        manager = LigandManager("docking/ligands/prepared")
        manager.scan()

        manager.select_all()
        manager.assign_group("Antidépresseurs")

        ligands = manager.get_selected()
    """

    def __init__(
        self,
        prepared_dir: str | Path,
        recursive: bool = False,
    ):
        self.prepared_dir = Path(prepared_dir).expanduser().resolve()
        self.recursive = recursive
        self.ligands: list[Ligand] = []

    # ------------------------------------------------------------------
    # DISCOVERY
    # ------------------------------------------------------------------

    def scan(self) -> list[Ligand]:
        """
        Recherche les fichiers PDBQT dans le dossier des ligands préparés.

        Retourne la liste complète des ligands trouvés.
        """

        if not self.prepared_dir.exists():
            raise FileNotFoundError(
                f"Dossier de ligands introuvable : {self.prepared_dir}"
            )

        if not self.prepared_dir.is_dir():
            raise NotADirectoryError(
                f"Le chemin n'est pas un dossier : {self.prepared_dir}"
            )

        pattern = "**/*.pdbqt" if self.recursive else "*.pdbqt"

        found = sorted(
            self.prepared_dir.glob(pattern),
            key=lambda p: p.name.lower(),
        )

        self.ligands = [
            Ligand(
                name=path.stem,
                path=path,
            )
            for path in found
            if path.is_file()
        ]

        return self.ligands

    # ------------------------------------------------------------------
    # INFORMATION
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Nombre total de ligands."""
        return len(self.ligands)

    def selected_count(self) -> int:
        """Nombre de ligands actuellement sélectionnés."""
        return sum(ligand.selected for ligand in self.ligands)

    def get_all(self) -> list[Ligand]:
        """Retourne tous les ligands."""
        return list(self.ligands)

    def get_selected(self) -> list[Ligand]:
        """Retourne uniquement les ligands sélectionnés."""
        return [
            ligand
            for ligand in self.ligands
            if ligand.selected
        ]

    # ------------------------------------------------------------------
    # SELECTION
    # ------------------------------------------------------------------

    def select_all(self) -> None:
        """Sélectionne tous les ligands."""
        for ligand in self.ligands:
            ligand.selected = True

    def deselect_all(self) -> None:
        """Désélectionne tous les ligands."""
        for ligand in self.ligands:
            ligand.selected = False

    def select(self, name: str) -> bool:
        """
        Sélectionne un ligand par son nom.

        Retourne True si le ligand existe.
        """

        ligand = self._find(name)

        if ligand is None:
            return False

        ligand.selected = True
        return True

    def deselect(self, name: str) -> bool:
        """Désélectionne un ligand par son nom."""

        ligand = self._find(name)

        if ligand is None:
            return False

        ligand.selected = False
        return True

    def set_selected(
        self,
        names: Iterable[str],
    ) -> None:
        """
        Définit précisément la sélection.

        Les ligands dont le nom est fourni sont sélectionnés.
        Tous les autres sont désélectionnés.
        """

        selected_names = set(names)

        for ligand in self.ligands:
            ligand.selected = ligand.name in selected_names

    # ------------------------------------------------------------------
    # GROUPES
    # ------------------------------------------------------------------

    def assign_group(
        self,
        group: str,
        selected_only: bool = True,
    ) -> int:
        """
        Attribue un groupe aux ligands.

        Parameters
        ----------
        group:
            Nom du groupe.
            Une chaîne vide signifie "aucun groupe".

        selected_only:
            Si True, le groupe est appliqué uniquement aux ligands
            sélectionnés.

        Returns
        -------
        int
            Nombre de ligands modifiés.
        """

        # Nettoyage du nom du groupe.
        group = (group or "").strip()

        targets = (
            self.get_selected()
            if selected_only
            else self.ligands
        )

        for ligand in targets:
            ligand.group = group

        return len(targets)

    def clear_groups(
        self,
        selected_only: bool = True,
    ) -> int:
        """Supprime les groupes des ligands ciblés."""

        return self.assign_group(
            "",
            selected_only=selected_only,
        )

    def groups(self) -> list[str]:
        """
        Retourne les groupes actuellement utilisés.

        Le groupe vide n'est pas retourné.
        """

        values = {
            ligand.group.strip()
            for ligand in self.ligands
            if ligand.group.strip()
        }

        return sorted(values, key=str.lower)

    def get_group(self, group: str) -> list[Ligand]:
        """Retourne tous les ligands appartenant à un groupe."""

        group = (group or "").strip()

        return [
            ligand
            for ligand in self.ligands
            if ligand.group.strip() == group
        ]

    # ------------------------------------------------------------------
    # RECHERCHE
    # ------------------------------------------------------------------

    def search(self, text: str) -> list[Ligand]:
        """
        Recherche un ligand par nom ou nom de fichier.
        """

        query = (text or "").strip().lower()

        if not query:
            return self.get_all()

        return [
            ligand
            for ligand in self.ligands
            if query in ligand.name.lower()
            or query in ligand.filename.lower()
        ]

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    def validate_selection(self) -> tuple[bool, str]:
        """
        Vérifie que la sélection peut être envoyée au moteur de docking.
        """

        selected = self.get_selected()

        if not selected:
            return (
                False,
                "Aucun ligand sélectionné.",
            )

        missing = [
            ligand
            for ligand in selected
            if not ligand.path.exists()
        ]

        if missing:
            names = ", ".join(
                ligand.name
                for ligand in missing[:5]
            )

            if len(missing) > 5:
                names += "..."

            return (
                False,
                f"{len(missing)} ligand(s) introuvable(s) : {names}",
            )

        invalid = [
            ligand
            for ligand in selected
            if ligand.path.suffix.lower() != ".pdbqt"
        ]

        if invalid:
            return (
                False,
                "Certains fichiers sélectionnés ne sont pas au format PDBQT.",
            )

        return True, "Sélection valide."

    # ------------------------------------------------------------------
    # SERIALISATION
    # ------------------------------------------------------------------

    def to_records(self) -> list[dict]:
        """Convertit les ligands en structures sérialisables."""

        return [
            ligand.to_dict()
            for ligand in self.ligands
        ]

    def save_selection(
        self,
        output_path: str | Path,
    ) -> Path:
        """
        Sauvegarde les ligands sélectionnés dans un CSV.
        """

        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        selected = self.get_selected()

        with output.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "name",
                    "path",
                    "filename",
                    "group",
                    "selected",
                ],
            )

            writer.writeheader()

            for ligand in selected:
                writer.writerow(ligand.to_dict())

        return output

    def load_selection(
        self,
        input_path: str | Path,
    ) -> int:
        """
        Recharge une sélection sauvegardée précédemment.

        Les ligands doivent déjà avoir été découverts avec scan().
        """

        path = Path(input_path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Fichier de sélection introuvable : {path}"
            )

        # Tout désélectionner avant restauration.
        self.deselect_all()

        restored = 0

        with path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as handle:

            reader = csv.DictReader(handle)

            for row in reader:

                name = (row.get("name") or "").strip()

                if not name:
                    continue

                ligand = self._find(name)

                if ligand is None:
                    continue

                ligand.selected = True
                ligand.group = (
                    row.get("group") or ""
                ).strip()

                restored += 1

        return restored

    # ------------------------------------------------------------------
    # UTILITAIRES INTERNES
    # ------------------------------------------------------------------

    def _find(self, name: str) -> Ligand | None:
        """Recherche exacte d'un ligand."""

        name = (name or "").strip()

        for ligand in self.ligands:
            if ligand.name == name:
                return ligand

        return None


# ======================================================================
# TEST MANUEL
# ======================================================================

def main() -> None:

    root = Path(__file__).resolve().parents[2]

    prepared_dir = (
        root
        / "docking"
        / "ligands"
        / "prepared"
    )

    manager = LigandManager(prepared_dir)

    print("=" * 70)
    print("GESTIONNAIRE DE LIGANDS — TEST")
    print("=" * 70)

    ligands = manager.scan()

    print(f"\nDossier : {prepared_dir}")
    print(f"Nombre de ligands : {len(ligands)}")

    if not ligands:
        print("\nAucun ligand PDBQT trouvé.")
        return

    print("\nLigands détectés :")

    for ligand in ligands:
        print(
            f"  - {ligand.name}"
            f" | groupe={ligand.group or 'Aucun'}"
        )

    # Test de sélection.
    manager.select_all()

    print(
        f"\nSélection : "
        f"{manager.selected_count()}/{manager.count()}"
    )

    # Test de groupe.
    modified = manager.assign_group(
        "Antidépresseurs"
    )

    print(
        f"Groupe attribué : Antidépresseurs"
        f" → {modified} ligand(s)"
    )

    print(
        f"Groupes détectés : "
        f"{manager.groups()}"
    )

    # Validation.
    valid, message = manager.validate_selection()

    print(
        f"\nValidation : "
        f"{'OK' if valid else 'ERREUR'}"
    )
    print(f"Message : {message}")

    print("\nSélection finale :")

    for ligand in manager.get_selected():
        print(
            f"  {ligand.name}"
            f" | {ligand.group or 'Aucun groupe'}"
        )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
