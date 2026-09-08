# -*- coding: utf-8 -*-
"""
docking_results.py

Gestion et analyse des résultats AutoDock Vina.

Responsabilités :
- charger un CSV de résultats Vina ;
- vérifier sa structure ;
- classer les ligands par affinité ;
- identifier le meilleur ligand ;
- calculer des statistiques simples ;
- attribuer les rangs ;
- filtrer les résultats ;
- exporter un CSV enrichi.

Aucune dépendance externe obligatoire.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import csv
import statistics


# ---------------------------------------------------------------------------
# STRUCTURE D'UN RESULTAT
# ---------------------------------------------------------------------------

@dataclass
class DockingRecord:
    """Un résultat individuel de docking."""

    molecule: str
    ligand_file: str
    status: str

    best_affinity: Optional[float] = None
    best_mode: Optional[int] = None
    n_modes: int = 0

    output_pdbqt: Optional[str] = None
    log_file: Optional[str] = None

    error: Optional[str] = None
    duration_seconds: Optional[float] = None

    group: Optional[str] = None
    rank: Optional[int] = None

    def to_dict(self) -> dict:
        """Convertit l'enregistrement en dictionnaire."""

        return asdict(self)


# ---------------------------------------------------------------------------
# COLLECTION DES RESULTATS
# ---------------------------------------------------------------------------

class DockingResults:
    """Gestionnaire des résultats de docking."""

    REQUIRED_COLUMNS = {
        "molecule",
        "ligand_file",
        "status",
        "best_affinity",
        "best_mode",
        "n_modes",
    }

    def __init__(
        self,
        records: Optional[list[DockingRecord]] = None,
    ):
        self.records = records or []

    # ------------------------------------------------------------------
    # CHARGEMENT CSV
    # ------------------------------------------------------------------

    @classmethod
    def from_csv(
        cls,
        csv_path: str | Path,
    ) -> "DockingResults":
        """
        Charge un fichier CSV produit par vina_engine.py.
        """

        path = Path(csv_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Fichier CSV introuvable : {path}"
            )

        records: list[DockingRecord] = []

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            if reader.fieldnames is None:
                raise ValueError(
                    "Le CSV ne contient aucune colonne."
                )

            columns = set(reader.fieldnames)

            missing = (
                cls.REQUIRED_COLUMNS - columns
            )

            if missing:
                raise ValueError(
                    "Colonnes manquantes dans le CSV : "
                    + ", ".join(sorted(missing))
                )

            for row in reader:

                affinity = cls._optional_float(
                    row.get("best_affinity")
                )

                best_mode = cls._optional_int(
                    row.get("best_mode")
                )

                n_modes = cls._optional_int(
                    row.get("n_modes")
                )

                duration = cls._optional_float(
                    row.get("duration_seconds")
                )

                record = DockingRecord(
                    molecule=(
                        row.get("molecule") or ""
                    ),
                    ligand_file=(
                        row.get("ligand_file") or ""
                    ),
                    status=(
                        row.get("status") or ""
                    ),
                    best_affinity=affinity,
                    best_mode=best_mode,
                    n_modes=n_modes or 0,
                    output_pdbqt=(
                        row.get("output_pdbqt")
                        or None
                    ),
                    log_file=(
                        row.get("log_file")
                        or None
                    ),
                    error=(
                        row.get("error")
                        or None
                    ),
                    duration_seconds=duration,
                    group=(
                        row.get("group")
                        or None
                    ),
                )

                records.append(record)

        return cls(records)

    # ------------------------------------------------------------------
    # CONVERSIONS
    # ------------------------------------------------------------------

    @staticmethod
    def _optional_float(
        value: Optional[str],
    ) -> Optional[float]:

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _optional_int(
        value: Optional[str],
    ) -> Optional[int]:

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        try:
            return int(float(value))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # RESULTATS VALIDES
    # ------------------------------------------------------------------

    @property
    def successful(self) -> list[DockingRecord]:
        """Retourne uniquement les dockings réussis."""

        return [
            record
            for record in self.records
            if record.status.upper() == "OK"
            and record.best_affinity is not None
        ]

    @property
    def failed(self) -> list[DockingRecord]:
        """Retourne les dockings échoués."""

        return [
            record
            for record in self.records
            if record.status.upper() != "OK"
        ]

    # ------------------------------------------------------------------
    # CLASSEMENT
    # ------------------------------------------------------------------

    def rank(
        self,
    ) -> list[DockingRecord]:
        """
        Classe les molécules par affinité croissante.

        Plus l'affinité est négative, meilleur est le score.
        """

        ranked = sorted(
            self.successful,
            key=lambda record: record.best_affinity,
        )

        for index, record in enumerate(
            ranked,
            start=1,
        ):
            record.rank = index

        return ranked

    # ------------------------------------------------------------------
    # MEILLEUR LIGAND
    # ------------------------------------------------------------------

    def best(
        self,
    ) -> Optional[DockingRecord]:
        """Retourne le ligand ayant la meilleure affinité."""

        ranked = self.rank()

        if not ranked:
            return None

        return ranked[0]

    # ------------------------------------------------------------------
    # STATISTIQUES
    # ------------------------------------------------------------------

    def affinities(self) -> list[float]:
        """Retourne toutes les affinités valides."""

        return [
            record.best_affinity
            for record in self.successful
            if record.best_affinity is not None
        ]

    def statistics(self) -> dict:
        """Calcule des statistiques sur les affinités."""

        values = self.affinities()

        if not values:
            return {
                "n_total": len(self.records),
                "n_success": len(self.successful),
                "n_failed": len(self.failed),
                "minimum": None,
                "maximum": None,
                "mean": None,
                "median": None,
            }

        return {
            "n_total": len(self.records),
            "n_success": len(self.successful),
            "n_failed": len(self.failed),
            "minimum": min(values),
            "maximum": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
        }

    # ------------------------------------------------------------------
    # GROUPES
    # ------------------------------------------------------------------

    def assign_group(
        self,
        group: str,
        molecules: Optional[list[str]] = None,
    ) -> int:
        """
        Attribue un groupe à des molécules.

        Si molecules=None, le groupe est attribué
        à tous les résultats.
        """

        if not group.strip():
            raise ValueError(
                "Le nom du groupe ne peut pas être vide."
            )

        count = 0

        for record in self.records:

            if (
                molecules is None
                or record.molecule in molecules
            ):
                record.group = group
                count += 1

        return count

    def groups(self) -> list[str]:
        """Retourne les groupes présents."""

        groups = {
            record.group
            for record in self.records
            if record.group
        }

        return sorted(groups)

    # ------------------------------------------------------------------
    # FILTRAGE PAR AFFINITE
    # ------------------------------------------------------------------

    def filter_affinity(
        self,
        threshold: float,
    ) -> list[DockingRecord]:
        """
        Retourne les ligands dont l'affinité est
        inférieure ou égale au seuil.

        Exemple :
            threshold = -8.0

        conserve :
            -8.0
            -9.0
            -10.0
        """

        return [
            record
            for record in self.successful
            if (
                record.best_affinity is not None
                and record.best_affinity <= threshold
            )
        ]

    # ------------------------------------------------------------------
    # EXPORT CSV CLASSE
    # ------------------------------------------------------------------

    def export_ranked_csv(
        self,
        output_path: str | Path,
    ) -> Path:
        """Exporte les résultats classés."""

        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ranked = self.rank()

        fieldnames = [
            "rank",
            "molecule",
            "ligand_file",
            "group",
            "status",
            "best_affinity",
            "best_mode",
            "n_modes",
            "output_pdbqt",
            "log_file",
            "error",
            "duration_seconds",
        ]

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for record in ranked:
                writer.writerow(
                    {
                        "rank": record.rank,
                        "molecule": record.molecule,
                        "ligand_file": record.ligand_file,
                        "group": record.group or "",
                        "status": record.status,
                        "best_affinity": (
                            record.best_affinity
                        ),
                        "best_mode": record.best_mode,
                        "n_modes": record.n_modes,
                        "output_pdbqt": (
                            record.output_pdbqt
                            or ""
                        ),
                        "log_file": (
                            record.log_file
                            or ""
                        ),
                        "error": (
                            record.error
                            or ""
                        ),
                        "duration_seconds": (
                            record.duration_seconds
                        ),
                    }
                )

        return path

    # ------------------------------------------------------------------
    # RAPPORT TEXTE
    # ------------------------------------------------------------------

    def report(self) -> str:
        """Construit un rapport texte lisible."""

        stats = self.statistics()
        ranked = self.rank()

        lines = []

        lines.append(
            "=" * 70
        )

        lines.append(
            "RAPPORT DES RESULTATS DE DOCKING"
        )

        lines.append(
            "=" * 70
        )

        lines.append(
            f"Total       : {stats['n_total']}"
        )

        lines.append(
            f"Réussis     : {stats['n_success']}"
        )

        lines.append(
            f"Échecs      : {stats['n_failed']}"
        )

        if stats["mean"] is not None:

            lines.append(
                f"Moyenne     : "
                f"{stats['mean']:.3f} kcal/mol"
            )

            lines.append(
                f"Médiane     : "
                f"{stats['median']:.3f} kcal/mol"
            )

            lines.append(
                f"Meilleur    : "
                f"{stats['minimum']:.3f} kcal/mol"
            )

            lines.append(
                f"Plus faible : "
                f"{stats['maximum']:.3f} kcal/mol"
            )

        lines.append("")

        lines.append(
            "CLASSEMENT"
        )

        lines.append(
            "-" * 70
        )

        for record in ranked:

            group = (
                record.group
                if record.group
                else "Aucun"
            )

            lines.append(
                f"{record.rank:2d}. "
                f"{record.molecule:<32} "
                f"{record.best_affinity:8.3f} "
                f"kcal/mol | "
                f"{group}"
            )

        if self.failed:

            lines.append("")

            lines.append(
                "DOCKINGS ÉCHOUÉS"
            )

            lines.append(
                "-" * 70
            )

            for record in self.failed:

                lines.append(
                    f"- {record.molecule} : "
                    f"{record.error or 'Erreur inconnue'}"
                )

        lines.append(
            "=" * 70
        )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# TEST
# ---------------------------------------------------------------------------

def main():

    print("=" * 70)
    print("DOCKING RESULTS — TEST")
    print("=" * 70)

    csv_path = (
        Path(__file__).resolve().parents[2]
        / "docking/results/batch_vina_engine/docking_results.csv"
    )

    print()
    print(
        f"CSV : {csv_path}"
    )

    # --------------------------------------------------------------
    # CHARGEMENT
    # --------------------------------------------------------------

    try:

        results = DockingResults.from_csv(
            csv_path
        )

    except Exception as exc:

        print()
        print(
            f"[ERREUR] {exc}"
        )

        return 1

    print()
    print(
        f"[OK] Résultats chargés : "
        f"{len(results.records)}"
    )

    # --------------------------------------------------------------
    # GROUPE
    # --------------------------------------------------------------

    count = results.assign_group(
        "Antidépresseurs"
    )

    print(
        f"[OK] Groupe attribué : "
        f"Antidépresseurs → {count} ligand(s)"
    )

    # --------------------------------------------------------------
    # RAPPORT
    # --------------------------------------------------------------

    print()
    print(
        results.report()
    )

    # --------------------------------------------------------------
    # MEILLEUR
    # --------------------------------------------------------------

    best = results.best()

    print()
    print(
        "MEILLEUR LIGAND"
    )

    print("-" * 70)

    if best:

        print(
            f"Molecule : {best.molecule}"
        )

        print(
            f"Affinité : "
            f"{best.best_affinity:.3f} kcal/mol"
        )

        print(
            f"Rang     : {best.rank}"
        )

        print(
            f"Groupe   : "
            f"{best.group or 'Aucun'}"
        )

    else:

        print(
            "Aucun résultat valide."
        )

    # --------------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------------

    output_path = (
        Path(__file__).resolve().parents[2]
        / "docking/results/batch_vina_engine/"
        "docking_results_ranked.csv"
    )

    exported = results.export_ranked_csv(
        output_path
    )

    print()
    print(
        f"[OK] CSV classé créé : "
        f"{exported}"
    )

    # --------------------------------------------------------------
    # FILTRE
    # --------------------------------------------------------------

    strong_hits = results.filter_affinity(
        -8.0
    )

    print()
    print(
        "HITS ≤ -8.0 kcal/mol"
    )

    print("-" * 70)

    for record in strong_hits:

        print(
            f"  {record.molecule:<32} "
            f"{record.best_affinity:8.3f} kcal/mol"
        )

    print()
    print("=" * 70)
    print("TEST TERMINE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
