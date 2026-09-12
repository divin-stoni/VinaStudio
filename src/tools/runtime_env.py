# -*- coding: utf-8 -*-
"""
runtime_env.py

Configuration de l'environnement d'execution pour les outils
externes embarques (Vina, Open Babel) en mode application
packagee (PyInstaller), sur Linux comme sur Windows.
"""

from __future__ import annotations

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_configured = False


def configure_bundled_runtime() -> None:
    """
    Prepare les variables d'environnement necessaires pour que
    les executables embarques (vina, obabel) retrouvent leurs
    bibliotheques partagees et donnees, une seule fois par
    session.

    Ne fait rien si l'application ne tourne pas en mode packagee :
    dans ce cas, les outils installes au niveau systeme sont
    utilises tels quels (comportement historique inchange).
    """
    global _configured

    if _configured:
        return
    _configured = True

    if not getattr(sys, "frozen", False):
        return

    if sys.platform.startswith("linux"):
        lib_dir = PROJECT_ROOT / "runtime_libs"
        if lib_dir.exists():
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                f"{lib_dir}{os.pathsep}{existing}" if existing else str(lib_dir)
            )

        plugin_dir = PROJECT_ROOT / "obabel_runtime" / "lib" / "openbabel"
        if plugin_dir.exists():
            os.environ["BABEL_LIBDIR"] = str(plugin_dir)

        data_dir = PROJECT_ROOT / "obabel_runtime" / "share" / "openbabel"
        if data_dir.exists():
            os.environ["BABEL_DATADIR"] = str(data_dir)
