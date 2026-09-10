# -*- coding: utf-8 -*-
"""
plip_worker.py

Execute PLIP directement en appelant sa fonction main() Python,
dans un sous-processus qui relance l'executable lui-meme (avec
l'argument cache --plip-worker), plutot que de dependre d'une
commande externe "plip" introuvable une fois l'app packagee.
"""

from __future__ import annotations

import sys


def run_plip_worker() -> None:
    """
    A appeler quand sys.argv[1] == "--plip-worker".
    Reconstruit des arguments compatibles avec plip.plipcmd.main()
    (qui lit sys.argv comme une vraie commande "plip ...").
    """
    from plip.plipcmd import main as plip_main

    sys.argv = ["plip"] + sys.argv[2:]

    try:
        plip_main()
    except SystemExit as exc:
        raise SystemExit(exc.code if exc.code is not None else 0)
