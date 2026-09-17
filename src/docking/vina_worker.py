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
        pair_roles: dict[str, str] | None = None,
    ):
        super().__init__()

        # pair_roles decrit le couple pompe/derepresseur de la campagne :
        #     {"pump": "<nom du moteur>", "repressor": "<nom du moteur>"}
        # Quand il est fourni, la fusion scientifique s'applique a
        # n'importe quel couple et plus seulement a MexB/MexR.
        self.pair_roles = dict(pair_roles or {})

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

            # Résultats par moteur, quel que soit son nom (MexB, MexR,
            # ou n'importe quel récepteur importé/générique). Remplace
            # les anciennes listes mexb_results/mexr_results codées en
            # dur par un dict générique.
            results_by_engine = {
                name: []
                for name in self.engines
            }

            for index, ligand in enumerate(
                self.ligands,
                start=1,
            ):

                if self._is_cancelled:
                    self._emit_cancelled()
                    return

                ligand_name = ligand.name

                self.log_line.emit(
                    f"▶ Ligand {index}/{total} : "
                    f"{ligand_name}"
                )

                for engine_name, engine in self.engines.items():

                    self.log_line.emit(
                        f"▶ Docking {engine_name} : "
                        f"{ligand_name}"
                    )

                    self.progress.emit(
                        engine_name,
                        index,
                        total,
                        ligand_name,
                    )

                    result = engine.dock_ligand(ligand)
                    result.groupe = self._get_group(ligand)

                    results_by_engine[engine_name].append(result)

                    self.log_line.emit(
                        self._format_result(engine_name, result)
                    )

                    if self._is_cancelled:
                        self._emit_cancelled()
                        return

            # ==========================================================
            # EXPORT
            # ==========================================================

            csv_by_engine = {}

            for engine_name, results in results_by_engine.items():
                if results:
                    csv_by_engine[engine_name] = (
                        self.engines[engine_name].export_csv(results)
                    )

            active = [
                name
                for name, results in results_by_engine.items()
                if results
            ]

            if not active:
                raise RuntimeError(
                    "Aucun résultat à exporter."
                )

            # ----------------------------------------------------------
            # CAS SIMPLE : une seule cible active (couvre maintenant
            # aussi bien MexB seul, MexR seul, qu'un récepteur générique
            # importé seul).
            # ----------------------------------------------------------
            if len(active) == 1:

                csv_path = csv_by_engine[active[0]]

                self.finished.emit(
                    str(csv_path)
                )

                return

            # ----------------------------------------------------------
            # COUPLE POMPE + DEREPRESSEUR -> fusion scientifique.
            #
            # Le couple MexB/MexR reste un cas particulier de la regle
            # generale : la pompe alimente les colonnes _mexb, le
            # derepresseur les colonnes _mexr. Les noms de colonnes sont
            # volontairement inchanges pour que toute la chaine
            # d'analyse existante fonctionne a l'identique sur n'importe
            # quel couple.
            # ----------------------------------------------------------
            pump_name, repressor_name = self._resolve_pair(active)

            if pump_name and repressor_name:

                combined_csv = (
                    self.results_root
                    / "docking_results_combined.csv"
                )

                export_combined_csv(
                    results_by_engine[pump_name],
                    results_by_engine[repressor_name],
                    combined_csv,
                    pump_name=pump_name,
                    repressor_name=repressor_name,
                )

                # Copie nommee d'apres le couple : permet de garder
                # cote a cote les resultats de plusieurs couples et de
                # comparer leurs correlations sans ecrasement.
                pair_csv = (
                    self.results_root
                    / (
                        "docking_results_combined_"
                        f"{self._slug(pump_name)}_"
                        f"{self._slug(repressor_name)}.csv"
                    )
                )

                try:
                    import shutil as _shutil

                    _shutil.copyfile(combined_csv, pair_csv)
                except Exception:
                    pair_csv = None

                self.log_line.emit(
                    f"✓ CSV {pump_name} (pompe) : "
                    f"{csv_by_engine[pump_name]}"
                )

                self.log_line.emit(
                    f"✓ CSV {repressor_name} (dérépresseur) : "
                    f"{csv_by_engine[repressor_name]}"
                )

                self.log_line.emit(
                    f"✓ CSV fusionné (filtre à double sélectivité) : "
                    f"{combined_csv}"
                )

                if pair_csv is not None:
                    self.log_line.emit(
                        f"✓ Copie archivée du couple : {pair_csv}"
                    )

                self.finished.emit(
                    str(combined_csv)
                )

                return

            # ----------------------------------------------------------
            # CAS GÉNÉRIQUE : 2 cibles actives ou plus, autres que le
            # couple historique MexB/MexR. Pas encore de fusion
            # scientifique dédiée (indice de sélectivité) pour un
            # couple générique -> concaténation brute des résultats par
            # cible, avec une colonne "cible", dans un seul CSV.
            # ----------------------------------------------------------
            import csv as _csv

            combined_csv = (
                self.results_root
                / "docking_results_combined.csv"
            )

            fieldnames = [
                "cible",
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

            with combined_csv.open(
                "w", newline="", encoding="utf-8"
            ) as handle:

                writer = _csv.DictWriter(
                    handle, fieldnames=fieldnames
                )
                writer.writeheader()

                for engine_name in active:
                    for result in results_by_engine[engine_name]:
                        row = result.to_dict()
                        row["cible"] = engine_name
                        writer.writerow(row)

            for engine_name in active:
                self.log_line.emit(
                    f"✓ CSV {engine_name} : "
                    f"{csv_by_engine[engine_name]}"
                )

            self.log_line.emit(
                "✓ CSV combiné (résultats bruts par cible, SANS indice "
                f"de sélectivité) : {combined_csv}"
            )

            self.finished.emit(
                str(combined_csv)
            )

        except Exception as exc:

            self.failed.emit(
                str(exc)
            )


    # ------------------------------------------------------------------
    # RESOLUTION DU COUPLE POMPE / DEREPRESSEUR
    # ------------------------------------------------------------------

    @staticmethod
    def _slug(name: str) -> str:
        """Nom de fichier sur, derive d'un nom de cible."""

        safe = []

        for char in str(name):
            safe.append(char if char.isalnum() else "_")

        return "".join(safe).strip("_") or "cible"

    def _resolve_pair(self, active: list[str]):
        """
        Determine, parmi les cibles ayant produit des resultats, laquelle
        joue le role de pompe et laquelle joue le role de derepresseur.

        Trois sources, dans cet ordre :
            1. pair_roles transmis par l'interface (source privilegiee) ;
            2. le champ "role" des profils de recepteurs ;
            3. le couple historique MexB / MexR.

        Retourne (None, None) si les cibles actives ne forment pas un
        couple exploitable — on retombe alors sur la concatenation brute.
        """

        if len(active) != 2:
            return None, None

        # --- 1. Information fournie par l'interface -------------------
        pump = self.pair_roles.get("pump")
        repressor = self.pair_roles.get("repressor")

        if pump in active and repressor in active and pump != repressor:
            return pump, repressor

        # --- 2. Roles declares dans les profils -----------------------
        try:
            from src.docking.receptor_profile import (
                normalize_role,
                resolve_target_profile,
            )

            roles = {}

            for name in active:
                try:
                    profile = resolve_target_profile(name)
                except Exception:
                    continue
                roles[name] = normalize_role(profile.role)

            pumps = [n for n, r in roles.items() if r == "pump"]
            repressors = [n for n, r in roles.items() if r == "repressor"]

            if len(pumps) == 1 and len(repressors) == 1:
                return pumps[0], repressors[0]

        except Exception:
            pass

        # --- 3. Couple historique -------------------------------------
        if set(active) == {"MexB", "MexR"}:
            return "MexB", "MexR"

        return None, None

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
