#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_i18n_visualization_subtabs.py

Etend la couverture des langues aux 3 sous-onglets de la page
Visualisation : "Résidus de référence", "Calcul PLIP", "Interaction 2D".

Ajoute a VisualizationPage le meme mecanisme _t_label/_t_button/_i18n
que DockingPage et AnalysisPage, et cascade son retranslate() complet
depuis MainWindow.retranslate_ui().

Ne touche pas (dynamique) : les messages d'erreur ponctuels affiches
pendant le calcul (ex. "Impossible de charger l'image générée.").

A lancer depuis le dossier "src" du projet, APRES patch_i18n_analysis_page.py :
    cd ~/MexAB_MexR_Analyzer_BETA/src
    python3 patch_i18n_visualization_subtabs.py
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


NEW_TR_KEYS = '''    "viz_residues_desc": {
        "fr": "Résidus du récepteur impliqués dans les interactions, calculés automatiquement pour tous les hits.",
        "en": "Receptor residues involved in the interactions, computed automatically for all hits.",
        "de": "Rezeptorreste, die an den Wechselwirkungen beteiligt sind, automatisch für alle Treffer berechnet.",
        "zh": "参与相互作用的受体残基，针对所有命中自动计算。",
        "ja": "相互作用に関与するレセプター残基。すべてのヒットについて自動的に計算されます。",
    },
    "viz_col_residue": {
        "fr": "Résidu", "en": "Residue", "de": "Rest", "zh": "残基", "ja": "残基",
    },
    "viz_col_chain": {
        "fr": "Chaîne", "en": "Chain", "de": "Kette", "zh": "链", "ja": "鎖",
    },
    "viz_col_position": {
        "fr": "Position", "en": "Position", "de": "Position", "zh": "位置", "ja": "位置",
    },
    "viz_col_type": {
        "fr": "Type", "en": "Type", "de": "Typ", "zh": "类型", "ja": "タイプ",
    },
    "viz_col_molecules": {
        "fr": "Molécules", "en": "Molecules", "de": "Moleküle", "zh": "分子", "ja": "分子",
    },
    "viz_plip_desc": {
        "fr": "Le calcul PLIP (extraction de pose, conversion PDB, interactions) est lancé automatiquement pour tous les hits — rien à configurer ici.",
        "en": "The PLIP calculation (pose extraction, PDB conversion, interactions) is run automatically for all hits — nothing to configure here.",
        "de": "Die PLIP-Berechnung (Pose-Extraktion, PDB-Konvertierung, Interaktionen) wird automatisch für alle Treffer ausgeführt — hier ist nichts zu konfigurieren.",
        "zh": "PLIP 计算（姿势提取、PDB 转换、相互作用）会自动针对所有命中运行 — 此处无需配置。",
        "ja": "PLIP計算（ポーズ抽出、PDB変換、相互作用）はすべてのヒットに対して自動的に実行されます。ここで設定する項目はありません。",
    },
    "viz_plip_state_panel_title": {
        "fr": "État du calcul", "en": "Calculation status",
        "de": "Berechnungsstatus", "zh": "计算状态", "ja": "計算状況",
    },
    "viz_plip_no_errors_yet": {
        "fr": "Aucune erreur pour le moment.", "en": "No errors so far.",
        "de": "Bisher keine Fehler.", "zh": "目前没有错误。", "ja": "現時点でエラーはありません。",
    },
    "viz_btn_export_image": {
        "fr": "Exporter l'image", "en": "Export image",
        "de": "Bild exportieren", "zh": "导出图像", "ja": "画像をエクスポート",
    },
    "viz_interaction_placeholder": {
        "fr": "VISUALISATION DES INTERACTIONS\\n\\nLes diagrammes sont générés automatiquement pour toutes les molécules ; choisis-en une ci-dessus pour l'afficher.",
        "en": "INTERACTION VISUALIZATION\\n\\nDiagrams are generated automatically for every molecule; pick one above to display it.",
        "de": "VISUALISIERUNG DER INTERAKTIONEN\\n\\nDiagramme werden automatisch für jedes Molekül erzeugt; wähle oben eines aus, um es anzuzeigen.",
        "zh": "相互作用可视化\\n\\n系统会自动为每个分子生成图表；请在上方选择一个以显示。",
        "ja": "相互作用の可視化\\n\\n各分子の図は自動的に生成されます。上で分子を選択すると表示されます。",
    },
'''


def main():
    root = locate_base()
    main_window_py = root / "gui" / "main_window.py"
    translations_py = root / "translations.py"

    report = []
    for f in (main_window_py, translations_py):
        bak = f.with_name(f"{f.name}.backup_i18n_viz_subtabs_{TS}")
        shutil.copy2(f, bak)
        print(f"Sauvegarde : {bak}")
    print()

    # ------------------------------------------------------------------
    # translations.py
    # ------------------------------------------------------------------
    text = translations_py.read_text(encoding="utf-8")
    anchor_old = '''    "analysis_results_analytics_desc": {
        "fr": "Les résultats sont générés automatiquement par le moteur statistique.",
        "en": "Results are generated automatically by the statistics engine.",
        "de": "Die Ergebnisse werden automatisch von der Statistik-Engine erzeugt.",
        "zh": "结果由统计引擎自动生成。",
        "ja": "結果は統計エンジンによって自動的に生成されます。",
    },
}


def tr(key, lang="fr", **kwargs):'''
    anchor_new = '''    "analysis_results_analytics_desc": {
        "fr": "Les résultats sont générés automatiquement par le moteur statistique.",
        "en": "Results are generated automatically by the statistics engine.",
        "de": "Die Ergebnisse werden automatisch von der Statistik-Engine erzeugt.",
        "zh": "结果由统计引擎自动生成。",
        "ja": "結果は統計エンジンによって自動的に生成されます。",
    },
''' + NEW_TR_KEYS + '''}


def tr(key, lang="fr", **kwargs):'''
    text, _ = apply_one(text, anchor_old, anchor_new, "Ajout des cles sous-onglets Visualisation", report)
    translations_py.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # gui/main_window.py
    # ------------------------------------------------------------------
    text = main_window_py.read_text(encoding="utf-8")

    # 1) Ajout de self._i18n = [] dans VisualizationPage.__init__
    text, _ = apply_one(
        text,
        '''        self.docking_page = docking_page
        self.analysis_page = analysis_page
        self.lang_mgr = lang_mgr

        self.current_hits = []''',
        '''        self.docking_page = docking_page
        self.analysis_page = analysis_page
        self.lang_mgr = lang_mgr
        self._i18n = []

        self.current_hits = []''',
        "VisualizationPage : ajout de self._i18n",
        report,
    )

    # 2) Helpers _t_label / _t_button, inseres avant residues_page()
    text, _ = apply_one(
        text,
        '''    def residues_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        layout.addWidget(
            make_label("Résidus de référence", "SectionTitle")
        )

        layout.addWidget(
            make_label(
                "Résidus du récepteur impliqués dans les interactions, "
                "calculés automatiquement pour tous les hits.",
                "SectionDescription",
            )
        )

        table = QTableWidget(0, 5)

        table.setHorizontalHeaderLabels(
            ["Résidu", "Chaîne", "Position", "Type", "Molécules"]
        )''',
        '''    def _t_label(self, key, fallback, object_name=None):
        text = self.lang_mgr.t(key) if self.lang_mgr else fallback
        label = make_label(text, object_name)
        self._i18n.append((label, key, fallback))
        return label

    def _t_button(self, key, fallback, primary=False):
        text = self.lang_mgr.t(key) if self.lang_mgr else fallback
        button = create_button(text, primary=primary)
        self._i18n.append((button, key, fallback))
        return button

    def _residues_table_headers(self):
        if self.lang_mgr:
            return [
                self.lang_mgr.t("viz_col_residue"),
                self.lang_mgr.t("viz_col_chain"),
                self.lang_mgr.t("viz_col_position"),
                self.lang_mgr.t("viz_col_type"),
                self.lang_mgr.t("viz_col_molecules"),
            ]
        return ["Résidu", "Chaîne", "Position", "Type", "Molécules"]

    def retranslate_subtabs(self):
        for widget, key, fallback in self._i18n:
            widget.setText(self.lang_mgr.t(key) if self.lang_mgr else fallback)

        if hasattr(self, "residues_table"):
            self.residues_table.setHorizontalHeaderLabels(self._residues_table_headers())

    def residues_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        layout.addWidget(
            self._t_label("viz_tab_residues", "Résidus de référence", "SectionTitle")
        )

        layout.addWidget(
            self._t_label(
                "viz_residues_desc",
                "Résidus du récepteur impliqués dans les interactions, "
                "calculés automatiquement pour tous les hits.",
                "SectionDescription",
            )
        )

        table = QTableWidget(0, 5)

        table.setHorizontalHeaderLabels(
            self._residues_table_headers()
        )''',
        "VisualizationPage : helpers + onglet 'Résidus de référence' traduits",
        report,
    )

    # 3) Onglet "Calcul PLIP"
    text, _ = apply_one(
        text,
        '''        layout.addWidget(
            make_label("Calcul PLIP", "SectionTitle")
        )

        layout.addWidget(
            make_label(
                "Le calcul PLIP (extraction de pose, conversion PDB, interactions) "
                "est lancé automatiquement pour tous les hits — rien à configurer ici.",
                "SectionDescription",
            )
        )

        panel = QFrame()
        panel.setObjectName("ContentPanel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)
        panel_layout.setSpacing(10)

        panel_layout.addWidget(make_panel_title("État du calcul"))

        self.plip_errors_label = make_label(
            "Aucune erreur pour le moment.",
            "SectionDescription",
        )''',
        '''        layout.addWidget(
            self._t_label("viz_tab_plip", "Calcul PLIP", "SectionTitle")
        )

        layout.addWidget(
            self._t_label(
                "viz_plip_desc",
                "Le calcul PLIP (extraction de pose, conversion PDB, interactions) "
                "est lancé automatiquement pour tous les hits — rien à configurer ici.",
                "SectionDescription",
            )
        )

        panel = QFrame()
        panel.setObjectName("ContentPanel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)
        panel_layout.setSpacing(10)

        panel_layout.addWidget(
            self._t_label("viz_plip_state_panel_title", "État du calcul", "PanelTitle")
        )

        self.plip_errors_label = self._t_label(
            "viz_plip_no_errors_yet",
            "Aucune erreur pour le moment.",
            "SectionDescription",
        )''',
        "VisualizationPage : onglet 'Calcul PLIP' traduit",
        report,
    )

    # 4) Onglet "Interaction 2D"
    text, _ = apply_one(
        text,
        '''        header.addWidget(
            make_label("Interaction 2D", "SectionTitle")
        )

        header.addStretch()

        self.diagram_molecule_combo = QComboBox()
        self.diagram_molecule_combo.currentTextChanged.connect(
            self._on_diagram_molecule_changed
        )
        header.addWidget(self.diagram_molecule_combo)

        export = create_button("Exporter l'image")
        export.clicked.connect(self._on_export_2d_clicked)

        header.addWidget(export)

        layout.addLayout(header)

        viewer = QFrame()
        viewer.setObjectName("Viewer")

        viewer_layout = QVBoxLayout(viewer)

        message = make_label(
            "VISUALISATION DES INTERACTIONS\\n\\n"
            "Les diagrammes sont générés automatiquement pour toutes les "
            "molécules ; choisis-en une ci-dessus pour l'afficher.",
        )''',
        '''        header.addWidget(
            self._t_label("viz_tab_interaction2d", "Interaction 2D", "SectionTitle")
        )

        header.addStretch()

        self.diagram_molecule_combo = QComboBox()
        self.diagram_molecule_combo.currentTextChanged.connect(
            self._on_diagram_molecule_changed
        )
        header.addWidget(self.diagram_molecule_combo)

        export = self._t_button("viz_btn_export_image", "Exporter l'image")
        export.clicked.connect(self._on_export_2d_clicked)

        header.addWidget(export)

        layout.addLayout(header)

        viewer = QFrame()
        viewer.setObjectName("Viewer")

        viewer_layout = QVBoxLayout(viewer)

        message = self._t_label(
            "viz_interaction_placeholder",
            "VISUALISATION DES INTERACTIONS\\n\\n"
            "Les diagrammes sont générés automatiquement pour toutes les "
            "molécules ; choisis-en une ci-dessus pour l'afficher.",
        )''',
        "VisualizationPage : onglet 'Interaction 2D' traduit",
        report,
    )

    # 5) Cascade depuis MainWindow.retranslate_ui()
    text, _ = apply_one(
        text,
        '''            if hasattr(self.visualization_page, "recompute_button"):
                self.visualization_page.recompute_button.setText(t("viz_btn_recompute"))
            if hasattr(self.visualization_page, "export_all_button"):
                self.visualization_page.export_all_button.setText(t("viz_btn_export_all"))''',
        '''            if hasattr(self.visualization_page, "recompute_button"):
                self.visualization_page.recompute_button.setText(t("viz_btn_recompute"))
            if hasattr(self.visualization_page, "export_all_button"):
                self.visualization_page.export_all_button.setText(t("viz_btn_export_all"))
            if hasattr(self.visualization_page, "retranslate_subtabs"):
                self.visualization_page.retranslate_subtabs()''',
        "MainWindow.retranslate_ui() : appel de visualization_page.retranslate_subtabs()",
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
