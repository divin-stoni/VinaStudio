#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_and_imports.py

Corrige en une seule fois :
  1) Le systeme de langues (i18n) jamais branche dans gui/main_window.py
     -> ajoute LanguageManager, un bouton de langue dans la toolbar,
        une methode retranslate_ui(), et des cles de traduction pour
        tous les textes actuellement codes en dur qu'on a identifies.
  2) La fragilite des imports "from src.xxx" -> rend main.py capable
     de se lancer que le repertoire courant soit le dossier du projet
     OU le dossier src/ lui-meme.

A lancer depuis le dossier "src" du projet :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_and_imports.py
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

TS = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE = Path.cwd()

REQUIRED = ["main.py", "translations.py", "i18n/language_manager.py", "gui/main_window.py"]


def locate_base() -> Path:
    if all((BASE / f).exists() for f in REQUIRED):
        return BASE
    if all((BASE / "src" / f).exists() for f in REQUIRED):
        return BASE / "src"
    print("[ERREUR] Impossible de trouver les fichiers attendus.")
    print("Lance ce script depuis le dossier 'src' du projet (celui qui contient main.py, translations.py, i18n/, gui/).")
    sys.exit(1)


def backup(path: Path) -> Path:
    bak = path.with_name(f"{path.name}.backup_i18n_wiring_{TS}")
    shutil.copy2(path, bak)
    return bak


def apply_one(path: Path, old: str, new: str, label: str, report: list):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        report.append(f"  [ECHEC] {label} (trouve {count} fois au lieu de 1) — fichier NON modifie pour ce bloc")
        return text, False
    text = text.replace(old, new, 1)
    report.append(f"  [OK] {label}")
    return text, True


def main():
    root = locate_base()
    print(f"Projet detecte : {root}\n")

    main_py = root / "main.py"
    translations_py = root / "translations.py"
    main_window_py = root / "gui" / "main_window.py"

    for f in (main_py, translations_py, main_window_py):
        bak = backup(f)
        print(f"Sauvegarde : {bak}")

    report = []

    # ------------------------------------------------------------------
    # 1) main.py : robustesse du sys.path
    # ------------------------------------------------------------------
    text = main_py.read_text(encoding="utf-8")
    old = '''import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow, APP_STYLE'''
    new = '''import sys
from pathlib import Path

# ----------------------------------------------------------------------
# Rend les imports "from src...." robustes, que le script soit lance
# depuis MexAB_MexR_Analyzer_BETA/ ou depuis MexAB_MexR_Analyzer_BETA/src/.
# On s'assure que le dossier PARENT de "src" est sur sys.path.
# ----------------------------------------------------------------------
_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow, APP_STYLE'''
    count = text.count(old)
    if count == 1:
        main_py.write_text(text.replace(old, new, 1), encoding="utf-8")
        report.append("[main.py] [OK] Bootstrap sys.path ajoute")
    else:
        report.append(f"[main.py] [ECHEC] bloc d'imports non trouve tel quel (occurrences={count})")

    # ------------------------------------------------------------------
    # 2) translations.py : nouvelles cles pour les textes VINA Studio
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''        "ja": "グラフ — パーセンタイル / ステータス（予測）",
    },
}


def tr(key, lang="fr", **kwargs):'''
    new_keys = '''        "ja": "グラフ — パーセンタイル / ステータス（予測）",
    },

    "vina_window_title": {
        "fr": "VINA Studio — Docking moléculaire & Analyse",
        "en": "VINA Studio — Molecular Docking & Analysis",
        "de": "VINA Studio — Molekulares Docking & Analyse",
        "zh": "VINA Studio — 分子对接与分析",
        "ja": "VINA Studio — 分子ドッキング＆解析",
    },
    "vina_app_name": {
        "fr": "VINA Studio", "en": "VINA Studio", "de": "VINA Studio",
        "zh": "VINA Studio", "ja": "VINA Studio",
    },
    "vina_app_subtitle": {
        "fr": "Docking moléculaire & analyse des interactions",
        "en": "Molecular Docking & Interaction Analysis",
        "de": "Molekulares Docking & Interaktionsanalyse",
        "zh": "分子对接与相互作用分析",
        "ja": "分子ドッキング＆相互作用解析",
    },
    "nav_prepare_ligands": {
        "fr": "Préparer les ligands", "en": "Prepare ligands",
        "de": "Liganden vorbereiten", "zh": "准备配体", "ja": "リガンド準備",
    },
    "nav_run_docking": {
        "fr": "Lancer le docking", "en": "Run docking",
        "de": "Docking starten", "zh": "开始对接", "ja": "ドッキング実行",
    },
    "nav_analysis": {
        "fr": "Analyse", "en": "Analysis", "de": "Analyse", "zh": "分析", "ja": "解析",
    },
    "nav_visualization": {
        "fr": "Visualisation", "en": "Visualization",
        "de": "Visualisierung", "zh": "可视化", "ja": "可視化",
    },
    "status_ready": {
        "fr": "Prêt — aucun calcul en cours",
        "en": "Ready — no computation running",
        "de": "Bereit — keine Berechnung läuft",
        "zh": "就绪 — 当前无计算任务",
        "ja": "準備完了 — 実行中の計算はありません",
    },
    "status_loading_hits": {
        "fr": "Chargement des hits de docking…",
        "en": "Loading docking hits…",
        "de": "Docking-Treffer werden geladen…",
        "zh": "正在加载对接命中结果…",
        "ja": "ドッキングヒットを読み込み中…",
    },
    "status_no_errors": {
        "fr": "Aucune erreur.", "en": "No errors.",
        "de": "Keine Fehler.", "zh": "无错误。", "ja": "エラーなし。",
    },
}


def tr(key, lang="fr", **kwargs):'''
    count = text.count(anchor_old)
    if count == 1:
        translations_py.write_text(text.replace(anchor_old, new_keys, 1), encoding="utf-8")
        report.append("[translations.py] [OK] Nouvelles cles ajoutees (vina_*, nav_*, status_*)")
    else:
        report.append(f"[translations.py] [ECHEC] point d'ancrage de fin de TR non trouve (occurrences={count})")

    # ------------------------------------------------------------------
    # 3) gui/main_window.py : branchement complet de LanguageManager
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")
    blocks = []

    blocks.append((
        '''from __future__ import annotations
from src.session_runtime import start_new_session, end_session''',
        '''from __future__ import annotations
from src.session_runtime import start_new_session, end_session
from src.i18n.language_manager import LanguageManager''',
        "Import de LanguageManager",
    ))

    blocks.append((
        '''        try:
            start_new_session()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage début de session : {exc}")

        self.setWindowTitle(
            "VINA Studio — Molecular Docking & Analysis"
        )

        self.resize(1500, 900)
        self.setMinimumSize(1100, 700)

        self.create_menu()
        self.create_toolbar()

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.status.showMessage(
            "Prêt — aucun calcul en cours"
        )

        self.build_interface()''',
        '''        try:
            start_new_session()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage début de session : {exc}")

        self.lang_mgr = LanguageManager()
        self.lang_mgr.languageChanged.connect(self.retranslate_ui)

        self.setWindowTitle(
            "VINA Studio — Molecular Docking & Analysis"
        )

        self.resize(1500, 900)
        self.setMinimumSize(1100, 700)

        self.create_menu()
        self.create_toolbar()

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.status.showMessage(
            "Prêt — aucun calcul en cours"
        )

        self.build_interface()

        self.retranslate_ui()''',
        "Instanciation de lang_mgr + appel initial de retranslate_ui()",
    ))

    blocks.append((
        '''    def closeEvent(self, event):

        try:
            viz_bridge.cleanup_visualization_outputs()''',
        '''    def retranslate_ui(self, _code=None):
        """Re-applique les textes de l'interface dans la langue active."""
        t = self.lang_mgr.t

        self.setWindowTitle(t("vina_window_title"))

        if hasattr(self, "app_name_label"):
            self.app_name_label.setText(t("vina_app_name"))
        if hasattr(self, "app_subtitle_label"):
            self.app_subtitle_label.setText(t("vina_app_subtitle"))

        if hasattr(self, "nav_action_prepare"):
            self.nav_action_prepare.setText(t("nav_prepare_ligands"))
        if hasattr(self, "nav_action_docking"):
            self.nav_action_docking.setText(t("nav_run_docking"))
        if hasattr(self, "nav_action_analysis"):
            self.nav_action_analysis.setText(t("nav_analysis"))
        if hasattr(self, "nav_action_visualization"):
            self.nav_action_visualization.setText(t("nav_visualization"))

        if hasattr(self, "lang_action"):
            self.lang_action.setText(self.lang_mgr.native_name())

        if hasattr(self, "status"):
            self.status.showMessage(t("status_ready"))

    def _on_toggle_language(self):
        self.lang_mgr.cycle_language()

    def closeEvent(self, event):

        try:
            viz_bridge.cleanup_visualization_outputs()''',
        "Ajout de retranslate_ui() et _on_toggle_language()",
    ))

    blocks.append((
        '''        add_navigation_action("Préparer les ligands", 0)
        add_navigation_action("Lancer le docking", 0)

        toolbar.addSeparator()

        add_navigation_action("Analyse", 1)
        add_navigation_action("Visualisation", 2)''',
        '''        self.nav_action_prepare = add_navigation_action("Préparer les ligands", 0)
        self.nav_action_docking = add_navigation_action("Lancer le docking", 0)

        toolbar.addSeparator()

        self.nav_action_analysis = add_navigation_action("Analyse", 1)
        self.nav_action_visualization = add_navigation_action("Visualisation", 2)

        toolbar.addSeparator()

        self.lang_action = QAction(self.lang_mgr.native_name(), self)
        self.lang_action.setToolTip("Changer la langue de l'interface")
        self.lang_action.triggered.connect(self._on_toggle_language)
        toolbar.addAction(self.lang_action)''',
        "Bouton de changement de langue dans la toolbar",
    ))

    blocks.append((
        '''        branding.addWidget(
            make_label(
                "VINA Studio",
                "ApplicationName",
            )
        )

        branding.addWidget(
            make_label(
                "Molecular Docking & Interaction Analysis",
                "ApplicationSubtitle",
            )
        )''',
        '''        self.app_name_label = make_label(
            "VINA Studio",
            "ApplicationName",
        )
        branding.addWidget(self.app_name_label)

        self.app_subtitle_label = make_label(
            "Molecular Docking & Interaction Analysis",
            "ApplicationSubtitle",
        )
        branding.addWidget(self.app_subtitle_label)''',
        "Reference conservee sur les labels de branding (nom + sous-titre)",
    ))

    blocks.append((
        '''        self.batch_status.setText("Chargement des hits de docking…")''',
        '''        self.batch_status.setText(self.lang_mgr.t("status_loading_hits"))''',
        "Texte traduit : chargement des hits de docking",
    ))

    blocks.append((
        '''            self.plip_errors_label.setText("Aucune erreur.")''',
        '''            self.plip_errors_label.setText(self.lang_mgr.t("status_no_errors"))''',
        "Texte traduit : aucune erreur",
    ))

    for old, new, label in blocks:
        text, ok = apply_one_str(text, old, new, label, report)

    main_window_py.write_text(text, encoding="utf-8")

    print("\n=== RAPPORT ===")
    for line in report:
        print(line)

    n_fail = sum(1 for l in report if "ECHEC" in l)
    print("\nTermine avec succes." if n_fail == 0 else f"\nTermine avec {n_fail} bloc(s) en echec — voir ci-dessus.")


def apply_one_str(text: str, old: str, new: str, label: str, report: list):
    count = text.count(old)
    if count != 1:
        report.append(f"[main_window.py] [ECHEC] {label} (trouve {count} fois au lieu de 1)")
        return text, False
    report.append(f"[main_window.py] [OK] {label}")
    return text.replace(old, new, 1), True


if __name__ == "__main__":
    main()
