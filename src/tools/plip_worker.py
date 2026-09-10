# -*- coding: utf-8 -*-
"""
plip_worker.py

Execute PLIP directement en appelant sa fonction main() Python,
dans un sous-processus qui relance l'executable lui-meme (avec
l'argument cache --plip-worker), plutot que de dependre d'une
commande externe "plip" introuvable une fois l'app packagee.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _fix_babel_datadir_for_python_bindings() -> None:
    """
    Le module Python "openbabel" (importe par plip via "from openbabel
    import pybel") a besoin de son propre BABEL_DATADIR, distinct de
    celui utilise pour le binaire standalone obabel.exe. Une fois
    package par PyInstaller, ses donnees se trouvent sous
    sys._MEIPASS/openbabel/share/openbabel. Doit etre positionne
    AVANT le premier "import pybel"/"import openbabel".
    """
    if not getattr(sys, "frozen", False):
        return

    data_dir = Path(sys._MEIPASS) / "openbabel" / "share" / "openbabel"
    if data_dir.exists():
        os.environ["BABEL_DATADIR"] = str(data_dir)


def run_plip_worker() -> None:
    """
    A appeler quand sys.argv[1] == "--plip-worker".
    Reconstruit des arguments compatibles avec plip.plipcmd.main()
    (qui lit sys.argv comme une vraie commande "plip ...").
    """
    _fix_babel_datadir_for_python_bindings()

    from plip.plipcmd import main as plip_main

    sys.argv = ["plip"] + sys.argv[2:]

    try:
        plip_main()
    except SystemExit as exc:
        raise SystemExit(exc.code if exc.code is not None else 0)
