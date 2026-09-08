#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_docking_sdf_tab.py

Etend la couverture des langues au premier onglet de la page Docking
("Préparer les SDF") : titre de section, description, titre de panneau,
3 boutons, label "Dossier de sortie", bouton "Préparer les molécules",
titre de panneau "État de préparation".

Introduit un mecanisme reutilisable pour la suite (onglets "Charger les
PDBQT" et "Lancer le docking") : DockingPage recoit desormais lang_mgr,
avec des helpers _t_label()/_t_button() qui enregistrent chaque widget
traduit, et une methode retranslate() qui les remet a jour d'un coup.

A lancer depuis le dossier "src" du projet, APRES les 3 patches
precedents (i18n_and_imports, fix_lang_mgr_visualization_page,
i18n_extend_navigation) :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_docking_sdf_tab.py
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

TS = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE = Path.cwd()
REQUIRED = ["gui/main_window.py", "translations.py"]


def locate_base() -> Path:
    if all((BASE / f).exists() for f in REQUIRED):
        return BASE
    if all((BASE / "src" / f).exists() for f in REQUIRED):
        return BASE / "src"
    print("[ERREUR] Fichiers attendus introuvables depuis ce dossier.")
    print("Lance ce script depuis le dossier 'src' du projet.")
    sys.exit(1)


def apply_one(text: str, old: str, new: str, label: str, report: list):
    count = text.count(old)
    if count != 1:
        report.append(f"[ECHEC] {label} (trouve {count} fois au lieu de 1)")
        return text, False
    report.append(f"[OK] {label}")
    return text.replace(old, new, 1), True


NEW_TR_KEYS = '''    "sdf_section_title": {
        "fr": "Préparation des ligands", "en": "Ligand preparation",
        "de": "Ligandenvorbereitung", "zh": "配体制备", "ja": "リガンド調製",
    },
    "sdf_section_desc": {
        "fr": "Importez un ou plusieurs fichiers SDF, ou un dossier contenant des fichiers SDF, puis convertissez les molécules en fichiers PDBQT utilisables par AutoDock Vina.",
        "en": "Import one or more SDF files, or a folder containing SDF files, then convert the molecules into PDBQT files usable by AutoDock Vina.",
        "de": "Importieren Sie eine oder mehrere SDF-Dateien oder einen Ordner mit SDF-Dateien und konvertieren Sie die Moleküle anschließend in PDBQT-Dateien, die von AutoDock Vina verwendet werden können.",
        "zh": "导入一个或多个 SDF 文件，或包含 SDF 文件的文件夹，然后将分子转换为 AutoDock Vina 可用的 PDBQT 文件。",
        "ja": "1つ以上のSDFファイル、またはSDFファイルを含むフォルダをインポートし、分子をAutoDock Vinaで使用できるPDBQTファイルに変換します。",
    },
    "sdf_panel_title": {
        "fr": "Bibliothèque SDF", "en": "SDF library",
        "de": "SDF-Bibliothek", "zh": "SDF 库", "ja": "SDFライブラリ",
    },
    "sdf_btn_add_files": {
        "fr": "Ajouter des fichiers SDF", "en": "Add SDF files",
        "de": "SDF-Dateien hinzufügen", "zh": "添加 SDF 文件", "ja": "SDFファイルを追加",
    },
    "sdf_btn_add_folder": {
        "fr": "Ajouter un dossier", "en": "Add a folder",
        "de": "Ordner hinzufügen", "zh": "添加文件夹", "ja": "フォルダを追加",
    },
    "sdf_btn_clear_selection": {
        "fr": "Vider la sélection", "en": "Clear selection",
        "de": "Auswahl leeren", "zh": "清空选择", "ja": "選択をクリア",
    },
    "sdf_output_folder_label": {
        "fr": "Dossier de sortie", "en": "Output folder",
        "de": "Ausgabeordner", "zh": "输出文件夹", "ja": "出力フォルダ",
    },
    "sdf_btn_prepare_molecules": {
        "fr": "Préparer les molécules", "en": "Prepare molecules",
        "de": "Moleküle vorbereiten", "zh": "准备分子", "ja": "分子を準備",
    },
    "sdf_state_panel_title": {
        "fr": "État de préparation", "en": "Preparation status",
        "de": "Vorbereitungsstatus", "zh": "准备状态", "ja": "準備状況",
    },
'''


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"
    translations_py = root / "translations.py"

    report = []
    for f in (main_window_py, translations_py):
        bak = f.with_name(f"{f.name}.backup_i18n_docking_sdf_{TS}")
        shutil.copy2(f, bak)
        print(f"Sauvegarde : {bak}")
    print()

    # ------------------------------------------------------------------
    # translations.py
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''    "menu_help": {
        "fr": "Aide", "en": "Help", "de": "Hilfe", "zh": "帮助", "ja": "ヘルプ",
    },
}


def tr(key, lang="fr", **kwargs):'''
    anchor_new = '''    "menu_help": {
        "fr": "Aide", "en": "Help", "de": "Hilfe", "zh": "帮助", "ja": "ヘルプ",
    },
''' + NEW_TR_KEYS + '''}


def tr(key, lang="fr", **kwargs):'''
    text, _ = apply_one(text, anchor_old, anchor_new, "Ajout des cles onglet SDF", report)
    translations_py.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # gui/main_window.py
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")

    # 1) Signature DockingPage.__init__ + lang_mgr
    text, _ = apply_one(
        text,
        '''class DockingPage(QWidget):

    def __init__(self):

        super().__init__()

        self.visualization_manager = VisualizationManager()''',
        '''class DockingPage(QWidget):

    def __init__(self, lang_mgr=None):

        super().__init__()

        self.lang_mgr = lang_mgr
        self._i18n = []

        self.visualization_manager = VisualizationManager()''',
        "DockingPage : ajout du parametre lang_mgr",
        report,
    )

    # 2) Helpers _t_label / _t_button / retranslate, inseres apres la
    #    construction du stack de pages.
    text, _ = apply_one(
        text,
        '''        self.stack.addWidget(self.sdf_page)
        self.stack.addWidget(self.pdbqt_page)
        self.stack.addWidget(self.docking_page)

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------''',
        '''        self.stack.addWidget(self.sdf_page)
        self.stack.addWidget(self.pdbqt_page)
        self.stack.addWidget(self.docking_page)

    # ------------------------------------------------------------------
    # TRADUCTION
    # ------------------------------------------------------------------

    def _t_label(self, key, fallback, object_name=None):
        text = self.lang_mgr.t(key) if self.lang_mgr else fallback
        label = make_label(text, object_name)
        self._i18n.append((label, key, fallback))
        return label

    def _t_button(self, key, fallback, primary=False):
        text = self.lang_mgr.t(key) if self.lang_mgr else fallback
        button = create_button(text, primary=primary)
        self._i18n.append((button, key, fallback))
        return button

    def retranslate(self):
        for widget, key, fallback in self._i18n:
            widget.setText(self.lang_mgr.t(key) if self.lang_mgr else fallback)

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------''',
        "DockingPage : ajout des helpers _t_label/_t_button/retranslate",
        report,
    )

    # 3) Titre + description de section
    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label(
                "Préparation des ligands",
                "SectionTitle",
            )
        )

        layout.addWidget(
            make_label(
                "Importez un ou plusieurs fichiers SDF, ou un dossier "
                "contenant des fichiers SDF, puis convertissez les molécules "
                "en fichiers PDBQT utilisables par AutoDock Vina.",
                "SectionDescription",
            )
        )''',
        '''        layout.addWidget(
            self._t_label(
                "sdf_section_title",
                "Préparation des ligands",
                "SectionTitle",
            )
        )

        layout.addWidget(
            self._t_label(
                "sdf_section_desc",
                "Importez un ou plusieurs fichiers SDF, ou un dossier "
                "contenant des fichiers SDF, puis convertissez les molécules "
                "en fichiers PDBQT utilisables par AutoDock Vina.",
                "SectionDescription",
            )
        )''',
        "Onglet SDF : titre + description traduits",
        report,
    )

    # 4) Titre de panneau "Bibliotheque SDF"
    text, _ = apply_one(
        text,
        '''        panel_layout.addWidget(
            make_panel_title("Bibliothèque SDF")
        )''',
        '''        panel_layout.addWidget(
            self._t_label("sdf_panel_title", "Bibliothèque SDF", "PanelTitle")
        )''',
        "Onglet SDF : titre de panneau traduit",
        report,
    )

    # 5) Boutons Ajouter fichiers / Ajouter dossier / Vider selection
    text, _ = apply_one(
        text,
        '''        add_files = create_button(
            "Ajouter des fichiers SDF"
        )''',
        '''        add_files = self._t_button(
            "sdf_btn_add_files",
            "Ajouter des fichiers SDF",
        )''',
        "Onglet SDF : bouton 'Ajouter des fichiers SDF' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        add_folder = create_button(
            "Ajouter un dossier"
        )''',
        '''        add_folder = self._t_button(
            "sdf_btn_add_folder",
            "Ajouter un dossier",
        )''',
        "Onglet SDF : bouton 'Ajouter un dossier' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        clear = create_button(
            "Vider la sélection"
        )''',
        '''        clear = self._t_button(
            "sdf_btn_clear_selection",
            "Vider la sélection",
        )''',
        "Onglet SDF : bouton 'Vider la sélection' traduit",
        report,
    )

    # 6) Label "Dossier de sortie"
    text, _ = apply_one(
        text,
        '''        panel_layout.addWidget(
            make_label("Dossier de sortie")
        )''',
        '''        panel_layout.addWidget(
            self._t_label("sdf_output_folder_label", "Dossier de sortie")
        )''',
        "Onglet SDF : label 'Dossier de sortie' traduit",
        report,
    )

    # 7) Bouton "Preparer les molecules"
    text, _ = apply_one(
        text,
        '''        self.prepare_button = create_button(
            "Préparer les molécules",
            primary=True,
        )''',
        '''        self.prepare_button = self._t_button(
            "sdf_btn_prepare_molecules",
            "Préparer les molécules",
            primary=True,
        )''',
        "Onglet SDF : bouton 'Préparer les molécules' traduit",
        report,
    )

    # 8) Titre de panneau "Etat de preparation"
    text, _ = apply_one(
        text,
        '''        log_layout.addWidget(
            make_panel_title(
                "État de préparation"
            )
        )''',
        '''        log_layout.addWidget(
            self._t_label(
                "sdf_state_panel_title",
                "État de préparation",
                "PanelTitle",
            )
        )''',
        "Onglet SDF : titre de panneau 'État de préparation' traduit",
        report,
    )

    # 9) Instanciation de DockingPage avec lang_mgr
    text, _ = apply_one(
        text,
        '''        self.docking_page = DockingPage()''',
        '''        self.docking_page = DockingPage(lang_mgr=self.lang_mgr)''',
        "MainWindow : transmission de lang_mgr a DockingPage",
        report,
    )

    # 10) Appel de docking_page.retranslate() dans MainWindow.retranslate_ui()
    text, _ = apply_one(
        text,
        '''        if hasattr(self, "docking_page") and hasattr(self.docking_page, "secondary"):
            nav = self.docking_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_docking").upper())
            dock_labels = [t("dock_tab_prepare_sdf"), t("dock_tab_load_pdbqt"), t("dock_tab_run_docking")]
            for btn, lbl in zip(nav.buttons, dock_labels):
                btn.setText(lbl)''',
        '''        if hasattr(self, "docking_page") and hasattr(self.docking_page, "secondary"):
            nav = self.docking_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_docking").upper())
            dock_labels = [t("dock_tab_prepare_sdf"), t("dock_tab_load_pdbqt"), t("dock_tab_run_docking")]
            for btn, lbl in zip(nav.buttons, dock_labels):
                btn.setText(lbl)

        if hasattr(self, "docking_page") and hasattr(self.docking_page, "retranslate"):
            self.docking_page.retranslate()''',
        "MainWindow.retranslate_ui() : appel de docking_page.retranslate()",
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
