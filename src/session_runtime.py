# -*- coding: utf-8 -*-
"""
session_runtime.py

Frontière de session de STONI.

Principe :
    Tout ce qui est généré par le logiciel pendant une session est
    considéré comme temporaire tant qu'il n'a pas été exporté.

    Les fichiers utilisateur importés ne sont PAS supprimés.

    Les anciens répertoires de résultats legacy sont purgés :
        - docking/results/
        - visualization_results/

    Le workspace .session/ est également nettoyé lorsqu'il s'agit
    d'anciennes sessions temporaires.

Ce module ne supprime jamais :
        - les fichiers d'entrée utilisateur situés hors des sorties
          logicielles ;
        - le code source ;
        - le venv ;
        - les fichiers de configuration utilisateur ;
        - les sauvegardes Python ;
        - les exports explicitement placés ailleurs.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# RACINES LOGICIELLES TEMPORAIRES
# ---------------------------------------------------------------------------

LEGACY_GENERATED_ROOTS = (
    PROJECT_ROOT / "docking" / "results",
    PROJECT_ROOT / "visualization_results",
    PROJECT_ROOT / "docking" / "ligands" / "prepared",
)


SESSION_ROOT = PROJECT_ROOT / ".session"


# ---------------------------------------------------------------------------
# SECURITE
# ---------------------------------------------------------------------------

def _safe_remove_tree(path: Path) -> None:
    """
    Supprime uniquement un répertoire explicitement autorisé.
    """

    path = path.resolve()

    if path == Path("/"):
        raise RuntimeError("Refus de supprimer /")

    if path == PROJECT_ROOT:
        raise RuntimeError("Refus de supprimer le projet entier")

    if not str(path).startswith(str(PROJECT_ROOT) + os.sep):
        raise RuntimeError(
            f"Refus de supprimer un chemin hors projet : {path}"
        )

    if path.exists():
        print(f"[SESSION CLEANUP] suppression : {path}")
        shutil.rmtree(path, ignore_errors=False)


def _safe_remove_file(path: Path) -> None:
    path = path.resolve()

    if not str(path).startswith(str(PROJECT_ROOT) + os.sep):
        raise RuntimeError(
            f"Refus de supprimer un fichier hors projet : {path}"
        )

    if path.exists() and path.is_file():
        print(f"[SESSION CLEANUP] suppression fichier : {path}")
        path.unlink()


# ---------------------------------------------------------------------------
# NETTOYAGE DES SORTIES LEGACY
# ---------------------------------------------------------------------------

def cleanup_legacy_outputs() -> None:
    """
    Supprime les sorties générées par les anciennes versions du logiciel.

    C'est cette fonction qui élimine notamment les anciens :
        docking/results/batch_vina_engine/...
        visualization_results/...
    """

    print()
    print("[SESSION] Nettoyage des sorties legacy...")

    for root in LEGACY_GENERATED_ROOTS:
        if root.exists():
            _safe_remove_tree(root)

    print("[SESSION] Sorties legacy nettoyées.")


# ---------------------------------------------------------------------------
# NETTOYAGE DES ANCIENNES SESSIONS
# ---------------------------------------------------------------------------

def cleanup_old_sessions() -> None:
    """
    Supprime les anciennes sessions temporaires.

    Les exports externes ne sont pas concernés.
    """

    if not SESSION_ROOT.exists():
        return

    print("[SESSION] Nettoyage des anciennes sessions...")

    for child in SESSION_ROOT.iterdir():
        if child.is_dir():
            _safe_remove_tree(child)

    print("[SESSION] Anciennes sessions nettoyées.")


# ---------------------------------------------------------------------------
# NOUVELLE SESSION
# ---------------------------------------------------------------------------

def start_new_session() -> None:
    """
    Prépare une session totalement propre.

    Ordre volontaire :
        1. sorties legacy
        2. anciennes sessions
        3. création d'une nouvelle session
    """

    print()
    print("=" * 78)
    print("[SESSION] NOUVELLE SESSION")
    print("=" * 78)

    cleanup_legacy_outputs()
    cleanup_old_sessions()

    print("[SESSION] Session prête.")
    print()


# ---------------------------------------------------------------------------
# FIN DE SESSION
# ---------------------------------------------------------------------------

def end_session() -> None:
    """
    Nettoyage final à la fermeture.

    Les données exportées ailleurs ne sont pas supprimées.
    """

    print()
    print("=" * 78)
    print("[SESSION] FERMETURE — NETTOYAGE")
    print("=" * 78)

    cleanup_legacy_outputs()

    # Ne supprime que les workspaces temporaires.
    cleanup_old_sessions()

    print("[SESSION] Nettoyage terminé.")
    print()


# ---------------------------------------------------------------------------
# RESET AVANT NOUVEAU DOCKING
# ---------------------------------------------------------------------------

def reset_before_docking() -> None:
    """
    Nettoyage avant le démarrage d'un nouveau docking.

    Ceci empêche un nouveau docking de récupérer les hits du précédent.
    """

    print()
    print("=" * 78)
    print("[SESSION] RESET AVANT DOCKING")
    print("=" * 78)

    cleanup_legacy_outputs()

    print("[SESSION] Anciennes sorties docking supprimées.")
    print("[SESSION] Nouveau docking autorisé.")
    print()
