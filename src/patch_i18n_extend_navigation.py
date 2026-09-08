#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_extend_navigation.py

Etend la couverture des langues (apres patch_i18n_and_imports.py +
patch_fix_lang_mgr_visualization_page.py) a tout le "chrome" visible
en permanence :
  - Barre laterale principale (ESPACE DE TRAVAIL / Docking / Analyse / Visualisation)
  - Barres laterales secondaires de chaque page (onglets Docking, Analyse, Visualisation)
  - Boutons "Recalculer tout" / "Exporter tout" de la page Visualisation
  - Barre de menu (Fichier / Docking / Analyse / Visualisation / Outils / Aide)

Ne touche PAS (pour l'instant) : les textes internes des pages (labels de
formulaires, messages de log/statut generes pendant le docking/l'analyse,
en-tetes de tableaux). C'est un chantier separe, plus gros, a faire ensuite.

A lancer depuis le dossier "src" du projet, APRES les deux patches
precedents :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_extend_navigation.py
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


NEW_TR_KEYS = '''    "side_espace_travail": {
        "fr": "ESPACE DE TRAVAIL", "en": "WORKSPACE",
        "de": "ARBEITSBEREICH", "zh": "工作区", "ja": "ワークスペース",
    },
    "side_docking": {
        "fr": "Docking", "en": "Docking", "de": "Docking",
        "zh": "对接", "ja": "ドッキング",
    },
    "side_analysis": {
        "fr": "Analyse", "en": "Analysis", "de": "Analyse",
        "zh": "分析", "ja": "解析",
    },
    "side_visualization": {
        "fr": "Visualisation", "en": "Visualization", "de": "Visualisierung",
        "zh": "可视化", "ja": "可視化",
    },
    "dock_tab_prepare_sdf": {
        "fr": "Préparer les SDF", "en": "Prepare SDF",
        "de": "SDF vorbereiten", "zh": "准备 SDF", "ja": "SDF準備",
    },
    "dock_tab_load_pdbqt": {
        "fr": "Charger les PDBQT", "en": "Load PDBQT",
        "de": "PDBQT laden", "zh": "加载 PDBQT", "ja": "PDBQT読み込み",
    },
    "dock_tab_run_docking": {
        "fr": "Lancer le docking", "en": "Run docking",
        "de": "Docking starten", "zh": "开始对接", "ja": "ドッキング実行",
    },
    "analysis_tab_results": {
        "fr": "Résultats", "en": "Results", "de": "Ergebnisse",
        "zh": "结果", "ja": "結果",
    },
    "analysis_tab_type": {
        "fr": "Type d'analyse", "en": "Analysis type",
        "de": "Analysetyp", "zh": "分析类型", "ja": "解析タイプ",
    },
    "analysis_tab_results_analytics": {
        "fr": "Résultats analytiques", "en": "Analytical results",
        "de": "Analytische Ergebnisse", "zh": "分析结果", "ja": "分析結果",
    },
    "viz_tab_residues": {
        "fr": "Résidus de référence", "en": "Reference residues",
        "de": "Referenzreste", "zh": "参考残基", "ja": "参照残基",
    },
    "viz_tab_plip": {
        "fr": "Calcul PLIP", "en": "PLIP calculation",
        "de": "PLIP-Berechnung", "zh": "PLIP 计算", "ja": "PLIP計算",
    },
    "viz_tab_interaction2d": {
        "fr": "Interaction 2D", "en": "Interaction 2D", "de": "Interaction 2D",
        "zh": "2D 相互作用", "ja": "2D相互作用",
    },
    "viz_btn_recompute": {
        "fr": "Recalculer tout", "en": "Recompute all",
        "de": "Alles neu berechnen", "zh": "全部重新计算", "ja": "すべて再計算",
    },
    "viz_btn_export_all": {
        "fr": "Exporter tout", "en": "Export all",
        "de": "Alles exportieren", "zh": "全部导出", "ja": "すべてエクスポート",
    },
    "menu_file": {
        "fr": "Fichier", "en": "File", "de": "Datei", "zh": "文件", "ja": "ファイル",
    },
    "menu_tools": {
        "fr": "Outils", "en": "Tools", "de": "Werkzeuge", "zh": "工具", "ja": "ツール",
    },
    "menu_help": {
        "fr": "Aide", "en": "Help", "de": "Hilfe", "zh": "帮助", "ja": "ヘルプ",
    },
'''


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"
    translations_py = root / "translations.py"

    report = []

    for f in (main_window_py, translations_py):
        bak = f.with_name(f"{f.name}.backup_i18n_extend_{TS}")
        shutil.copy2(f, bak)
        print(f"Sauvegarde : {bak}")
    print()

    # ------------------------------------------------------------------
    # translations.py : nouvelles cles
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''    "status_no_errors": {
        "fr": "Aucune erreur.", "en": "No errors.",
        "de": "Keine Fehler.", "zh": "无错误。", "ja": "エラーなし。",
    },
}


def tr(key, lang="fr", **kwargs):'''
    anchor_new = '''    "status_no_errors": {
        "fr": "Aucune erreur.", "en": "No errors.",
        "de": "Keine Fehler.", "zh": "无错误。", "ja": "エラーなし。",
    },
''' + NEW_TR_KEYS + '''}


def tr(key, lang="fr", **kwargs):'''
    text, _ = apply_one(text, anchor_old, anchor_new, "Ajout des cles de navigation/menu", report)
    translations_py.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # gui/main_window.py
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")

    text, _ = apply_one(
        text,
        '''        title = make_label("ESPACE DE TRAVAIL")
        title.setStyleSheet(
            f"font-size: 10px; "
            f"font-weight: 700; "
            f"color: {COLORS['text_muted']};"
        )

        header_layout.addWidget(title)''',
        '''        self.title_label = make_label("ESPACE DE TRAVAIL")
        self.title_label.setStyleSheet(
            f"font-size: 10px; "
            f"font-weight: 700; "
            f"color: {COLORS['text_muted']};"
        )

        header_layout.addWidget(self.title_label)''',
        "PrimaryNavigation : titre conserve comme reference (self.title_label)",
        report,
    )

    text, _ = apply_one(
        text,
        '''        title_label = make_label(
            title.upper()
        )

        title_label.setStyleSheet(
            f"font-size: 11px; "
            f"font-weight: 700; "
            f"color: {COLORS['text_muted']};"
        )

        header_layout.addWidget(title_label)
        layout.addWidget(header)''',
        '''        self.title_label = make_label(
            title.upper()
        )

        self.title_label.setStyleSheet(
            f"font-size: 11px; "
            f"font-weight: 700; "
            f"color: {COLORS['text_muted']};"
        )

        header_layout.addWidget(self.title_label)
        layout.addWidget(header)''',
        "SecondaryNavigation : titre conserve comme reference (self.title_label)",
        report,
    )

    text, _ = apply_one(
        text,
        '''        secondary = SecondaryNavigation(
            "Analyse",
            [
                "Résultats",
                "Type d'analyse",
                "Résultats analytiques",
            ],
            self.switch_tab,
        )

        root.addWidget(secondary)''',
        '''        self.secondary = SecondaryNavigation(
            "Analyse",
            [
                "Résultats",
                "Type d'analyse",
                "Résultats analytiques",
            ],
            self.switch_tab,
        )

        root.addWidget(self.secondary)''',
        "AnalysisPage : secondary conserve comme reference (self.secondary)",
        report,
    )

    text, _ = apply_one(
        text,
        '''        secondary = SecondaryNavigation(
            "Visualisation",
            [
                "Résidus de référence",
                "Calcul PLIP",
                "Interaction 2D",
            ],
            self.switch_tab,
        )

        body.addWidget(secondary)''',
        '''        self.secondary = SecondaryNavigation(
            "Visualisation",
            [
                "Résidus de référence",
                "Calcul PLIP",
                "Interaction 2D",
            ],
            self.switch_tab,
        )

        body.addWidget(self.secondary)''',
        "VisualizationPage : secondary conserve comme reference (self.secondary)",
        report,
    )

    text, _ = apply_one(
        text,
        '''        file_menu = menu.addMenu("Fichier")
        docking_menu = menu.addMenu("Docking")
        analysis_menu = menu.addMenu("Analyse")
        visualization_menu = menu.addMenu("Visualisation")
        tools_menu = menu.addMenu("Outils")
        help_menu = menu.addMenu("Aide")''',
        '''        file_menu = menu.addMenu("Fichier")
        docking_menu = menu.addMenu("Docking")
        analysis_menu = menu.addMenu("Analyse")
        visualization_menu = menu.addMenu("Visualisation")
        tools_menu = menu.addMenu("Outils")
        help_menu = menu.addMenu("Aide")

        self.menu_file = file_menu
        self.menu_docking = docking_menu
        self.menu_analysis = analysis_menu
        self.menu_visualization = visualization_menu
        self.menu_tools = tools_menu
        self.menu_help = help_menu''',
        "Menu bar : references conservees (self.menu_*)",
        report,
    )

    text, _ = apply_one(
        text,
        '''        if hasattr(self, "nav_action_visualization"):
            self.nav_action_visualization.setText(t("nav_visualization"))

        if hasattr(self, "lang_action"):''',
        '''        if hasattr(self, "nav_action_visualization"):
            self.nav_action_visualization.setText(t("nav_visualization"))

        if hasattr(self, "primary_navigation"):
            nav = self.primary_navigation
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_espace_travail"))
            side_labels = [t("side_docking"), t("side_analysis"), t("side_visualization")]
            for btn, lbl in zip(nav.buttons, side_labels):
                btn.setText(lbl)

        if hasattr(self, "docking_page") and hasattr(self.docking_page, "secondary"):
            nav = self.docking_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_docking").upper())
            dock_labels = [t("dock_tab_prepare_sdf"), t("dock_tab_load_pdbqt"), t("dock_tab_run_docking")]
            for btn, lbl in zip(nav.buttons, dock_labels):
                btn.setText(lbl)

        if hasattr(self, "analysis_page") and hasattr(self.analysis_page, "secondary"):
            nav = self.analysis_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_analysis").upper())
            analysis_labels = [t("analysis_tab_results"), t("analysis_tab_type"), t("analysis_tab_results_analytics")]
            for btn, lbl in zip(nav.buttons, analysis_labels):
                btn.setText(lbl)

        if hasattr(self, "visualization_page") and hasattr(self.visualization_page, "secondary"):
            nav = self.visualization_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_visualization").upper())
            viz_labels = [t("viz_tab_residues"), t("viz_tab_plip"), t("viz_tab_interaction2d")]
            for btn, lbl in zip(nav.buttons, viz_labels):
                btn.setText(lbl)
            if hasattr(self.visualization_page, "recompute_button"):
                self.visualization_page.recompute_button.setText(t("viz_btn_recompute"))
            if hasattr(self.visualization_page, "export_all_button"):
                self.visualization_page.export_all_button.setText(t("viz_btn_export_all"))

        if hasattr(self, "menu_file"):
            self.menu_file.setTitle(t("menu_file"))
        if hasattr(self, "menu_docking"):
            self.menu_docking.setTitle(t("side_docking"))
        if hasattr(self, "menu_analysis"):
            self.menu_analysis.setTitle(t("nav_analysis"))
        if hasattr(self, "menu_visualization"):
            self.menu_visualization.setTitle(t("nav_visualization"))
        if hasattr(self, "menu_tools"):
            self.menu_tools.setTitle(t("menu_tools"))
        if hasattr(self, "menu_help"):
            self.menu_help.setTitle(t("menu_help"))

        if hasattr(self, "lang_action"):''',
        "retranslate_ui() : ajout navigation principale/secondaire + menu + boutons Visualisation",
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
