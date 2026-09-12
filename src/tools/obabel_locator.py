# -*- coding: utf-8 -*-
"""
obabel_locator.py

Resolution de l'executable Open Babel (obabel) et de son
environnement (BABEL_DATADIR), avec prise en charge du mode
package (PyInstaller, typiquement sur Windows).
"""

from __future__ import annotations

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_obabel_executable() -> str:
    """
    Determine le chemin de l'executable obabel a utiliser.

    - Si l'application tourne en executable package (PyInstaller)
      ET qu'un binaire obabel embarque existe, on l'utilise
      directement (obabel_runtime/bin/obabel.exe sur Windows,
      obabel_runtime/bin/obabel sur Linux).
    - Sinon (execution normale en Python), on garde le
      comportement historique : "obabel" recherche dans le PATH
      systeme.
    """
    from src.tools.runtime_env import configure_bundled_runtime
    configure_bundled_runtime()

    if getattr(sys, "frozen", False):
        if sys.platform.startswith("linux"):
            bundled = PROJECT_ROOT / "obabel_runtime" / "bin" / "obabel"
        else:
            bundled = PROJECT_ROOT / "obabel_runtime" / "bin" / "obabel.exe"

        if bundled.exists():
            return str(bundled)

    return "obabel"


def obabel_subprocess_env() -> dict:
    """
    Construit l'environnement a transmettre aux appels subprocess
    d'obabel. Positionne BABEL_DATADIR uniquement si l'executable
    embarque (mode package) est utilise ; sinon, environnement
    systeme inchange (obabel installe normalement sait deja ou
    trouver ses propres donnees).
    """
    env = os.environ.copy()

    if getattr(sys, "frozen", False):
        data_dir = PROJECT_ROOT / "obabel_runtime" / "share" / "openbabel"
        if data_dir.exists():
            env["BABEL_DATADIR"] = str(data_dir)

    return env
