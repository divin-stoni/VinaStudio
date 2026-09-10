#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import multiprocessing

multiprocessing.freeze_support()

if len(sys.argv) > 1 and sys.argv[1] == "--plip-worker":
    from src.tools.plip_worker import run_plip_worker
    run_plip_worker()
    raise SystemExit(0)

from src.tools.vcredist_check import ensure_vcredist_installed
ensure_vcredist_installed()

from src.gui.main_window import main

if __name__ == "__main__":
    raise SystemExit(main())
