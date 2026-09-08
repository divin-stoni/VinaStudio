#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_analysis_page.py

Etend la couverture des langues a la page Analyse (les 3 onglets :
Resultats / Type d'analyse / Resultats analytiques), pour les elements
STATIQUES (titres, descriptions, boutons, en-tetes de tableau).

Ne touche pas (dynamique, gere plus tard) :
  - self.statistics_status (change en cours d'analyse)
  - Les onglets generes dynamiquement dans build_dynamic_statistics_tabs()
    ("Top candidats", "Correlations", etc.) — ils dependent des resultats
    d'une analyse et sont reconstruits a chaque execution.

A lancer depuis le dossier "src" du projet, APRES patch_i18n_docking_launch_tab.py :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_analysis_page.py
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


NEW_TR_KEYS = '''    "analysis_results_section_title": {
        "fr": "Résultats du docking", "en": "Docking results",
        "de": "Docking-Ergebnisse", "zh": "对接结果", "ja": "ドッキング結果",
    },
    "analysis_results_section_desc": {
        "fr": "Classement des molécules selon leur meilleure affinité de liaison.",
        "en": "Ranking of molecules by their best binding affinity.",
        "de": "Rangliste der Moleküle nach ihrer besten Bindungsaffinität.",
        "zh": "根据最佳结合亲和力对分子进行排名。",
        "ja": "最良の結合親和性による分子のランキング。",
    },
    "analysis_campaign_label": {
        "fr": "Campagne", "en": "Campaign", "de": "Kampagne",
        "zh": "活动", "ja": "キャンペーン",
    },
    "analysis_btn_run": {
        "fr": "Lancer l'analyse", "en": "Run analysis", "de": "Analyse starten",
        "zh": "运行分析", "ja": "分析を実行",
    },
    "analysis_col_rank": {
        "fr": "Rang", "en": "Rank", "de": "Rang", "zh": "排名", "ja": "順位",
    },
    "analysis_col_molecule": {
        "fr": "Molécule", "en": "Molecule", "de": "Molekül", "zh": "分子", "ja": "分子",
    },
    "analysis_col_group": {
        "fr": "Groupe", "en": "Group", "de": "Gruppe", "zh": "分组", "ja": "グループ",
    },
    "analysis_col_mexb": {
        "fr": "MexB (kcal/mol)", "en": "MexB (kcal/mol)", "de": "MexB (kcal/mol)",
        "zh": "MexB (kcal/mol)", "ja": "MexB (kcal/mol)",
    },
    "analysis_col_mexr": {
        "fr": "MexR (kcal/mol)", "en": "MexR (kcal/mol)", "de": "MexR (kcal/mol)",
        "zh": "MexR (kcal/mol)", "ja": "MexR (kcal/mol)",
    },
    "analysis_col_status": {
        "fr": "Statut", "en": "Status", "de": "Status", "zh": "状态", "ja": "ステータス",
    },
    "analysis_type_section_title": {
        "fr": "Analyse scientifique MexB / MexR", "en": "MexB / MexR scientific analysis",
        "de": "Wissenschaftliche Analyse MexB / MexR", "zh": "MexB / MexR 科学分析",
        "ja": "MexB / MexR 科学分析",
    },
    "analysis_type_section_desc": {
        "fr": "Chargez un fichier CSV scientifique produit par la fusion docking.",
        "en": "Load a scientific CSV file produced by the docking fusion.",
        "de": "Laden Sie eine wissenschaftliche CSV-Datei, die durch die Docking-Fusion erzeugt wurde.",
        "zh": "加载由对接融合生成的科学 CSV 文件。",
        "ja": "ドッキング統合によって生成された科学的CSVファイルを読み込みます。",
    },
    "analysis_internal_csv_label": {
        "fr": "CSV scientifique interne : scores_fusionnes.csv",
        "en": "Internal scientific CSV: scores_fusionnes.csv",
        "de": "Interne wissenschaftliche CSV: scores_fusionnes.csv",
        "zh": "内部科学 CSV：scores_fusionnes.csv",
        "ja": "内部科学CSV：scores_fusionnes.csv",
    },
    "analysis_btn_run_scientific": {
        "fr": "Lancer analyse scientifique", "en": "Run scientific analysis",
        "de": "Wissenschaftliche Analyse starten", "zh": "运行科学分析", "ja": "科学分析を実行",
    },
    "analysis_btn_load_csv": {
        "fr": "Charger un CSV externe", "en": "Load an external CSV",
        "de": "Externe CSV laden", "zh": "加载外部 CSV", "ja": "外部CSVを読み込む",
    },
    "analysis_results_analytics_desc": {
        "fr": "Les résultats sont générés automatiquement par le moteur statistique.",
        "en": "Results are generated automatically by the statistics engine.",
        "de": "Die Ergebnisse werden automatisch von der Statistik-Engine erzeugt.",
        "zh": "结果由统计引擎自动生成。",
        "ja": "結果は統計エンジンによって自動的に生成されます。",
    },
'''


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"
    translations_py = root / "translations.py"

    report = []
    for f in (main_window_py, translations_py):
        bak = f.with_name(f"{f.name}.backup_i18n_analysis_{TS}")
        shutil.copy2(f, bak)
        print(f"Sauvegarde : {bak}")
    print()

    # ------------------------------------------------------------------
    # translations.py
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''    "dock_execution_log_panel_title": {
        "fr": "Journal d'exécution", "en": "Execution log",
        "de": "Ausführungsprotokoll", "zh": "执行日志", "ja": "実行ログ",
    },
}


def tr(key, lang="fr", **kwargs):'''
    anchor_new = '''    "dock_execution_log_panel_title": {
        "fr": "Journal d'exécution", "en": "Execution log",
        "de": "Ausführungsprotokoll", "zh": "执行日志", "ja": "実行ログ",
    },
''' + NEW_TR_KEYS + '''}


def tr(key, lang="fr", **kwargs):'''
    text, _ = apply_one(text, anchor_old, anchor_new, "Ajout des cles page Analyse", report)
    translations_py.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # gui/main_window.py
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")

    # 1) Signature AnalysisPage.__init__ + lang_mgr + helpers
    text, _ = apply_one(
        text,
        '''    def __init__(self):

        super().__init__()

        self.statistics_csv = None
        self.statistics_result = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.secondary = SecondaryNavigation(
            "Analyse",
            [
                "Résultats",
                "Type d'analyse",
                "Résultats analytiques",
            ],
            self.switch_tab,
        )

        root.addWidget(self.secondary)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)''',
        '''    def __init__(self, lang_mgr=None):

        super().__init__()

        self.lang_mgr = lang_mgr
        self._i18n = []

        self.statistics_csv = None
        self.statistics_result = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.secondary = SecondaryNavigation(
            "Analyse",
            [
                "Résultats",
                "Type d'analyse",
                "Résultats analytiques",
            ],
            self.switch_tab,
        )

        root.addWidget(self.secondary)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)''',
        "AnalysisPage : ajout du parametre lang_mgr",
        report,
    )

    text, _ = apply_one(
        text,
        '''    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def run_docking_analysis(self):''',
        '''    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

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

    def _docking_results_headers(self):
        if self.lang_mgr:
            return [
                self.lang_mgr.t("analysis_col_rank"),
                self.lang_mgr.t("analysis_col_molecule"),
                self.lang_mgr.t("analysis_col_group"),
                self.lang_mgr.t("analysis_col_mexb"),
                self.lang_mgr.t("analysis_col_mexr"),
                self.lang_mgr.t("analysis_col_status"),
            ]
        return ["Rang", "Molécule", "Groupe", "MexB (kcal/mol)", "MexR (kcal/mol)", "Statut"]

    def retranslate(self):
        for widget, key, fallback in self._i18n:
            widget.setText(self.lang_mgr.t(key) if self.lang_mgr else fallback)

        if hasattr(self, "docking_results_table"):
            self.docking_results_table.setHorizontalHeaderLabels(
                self._docking_results_headers()
            )

    def run_docking_analysis(self):''',
        "AnalysisPage : ajout des helpers _t_label/_t_button/retranslate",
        report,
    )

    # 2) results_page() : titre, description, label Campagne, bouton, en-tetes
    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label(
                "Résultats du docking",
                "SectionTitle",
            )
        )

        layout.addWidget(
            make_label(
                "Classement des molécules selon leur meilleure "
                "affinité de liaison.",
                "SectionDescription",
            )
        )''',
        '''        layout.addWidget(
            self._t_label(
                "analysis_results_section_title",
                "Résultats du docking",
                "SectionTitle",
            )
        )

        layout.addWidget(
            self._t_label(
                "analysis_results_section_desc",
                "Classement des molécules selon leur meilleure "
                "affinité de liaison.",
                "SectionDescription",
            )
        )''',
        "Onglet Résultats : titre + description traduits",
        report,
    )

    text, _ = apply_one(
        text,
        '''        row.addWidget(
            make_label("Campagne")
        )''',
        '''        row.addWidget(
            self._t_label("analysis_campaign_label", "Campagne")
        )''',
        "Onglet Résultats : label 'Campagne' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        analyze = create_button(
            "Lancer l'analyse",
            primary=True,
        )''',
        '''        analyze = self._t_button(
            "analysis_btn_run",
            "Lancer l'analyse",
            primary=True,
        )''',
        "Onglet Résultats : bouton 'Lancer l'analyse' traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        table.setHorizontalHeaderLabels(
            [
                "Rang",
                "Molécule",
                "Groupe",
                "MexB (kcal/mol)",
                "MexR (kcal/mol)",
                "Statut",
            ]
        )''',
        '''        table.setHorizontalHeaderLabels(
            self._docking_results_headers()
        )''',
        "Onglet Résultats : en-tetes de tableau traduits",
        report,
    )

    # 3) analysis_type_page() : titre, description, label CSV, boutons
    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label(
                "Analyse scientifique MexB / MexR",
                "SectionTitle",
            )
        )

        layout.addWidget(
            make_label(
                "Chargez un fichier CSV scientifique "
                "produit par la fusion docking.",
                "SectionDescription",
            )
        )''',
        '''        layout.addWidget(
            self._t_label(
                "analysis_type_section_title",
                "Analyse scientifique MexB / MexR",
                "SectionTitle",
            )
        )

        layout.addWidget(
            self._t_label(
                "analysis_type_section_desc",
                "Chargez un fichier CSV scientifique "
                "produit par la fusion docking.",
                "SectionDescription",
            )
        )''',
        "Onglet Type d'analyse : titre + description traduits",
        report,
    )

    text, _ = apply_one(
        text,
        '''        grid.addWidget(
            make_label(
                "CSV scientifique interne : "
                "scores_fusionnes.csv"
            ),
            0,
            0,
            1,
            3
        )''',
        '''        grid.addWidget(
            self._t_label(
                "analysis_internal_csv_label",
                "CSV scientifique interne : "
                "scores_fusionnes.csv",
            ),
            0,
            0,
            1,
            3
        )''',
        "Onglet Type d'analyse : label CSV interne traduit",
        report,
    )

    text, _ = apply_one(
        text,
        '''        launch = create_button(
            "Lancer analyse scientifique",
            primary=True,
        )

        load_csv = QPushButton(
            "Charger un CSV externe"
        )''',
        '''        launch = self._t_button(
            "analysis_btn_run_scientific",
            "Lancer analyse scientifique",
            primary=True,
        )

        load_csv = QPushButton(
            self.lang_mgr.t("analysis_btn_load_csv") if self.lang_mgr
            else "Charger un CSV externe"
        )
        self._i18n.append((load_csv, "analysis_btn_load_csv", "Charger un CSV externe"))''',
        "Onglet Type d'analyse : boutons 'Lancer analyse scientifique' / 'Charger un CSV externe' traduits",
        report,
    )

    # 4) analysis_results_page() : titre + description
    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label(
                "Résultats analytiques",
                "SectionTitle",
            )
        )


        layout.addWidget(
            make_label(
                "Les résultats sont générés automatiquement "
                "par le moteur statistique.",
                "SectionDescription",
            )
        )''',
        '''        layout.addWidget(
            self._t_label(
                "analysis_tab_results_analytics",
                "Résultats analytiques",
                "SectionTitle",
            )
        )


        layout.addWidget(
            self._t_label(
                "analysis_results_analytics_desc",
                "Les résultats sont générés automatiquement "
                "par le moteur statistique.",
                "SectionDescription",
            )
        )''',
        "Onglet Résultats analytiques : titre + description traduits",
        report,
    )

    # 5) Instanciation dans MainWindow + appel retranslate()
    text, _ = apply_one(
        text,
        '''        self.analysis_page = AnalysisPage()''',
        '''        self.analysis_page = AnalysisPage(lang_mgr=self.lang_mgr)''',
        "MainWindow : transmission de lang_mgr a AnalysisPage",
        report,
    )

    text, _ = apply_one(
        text,
        '''        if hasattr(self, "analysis_page") and hasattr(self.analysis_page, "secondary"):
            nav = self.analysis_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_analysis").upper())
            analysis_labels = [t("analysis_tab_results"), t("analysis_tab_type"), t("analysis_tab_results_analytics")]
            for btn, lbl in zip(nav.buttons, analysis_labels):
                btn.setText(lbl)''',
        '''        if hasattr(self, "analysis_page") and hasattr(self.analysis_page, "secondary"):
            nav = self.analysis_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_analysis").upper())
            analysis_labels = [t("analysis_tab_results"), t("analysis_tab_type"), t("analysis_tab_results_analytics")]
            for btn, lbl in zip(nav.buttons, analysis_labels):
                btn.setText(lbl)

        if hasattr(self, "analysis_page") and hasattr(self.analysis_page, "retranslate"):
            self.analysis_page.retranslate()''',
        "MainWindow.retranslate_ui() : appel de analysis_page.retranslate()",
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
