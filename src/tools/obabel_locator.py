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

    - Si l'application tourne en executable package (PyInstaller,
      typiquement sur Windows) ET qu'un obabel.exe embarque existe
      dans obabel_runtime/bin/, on l'utilise directement.
    - Sinon (execution normale en Python, notamment sur Linux),
      on garde le comportement historique : "obabel" recherche
      dans le PATH systeme.
    """
    if getattr(sys, "frozen", False):
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
