#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.tools.vcredist_check import ensure_vcredist_installed
ensure_vcredist_installed()

from src.gui.main_window import main

if __name__ == "__main__":
    raise SystemExit(main())
