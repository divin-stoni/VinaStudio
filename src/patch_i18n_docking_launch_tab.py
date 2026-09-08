#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_docking_launch_tab.py

Etend la couverture des langues au troisieme onglet de la page Docking
("Lancer le docking") pour les elements STATIQUES (titres de section et
de panneaux, labels de champs, boutons Annuler/Lancer).

Ne touche pas (dynamique, gere plus tard) : execution_status,
current_ligand, mexr_receptor_label, mexr_info_label — ces textes
changent en cours de calcul.

A lancer depuis le dossier "src" du projet, APRES patch_i18n_docking_pdbqt_tab.py :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_docking_launch_tab.py
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


NEW_TR_KEYS = '''    "dock_config_section_title": {
        "fr": "Configuration du docking", "en": "Docking configuration",
        "de": "Docking-Konfiguration", "zh": "对接配置", "ja": "ドッキング設定",
    },
    "dock_config_section_desc": {
        "fr": "Sélectionnez la cible et vérifiez les paramètres de calcul avant de lancer la campagne.",
        "en": "Select the target and check the calculation parameters before launching the campaign.",
        "de": "Wählen Sie das Ziel aus und überprüfen Sie die Berechnungsparameter, bevor Sie die Kampagne starten.",
        "zh": "在启动计算活动之前，请选择目标并检查计算参数。",
        "ja": "キャンペーンを開始する前に、ターゲットを選択し、計算パラメータを確認してください。",
    },
    "dock_target_panel_title": {
        "fr": "Cible biologique", "en": "Biological target",
        "de": "Biologisches Ziel", "zh": "生物靶标", "ja": "生物学的標的",
    },
    "dock_receptor_label": {
        "fr": "Récepteur", "en": "Receptor", "de": "Rezeptor",
        "zh": "受体", "ja": "レセプター",
    },
    "dock_gridbox_panel_title": {
        "fr": "Grid box", "en": "Grid box", "de": "Grid Box",
        "zh": "格点框 (Grid Box)", "ja": "グリッドボックス",
    },
    "grid_center_x": {
        "fr": "Centre X", "en": "Center X", "de": "Zentrum X",
        "zh": "中心 X", "ja": "中心X",
    },
    "grid_center_y": {
        "fr": "Centre Y", "en": "Center Y", "de": "Zentrum Y",
        "zh": "中心 Y", "ja": "中心Y",
    },
    "grid_center_z": {
        "fr": "Centre Z", "en": "Center Z", "de": "Zentrum Z",
        "zh": "中心 Z", "ja": "中心Z",
    },
    "grid_size_x": {
        "fr": "Taille X", "en": "Size X", "de": "Größe X",
        "zh": "尺寸 X", "ja": "サイズX",
    },
    "grid_size_y": {
        "fr": "Taille Y", "en": "Size Y", "de": "Größe Y",
        "zh": "尺寸 Y", "ja": "サイズY",
    },
    "grid_size_z": {
        "fr": "Taille Z", "en": "Size Z", "de": "Größe Z",
        "zh": "尺寸 Z", "ja": "サイズZ",
    },
    "dock_vina_params_panel_title": {
        "fr": "Paramètres Vina", "en": "Vina parameters",
        "de": "Vina-Parameter", "zh": "Vina 参数", "ja": "Vinaパラメータ",
    },
    "dock_num_modes_label": {
        "fr": "Nombre de modes", "en": "Number of modes",
        "de": "Anzahl der Modi", "zh": "模式数量", "ja": "モード数",
    },
    "dock_mexr_config_panel_title": {
        "fr": "Configuration MexR", "en": "MexR configuration",
        "de": "MexR-Konfiguration", "zh": "MexR 配置", "ja": "MexR設定",
    },
    "dock_execution_panel_title": {
        "fr": "Exécution", "en": "Execution", "de": "Ausführung",
        "zh": "执行", "ja": "実行",
    },
    "dock_btn_cancel": {
        "fr": "Annuler", "en": "Cancel", "de": "Abbrechen",
        "zh": "取消", "ja": "キャンセル",
    },
    "dock_execution_log_panel_title": {
        "fr": "Journal d'exécution", "en": "Execution log",
        "de": "Ausführungsprotokoll", "zh": "执行日志", "ja": "実行ログ",
    },
'''


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"
    translations_py = root / "translations.py"

    report = []
    for f in (main_window_py, translations_py):
        bak = f.with_name(f"{f.name}.backup_i18n_docking_launch_{TS}")
        shutil.copy2(f, bak)
        print(f"Sauvegarde : {bak}")
    print()

    # ------------------------------------------------------------------
    # translations.py
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''    "pdbqt_col_status": {
        "fr": "Statut", "en": "Status", "de": "Status", "zh": "状态", "ja": "ステータス",
    },
}


def tr(key, lang="fr", **kwargs):'''
    anchor_new = '''    "pdbqt_col_status": {
        "fr": "Statut", "en": "Status", "de": "Status", "zh": "状态", "ja": "ステータス",
    },
''' + NEW_TR_KEYS + '''}


def tr(key, lang="fr", **kwargs):'''
    text, _ = apply_one(text, anchor_old, anchor_new, "Ajout des cles onglet Lancer le docking", report)
    translations_py.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # gui/main_window.py
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")

    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label(
                "Configuration du docking",
                "SectionTitle",
            )
        )

        layout.addWidget(
            make_label(
                "Sélectionnez la cible et vérifiez les paramètres "
                "de calcul avant de lancer la campagne.",
                "SectionDescription",
            )
        )''',
        '''        layout.addWidget(
            self._t_label(
                "dock_config_section_title",
                "Configuration du docking",
                "SectionTitle",
            )
        )

        layout.addWidget(
            self._t_label(
                "dock_config_section_desc",
                "Sélectionnez la cible et vérifiez les paramètres "
                "de calcul avant de lancer la campagne.",
                "SectionDescription",
            )
        )''',
        "Onglet Lancer le docking : titre + description traduits",
        report,
    )

    text, _ = apply_one(
        text,
        '''        grid.addWidget(
            make_panel_title("Cible biologique"),
            0, 0, 1, 4
        )

        grid.addWidget(
            make_label("Récepteur"),
            1, 0
        )''',
        '''        grid.addWidget(
            self._t_label("dock_target_panel_title", "Cible biologique", "PanelTitle"),
            0, 0, 1, 4
        )

        grid.addWidget(
            self._t_label("dock_receptor_label", "Récepteur"),
            1, 0
        )''',
        "Onglet Lancer le docking : panneau 'Cible biologique' + label 'Récepteur' traduits",
        report,
    )

    text, _ = apply_one(
        text,
        '''        grid.addWidget(
            make_panel_title("Grid box"),
            2, 0, 1, 4
        )''',
        '''        grid.addWidget(
            self._t_label("dock_gridbox_panel_title", "Grid box", "PanelTitle"),
            2, 0, 1, 4
        )''',
        "Onglet Lancer le docking : panneau 'Grid box' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        names = [
            ("Centre X", "center_x"),
            ("Centre Y", "center_y"),
            ("Centre Z", "center_z"),
            ("Taille X", "size_x"),
            ("Taille Y", "size_y"),
            ("Taille Z", "size_z"),
        ]

        for index, (label, key) in enumerate(names):

            row = 3 + index // 2
            col = (index % 2) * 2

            grid.addWidget(
                make_label(label),
                row,
                col,
            )''',
        '''        names = [
            ("Centre X", "center_x", "grid_center_x"),
            ("Centre Y", "center_y", "grid_center_y"),
            ("Centre Z", "center_z", "grid_center_z"),
            ("Taille X", "size_x", "grid_size_x"),
            ("Taille Y", "size_y", "grid_size_y"),
            ("Taille Z", "size_z", "grid_size_z"),
        ]

        for index, (label, key, tr_key) in enumerate(names):

            row = 3 + index // 2
            col = (index % 2) * 2

            grid.addWidget(
                self._t_label(tr_key, label),
                row,
                col,
            )''',
        "Onglet Lancer le docking : labels Centre/Taille X/Y/Z traduits",
        report,
    )

    text, _ = apply_one(
        text,
        '''        grid.addWidget(
            make_panel_title("Paramètres Vina"),
            6, 0, 1, 4
        )''',
        '''        grid.addWidget(
            self._t_label("dock_vina_params_panel_title", "Paramètres Vina", "PanelTitle"),
            6, 0, 1, 4
        )''',
        "Onglet Lancer le docking : panneau 'Paramètres Vina' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        grid.addWidget(
            make_label("Nombre de modes"),
            7, 2,
        )''',
        '''        grid.addWidget(
            self._t_label("dock_num_modes_label", "Nombre de modes"),
            7, 2,
        )''',
        "Onglet Lancer le docking : label 'Nombre de modes' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        mexr_layout.addWidget(
            make_panel_title(
                "Configuration MexR"
            )
        )''',
        '''        mexr_layout.addWidget(
            self._t_label(
                "dock_mexr_config_panel_title",
                "Configuration MexR",
                "PanelTitle",
            )
        )''',
        "Onglet Lancer le docking : panneau 'Configuration MexR' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        header.addWidget(
            make_panel_title("Exécution")
        )''',
        '''        header.addWidget(
            self._t_label("dock_execution_panel_title", "Exécution", "PanelTitle")
        )''',
        "Onglet Lancer le docking : panneau 'Exécution' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        self.cancel_button = create_button(
            "Annuler"
        )''',
        '''        self.cancel_button = self._t_button(
            "dock_btn_cancel",
            "Annuler",
        )''',
        "Onglet Lancer le docking : bouton 'Annuler' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        self.launch_button = create_button(
            "Lancer le docking",
            primary=True,
        )''',
        '''        self.launch_button = self._t_button(
            "dock_tab_run_docking",
            "Lancer le docking",
            primary=True,
        )''',
        "Onglet Lancer le docking : bouton 'Lancer le docking' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        log_layout.addWidget(
            make_panel_title("Journal d'exécution")
        )''',
        '''        log_layout.addWidget(
            self._t_label("dock_execution_log_panel_title", "Journal d'exécution", "PanelTitle")
        )''',
        "Onglet Lancer le docking : panneau 'Journal d'exécution' traduit",
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
