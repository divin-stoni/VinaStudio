#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fix_lang_mgr_visualization_page.py

Corrige l'AttributeError : 'VisualizationPage' object has no attribute 'lang_mgr'.

Cause : le patch precedent a traduit deux setText() qui vivent dans la
classe VisualizationPage (pas MainWindow) sans jamais transmettre le
lang_mgr a cette classe.

Ce script :
  1) Ajoute un parametre lang_mgr=None a VisualizationPage.__init__
  2) Transmet self.lang_mgr lors de l'instanciation dans MainWindow
  3) Securise les deux appels .t(...) avec un repli si lang_mgr est None

A lancer depuis le dossier "src" du projet :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_fix_lang_mgr_visualization_page.py
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

TS = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE = Path.cwd()
REQUIRED = ["gui/main_window.py"]


def locate_base() -> Path:
    if all((BASE / f).exists() for f in REQUIRED):
        return BASE
    if all((BASE / "src" / f).exists() for f in REQUIRED):
        return BASE / "src"
    print("[ERREUR] gui/main_window.py introuvable depuis ce dossier.")
    print("Lance ce script depuis le dossier 'src' du projet.")
    sys.exit(1)


def apply_one(text: str, old: str, new: str, label: str, report: list):
    count = text.count(old)
    if count != 1:
        report.append(f"[ECHEC] {label} (trouve {count} fois au lieu de 1)")
        return text, False
    report.append(f"[OK] {label}")
    return text.replace(old, new, 1), True


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"

    bak = main_window_py.with_name(f"main_window.py.backup_fix_lang_mgr_{TS}")
    shutil.copy2(main_window_py, bak)
    print(f"Sauvegarde : {bak}\n")

    text = main_window_py.read_text(encoding="utf-8")
    report = []

    text, _ = apply_one(
        text,
        '''    def __init__(self, docking_page=None, analysis_page=None):

        super().__init__()

        self.docking_page = docking_page
        self.analysis_page = analysis_page''',
        '''    def __init__(self, docking_page=None, analysis_page=None, lang_mgr=None):

        super().__init__()

        self.docking_page = docking_page
        self.analysis_page = analysis_page
        self.lang_mgr = lang_mgr''',
        "Ajout du parametre lang_mgr a VisualizationPage.__init__",
        report,
    )

    text, _ = apply_one(
        text,
        '''        self.visualization_page = VisualizationPage(
            docking_page=getattr(self, "docking_page", None),
            analysis_page=getattr(self, "analysis_page", None),
        )''',
        '''        self.visualization_page = VisualizationPage(
            docking_page=getattr(self, "docking_page", None),
            analysis_page=getattr(self, "analysis_page", None),
            lang_mgr=getattr(self, "lang_mgr", None),
        )''',
        "Transmission de lang_mgr lors de l'instanciation de VisualizationPage",
        report,
    )

    text, _ = apply_one(
        text,
        '''        self.batch_status.setText(self.lang_mgr.t("status_loading_hits"))''',
        '''        self.batch_status.setText(
            self.lang_mgr.t("status_loading_hits") if self.lang_mgr
            else "Chargement des hits de docking…"
        )''',
        "Securisation de l'appel .t() pour status_loading_hits",
        report,
    )

    text, _ = apply_one(
        text,
        '''            self.plip_errors_label.setText(self.lang_mgr.t("status_no_errors"))''',
        '''            self.plip_errors_label.setText(
                self.lang_mgr.t("status_no_errors") if self.lang_mgr
                else "Aucune erreur."
            )''',
        "Securisation de l'appel .t() pour status_no_errors",
        report,
    )

    main_window_py.write_text(text, encoding="utf-8")

    print("=== RAPPORT ===")
    for line in report:
        print(line)

    n_fail = sum(1 for l in report if "ECHEC" in l)
    print("\nTermine avec succes." if n_fail == 0 else f"\nTermine avec {n_fail} bloc(s) en echec.")


if __name__ == "__main__":
    main()
