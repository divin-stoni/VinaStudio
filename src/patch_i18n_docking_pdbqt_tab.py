#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_docking_pdbqt_tab.py

Etend la couverture des langues au deuxieme onglet de la page Docking
("Charger les PDBQT") : titre de section, description, 5 boutons de la
toolbar, et les en-tetes du tableau (#, Molecule, Fichier, Statut).

A lancer depuis le dossier "src" du projet, APRES patch_i18n_docking_sdf_tab.py :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_docking_pdbqt_tab.py
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


NEW_TR_KEYS = '''    "pdbqt_section_title": {
        "fr": "Ligands PDBQT", "en": "PDBQT ligands", "de": "PDBQT-Liganden",
        "zh": "PDBQT 配体", "ja": "PDBQTリガンド",
    },
    "pdbqt_section_desc": {
        "fr": "Contrôlez les ligands disponibles avant leur utilisation dans la campagne de docking.",
        "en": "Review the available ligands before using them in the docking campaign.",
        "de": "Überprüfen Sie die verfügbaren Liganden, bevor Sie sie in der Docking-Kampagne verwenden.",
        "zh": "在对接活动中使用配体之前，请检查可用的配体。",
        "ja": "ドッキングキャンペーンで使用する前に、利用可能なリガンドを確認してください。",
    },
    "pdbqt_btn_add_files": {
        "fr": "Ajouter des fichiers", "en": "Add files",
        "de": "Dateien hinzufügen", "zh": "添加文件", "ja": "ファイルを追加",
    },
    "pdbqt_btn_refresh": {
        "fr": "Actualiser", "en": "Refresh", "de": "Aktualisieren",
        "zh": "刷新", "ja": "更新",
    },
    "pdbqt_btn_select_all": {
        "fr": "Tout sélectionner", "en": "Select all", "de": "Alles auswählen",
        "zh": "全选", "ja": "すべて選択",
    },
    "pdbqt_btn_clear_selection": {
        "fr": "Effacer sélection", "en": "Clear selection", "de": "Auswahl löschen",
        "zh": "清除选择", "ja": "選択を消去",
    },
    "pdbqt_btn_use_selection": {
        "fr": "Utiliser la sélection", "en": "Use selection", "de": "Auswahl verwenden",
        "zh": "使用所选", "ja": "選択を使用",
    },
    "pdbqt_col_index": {
        "fr": "#", "en": "#", "de": "#", "zh": "#", "ja": "#",
    },
    "pdbqt_col_molecule": {
        "fr": "Molécule", "en": "Molecule", "de": "Molekül", "zh": "分子", "ja": "分子",
    },
    "pdbqt_col_file": {
        "fr": "Fichier", "en": "File", "de": "Datei", "zh": "文件", "ja": "ファイル",
    },
    "pdbqt_col_status": {
        "fr": "Statut", "en": "Status", "de": "Status", "zh": "状态", "ja": "ステータス",
    },
'''


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"
    translations_py = root / "translations.py"

    report = []
    for f in (main_window_py, translations_py):
        bak = f.with_name(f"{f.name}.backup_i18n_docking_pdbqt_{TS}")
        shutil.copy2(f, bak)
        print(f"Sauvegarde : {bak}")
    print()

    # ------------------------------------------------------------------
    # translations.py
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''    "sdf_state_panel_title": {
        "fr": "État de préparation", "en": "Preparation status",
        "de": "Vorbereitungsstatus", "zh": "准备状态", "ja": "準備状況",
    },
}


def tr(key, lang="fr", **kwargs):'''
    anchor_new = '''    "sdf_state_panel_title": {
        "fr": "État de préparation", "en": "Preparation status",
        "de": "Vorbereitungsstatus", "zh": "准备状态", "ja": "準備状況",
    },
''' + NEW_TR_KEYS + '''}


def tr(key, lang="fr", **kwargs):'''
    text, _ = apply_one(text, anchor_old, anchor_new, "Ajout des cles onglet PDBQT", report)
    translations_py.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # gui/main_window.py
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")

    # 1) Helper supplementaire pour les en-tetes de tableau + retranslate etendu
    text, _ = apply_one(
        text,
        '''    def retranslate(self):
        for widget, key, fallback in self._i18n:
            widget.setText(self.lang_mgr.t(key) if self.lang_mgr else fallback)''',
        '''    def _pdbqt_table_headers(self):
        if self.lang_mgr:
            return [
                self.lang_mgr.t("pdbqt_col_index"),
                self.lang_mgr.t("pdbqt_col_molecule"),
                self.lang_mgr.t("pdbqt_col_file"),
                self.lang_mgr.t("pdbqt_col_status"),
            ]
        return ["#", "Molécule", "Fichier", "Statut"]

    def retranslate(self):
        for widget, key, fallback in self._i18n:
            widget.setText(self.lang_mgr.t(key) if self.lang_mgr else fallback)

        if hasattr(self, "pdbqt_table"):
            self.pdbqt_table.setHorizontalHeaderLabels(self._pdbqt_table_headers())''',
        "DockingPage : ajout de _pdbqt_table_headers() + extension de retranslate()",
        report,
    )

    # 2) Titre + description de section
    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label(
                "Ligands PDBQT",
                "SectionTitle",
            )
        )

        layout.addWidget(
            make_label(
                "Contrôlez les ligands disponibles avant leur utilisation "
                "dans la campagne de docking.",
                "SectionDescription",
            )
        )''',
        '''        layout.addWidget(
            self._t_label(
                "pdbqt_section_title",
                "Ligands PDBQT",
                "SectionTitle",
            )
        )

        layout.addWidget(
            self._t_label(
                "pdbqt_section_desc",
                "Contrôlez les ligands disponibles avant leur utilisation "
                "dans la campagne de docking.",
                "SectionDescription",
            )
        )''',
        "Onglet PDBQT : titre + description traduits",
        report,
    )

    # 3) Boutons de la toolbar
    text, _ = apply_one(
        text,
        '''        add = create_button("Ajouter des fichiers")
        add.clicked.connect(self.add_pdbqt_files)

        refresh = create_button("Actualiser")
        refresh.clicked.connect(self.refresh_pdbqt_table)

        select_all = create_button("Tout sélectionner")
        select_all.clicked.connect(
            self.select_all_pdbqt
        )

        clear_selection = create_button("Effacer sélection")
        clear_selection.clicked.connect(
            self.clear_pdbqt_selection
        )

        use_selection = create_button(
            "Utiliser la sélection",
            primary=True,
        )
        use_selection.clicked.connect(
            self.use_selected_pdbqt
        )''',
        '''        add = self._t_button("pdbqt_btn_add_files", "Ajouter des fichiers")
        add.clicked.connect(self.add_pdbqt_files)

        refresh = self._t_button("pdbqt_btn_refresh", "Actualiser")
        refresh.clicked.connect(self.refresh_pdbqt_table)

        select_all = self._t_button("pdbqt_btn_select_all", "Tout sélectionner")
        select_all.clicked.connect(
            self.select_all_pdbqt
        )

        clear_selection = self._t_button("pdbqt_btn_clear_selection", "Effacer sélection")
        clear_selection.clicked.connect(
            self.clear_pdbqt_selection
        )

        use_selection = self._t_button(
            "pdbqt_btn_use_selection",
            "Utiliser la sélection",
            primary=True,
        )
        use_selection.clicked.connect(
            self.use_selected_pdbqt
        )''',
        "Onglet PDBQT : 5 boutons de toolbar traduits",
        report,
    )

    # 4) En-tetes du tableau (construction initiale, via helper commun)
    text, _ = apply_one(
        text,
        '''        self.pdbqt_table.setHorizontalHeaderLabels(
            [
                "#",
                "Molécule",
                "Fichier",
                "Statut",
            ]
        )''',
        '''        self.pdbqt_table.setHorizontalHeaderLabels(
            self._pdbqt_table_headers()
        )''',
        "Onglet PDBQT : en-tetes de tableau traduits",
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
