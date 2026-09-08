# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .vina_engine import (
    VinaEngine,
    VinaDockingResult,
    export_combined_csv,
)


class DockingWorker(QObject):
    """
    Worker Qt pour exécuter une campagne de docking
    sans bloquer l'interface graphique.

    Modes supportés :
        - MexB
        - MexR
        - MexB + MexR

    Le worker exécute les ligands séquentiellement et permet
    l'arrêt du processus Vina actuellement actif.
    """

    progress = Signal(str, int, int, str)
    log_line = Signal(str)

    finished = Signal(str)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(
        self,
        engines: dict[str, VinaEngine],
        ligands: list[str | Path],
        results_root: str | Path,
        ligand_groups: dict[str, str] | None = None,
    ):
        super().__init__()

        self.engines = engines

        self.ligands = [
            Path(path)
            for path in ligands
        ]

        self.results_root = Path(
            results_root
        )

        self.ligand_groups = (
            ligand_groups or {}
        )

        self._is_cancelled = False

    # ------------------------------------------------------------------
    # ANNULATION
    # ------------------------------------------------------------------

    def cancel(self):
        """
        Demande l'annulation et tente d'arrêter Vina immédiatement.
        """

        self._is_cancelled = True

        for engine in self.engines.values():

            try:
                engine.cancel_current_process()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------

    def run(self):

        try:

            total = len(self.ligands)

            if total == 0:
                raise RuntimeError(
                    "Aucun ligand à traiter."
                )

            mexb_results: list[
                VinaDockingResult
            ] = []

            mexr_results: list[
                VinaDockingResult
            ] = []

            for index, ligand in enumerate(
                self.ligands,
                start=1,
            ):

                if self._is_cancelled:

                    self._emit_cancelled()

                    return

                ligand_name = ligand.name

                # Progression globale ligand
                # Le moteur sera indiqué pendant chaque docking.

                self.log_line.emit(
                    f"▶ Ligand {index}/{total} : "
                    f"{ligand_name}"
                )

                # ======================================================
                # MEXB
                # ======================================================

                if "MexB" in self.engines:

                    self.log_line.emit(
                        f"▶ Docking MexB : "
                        f"{ligand_name}"
                    )

                    self.progress.emit(
                        "MexB",
                        index,
                        total,
                        ligand_name,
                    )

                    result_mexb = (
                        self.engines["MexB"]
                        .dock_ligand(ligand)
                    )

                    result_mexb.groupe = (
                        self._get_group(ligand)
                    )

                    mexb_results.append(
                        result_mexb
                    )

                    self.log_line.emit(
                        self._format_result(
                            "MexB",
                            result_mexb,
                        )
                    )

                if self._is_cancelled:

                    self._emit_cancelled()

                    return

                # ======================================================
                # MEXR
                # ======================================================

                if "MexR" in self.engines:

                    self.log_line.emit(
                        f"▶ Docking MexR : "
                        f"{ligand_name}"
                    )

                    self.progress.emit(
                        "MexR",
                        index,
                        total,
                        ligand_name,
                    )

                    result_mexr = (
                        self.engines["MexR"]
                        .dock_ligand(ligand)
                    )

                    result_mexr.groupe = (
                        self._get_group(ligand)
                    )

                    mexr_results.append(
                        result_mexr
                    )

                    self.log_line.emit(
                        self._format_result(
                            "MexR",
                            result_mexr,
                        )
                    )

                if self._is_cancelled:

                    self._emit_cancelled()

                    return

            # ==========================================================
            # EXPORT
            # ==========================================================

            mexb_csv = None
            mexr_csv = None

            if mexb_results:

                mexb_csv = (
                    self.engines["MexB"]
                    .export_csv(
                        mexb_results
                    )
                )

            if mexr_results:

                mexr_csv = (
                    self.engines["MexR"]
                    .export_csv(
                        mexr_results
                    )
                )

            # ----------------------------------------------------------
            # CAS SIMPLE : une seule cible
            # ----------------------------------------------------------

            if not (
                mexb_results
                and mexr_results
            ):

                csv_path = (
                    mexb_csv
                    if mexb_csv is not None
                    else mexr_csv
                )

                if csv_path is None:
                    raise RuntimeError(
                        "Aucun résultat à exporter."
                    )

                self.finished.emit(
                    str(csv_path)
                )

                return

            # ----------------------------------------------------------
            # CAS DOUBLE : CSV fusionné
            # ----------------------------------------------------------

            combined_csv = (
                self.results_root
                / "docking_results_combined.csv"
            )

            export_combined_csv(
                mexb_results,
                mexr_results,
                combined_csv,
            )

            self.log_line.emit(
                f"✓ CSV MexB : {mexb_csv}"
            )

            self.log_line.emit(
                f"✓ CSV MexR : {mexr_csv}"
            )

            self.log_line.emit(
                f"✓ CSV fusionné : {combined_csv}"
            )

            self.finished.emit(
                str(combined_csv)
            )

        except Exception as exc:

            self.failed.emit(
                str(exc)
            )

    # ------------------------------------------------------------------
    # UTILITAIRES
    # ------------------------------------------------------------------

    def _get_group(
        self,
        ligand: Path,
    ) -> str:

        resolved = str(
            ligand.resolve()
        )

        direct = str(ligand)

        return self.ligand_groups.get(
            resolved,
            self.ligand_groups.get(
                direct,
                "",
            ),
        )

    @staticmethod
    def _format_result(
        target: str,
        result: VinaDockingResult,
    ) -> str:

        if result.status != "OK":

            return (
                f"✗ {target} — "
                f"{result.molecule} — "
                f"ÉCHEC : "
                f"{result.error or 'erreur inconnue'}"
            )

        affinity = (
            f"{result.best_affinity:.3f}"
            if result.best_affinity is not None
            else "N/A"
        )

        return (
            f"✓ {target} — "
            f"{result.molecule} — "
            f"{affinity} kcal/mol"
        )

    def _emit_cancelled(self):

        self.log_line.emit(
            "⚠️ Campagne annulée par l'utilisateur."
        )

        self.cancelled.emit(
            "Campagne annulée par l'utilisateur."
        )
