#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import src.win_no_console  # noqa: F401
import sys
import multiprocessing

multiprocessing.freeze_support()

if len(sys.argv) > 1 and sys.argv[1] == "--plip-worker":
    from src.tools.plip_worker import run_plip_worker
    run_plip_worker()
    raise SystemExit(0)

from src.tools.vcredist_check import ensure_vcredist_installed
ensure_vcredist_installed()

if __name__ == "__main__":
    from src.tools import startup as _startup

    _st = _startup.begin()
    if _st is None:
        raise SystemExit(0)  # une autre instance tourne deja

    try:
        _st.preload()
        from src.gui.main_window import main
        _code = main(_st)
    finally:
        _st.close()

    raise SystemExit(_code)
