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


def _patch_inchikey_unavailable() -> None:
    """
    Certaines distributions d'Open Babel (dont celle utilisee ici,
    openbabel-wheel) ne compilent pas le format "inchi"/"inchikey"
    (licence InChI a part). PLIP appelle systematiquement
    molecule.write(format="inchikey") pour chaque ligand -- sans ce
    patch, l'absence du format fait planter tout le calcul PLIP.
    L'inchikey n'est qu'une metadonnee informative du rapport, pas
    utilisee pour la detection des interactions elle-meme : on peut
    donc la remplacer par une chaine vide en cas d'indisponibilite,
    sans affecter la qualite de l'analyse.
    """
    from openbabel import pybel

    original_write = pybel.Molecule.write

    def patched_write(self, format="", filename=None, overwrite=False, opt=None):
        if format == "inchikey":
            try:
                return original_write(self, format, filename, overwrite, opt)
            except ValueError:
                return ""
        return original_write(self, format, filename, overwrite, opt)

    pybel.Molecule.write = patched_write


def run_plip_worker() -> None:
    """
    A appeler quand sys.argv[1] == "--plip-worker".
    Reconstruit des arguments compatibles avec plip.plipcmd.main()
    (qui lit sys.argv comme une vraie commande "plip ...").
    """
    _fix_babel_datadir_for_python_bindings()
    _patch_inchikey_unavailable()

    from plip.plipcmd import main as plip_main

    sys.argv = ["plip"] + sys.argv[2:]

    try:
        plip_main()
    except SystemExit as exc:
        raise SystemExit(exc.code if exc.code is not None else 0)
