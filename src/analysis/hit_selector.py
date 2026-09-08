# -*- coding: utf-8 -*-
"""
hit_selector.py

Sélection automatique des meilleurs hits de docking.

Responsabilités :
- charger les résultats de docking ;
- sélectionner les meilleurs ligands selon leur affinité ;
- appliquer un seuil d'affinité ;
- produire une liste de hits prioritaires ;
- afficher un résumé lisible.

Aucune dépendance externe.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CSV = (
    PROJECT_ROOT
    / "docking/results/batch_vina_engine/"
    / "docking_results_ranked.csv"
)


@dataclass
class Hit:
    """Représente un ligand sélectionné comme hit."""

    rank: int
    molecule: str
    ligand_file: str
    affinity: float
    best_mode: Optional[int]
    n_modes: int
    group: Optional[str]
    output_pdbqt: Optional[str]
    log_file: Optional[str]

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "molecule": self.molecule,
            "ligand_file": self.ligand_file,
            "affinity": self.affinity,
            "best_mode": self.best_mode,
            "n_modes": self.n_modes,
            "group": self.group or "",
            "output_pdbqt": self.output_pdbqt or "",
            "log_file": self.log_file or "",
        }


class HitSelector:
    """Sélectionneur des meilleurs hits."""

    def __init__(self, csv_path: str | Path = DEFAULT_CSV):

        self.csv_path = Path(csv_path)
        self.records: list[dict] = []

    # ------------------------------------------------------------------
    # CHARGEMENT
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Charge le CSV des résultats."""

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"CSV introuvable : {self.csv_path}"
            )

        with self.csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            if not reader.fieldnames:
                raise ValueError(
                    "Le CSV ne contient aucune colonne."
                )

            required = {
                "rank",
                "molecule",
                "ligand_file",
                "best_affinity",
                "best_mode",
                "n_modes",
            }

            missing = required - set(reader.fieldnames)

            if missing:
                raise ValueError(
                    "Colonnes manquantes : "
                    + ", ".join(sorted(missing))
                )

            self.records = list(reader)

    # ------------------------------------------------------------------
    # CONVERSION
    # ------------------------------------------------------------------

    @staticmethod
    def _float(value: str) -> Optional[float]:

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(value: str) -> Optional[int]:

        if value is None:
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # HITS PAR SEUIL
    # ------------------------------------------------------------------

    def select_by_threshold(
        self,
        threshold: float = -8.0,
    ) -> list[Hit]:
        """
        Sélectionne tous les ligands dont le score
        est inférieur ou égal au seuil.
        """

        hits = []

        for row in self.records:

            affinity = self._float(
                row.get("best_affinity")
            )

            if affinity is None:
                continue

            if affinity <= threshold:

                rank = self._int(
                    row.get("rank")
                )

                best_mode = self._int(
                    row.get("best_mode")
                )

                n_modes = self._int(
                    row.get("n_modes")
                )

                hits.append(
                    Hit(
                        rank=rank or 0,
                        molecule=row.get(
                            "molecule", ""
                        ),
                        ligand_file=row.get(
                            "ligand_file", ""
                        ),
                        affinity=affinity,
                        best_mode=best_mode,
                        n_modes=n_modes or 0,
                        group=row.get("group")
                        or None,
                        output_pdbqt=row.get(
                            "output_pdbqt"
                        )
                        or None,
                        log_file=row.get(
                            "log_file"
                        )
                        or None,
                    )
                )

        return hits

    # ------------------------------------------------------------------
    # TOP N
    # ------------------------------------------------------------------

    def select_top(
        self,
        n: int = 3,
    ) -> list[Hit]:
        """Retourne les N meilleurs ligands."""

        if n < 1:
            raise ValueError(
                "n doit être >= 1."
            )

        valid = []

        for row in self.records:

            affinity = self._float(
                row.get("best_affinity")
            )

            if affinity is None:
                continue

            valid.append(
                (
                    affinity,
                    row,
                )
            )

        valid.sort(
            key=lambda item: item[0]
        )

        hits = []

        for affinity, row in valid[:n]:

            hits.append(
                Hit(
                    rank=self._int(
                        row.get("rank")
                    )
                    or 0,
                    molecule=row.get(
                        "molecule", ""
                    ),
                    ligand_file=row.get(
                        "ligand_file", ""
                    ),
                    affinity=affinity,
                    best_mode=self._int(
                        row.get("best_mode")
                    ),
                    n_modes=self._int(
                        row.get("n_modes")
                    )
                    or 0,
                    group=row.get("group")
                    or None,
                    output_pdbqt=row.get(
                        "output_pdbqt"
                    )
                    or None,
                    log_file=row.get(
                        "log_file"
                    )
                    or None,
                )
            )

        return hits

    # ------------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------------

    def export_hits(
        self,
        hits: list[Hit],
        output_path: str | Path,
    ) -> Path:
        """Exporte les hits sélectionnés dans un CSV."""

        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fieldnames = [
            "rank",
            "molecule",
            "ligand_file",
            "affinity",
            "best_mode",
            "n_modes",
            "group",
            "output_pdbqt",
            "log_file",
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

            for hit in hits:
                writer.writerow(
                    hit.to_dict()
                )

        return path


# ----------------------------------------------------------------------
# TEST
# ----------------------------------------------------------------------

def main():

    print("=" * 70)
    print("HIT SELECTOR — TEST")
    print("=" * 70)

    selector = HitSelector()

    print()
    print(
        f"CSV : {selector.csv_path}"
    )

    try:
        selector.load()

    except Exception as exc:

        print()
        print(
            f"[ERREUR] {exc}"
        )

        return 1

    print()
    print(
        f"[OK] Résultats chargés : "
        f"{len(selector.records)}"
    )

    # --------------------------------------------------------------
    # SEUIL
    # --------------------------------------------------------------

    threshold = -8.0

    hits = selector.select_by_threshold(
        threshold
    )

    print()
    print(
        f"HITS ≤ {threshold:.1f} kcal/mol"
    )

    print("-" * 70)

    for hit in hits:

        print(
            f"{hit.rank:2d}. "
            f"{hit.molecule:<35} "
            f"{hit.affinity:8.3f} kcal/mol"
        )

    print()
    print(
        f"Nombre de hits : {len(hits)}"
    )

    # --------------------------------------------------------------
    # TOP 3
    # --------------------------------------------------------------

    top_hits = selector.select_top(3)

    print()
    print("TOP 3")
    print("-" * 70)

    for hit in top_hits:

        print(
            f"{hit.rank:2d}. "
            f"{hit.molecule:<35} "
            f"{hit.affinity:8.3f} kcal/mol"
        )

    # --------------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------------

    output = (
        PROJECT_ROOT
        / "docking/results/batch_vina_engine/"
        / "selected_hits.csv"
    )

    exported = selector.export_hits(
        hits,
        output,
    )

    print()
    print(
        f"[OK] Hits exportés : {exported}"
    )

    print()
    print("=" * 70)
    print("TEST TERMINE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
