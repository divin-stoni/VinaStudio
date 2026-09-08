# -*- coding: utf-8 -*-
"""
session_manager.py

Gestionnaire central du workspace temporaire d'une session.

Responsabilités :
- créer un workspace de session isolé ;
- fournir les chemins internes ;
- gérer les entrées importées ;
- exporter intégralement la session ;
- nettoyer la session à la fermeture.

Aucun moteur scientifique n'est exécuté ici.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil


class SessionManager:
    """
    Gestionnaire du workspace temporaire d'une session.
    """

    def __init__(
        self,
        project_root: str | Path,
    ):
        self.project_root = (
            Path(project_root)
            .expanduser()
            .resolve()
        )

        self.session_root: Path | None = None

    # ------------------------------------------------------------------
    # CREATION
    # ------------------------------------------------------------------

    def create_session(self) -> Path:
        """
        Crée une nouvelle session propre.
        """

        if self.session_root is not None:
            raise RuntimeError(
                "Une session est déjà active."
            )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        root = (
            self.project_root
            / ".session"
            / f"session_{timestamp}"
        )

        root.mkdir(
            parents=True,
            exist_ok=False,
        )

        for directory in (
            "input",
            "prepared",
            "results",
            "analysis",
            "visualization",
            "plip",
            "exports",
        ):
            (
                root / directory
            ).mkdir(
                parents=True,
                exist_ok=True,
            )

        self.session_root = root

        return root

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    def require_session(self) -> Path:
        """
        Retourne la session active ou lève une erreur.
        """

        if self.session_root is None:
            raise RuntimeError(
                "Aucune session active."
            )

        return self.session_root

    # ------------------------------------------------------------------
    # CHEMINS INTERNES
    # ------------------------------------------------------------------

    @property
    def input_dir(self) -> Path:
        return self.require_session() / "input"

    @property
    def prepared_dir(self) -> Path:
        return self.require_session() / "prepared"

    @property
    def results_dir(self) -> Path:
        return self.require_session() / "results"

    @property
    def analysis_dir(self) -> Path:
        return self.require_session() / "analysis"

    @property
    def visualization_dir(self) -> Path:
        return self.require_session() / "visualization"

    @property
    def plip_dir(self) -> Path:
        return self.require_session() / "plip"

    # ------------------------------------------------------------------
    # IMPORT D'UN FICHIER EXTERNE
    # ------------------------------------------------------------------

    def import_file(
        self,
        source: str | Path,
        destination_name: str | None = None,
    ) -> Path:
        """
        Copie un fichier externe dans input/.

        Le chemin externe original n'est pas mémorisé
        comme état de session.
        """

        source = (
            Path(source)
            .expanduser()
            .resolve()
        )

        if not source.exists():
            raise FileNotFoundError(
                f"Fichier introuvable : {source}"
            )

        if not source.is_file():
            raise ValueError(
                f"Le chemin n'est pas un fichier : {source}"
            )

        destination = (
            self.input_dir
            / (
                destination_name
                or source.name
            )
        )

        shutil.copy2(
            source,
            destination,
        )

        return destination

    # ------------------------------------------------------------------
    # EXPORT GLOBAL
    # ------------------------------------------------------------------

    def export_session(
        self,
        destination: str | Path,
    ) -> tuple[Path, list[Path]]:
        """
        Exporte intégralement la session.

        Retourne :
            (dossier_export, liste_des_fichiers_exportes)
        """

        session = self.require_session()

        destination = (
            Path(destination)
            .expanduser()
            .resolve()
        )

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        exported_root = (
            destination
            / session.name
        )

        if exported_root.exists():
            shutil.rmtree(
                exported_root
            )

        shutil.copytree(
            session,
            exported_root,
        )

        exported_files = sorted(
            path
            for path in exported_root.rglob("*")
            if path.is_file()
        )

        manifest = (
            exported_root
            / "MANIFEST.txt"
        )

        with manifest.open(
            "w",
            encoding="utf-8",
        ) as handle:

            handle.write(
                "EXPORT GLOBAL DE SESSION\n"
            )

            handle.write(
                "=" * 70
                + "\n\n"
            )

            handle.write(
                f"Session : {session.name}\n"
            )

            handle.write(
                f"Nombre de fichiers : "
                f"{len(exported_files)}\n\n"
            )

            for index, file_path in enumerate(
                exported_files,
                start=1,
            ):

                relative = file_path.relative_to(
                    exported_root
                )

                size = file_path.stat().st_size

                handle.write(
                    f"{index:04d} | "
                    f"{relative} | "
                    f"{size} octets\n"
                )

        if manifest not in exported_files:
            exported_files.append(
                manifest
            )

        return (
            exported_root,
            sorted(exported_files),
        )

    # ------------------------------------------------------------------
    # NETTOYAGE
    # ------------------------------------------------------------------

    def cleanup_session(self) -> None:
        """
        Supprime complètement le workspace temporaire.
        """

        if self.session_root is None:
            return

        root = self.session_root

        if root.exists():
            shutil.rmtree(
                root
            )

        self.session_root = None

    # ------------------------------------------------------------------
    # ETAT
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        return (
            self.session_root is not None
            and self.session_root.exists()
        )
