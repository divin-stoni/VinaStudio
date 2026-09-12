# -*- coding: utf-8 -*-
"""
vcredist_check.py

Verification/installation silencieuse du Visual C++ Redistributable,
necessaire uniquement en mode package (PyInstaller/Windows).
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path


def _vcredist_present() -> bool:
    """Verifie rapidement (sans installateur) si le runtime est present."""
    try:
        ctypes.WinDLL("vcruntime140.dll")
        ctypes.WinDLL("vcruntime140_1.dll")
        ctypes.WinDLL("msvcp140.dll")
        return True
    except OSError:
        return False


def ensure_vcredist_installed() -> None:
    """
    A appeler tout au debut de run_gui.py, avant le reste.
    Ne fait rien si le runtime est deja present (cas normal, quasi
    instantane). Sinon, lance l'installateur embarque silencieusement
    (necessite les droits administrateur : UAC s'affichera une seule
    fois, uniquement sur une machine qui n'a jamais eu le runtime).
    """
    if not getattr(sys, "frozen", False):
        return  # dev : pas concerne

    if not sys.platform.startswith("win"):
        return  # Linux/macOS : le VC++ Redistributable n'existe pas ici

    if _vcredist_present():
        return

    bundled = Path(sys._MEIPASS) / "vcredist" / "vc_redist.x64.exe"
    if not bundled.exists():
        return  # rien a faire si non embarque

    subprocess.run(
        [str(bundled), "/install", "/quiet", "/norestart"],
        check=False,
    )
