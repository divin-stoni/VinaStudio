# -*- coding: utf-8 -*-

from __future__ import annotations
from src.session_runtime import start_new_session, end_session
from src.i18n.language_manager import LanguageManager

import sys
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QThread, QObject, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QPixmap
# ============================================================================
# BACKEND SCIENTIFIQUE
# ============================================================================

from src.docking.sdf_preparer import prepare_sdf
from src.docking.vina_engine import VinaEngine, create_target_config
from src.docking.vina_worker import DockingWorker
from src.analysis.statistics_pipeline import run_statistics_pipeline
from src.analysis.analysis_controller import analyze_docking_csv
from src.gui import visualization_bridge as viz_bridge

from src.plotting import (
    fig_scatter_corr,
    fig_histogram_si,
    fig_histogram_si_by_group,
    fig_forest_correlations,
    fig_percentile_scatter,
    fig_loo_influence,
)

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas
)



from PySide6.QtWidgets import (
    QTabWidget,
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QComboBox,
    QLineEdit,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QAbstractItemView,
    QScrollArea,
)


# ============================================================================
# PALETTE
# ============================================================================

COLORS = {
    "window": "#eef1f4",
    "surface": "#f7f8fa",
    "surface_alt": "#e7ebef",
    "panel": "#ffffff",
    "border": "#cfd5dc",
    "border_dark": "#b9c1ca",

    "text": "#26323d",
    "text_secondary": "#65717d",
    "text_muted": "#89939d",

    "accent": "#246b8f",
    "accent_dark": "#1d5875",
    "accent_light": "#dcecf4",

    "success": "#3d7b61",
    "success_light": "#e1efe8",

    "warning": "#a97932",
    "warning_light": "#f4ead9",

    "danger": "#a94b4b",
    "danger_light": "#f4dfdf",

    "viewer": "#202830",
}


# ============================================================================
# STYLE
# ============================================================================

APP_STYLE = f"""
QMainWindow {{
    background: {COLORS["window"]};
}}

QWidget {{
    font-family: "Noto Sans", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {COLORS["text"]};
}}

QMenuBar {{
    background: {COLORS["panel"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px 8px;
}}

QMenuBar::item {{
    padding: 7px 11px;
    background: transparent;
}}

QMenuBar::item:selected {{
    background: {COLORS["accent_light"]};
    color: {COLORS["accent_dark"]};
}}

QMenu {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    padding: 5px;
}}

QMenu::item {{
    padding: 7px 28px 7px 12px;
}}

QMenu::item:selected {{
    background: {COLORS["accent_light"]};
    color: {COLORS["accent_dark"]};
}}

QToolBar {{
    background: {COLORS["surface"]};
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    spacing: 4px;
    padding: 5px 8px;
}}

QToolButton {{
    border: 1px solid transparent;
    padding: 6px 10px;
    border-radius: 3px;
}}

QToolButton:hover {{
    background: {COLORS["surface_alt"]};
    border-color: {COLORS["border"]};
}}

QToolButton:pressed {{
    background: {COLORS["accent_light"]};
}}

QFrame#TopHeader {{
    background: {COLORS["panel"]};
    border-bottom: 1px solid {COLORS["border"]};
}}

QLabel#ApplicationName {{
    font-size: 19px;
    font-weight: 650;
    color: {COLORS["text"]};
}}

QLabel#ApplicationSubtitle {{
    font-size: 11px;
    color: {COLORS["text_secondary"]};
}}

QLabel#SectionTitle {{
    font-size: 17px;
    font-weight: 620;
    color: {COLORS["text"]};
}}

QLabel#SectionDescription {{
    font-size: 12px;
    color: {COLORS["text_secondary"]};
}}

QLabel#PanelTitle {{
    font-size: 13px;
    font-weight: 650;
    color: {COLORS["text"]};
}}

QFrame#Navigation {{
    background: {COLORS["surface"]};
    border-right: 1px solid {COLORS["border"]};
}}

QFrame#NavigationHeader {{
    background: {COLORS["surface"]};
    border-bottom: 1px solid {COLORS["border"]};
}}

QToolButton#PrimaryNavigation {{
    text-align: left;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 12px 14px;
    color: {COLORS["text_secondary"]};
    background: transparent;
}}

QToolButton#PrimaryNavigation:hover {{
    background: {COLORS["surface_alt"]};
    color: {COLORS["text"]};
}}

QToolButton#PrimaryNavigation:checked {{
    background: {COLORS["accent_light"]};
    color: {COLORS["accent_dark"]};
    border-left: 3px solid {COLORS["accent"]};
    font-weight: 650;
}}

QFrame#SecondaryNavigation {{
    background: {COLORS["panel"]};
    border-right: 1px solid {COLORS["border"]};
}}

QToolButton#SecondaryTab {{
    text-align: left;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    padding: 11px 13px;
    color: {COLORS["text_secondary"]};
    background: transparent;
}}

QToolButton#SecondaryTab:hover {{
    background: {COLORS["surface"]};
    color: {COLORS["text"]};
}}

QToolButton#SecondaryTab:checked {{
    color: {COLORS["accent_dark"]};
    background: {COLORS["accent_light"]};
    border-left: 2px solid {COLORS["accent"]};
    font-weight: 620;
}}

QFrame#Workspace {{
    background: {COLORS["window"]};
}}

QFrame#ContentPanel {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
}}

QFrame#ToolbarPanel {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
}}

QPushButton {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border_dark"]};
    border-radius: 3px;
    padding: 7px 14px;
    min-height: 18px;
}}

QPushButton:hover {{
    background: {COLORS["surface"]};
    border-color: {COLORS["accent"]};
}}

QPushButton:pressed {{
    background: {COLORS["accent_light"]};
}}

QPushButton#PrimaryButton {{
    background: {COLORS["accent"]};
    color: white;
    border: 1px solid {COLORS["accent_dark"]};
    font-weight: 620;
}}

QPushButton#PrimaryButton:hover {{
    background: {COLORS["accent_dark"]};
}}

QPushButton#DangerButton {{
    color: {COLORS["danger"]};
}}

QLineEdit,
QComboBox {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border_dark"]};
    border-radius: 3px;
    padding: 7px 8px;
    min-height: 18px;
}}

QLineEdit:focus,
QComboBox:focus {{
    border: 1px solid {COLORS["accent"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QComboBox QAbstractItemView {{
    background: {COLORS["panel"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_dark"]};
    outline: none;
    padding: 2px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 8px;
    color: {COLORS["text"]};
    background: {COLORS["panel"]};
}}

QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:hover {{
    background: {COLORS["accent_light"]};
    color: {COLORS["accent_dark"]};
}}

QTableWidget {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    gridline-color: {COLORS["border"]};
    selection-background-color: {COLORS["accent_light"]};
    selection-color: {COLORS["text"]};
    alternate-background-color: #f8fafb;
}}

QTableWidget::item {{
    padding: 6px;
}}

QHeaderView::section {{
    background: {COLORS["surface_alt"]};
    color: {COLORS["text"]};
    border: none;
    border-right: 1px solid {COLORS["border"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 7px;
    font-weight: 620;
}}

QProgressBar {{
    background: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 3px;
    height: 9px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {COLORS["accent"]};
    border-radius: 2px;
}}

QStatusBar {{
    background: {COLORS["surface"]};
    border-top: 1px solid {COLORS["border"]};
    color: {COLORS["text_secondary"]};
}}

QSplitter::handle {{
    background: {COLORS["border"]};
}}

QSplitter::handle:hover {{
    background: {COLORS["accent"]};
}}

QFrame#Viewer {{
    background: {COLORS["viewer"]};
    border: 1px solid #151b20;
}}

QScrollArea {{
    background: {COLORS["window"]};
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: {COLORS["window"]};
}}

QScrollArea#DockingScrollArea,
QScrollArea#DockingScrollArea > QWidget {{
    background: {COLORS["window"]};
}}

QScrollBar:vertical {{
    background: {COLORS["surface"]};
    width: 13px;
    margin: 0px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["border_dark"]};
    min-height: 24px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS["accent"]};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
    border: none;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: {COLORS["surface"]};
    height: 13px;
    margin: 0px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS["border_dark"]};
    min-width: 24px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS["accent"]};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
    border: none;
}}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

QDialog {{
    background: {COLORS["panel"]};
}}

QMessageBox {{
    background: {COLORS["panel"]};
}}

QMessageBox QLabel {{
    color: {COLORS["text"]};
    background: transparent;
}}

QDialog QLabel {{
    color: {COLORS["text"]};
    background: transparent;
}}

QMessageBox QPushButton {{
    min-width: 72px;
}}
"""


# ============================================================================
# HELPERS
# ============================================================================

def make_label(text="", object_name=None):
    label = QLabel(text)

    if object_name:
        label.setObjectName(object_name)

    return label


def make_panel_title(text):
    return make_label(text, "PanelTitle")


def create_button(text, primary=False):
    button = QPushButton(text)

    if primary:
        button.setObjectName("PrimaryButton")

    return button


# ============================================================================
# NAVIGATION PRINCIPALE
# ============================================================================

from src.visualization.visualization_manager import VisualizationManager
class PrimaryNavigation(QFrame):

    def __init__(self, callback):
        super().__init__()

        self.setObjectName("Navigation")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("NavigationHeader")

        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(15, 18, 15, 16)

        self.title_label = make_label("ESPACE DE TRAVAIL")
        self.title_label.setStyleSheet(
            f"font-size: 10px; "
            f"font-weight: 700; "
            f"color: {COLORS['text_muted']};"
        )

        header_layout.addWidget(self.title_label)

        layout.addWidget(header)

        self.buttons = []

        for index, text in enumerate(
            [
                "Docking",
                "Analyse",
                "Visualisation",
            ]
        ):
            button = QToolButton()
            button.setObjectName("PrimaryNavigation")
            button.setText(text)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setMinimumHeight(46)

            button.clicked.connect(
                lambda checked, i=index: callback(i)
            )

            self.buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        info = QFrame()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(15, 15, 15, 15)

        version = make_label(
            "VINA Studio\nMolecular Docking & Analysis"
        )

        version.setStyleSheet(
            f"font-size: 10px; "
            f"color: {COLORS['text_muted']};"
        )

        info_layout.addWidget(version)
        layout.addWidget(info)

        self.buttons[0].setChecked(True)


# ============================================================================
# NAVIGATION SECONDAIRE
# ============================================================================

class SecondaryNavigation(QFrame):

    def __init__(self, title, tabs, callback):
        super().__init__()

        self.setObjectName("SecondaryNavigation")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(15, 18, 15, 14)

        self.title_label = make_label(
            title.upper()
        )

        self.title_label.setStyleSheet(
            f"font-size: 11px; "
            f"font-weight: 700; "
            f"color: {COLORS['text_muted']};"
        )

        header_layout.addWidget(self.title_label)
        layout.addWidget(header)

        self.buttons = []

        for index, text in enumerate(tabs):

            button = QToolButton()
            button.setObjectName("SecondaryTab")
            button.setText(text)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setMinimumHeight(42)

            button.clicked.connect(
                lambda checked, i=index: callback(i)
            )

            self.buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        if self.buttons:
            self.buttons[0].setChecked(True)


# ============================================================================
# PAGE DOCKING
# ============================================================================

class DockingPage(QWidget):

    def __init__(self, lang_mgr=None):

        super().__init__()

        self.lang_mgr = lang_mgr
        self._i18n = []

        self.visualization_manager = VisualizationManager()

        self.visualization_data = self.visualization_manager.scan()

        print(
            "VISUALISATION CONNECTEE:",
            self.visualization_data
        )

        self.project_root = Path(__file__).resolve().parents[2]

        self.sdf_files = []
        self.prepared_ligands = []

        # Ligands PDBQT explicitement sélectionnés
        # par l'utilisateur pour la campagne de docking.
        self.selected_ligands = []

        self.thread = None
        self.worker = None
        self.engine = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.secondary = SecondaryNavigation(
            "Docking",
            [
                "Préparer les SDF",
                "Charger les PDBQT",
                "Lancer le docking",
            ],
            self.switch_tab,
        )

        root.addWidget(self.secondary)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.sdf_page = self.create_sdf_page()
        self.pdbqt_page = self.create_pdbqt_page()
        self.docking_page = self.create_docking_page()

        self.stack.addWidget(self.sdf_page)
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

    def _pdbqt_table_headers(self):
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
            self.pdbqt_table.setHorizontalHeaderLabels(self._pdbqt_table_headers())

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------

    def switch_tab(self, index):

        self.stack.setCurrentIndex(index)

        if index == 1:
            self.refresh_pdbqt_table()

    # ------------------------------------------------------------------
    # SDF
    # ------------------------------------------------------------------

    def create_sdf_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)

        layout.addWidget(
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
        )

        panel = QFrame()
        panel.setObjectName("ContentPanel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 24, 24, 24)
        panel_layout.setSpacing(14)

        panel_layout.addWidget(
            self._t_label("sdf_panel_title", "Bibliothèque SDF", "PanelTitle")
        )

        # --------------------------------------------------------------
        # BOUTONS DE SELECTION
        # --------------------------------------------------------------

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        add_files = self._t_button(
            "sdf_btn_add_files",
            "Ajouter des fichiers SDF",
        )

        add_files.clicked.connect(
            self.select_sdf_files
        )

        add_folder = self._t_button(
            "sdf_btn_add_folder",
            "Ajouter un dossier",
        )

        add_folder.clicked.connect(
            self.select_sdf_folder
        )

        clear = self._t_button(
            "sdf_btn_clear_selection",
            "Vider la sélection",
        )

        clear.clicked.connect(
            self.clear_sdf_selection
        )

        buttons.addWidget(add_files)
        buttons.addWidget(add_folder)
        buttons.addWidget(clear)
        buttons.addStretch()

        panel_layout.addLayout(buttons)

        # --------------------------------------------------------------
        # LISTE DES ELEMENTS SELECTIONNES
        # --------------------------------------------------------------

        self.sdf_path = QLineEdit()
        self.sdf_path.setReadOnly(True)
        self.sdf_path.setPlaceholderText(
            "Aucun fichier ou dossier SDF sélectionné."
        )

        panel_layout.addWidget(
            self.sdf_path
        )

        self.sdf_list = QTableWidget(
            0,
            2,
        )

        self.sdf_list.setHorizontalHeaderLabels(
            [
                "Type",
                "Chemin",
            ]
        )

        self.sdf_list.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
        )

        self.sdf_list.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.Stretch,
        )

        self.sdf_list.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.sdf_list.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.sdf_list.setAlternatingRowColors(
            True
        )

        self.sdf_list.setMinimumHeight(
            150
        )

        panel_layout.addWidget(
            self.sdf_list
        )

        # --------------------------------------------------------------
        # ETAT
        # --------------------------------------------------------------

        info = QFrame()
        info.setObjectName("ToolbarPanel")

        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )

        self.sdf_status = make_label(
            "Aucun fichier SDF sélectionné"
        )

        info_layout.addWidget(
            self.sdf_status
        )

        info_layout.addStretch()

        panel_layout.addWidget(
            info
        )

        # --------------------------------------------------------------
        # DOSSIER DE SORTIE
        # --------------------------------------------------------------

        panel_layout.addWidget(
            self._t_label("sdf_output_folder_label", "Dossier de sortie")
        )

        self.sdf_output = QLineEdit(
            str(
                self.project_root
                / "docking"
                / "ligands"
                / "prepared"
            )
        )

        panel_layout.addWidget(
            self.sdf_output
        )

        # --------------------------------------------------------------
        # PREPARATION
        # --------------------------------------------------------------

        prepare_buttons = QHBoxLayout()
        prepare_buttons.addStretch()

        self.prepare_button = self._t_button(
            "sdf_btn_prepare_molecules",
            "Préparer les molécules",
            primary=True,
        )

        self.prepare_button.clicked.connect(
            self.prepare_ligands
        )

        prepare_buttons.addWidget(
            self.prepare_button
        )

        panel_layout.addLayout(
            prepare_buttons
        )

        layout.addWidget(
            panel
        )

        # --------------------------------------------------------------
        # JOURNAL
        # --------------------------------------------------------------

        log_panel = QFrame()
        log_panel.setObjectName(
            "ContentPanel"
        )

        log_layout = QVBoxLayout(
            log_panel
        )

        log_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        log_layout.addWidget(
            self._t_label(
                "sdf_state_panel_title",
                "État de préparation",
                "PanelTitle",
            )
        )

        self.sdf_log = QLineEdit()
        self.sdf_log.setReadOnly(
            True
        )

        self.sdf_log.setText(
            "En attente de fichiers SDF."
        )

        log_layout.addWidget(
            self.sdf_log
        )

        layout.addWidget(
            log_panel
        )

        layout.addStretch()

        return page

    # ------------------------------------------------------------------
    # SELECTION SDF
    # ------------------------------------------------------------------

    def select_sdf_files(self):

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers SDF",
            "",
            "Structure Data File (*.sdf)",
        )

        if not files:
            return

        added = 0

        for file_path in files:

            path = Path(
                file_path
            ).resolve()

            if path not in self.sdf_files:

                self.sdf_files.append(
                    path
                )

                added += 1

        self.refresh_sdf_selection()

        self.sdf_log.setText(
            f"{added} fichier(s) SDF ajouté(s)."
        )

    def select_sdf_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier contenant les SDF",
            "",
        )

        if not folder:
            return

        path = Path(
            folder
        ).resolve()

        sdf_files = sorted(
            p.resolve()
            for p in path.iterdir()
            if p.is_file()
            and p.suffix.lower() == ".sdf"
        )

        if not sdf_files:

            QMessageBox.warning(
                self,
                "Aucun SDF",
                "Le dossier sélectionné ne contient "
                "aucun fichier .sdf.",
            )

            return

        added = 0

        for sdf_file in sdf_files:

            if sdf_file not in self.sdf_files:

                self.sdf_files.append(
                    sdf_file
                )

                added += 1

        self.refresh_sdf_selection()

        self.sdf_log.setText(
            f"Dossier ajouté : {added} fichier(s) SDF trouvé(s)."
        )

    def clear_sdf_selection(self):

        self.sdf_files.clear()

        self.refresh_sdf_selection()

        self.sdf_log.setText(
            "Sélection SDF vidée."
        )

    def refresh_sdf_selection(self):

        self.sdf_list.setRowCount(0)

        for path in self.sdf_files:

            row = self.sdf_list.rowCount()

            self.sdf_list.insertRow(
                row
            )

            type_item = QTableWidgetItem(
                "Fichier SDF"
            )

            path_item = QTableWidgetItem(
                str(path)
            )

            self.sdf_list.setItem(
                row,
                0,
                type_item,
            )

            self.sdf_list.setItem(
                row,
                1,
                path_item,
            )

        count = len(
            self.sdf_files
        )

        if count == 0:

            self.sdf_path.clear()

            self.sdf_status.setText(
                "Aucun fichier SDF sélectionné"
            )

            return

        self.sdf_path.setText(
            f"{count} fichier(s) SDF sélectionné(s)"
        )

        self.sdf_status.setText(
            f"{count} fichier(s) SDF prêt(s) pour la préparation."
        )

    def prepare_ligands(self):

        if not self.sdf_files:

            QMessageBox.warning(
                self,
                "Bibliothèque absente",
                "Sélectionnez au moins un fichier SDF "
                "ou un dossier contenant des fichiers SDF.",
            )

            return

        output_dir = Path(
            self.sdf_output.text().strip()
        )

        if not output_dir:
            QMessageBox.warning(
                self,
                "Dossier invalide",
                "Le dossier de sortie est vide.",
            )
            return

        self.prepare_button.setEnabled(False)

        self.sdf_status.setText(
            "Préparation en cours…"
        )

        self.sdf_log.setText(
            f"Préparation de {len(self.sdf_files)} "
            f"source(s) SDF avec Open Babel…"
        )

        QApplication.processEvents()

        try:

            from src.docking.sdf_preparer import (
                prepare_sdf_files,
            )

            generated = prepare_sdf_files(
                self.sdf_files,
                output_dir,
            )

            self.prepared_ligands = [
                Path(p)
                for p in generated
            ]

            self.sdf_status.setText(
                f"{len(generated)} molécule(s) préparée(s)"
            )

            self.sdf_log.setText(
                "Préparation terminée avec succès."
            )

            self.refresh_pdbqt_table()

            self.stack.setCurrentIndex(1)

            self.secondary.buttons[1].setChecked(
                True
            )

            self.status_message(
                f"{len(generated)} ligand(s) PDBQT préparé(s)."
            )

        except Exception as exc:

            self.sdf_status.setText(
                "Échec de la préparation"
            )

            self.sdf_log.setText(
                str(exc)
            )

            QMessageBox.critical(
                self,
                "Erreur de préparation",
                str(exc),
            )

        finally:

            self.prepare_button.setEnabled(
                True
            )

    # ------------------------------------------------------------------
    # PDBQT
    # ------------------------------------------------------------------

    def create_pdbqt_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(16)

        layout.addWidget(
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
        )

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarPanel")

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)

        add = self._t_button("pdbqt_btn_add_files", "Ajouter des fichiers")
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
        )

        toolbar_layout.addWidget(add)
        toolbar_layout.addWidget(refresh)
        toolbar_layout.addWidget(select_all)
        toolbar_layout.addWidget(clear_selection)
        toolbar_layout.addWidget(use_selection)
        toolbar_layout.addStretch()

        self.pdbqt_count = make_label(
            "0 ligand"
        )

        toolbar_layout.addWidget(
            self.pdbqt_count
        )

        layout.addWidget(toolbar)

        self.pdbqt_selection_status = make_label(
            "Aucun ligand sélectionné pour le docking."
        )

        self.pdbqt_selection_status.setStyleSheet(
            f"color: {COLORS['text_secondary']};"
        )

        layout.addWidget(
            self.pdbqt_selection_status
        )

        self.pdbqt_table = QTableWidget(0, 4)

        self.pdbqt_table.setHorizontalHeaderLabels(
            self._pdbqt_table_headers()
        )

        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
        )

        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.Stretch,
        )

        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.Stretch,
        )

        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeToContents,
        )

        self.pdbqt_table.setAlternatingRowColors(True)

        self.pdbqt_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.pdbqt_table.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )

        self.pdbqt_table.itemSelectionChanged.connect(
            self.update_pdbqt_selection_status
        )

        layout.addWidget(
            self.pdbqt_table,
            1,
        )

        return page

    def refresh_pdbqt_table(self):

        prepared_dir = (
            self.project_root
            / "docking"
            / "ligands"
            / "prepared"
        )

        if not prepared_dir.exists():
            prepared_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

        files = sorted(
            prepared_dir.glob("*.pdbqt"),
            key=lambda p: p.name.lower(),
        )

        self.prepared_ligands = files

        # Nettoyage des sélections qui ne correspondent
        # plus à des fichiers disponibles.
        available = {
            path.resolve()
            for path in files
        }

        self.selected_ligands = [
            path
            for path in self.selected_ligands
            if path.resolve() in available
        ]

        self.pdbqt_table.setRowCount(0)

        for index, ligand in enumerate(files, 1):

            row = self.pdbqt_table.rowCount()

            self.pdbqt_table.insertRow(row)

            values = [
                str(index),
                ligand.stem,
                str(ligand),
                "Prêt",
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(value)

                if column == 3:
                    item.setTextAlignment(
                        Qt.AlignCenter
                    )

                self.pdbqt_table.setItem(
                    row,
                    column,
                    item,
                )

        self.pdbqt_count.setText(
            f"{len(files)} ligand(s)"
        )

        self.update_pdbqt_selection_status()

    def select_all_pdbqt(self):
        """Sélectionne tous les ligands affichés."""

        if self.pdbqt_table.rowCount() == 0:
            self.pdbqt_selection_status.setText(
                "Aucun ligand PDBQT disponible."
            )
            return

        self.pdbqt_table.selectAll()

        self.update_pdbqt_selection_status()

    def clear_pdbqt_selection(self):
        """Efface la sélection actuelle."""

        self.pdbqt_table.clearSelection()

        self.selected_ligands = []

        self.pdbqt_selection_status.setText(
            "Aucun ligand sélectionné pour le docking."
        )

    def update_pdbqt_selection_status(self):
        """Met à jour le nombre de ligands sélectionnés."""

        rows = self.pdbqt_table.selectionModel().selectedRows()

        count = len(rows)

        if count == 0:
            self.pdbqt_selection_status.setText(
                "Aucun ligand sélectionné pour le docking."
            )
        else:
            self.pdbqt_selection_status.setText(
                f"{count} ligand(s) sélectionné(s) pour le docking."
            )

    def use_selected_pdbqt(self):
        """Valide la sélection PDBQT et passe à l'étape Docking."""

        rows = self.pdbqt_table.selectionModel().selectedRows()

        if not rows:
            QMessageBox.warning(
                self,
                "Aucun ligand sélectionné",
                "Sélectionnez au moins un ligand PDBQT "
                "avant de passer au docking.",
            )
            return

        selected = []

        for row_index in rows:

            row = row_index.row()

            item = self.pdbqt_table.item(row, 2)

            if item is None:
                continue

            path = Path(
                item.text().strip()
            ).resolve()

            if path.exists() and path.is_file():
                selected.append(path)

        if not selected:
            QMessageBox.warning(
                self,
                "Sélection invalide",
                "Les fichiers PDBQT sélectionnés "
                "sont introuvables.",
            )
            return

        self.selected_ligands = selected

        self.pdbqt_selection_status.setText(
            f"{len(selected)} ligand(s) sélectionné(s) "
            f"pour le docking."
        )

        self.current_ligand.setText(
            f"{len(selected)} ligand(s) prêt(s) pour le docking."
        )

        self.execution_status.setText(
            "Configuration prête"
        )

        self.docking_log.setRowCount(0)

        self.add_docking_log(
            "SÉLECTION",
            f"{len(selected)} ligand(s) sélectionné(s) "
            "pour la campagne.",
        )

        self.stack.setCurrentIndex(2)

        self.secondary.buttons[2].setChecked(
            True
        )

        self.status_message(
            f"{len(selected)} ligand(s) sélectionné(s) "
            "pour le docking."
        )

    def on_pdbqt_selection_changed(self, selected, deselected):
        """Actualise l'indicateur lorsque la sélection change."""

        self.update_pdbqt_selection_status()

    # ------------------------------------------------------------------
    # AJOUT DE FICHIERS PDBQT
    # ------------------------------------------------------------------

    def add_pdbqt_files(self):

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Ajouter des ligands PDBQT",
            "",
            "PDBQT (*.pdbqt)",
        )

        if not files:
            return

        destination = (
            self.project_root
            / "docking"
            / "ligands"
            / "prepared"
        )

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        import shutil

        copied = 0

        for file in files:

            source = Path(file)
            target = destination / source.name

            if source.resolve() != target.resolve():

                shutil.copy2(
                    source,
                    target,
                )

                copied += 1

        self.refresh_pdbqt_table()

        self.status_message(
            f"{copied} ligand(s) ajouté(s)."
        )

    # ------------------------------------------------------------------
    # DOCKING
    # ------------------------------------------------------------------

    def create_docking_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)

        layout.addWidget(
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
        )

        config_panel = QFrame()
        config_panel.setObjectName("ContentPanel")

        grid = QGridLayout(config_panel)

        grid.setContentsMargins(
            22, 22, 22, 22
        )

        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        grid.addWidget(
            self._t_label("dock_target_panel_title", "Cible biologique", "PanelTitle"),
            0, 0, 1, 4
        )

        grid.addWidget(
            self._t_label("dock_receptor_label", "Récepteur"),
            1, 0
        )

        self.target_combo = QComboBox()

        self.target_combo.addItems(
            [
                "MexB",
                "MexR",
		"MexB + MexR"
            ]
        )

        self.target_combo.currentTextChanged.connect(
            self.update_target_parameters
        )

        grid.addWidget(
            self.target_combo,
            1, 1, 1, 3
        )

        grid.addWidget(
            self._t_label("dock_gridbox_panel_title", "Grid box", "PanelTitle"),
            2, 0, 1, 4
        )

        # ----------------------------------------------------------
        # CONFIGURATIONS MULTI-CIBLES
        # ----------------------------------------------------------

        self.mexb_fields = {}
        self.mexr_fields = {}

        # Compatibilité ancienne interface
        self.grid_fields = self.mexb_fields

        names = [
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
            )

            field = QLineEdit()
            field.setMaximumWidth(130)

            self.grid_fields[key] = field

            grid.addWidget(
                field,
                row,
                col + 1,
            )

        grid.addWidget(
            self._t_label("dock_vina_params_panel_title", "Paramètres Vina", "PanelTitle"),
            6, 0, 1, 4
        )

        grid.addWidget(
            make_label("Exhaustiveness"),
            7, 0,
        )

        self.exhaustiveness_field = QLineEdit()
        self.exhaustiveness_field.setMaximumWidth(130)
        grid.addWidget(
            self.exhaustiveness_field,
            7, 1,
        )

        grid.addWidget(
            self._t_label("dock_num_modes_label", "Nombre de modes"),
            7, 2,
        )

        self.num_modes_field = QLineEdit()
        self.num_modes_field.setMaximumWidth(130)
        grid.addWidget(
            self.num_modes_field,
            7, 3,
        )

        layout.addWidget(
            config_panel
        )


        # ----------------------------------------------------------
        # CONFIGURATION MEXR (DOUBLE CIBLE)
        # ----------------------------------------------------------

        self.mexr_panel = QFrame()
        self.mexr_panel.setObjectName("ContentPanel")

        mexr_layout = QVBoxLayout(
            self.mexr_panel
        )

        mexr_layout.setContentsMargins(
            22,22,22,22
        )


        mexr_layout.addWidget(
            self._t_label(
                "dock_mexr_config_panel_title",
                "Configuration MexR",
                "PanelTitle",
            )
        )


        self.mexr_receptor_label = make_label(
            "Récepteur : MEXR_1LNW.pdbqt"
        )

        mexr_layout.addWidget(
            self.mexr_receptor_label
        )


        self.mexr_info_label = make_label(
            "Grid : non chargé"
        )

        mexr_layout.addWidget(
            self.mexr_info_label
        )


        layout.addWidget(
            self.mexr_panel
        )


        # ----------------------------------------------------------
        # EXECUTION
        # ----------------------------------------------------------

        execution = QFrame()
        execution.setObjectName("ContentPanel")

        execution_layout = QVBoxLayout(execution)

        execution_layout.setContentsMargins(
            22, 18, 22, 18
        )

        header = QHBoxLayout()

        header.addWidget(
            self._t_label("dock_execution_panel_title", "Exécution", "PanelTitle")
        )

        header.addStretch()

        self.execution_status = make_label(
            "Prêt"
        )

        self.execution_status.setStyleSheet(
            f"color: {COLORS['success']}; "
            f"font-weight: 650;"
        )

        header.addWidget(
            self.execution_status
        )

        execution_layout.addLayout(
            header
        )

        self.current_ligand = make_label(
            "Aucun calcul en cours"
        )

        self.current_ligand.setStyleSheet(
            f"color: {COLORS['text_secondary']};"
        )

        execution_layout.addWidget(
            self.current_ligand
        )

        self.progress = QProgressBar()
        self.progress.setRange(
            0, 100
        )

        self.progress.setValue(0)

        execution_layout.addWidget(
            self.progress
        )

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = self._t_button(
            "dock_btn_cancel",
            "Annuler",
        )

        self.cancel_button.setObjectName(
            "DangerButton"
        )

        self.cancel_button.clicked.connect(
            self.cancel_docking
        )

        buttons.addWidget(
            self.cancel_button
        )

        self.launch_button = self._t_button(
            "dock_tab_run_docking",
            "Lancer le docking",
            primary=True,
        )

        self.launch_button.clicked.connect(
            self.launch_docking
        )

        buttons.addWidget(
            self.launch_button
        )

        execution_layout.addLayout(
            buttons
        )

        layout.addWidget(
            execution
        )

        # ----------------------------------------------------------
        # JOURNAL
        # ----------------------------------------------------------

        log_panel = QFrame()
        log_panel.setObjectName("ContentPanel")

        log_layout = QVBoxLayout(log_panel)

        log_layout.setContentsMargins(
            18, 14, 18, 14
        )

        log_layout.addWidget(
            self._t_label("dock_execution_log_panel_title", "Journal d'exécution", "PanelTitle")
        )

        self.docking_log = QTableWidget(
            0,
            2,
        )

        self.docking_log.setHorizontalHeaderLabels(
            [
                "État",
                "Message",
            ]
        )

        self.docking_log.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
        )

        self.docking_log.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.Stretch,
        )

        self.docking_log.setMaximumHeight(
            150
        )

        log_layout.addWidget(
            self.docking_log
        )

        layout.addWidget(
            log_panel
        )

        self.cancel_button.setEnabled(False)

        self.update_target_parameters(
            self.target_combo.currentText()
        )

        scroll = QScrollArea()
        scroll.setObjectName("DockingScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

    # ------------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------------

    def update_target_parameters(self, target):

        try:

            # Mode double cible : utiliser MexB uniquement pour l'affichage GUI.
            # Les moteurs MexB et MexR seront créés séparément au lancement.
            # Gestion double cible :
            # pour l'affichage on garde la configuration MexB
            # temporairement mais on évite les erreurs MexB+MexR
            # dans create_target_config()

            config_target = target

            if target == "MexB + MexR":
                config_target = "MexB"

            config = create_target_config(
                config_target,
                results_root=(
                    self.project_root
                    / "docking"
                    / "results"
                    / "batch_vina_engine"
                ),
            )

            values = {
                "center_x": config.center_x,
                "center_y": config.center_y,
                "center_z": config.center_z,
                "size_x": config.size_x,
                "size_y": config.size_y,
            }

            # size_z
            values["size_z"] = config.size_z

            for key, value in values.items():

                field = self.grid_fields.get(key)

                if field:
                    field.setText(
                        str(value)
                    )

            self.exhaustiveness_field.setText(
                str(config.exhaustiveness)
            )

            self.num_modes_field.setText(
                str(config.num_modes)
            )

            # Panneau MexR : visible uniquement si MexR est concerné,
            # et rempli avec la vraie configuration (recepteur + grid box)
            # au lieu du texte fixe d'origine.
            mexr_active = target in ("MexR", "MexB + MexR")

            self.mexr_panel.setVisible(mexr_active)

            if mexr_active:

                mexr_config = create_target_config(
                    "MexR",
                    results_root=(
                        self.project_root
                        / "docking"
                        / "results"
                        / "batch_vina_engine"
                    ),
                )

                self.mexr_receptor_label.setText(
                    f"Récepteur : {mexr_config.receptor.name}"
                )

                self.mexr_info_label.setText(
                    "Grid : centre "
                    f"({mexr_config.center_x}, {mexr_config.center_y}, "
                    f"{mexr_config.center_z}) — taille "
                    f"({mexr_config.size_x}, {mexr_config.size_y}, "
                    f"{mexr_config.size_z})"
                )

        except Exception as exc:

            self.execution_status.setText(
                f"Erreur configuration : {exc}"
            )

    # ------------------------------------------------------------------
    # DOCKING
    # ------------------------------------------------------------------

    def launch_docking(self):

        if self.thread is not None:
            QMessageBox.information(
                self,
                "Docking en cours",
                "Une campagne de docking est déjà en cours.",
            )
            return

        if not self.selected_ligands:

            QMessageBox.warning(
                self,
                "Aucun ligand sélectionné",
                "Sélectionnez d'abord les ligands PDBQT "
                "dans l'étape « Charger les PDBQT », "
                "puis cliquez sur « Utiliser la sélection ».",
            )

            return

        # Vérification finale des fichiers sélectionnés.
        missing = [
            path
            for path in self.selected_ligands
            if not path.exists()
        ]

        if missing:

            QMessageBox.warning(
                self,
                "Ligand introuvable",
                "Un ou plusieurs fichiers sélectionnés "
                "n'existent plus.",
            )

            self.selected_ligands = [
                path
                for path in self.selected_ligands
                if path.exists()
            ]

            return

        target = self.target_combo.currentText()

        try:

            # Mode double cible : utiliser MexB uniquement pour l'affichage GUI.
            # Les moteurs MexB et MexR seront créés séparément au lancement.
            config_target = (
                "MexB"
                if target == "MexB + MexR"
                else target
            )

            config = create_target_config(
                config_target,
                results_root=(
                    self.project_root
                    / "docking"
                    / "results"
                    / "batch_vina_engine"
                ),
            )

            # Les paramètres de l'interface deviennent la configuration active.
            config.center_x = float(
                self.grid_fields["center_x"].text()
            )

            config.center_y = float(
                self.grid_fields["center_y"].text()
            )

            config.center_z = float(
                self.grid_fields["center_z"].text()
            )

            config.size_x = float(
                self.grid_fields["size_x"].text()
            )

            config.size_y = float(
                self.grid_fields["size_y"].text()
            )

            config.size_z = float(
                self.grid_fields["size_z"].text()
            )

            config.exhaustiveness = int(
                self.exhaustiveness_field.text()
            )

            config.num_modes = int(
                self.num_modes_field.text()
            )

        except ValueError as exc:

            QMessageBox.warning(
                self,
                "Paramètres invalides",
                f"Vérifiez les paramètres numériques.\n\n{exc}",
            )

            return

        # ------------------------------------------------------
        # CREATION DES MOTEURS SELON LA CIBLE
        # ------------------------------------------------------

        engines = {}

        if target == "MexB":

            engines["MexB"] = VinaEngine(
                config
            )


        elif target == "MexR":

            engines["MexR"] = VinaEngine(
                config
            )


        elif target == "MexB + MexR":

            for sub_target in ("MexB", "MexR"):

                sub_config = create_target_config(
                    sub_target,
                    results_root=(
                        self.project_root
                        / "docking"
                        / "results"
                        / "batch_vina_engine"
                    ),
                )

                # Les parametres de recherche saisis dans l'interface
                # s'appliquent aux deux cibles. La grid box reste
                # specifique a chaque cible (poches de liaison
                # differentes) et n'est PAS ecrasee ici.
                sub_config.exhaustiveness = config.exhaustiveness
                sub_config.num_modes = config.num_modes

                engines[sub_target] = VinaEngine(sub_config)

        else:

            raise ValueError(
                f"Cible inconnue : {target}"
            )



        # ------------------------------------------------------
        # VALIDATION DES MOTEURS ACTIFS
        # ------------------------------------------------------

        validation_errors = []

        for engine_name, engine in engines.items():

            valid, errors = engine.validate()

            if not valid:

                validation_errors.extend(
                    [
                        f"{engine_name} : {error}"
                        for error in errors
                    ]
                )


        if validation_errors:

            QMessageBox.critical(
                self,
                "Configuration invalide",
                "\n".join(
                    f"• {error}"
                    for error in validation_errors
                ),
            )

            return

        # ------------------------------------------------------
        # VERIFICATION VINA SUR TOUS LES MOTEURS
        # ------------------------------------------------------

        vina_errors = []

        for engine_name, engine in engines.items():

            vina_ok, vina_message = (
                engine.check_vina()
            )

            if not vina_ok:

                vina_errors.append(
                    f"{engine_name} : {vina_message}"
                )


        if vina_errors:

            QMessageBox.critical(
                self,
                "AutoDock Vina indisponible",
                "\n".join(vina_errors),
            )

            return

        ligands = [
            str(path)
            for path in self.selected_ligands
        ]

        self.docking_log.setRowCount(0)

        self.progress.setValue(0)

        self.execution_status.setText(
            "Préparation du calcul…"
        )

        self.execution_status.setStyleSheet(
            f"color: {COLORS['accent_dark']}; "
            f"font-weight: 650;"
        )

        self.launch_button.setEnabled(
            False
        )

        self.cancel_button.setEnabled(
            True
        )

        self.target_combo.setEnabled(
            False
        )

        self.add_docking_log(
            "INFO",
            f"Campagne {target} — {len(ligands)} ligand(s) sélectionné(s)",
        )

        self.current_ligand.setText(
            f"{len(ligands)} ligand(s) sélectionné(s) — "
            "préparation du calcul…"
        )

        # ----------------------------------------------------------
        # THREAD
        # ----------------------------------------------------------

        self.thread = QThread()

        self.worker = DockingWorker(
            engines=engines,
            ligands=ligands,
            results_root=self.project_root,
        )

        self.worker.moveToThread(
            self.thread
        )

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.progress.connect(
            self.on_docking_progress
        )

        self.worker.log_line.connect(
            self.on_docking_log
        )

        self.worker.finished.connect(
            self.on_docking_finished
        )

        self.worker.failed.connect(
            self.on_docking_failed
        )

        self.worker.cancelled.connect(
            self.on_docking_cancelled
        )

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.failed.connect(
            self.thread.quit
        )

        self.worker.cancelled.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self.on_thread_finished
        )

        self.thread.finished.connect(
            self.thread.deleteLater
        )

        self.thread.start()

    def cancel_docking(self):

        if self.worker is None:
            return

        self.worker.cancel()

        self.execution_status.setText(
            "Annulation demandée…"
        )

        self.cancel_button.setEnabled(
            False
        )

        self.add_docking_log(
            "ANNULATION",
            "Annulation demandée par l'utilisateur.",
        )

    def on_docking_progress(
        self,
        engine,
        current,
        total,
        ligand_name,
    ):

        if not hasattr(self, "docking_progress_state"):

            self.docking_progress_state = {}

        percent = int(
            (current / total) * 100
        ) if total else 0


        self.docking_progress_state[engine] = {
            "current": current,
            "total": total,
            "percent": percent,
            "ligand": ligand_name,
        }


        # Calcul progression globale
        values = [
            item["percent"]
            for item in self.docking_progress_state.values()
        ]

        global_percent = int(
            sum(values) / len(values)
        ) if values else 0


        self.progress.setValue(
            global_percent
        )


        states = []

        for name, data in self.docking_progress_state.items():

            states.append(
                f"{name}: "
                f"{data['current']}/{data['total']} "
                f"({data['percent']}%)"
            )


        self.current_ligand.setText(
            f"Ligand {ligand_name}"
            "\n"
            + " | ".join(states)
        )


        self.execution_status.setText(
            f"Docking en cours — {global_percent}%"
        )

    def on_docking_log(self, message):

        self.add_docking_log(
            "VINA",
            message,
        )

    def on_docking_finished(self, csv_path):

        self.docking_results_csv = str(csv_path)

        gui_debug(
            "DOCKING TERMINE CSV = " + str(csv_path)
        )

        # Connexion directe Docking -> Analyse -> Résultats docking
        try:

            if hasattr(self, "analysis_page"):

                self.analysis_page.docking_results_csv = str(csv_path)

                gui_debug(
                    "CSV transmis a AnalysisPage"
                )

                if hasattr(
                    self.analysis_page,
                    "refresh_docking_results"
                ):

                    self.analysis_page.refresh_docking_results()

                    gui_debug(
                        "Refresh resultats docking execute"
                    )

        except Exception as e:

            gui_debug(
                "Erreur refresh analyse : " + str(e)
            )



        # Mise à jour automatique des résultats docking
        try:

            if hasattr(
                self,
                "analysis_page"
            ):

                self.analysis_page.docking_results_csv = str(csv_path)

                self.analysis_page.refresh_docking_results()

                gui_debug(
                    "RESULTATS DOCKING ACTUALISES"
                )

        except Exception as e:

            gui_debug(
                "ERREUR REFRESH RESULTATS : " + str(e)
            )

        self.progress.setValue(
            100
        )

        self.execution_status.setText(
            "Campagne terminée"
        )

        self.execution_status.setStyleSheet(
            f"color: {COLORS['success']}; "
            f"font-weight: 650;"
        )

        self.current_ligand.setText(
            "Tous les ligands ont été traités."
        )

        self.add_docking_log(
            "TERMINÉ",
            f"Résultats exportés : {csv_path}",
        )

        self.status_message(
            f"Docking terminé — résultats : {csv_path}"
        )
	# ------------------------------------------------------
        # GENERATION AUTOMATIQUE DES SCORES SCIENTIFIQUES
        # ------------------------------------------------------

        try:

            from src.scientific_fusion import (
                create_scientific_scores
            )

            grouped, global_csv = (
                create_scientific_scores(
                    csv_path
                )
            )

            self.analysis_page.statistics_csv = str(
                global_csv
            )

            self.add_docking_log(
                "ANALYSE",
                f"Fusion scientifique créée : {global_csv}",
            )

            self.analysis_page.statistics_status.setText(
                "Résultats scientifiques disponibles automatiquement."
            )

        except Exception as exc:

            self.add_docking_log(
                "ERREUR ANALYSE",
                str(exc),
            )

            global_csv = None
        # ------------------------------------------------------
        # ANALYSE STATISTIQUE AUTOMATIQUE
        # ------------------------------------------------------
        # L'indice de selectivite (fusion scientifique) compare
        # MexB et MexR : il ne peut exister que pour une campagne
        # ayant docke les DEUX cibles. Pour une campagne a une seule
        # cible, global_csv est None ci-dessus (comportement normal,
        # pas une erreur) : on saute proprement cette etape au lieu
        # de planter sur une variable non definie.

        if global_csv is None:

            self.add_docking_log(
                "ANALYSE",
                "Indice de selectivite non calcule (necessite MexB "
                "ET MexR). Les affinites brutes restent disponibles "
                "dans le tableau des resultats.",
            )

        else:

            try:

                self.analysis_page.statistics_result = (
                    run_statistics_pipeline(
                        str(global_csv)
                    )
                )

                print("===== RESULTAT PIPELINE =====")
                print("TYPE :", type(self.analysis_page.statistics_result))

                if isinstance(self.analysis_page.statistics_result, dict):

                    print("CLES :", self.analysis_page.statistics_result.keys())

                    for k, v in self.analysis_page.statistics_result.items():
                        print(
                            "CLE :",
                            k,
                            "TYPE :",
                            type(v)
                        )

                print("============================")


                if hasattr(self.analysis_page, "results_table"):
                    self.analysis_page.populate_statistics_results()

                self.status_message(
                    "Analyse scientifique automatique terminée."
                )

                self.analysis_page.statistics_status.setText(
                    "Analyse scientifique disponible."
                )

            except Exception as e:

                self.add_docking_log(
                    "ERREUR STATISTIQUES",
                    str(e),
                )

        # ------------------------------------------------------
        # VISUALISATION AUTOMATIQUE (PLIP + interactions)
        # ------------------------------------------------------
        # Auparavant, ce calcul ne se declenchait que si
        # l'utilisateur cliquait manuellement sur l'onglet
        # "Visualisation". On l'enchaine desormais automatiquement
        # a la fin du docking, sans attendre d'action GUI.

        try:

            if hasattr(self, "visualization_page"):

                self.visualization_page.run_full_batch()

                self.add_docking_log(
                    "VISUALISATION",
                    "Calcul PLIP / interactions lance automatiquement.",
                )

        except Exception as exc:

            self.add_docking_log(
                "ERREUR VISUALISATION",
                str(exc),
            )

        QMessageBox.information(
            self,
            "Docking terminé",
            "La campagne de docking est terminée.\n\n"
            f"Résultats :\n{csv_path}",
        )

    def on_docking_cancelled(self, message):

        self.progress.setValue(
            0
        )

        self.execution_status.setText(
            "Campagne annulée"
        )

        self.execution_status.setStyleSheet(
            f"color: {COLORS['warning']}; "
            f"font-weight: 650;"
        )

        self.current_ligand.setText(
            "Le docking a été interrompu."
        )

        self.add_docking_log(
            "ANNULÉ",
            message,
        )

        self.status_message(
            "Campagne de docking annulée."
        )


    def on_docking_failed(self, message):

        self.execution_status.setText(
            "Échec du docking"
        )

        self.execution_status.setStyleSheet(
            f"color: {COLORS['danger']}; "
            f"font-weight: 650;"
        )

        self.add_docking_log(
            "ERREUR",
            message,
        )

        QMessageBox.critical(
            self,
            "Erreur de docking",
            message,
        )

    def on_thread_finished(self):

        self.thread = None
        self.worker = None

        self.launch_button.setEnabled(
            True
        )

        self.cancel_button.setEnabled(
            False
        )

        self.target_combo.setEnabled(
            True
        )

    def add_docking_log(
        self,
        state,
        message,
    ):

        row = self.docking_log.rowCount()

        self.docking_log.insertRow(
            row
        )

        self.docking_log.setItem(
            row,
            0,
            QTableWidgetItem(state),
        )

        self.docking_log.setItem(
            row,
            1,
            QTableWidgetItem(
                str(message)
            ),
        )

        self.docking_log.scrollToBottom()

    def status_message(self, message):

        window = self.window()

        if hasattr(window, "status"):
            window.status.showMessage(
                message
            )


# ============================================================================
# PAGE ANALYSE
# ============================================================================

class AnalysisPage(QWidget):


    def populate_statistics_results(self):

        gui_debug(
            "REMPLISSAGE RESULTATS ANALYTIQUES"
        )


        if not self.statistics_result:

            gui_debug(
                "Aucun résultat statistique"
            )

            return


        # ------------------------------------------------
        # Nouveau système :
        # les résultats sont construits dynamiquement
        # depuis statistics_result
        # ------------------------------------------------

        if hasattr(
            self,
            "results_tabs"
        ):

            self.build_dynamic_statistics_tabs()

            gui_debug(
                "RESULTATS DYNAMIQUES RECONSTRUITS"
            )

        else:

            gui_debug(
                "results_tabs absent"
            )


    def __init__(self, lang_mgr=None):

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
        root.addWidget(self.stack, 1)

        gui_debug("Création d'un nouvel onglet")


        self.stack.addWidget(
            self.results_page()
        )

        gui_debug("Création d'un nouvel onglet")


        self.stack.addWidget(
            self.analysis_type_page()
        )

        gui_debug("Création d'un nouvel onglet")


        self.stack.addWidget(
            self.analysis_results_page()
        )

    def switch_tab(self, index):
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

    def run_docking_analysis(self):

        csv_path = getattr(
            self,
            "docking_results_csv",
            None
        )

        if not csv_path:

            QMessageBox.warning(
                self,
                "Analyse",
                "Aucun résultat de docking disponible."
            )

            return


        try:

            gui_debug(
                "LANCEMENT ANALYSE CSV : "
                + str(csv_path)
            )


            # Normalisation automatique CSV docking -> analyse statistique

            import pandas as pd

            df_analysis = pd.read_csv(csv_path)


            rename_map = {}

            for source, target_col in {

                "best_affinity_mexb": "dg_mexb",
                "best_affinity_mexr": "dg_mexr",
                "MexB": "dg_mexb",
                "MexR": "dg_mexr",

            }.items():

                if source in df_analysis.columns:
                    rename_map[source] = target_col


            if rename_map:

                df_analysis = df_analysis.rename(
                    columns=rename_map
                )


            required = [
                "dg_mexb",
                "dg_mexr",
            ]


            missing = [
                c for c in required
                if c not in df_analysis.columns
            ]


            if missing:

                raise Exception(
                    "Colonnes absentes après normalisation : "
                    + str(missing)
                    + " | disponibles : "
                    + str(list(df_analysis.columns))
                )


            temp_csv = Path(csv_path).with_name(
                "analysis_ready.csv"
            )

            df_analysis.to_csv(
                temp_csv,
                index=False
            )


            gui_debug(
                "CSV ANALYSE NORMALISE : "
                + str(temp_csv)
            )


            self.statistics_result = (
                run_statistics_pipeline(
                    temp_csv
                )
            )


            gui_debug(
                "MODE ANALYSE : "
                + str(
                    self.statistics_result.get(
                        "mode"
                    )
                )
            )


            self.populate_statistics_results()

            self.stack.setCurrentIndex(
                2
            )


            self.build_dynamic_statistics_tabs()


        except Exception as e:

            QMessageBox.critical(
                self,
                "Erreur analyse",
                str(e)
            )


    def results_page(self):

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        layout.addWidget(
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
        )

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarPanel")

        row = QHBoxLayout(toolbar)
        row.setContentsMargins(10, 8, 10, 8)

        row.addWidget(
            self._t_label("analysis_campaign_label", "Campagne")
        )

        combo = QComboBox()
        combo.addItems(
            [
                "MexB + MexR",
                "MexB",
                "MexR",
            ]
        )

        row.addWidget(combo)
        row.addStretch()

        analyze = self._t_button(
            "analysis_btn_run",
            "Lancer l'analyse",
            primary=True,
        )

        analyze.clicked.connect(
            self.run_docking_analysis
        )

        row.addWidget(analyze)

        layout.addWidget(toolbar)

        self.docking_results_table = QTableWidget(0, 6)

        table = self.docking_results_table

        table.setHorizontalHeaderLabels(
            self._docking_results_headers()
        )

        for col in range(6):
            table.horizontalHeader().setSectionResizeMode(
                col,
                QHeaderView.Stretch,
            )

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        import csv

        csv_path = getattr(
            self,
            "docking_results_csv",
            None
        )

        if not csv_path:

            table.insertRow(0)

            table.setItem(
                0,
                1,
                QTableWidgetItem(
                    "Aucun résultat de docking disponible"
                )
            )

            layout.addWidget(
                table,
                1
            )

            return page

        csv_file = Path(csv_path)

        if csv_file.exists():

            with csv_file.open(
                "r",
                encoding="utf-8"
            ) as handle:

                reader = csv.DictReader(handle)

                rows = []

                for index, data in enumerate(reader, start=1):

                    mexb = data.get(
                        "best_affinity_mexb",
                        ""
                    )

                    mexr = data.get(
                        "best_affinity_mexr",
                        ""
                    )

                    status = (
                        data.get("status_mexb", "")
                        + " / "
                        + data.get("status_mexr", "")
                    )

                    rows.append(
                        (
                            str(index),
                            data.get("molecule", ""),
                            data.get("groupe", ""),
                            mexb,
                            mexr,
                            status,
                        )
                    )


            for row_data in rows:

                row_index = table.rowCount()

                table.insertRow(
                    row_index
                )

                for col, value in enumerate(row_data):

                    table.setItem(
                        row_index,
                        col,
                        QTableWidgetItem(str(value)),
                    )

        layout.addWidget(table, 1)

        return page



    def refresh_docking_results(self):

        if not hasattr(
            self,
            "docking_results_table"
        ):
            return


        table = self.docking_results_table

        table.setRowCount(0)


        csv_path = getattr(
            self,
            "docking_results_csv",
            None
        )


        if not csv_path:
            return


        import csv


        path = Path(csv_path)


        if not path.exists():
            return


        with path.open(
            "r",
            encoding="utf-8"
        ) as handle:

            reader = csv.DictReader(handle)

            fieldnames = reader.fieldnames or []

            # Le CSV combine (campagne "MexB + MexR") a des colonnes
            # suffixees _mexb / _mexr. Le CSV d'une seule cible
            # (docking_results.csv) n'a que "best_affinity" /
            # "status", sans suffixe : avant ce correctif, ces
            # colonnes n'existaient jamais sous les noms attendus
            # ci-dessous et le tableau restait vide pour les
            # campagnes a une seule cible, meme quand le docking
            # avait parfaitement reussi.
            combined_schema = "best_affinity_mexb" in fieldnames

            single_target = None

            if not combined_schema:
                single_target = (
                    "MexR"
                    if "MexR" in path.parts
                    else "MexB"
                )

            for index, data in enumerate(
                reader,
                start=1
            ):

                row = table.rowCount()

                table.insertRow(row)

                if combined_schema:

                    affinity_mexb = data.get(
                        "best_affinity_mexb", ""
                    )

                    affinity_mexr = data.get(
                        "best_affinity_mexr", ""
                    )

                    status = (
                        data.get("status_mexb", "")
                        or data.get("status_mexr", "")
                    )

                else:

                    affinity = data.get(
                        "best_affinity", ""
                    )

                    status = data.get(
                        "status", ""
                    )

                    affinity_mexb = (
                        affinity
                        if single_target == "MexB"
                        else ""
                    )

                    affinity_mexr = (
                        affinity
                        if single_target == "MexR"
                        else ""
                    )

                values = [

                    index,

                    data.get(
                        "molecule",
                        ""
                    ),

                    data.get(
                        "groupe",
                        ""
                    ),

                    affinity_mexb,

                    affinity_mexr,

                    status,

                ]


                for col,value in enumerate(values):

                    table.setItem(
                        row,
                        col,
                        QTableWidgetItem(
                            str(value)
                        )
                    )



    def analysis_type_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            28, 26, 28, 26
        )
        layout.setSpacing(18)

        layout.addWidget(
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
        )

        panel = QFrame()
        panel.setObjectName(
            "ContentPanel"
        )

        grid = QGridLayout(panel)

        self.statistics_csv = (
            "reference_data/scores_fusionnes.csv"
        )

        grid.addWidget(
            self._t_label(
                "analysis_internal_csv_label",
                "CSV scientifique interne : "
                "scores_fusionnes.csv",
            ),
            0,
            0,
            1,
            3
        )


        self.statistics_status = make_label(
            "Aucune analyse chargée."
        )

        grid.addWidget(
            self.statistics_status,
            1,
            0,
            1,
            3
        )


        launch = self._t_button(
            "analysis_btn_run_scientific",
            "Lancer analyse scientifique",
            primary=True,
        )

        load_csv = QPushButton(
            self.lang_mgr.t("analysis_btn_load_csv") if self.lang_mgr
            else "Charger un CSV externe"
        )
        self._i18n.append((load_csv, "analysis_btn_load_csv", "Charger un CSV externe"))

        load_csv.clicked.connect(
            self.load_external_statistics_csv
        )

        grid.addWidget(
            load_csv,
            2,
            0
        )


        launch.clicked.connect(
            self.run_statistics_analysis
        )

        grid.addWidget(
            launch,
            2,
            2
        )


        layout.addWidget(
            panel
        )

        layout.addStretch()

        return page





    def load_external_statistics_csv(self):

        csv, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier CSV",
            "",
            "CSV (*.csv)"
        )

        if not csv:
            return


        self.statistics_csv = csv


        self.statistics_status.setText(
            f"CSV chargé : {Path(csv).name}"
        )


        print(
            "CSV STATISTIQUE CHARGÉ :",
            csv
        )

    def run_statistics_analysis(self):

        gui_debug(
            "LANCEMENT ANALYSE STATISTIQUE"
        )


        csv = self.statistics_csv


        if not csv:

            QMessageBox.warning(
                self,
                "CSV manquant",
                "Veuillez charger un fichier CSV avant de lancer l'analyse."
            )

            return


        try:

            self.statistics_result = (
                run_statistics_pipeline(
                    csv
                )
            )


            self.statistics_status.setText(
                "Analyse terminée."
            )

            self.populate_statistics_results()


            self.stack.setCurrentIndex(
                2
            )


        except Exception as e:

            QMessageBox.critical(
                self,
                "Erreur analyse",
                str(e)
            )



    def build_dynamic_statistics_tabs(self):

        if not hasattr(self, "results_tabs"):
            return


        self.results_tabs.clear()


        result = getattr(
            self,
            "statistics_result",
            None
        )

        if not result:
            return


        classification = result.get(
            "classification"
        )


        def add_table(name):

            page = QWidget()
            layout = QVBoxLayout(page)

            table = QTableWidget()

            if classification is not None:

                cols = list(
                    classification.columns
                )

                table.setColumnCount(
                    len(cols)
                )

                table.setHorizontalHeaderLabels(
                    cols
                )

                for _, row in classification.iterrows():

                    idx = table.rowCount()

                    table.insertRow(idx)

                    for c, col in enumerate(cols):

                        table.setItem(
                            idx,
                            c,
                            QTableWidgetItem(
                                str(row.get(col, ""))
                            )
                        )


            layout.addWidget(table)

            self.results_tabs.addTab(
                page,
                name
            )

            self.results_tabs.tabBar().setTabTextColor(
                self.results_tabs.count()-1,
                QColor("#3d7b61")
            )


        def add_figure(name, fig):

            page = QWidget()

            layout = QVBoxLayout(page)

            canvas = FigureCanvas(fig)

            layout.addWidget(
                canvas
            )

            self.results_tabs.addTab(
                page,
                name
            )

            self.results_tabs.tabBar().setTabTextColor(
                self.results_tabs.count()-1,
                QColor("#3d7b61")
            )


        # --------------------------
        # TOUJOURS DISPONIBLE
        # --------------------------




        add_table(
            "Top candidats"
        )



        # --------------------------
        # DOUBLE SELECTIVITE
        # --------------------------

        dual = result.get(
            "dual_filter"
        )


        if isinstance(dual, dict):

            def add_dual_table(title, dataframe):

                page = QWidget()

                layout = QVBoxLayout(page)

                table = QTableWidget()


                if dataframe is not None:

                    cols = list(
                        dataframe.columns
                    )

                    table.setColumnCount(
                        len(cols)
                    )

                    table.setHorizontalHeaderLabels(
                        cols
                    )


                    for _, row in dataframe.iterrows():

                        idx = table.rowCount()

                        table.insertRow(
                            idx
                        )

                        for c, col in enumerate(cols):

                            table.setItem(
                                idx,
                                c,
                                QTableWidgetItem(
                                    str(row.get(col, ""))
                                )
                            )


                layout.addWidget(
                    table
                )


                self.results_tabs.addTab(
                    page,
                    title
                )


                self.results_tabs.tabBar().setTabTextColor(
                    self.results_tabs.count()-1,
                    QColor("#3d7b61")
                )


            dual_page = QWidget()

            dual_layout = QVBoxLayout(
                dual_page
            )


            dual_layout.addWidget(
                make_panel_title(
                    "Filtre à double sélectivité"
                )
            )


            dual_layout.addWidget(
                make_label(
                    "Critères :\n"
                    "- SI percentile > 50\n"
                    "- ΔG MexR meilleur que le seuil piocyanine (-8.289 kcal/mol)"
                )
            )


            candidates = dual.get(
                "candidates"
            )

            excluded = dual.get(
                "excluded_absolute"
            )


            dual_layout.addWidget(
                make_label(
                    "Candidats retenus : "
                    + str(len(candidates))
                )
            )


            add_dual_table(
                "Filtre double sélectivité",
                candidates
            )


            add_dual_table(
                "Exclus seuil piocyanine",
                excluded
            )


        # --------------------------
        # FIGURES
        # --------------------------

        try:

            add_figure(
                "Histogramme SI",
                fig_histogram_si(
                    classification
                )
            )

        except Exception as e:
            print(
                "Histogramme SI ignoré :",
                e
            )


        try:

            corr = result.get(
                "correlations"
            )

            boot = result.get(
                "bootstrap"
            )


            add_figure(
                "Corrélations",
                fig_forest_correlations(
                    corr,
                    boot
                )
            )


        except Exception as e:
            print(
                "Corrélation ignorée :",
                e
            )


        # --------------------------
        # MODE GROUPES
        # --------------------------

        if result.get("mode") == "GROUPES":

            try:

                add_figure(
                    "Histogrammes groupes",
                    fig_histogram_si_by_group(
                        classification
                    )
                )

            except Exception as e:
                print(
                    "Histogrammes groupes ignorés :",
                    e
                )


        # ---------------------------------------------
        # RAFRAICHISSEMENT INTERFACE DYNAMIQUE
        # ---------------------------------------------

        if hasattr(self, "results_tabs"):

            self.results_tabs.setCurrentIndex(0)

            self.results_tabs.show()

            self.results_tabs.update()

            self.results_tabs.repaint()


            gui_debug(
                "ONGLETS DYNAMIQUES VISIBLES = "
                + str(self.results_tabs.count())
            )


            loo = result.get(
                "leave_one_out"
            )

            if loo is not None:

                try:

                    add_figure(
                        "Leave-one-out",
                        fig_loo_influence(
                            loo
                        )
                    )

                except Exception as e:

                    print(
                        "LOO ignoré :",
                        e
                    )




    def analysis_results_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            28,
            26,
            28,
            26
        )
        layout.setSpacing(16)


        layout.addWidget(
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
        )


        # -------------------------------------------------
        # UNIQUE CONTENEUR DES RESULTATS STATISTIQUES
        # -------------------------------------------------

        self.results_tabs = QTabWidget()


        self.results_tabs.setMovable(
            True
        )


        self.results_tabs.setTabsClosable(
            False
        )


        self.results_tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #cfd5dc;
                background: #ffffff;
                border-radius: 6px;
            }

            QTabBar::tab {
                background: #e7ebef;
                color: #65717d;
                padding: 8px 18px;
                margin-right: 3px;
                border: 1px solid #cfd5dc;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            QTabBar::tab:selected {
                background: #ffffff;
                color: #3d7b61;
                border-bottom: 3px solid #3d7b61;
            }

            QTabBar::tab:hover {
                background: #dcecf4;
            }
            """
        )


        layout.addWidget(
            self.results_tabs,
            1
        )


        return page


# ============================================================================
# PAGE VISUALISATION
# ============================================================================

class VisualizationPage(QWidget):

    def __init__(self, docking_page=None, analysis_page=None, lang_mgr=None):

        super().__init__()

        self.docking_page = docking_page
        self.analysis_page = analysis_page
        self.lang_mgr = lang_mgr
        self._i18n = []

        self.current_hits = []
        self.hit_results = {}
        self.batch_errors = []

        self.batch_thread = None
        self.batch_worker = None
        self.batch_started = False
        self.batch_running = False

        self.current_diagram_path = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar_frame = QFrame()
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(22, 14, 22, 14)

        self.batch_status = make_label(
            "En attente du premier passage sur cet onglet…",
            "SectionDescription",
        )
        toolbar.addWidget(self.batch_status, 1)

        self.recompute_button = create_button("Recalculer tout")
        self.recompute_button.clicked.connect(self.run_full_batch)
        toolbar.addWidget(self.recompute_button)

        self.export_all_button = create_button("Exporter tout", primary=True)
        self.export_all_button.clicked.connect(self._on_export_all_clicked)
        self.export_all_button.setEnabled(False)
        toolbar.addWidget(self.export_all_button)

        root.addWidget(toolbar_frame)

        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.secondary = SecondaryNavigation(
            "Visualisation",
            [
                "Résidus de référence",
                "Calcul PLIP",
                "Interaction 2D",
            ],
            self.switch_tab,
        )

        body.addWidget(self.secondary)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self.stack.addWidget(self.residues_page())
        self.stack.addWidget(self.plip_page())
        self.stack.addWidget(self.interaction_page())

        root.addWidget(body_widget, 1)

    # ------------------------------------------------------------------
    # DÉCLENCHEMENT AUTOMATIQUE (aucune sélection utilisateur)
    # ------------------------------------------------------------------

    def ensure_batch_started(self):
        if not self.batch_started:
            self.run_full_batch()

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def run_full_batch(self):

        if self.batch_running:
            return

        self.batch_started = True
        self.batch_running = True
        self.export_all_button.setEnabled(False)
        self.batch_status.setText(
            self.lang_mgr.t("status_loading_hits") if self.lang_mgr
            else "Chargement des hits de docking…"
        )
        QApplication.processEvents()

        try:
            # On charge les hits pour toutes les cibles qui ont
            # effectivement des resultats de docking sur disque
            # (MexB seul, MexR seul, ou les deux en campagne
            # "MexB + MexR"), plutot que de se limiter a la cible
            # par defaut (MexB).
            hits = []
            for candidate_target in ("MexB", "MexR"):
                if viz_bridge._results_csv(candidate_target).exists():
                    hits.extend(
                        viz_bridge.load_top_hits(
                            viz_bridge.AUTO_TOP_N,
                            target=candidate_target,
                        )
                    )
        except Exception as exc:
            self.batch_running = False
            self.batch_status.setText(f"Erreur au chargement des hits : {exc}")
            return

        if not hits:
            self.batch_running = False
            self.batch_status.setText(
                "Aucun hit exploitable trouvé dans les résultats de docking."
            )
            return

        self.current_hits = hits
        self.hit_results = {}
        self.batch_errors = []

        self.batch_status.setText(f"Calcul PLIP en cours — 0/{len(hits)}…")

        self.batch_thread = QThread()
        self.batch_worker = viz_bridge.BatchWorker(hits)
        self.batch_worker.moveToThread(self.batch_thread)

        self.batch_thread.started.connect(self.batch_worker.run)
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.finished.connect(self._on_batch_finished)
        self.batch_worker.finished.connect(self.batch_thread.quit)
        self.batch_thread.finished.connect(self.batch_thread.deleteLater)

        self.batch_thread.start()

    def _on_batch_progress(self, molecule, index, total):
        self.batch_status.setText(
            f"Calcul PLIP en cours — {index}/{total} : {molecule}…"
        )

    def _on_batch_finished(self, payload):

        self.batch_running = False
        self.hit_results = payload.get("results", {})
        self.batch_errors = payload.get("errors", [])

        rows = []
        for molecule, data in self.hit_results.items():
            for res in data["interactions"]["summary"]:
                rows.append(
                    (
                        res["residue"],
                        res["chain"],
                        str(res["residue_id"]),
                        res["interaction_types"],
                        molecule,
                    )
                )

        self._populate_residues_table(rows)
        self._refresh_molecule_combo()

        status_text = (
            f"{len(self.hit_results)} molécule(s) traitée(s) automatiquement, "
            f"{len(rows)} contact(s) résidu affiché(s)."
        )

        if self.batch_errors:
            status_text += (
                f" — {len(self.batch_errors)} molécule(s) en erreur."
            )
            self.plip_errors_label.setText(
                "Erreurs :\n" + "\n".join(self.batch_errors)
            )
        else:
            self.plip_errors_label.setText(
                self.lang_mgr.t("status_no_errors") if self.lang_mgr
                else "Aucune erreur."
            )

        self.batch_status.setText(status_text)
        self.export_all_button.setEnabled(bool(self.hit_results))

        if self.hit_results:
            first_molecule = next(iter(self.hit_results))
            self._display_diagram_image(self.hit_results[first_molecule]["diagram"])

    # ------------------------------------------------------------------
    # RÉSIDUS DE RÉFÉRENCE (lecture seule, peuplé automatiquement)
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
        )

        for col in range(5):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        self.residues_table = table

        layout.addWidget(table, 1)

        return page

    def _populate_residues_table(self, rows):

        table = self.residues_table
        table.setRowCount(0)

        for values in rows:

            row = table.rowCount()
            table.insertRow(row)

            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(str(value)))

    # ------------------------------------------------------------------
    # CALCUL PLIP (statut uniquement, plus de configuration manuelle)
    # ------------------------------------------------------------------

    def plip_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        layout.addWidget(
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
        )

        panel_layout.addWidget(self.plip_errors_label)

        layout.addWidget(panel)
        layout.addStretch()

        return page

    # ------------------------------------------------------------------
    # INTERACTION 2D (visualisation uniquement, rien à calculer ici)
    # ------------------------------------------------------------------

    def interaction_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()

        header.addWidget(
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
            "VISUALISATION DES INTERACTIONS\n\n"
            "Les diagrammes sont générés automatiquement pour toutes les "
            "molécules ; choisis-en une ci-dessus pour l'afficher.",
        )

        message.setAlignment(Qt.AlignCenter)

        message.setStyleSheet(
            "color: #9ba8b3; "
            "font-size: 14px;"
        )

        self.diagram_label = message

        viewer_layout.addWidget(message)

        layout.addWidget(viewer, 1)

        return page

    def _refresh_molecule_combo(self):

        molecules = sorted(self.hit_results.keys())

        combo = self.diagram_molecule_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(molecules)
        combo.blockSignals(False)

        if molecules:
            combo.setCurrentIndex(0)
            self._on_diagram_molecule_changed(molecules[0])

    def _on_diagram_molecule_changed(self, molecule):

        if not molecule or molecule not in self.hit_results:
            return

        self._display_diagram_image(self.hit_results[molecule]["diagram"])

    def _display_diagram_image(self, png_path):

        pixmap = QPixmap(png_path)

        if pixmap.isNull():
            self.diagram_label.setText(
                "Impossible de charger l'image générée."
            )
            return

        self.diagram_label.setPixmap(
            pixmap.scaled(
                900,
                700,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.diagram_label.setText("")
        self.current_diagram_path = png_path

    def _on_export_2d_clicked(self):

        if not self.current_diagram_path:
            return

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter l'image",
            "diagramme_interactions.png",
            "Images PNG (*.png)",
        )

        if not destination:
            return

        shutil.copyfile(self.current_diagram_path, destination)

    # ------------------------------------------------------------------
    # EXPORT GLOBAL
    # ------------------------------------------------------------------

    def _on_export_all_clicked(self):

        if not self.hit_results:
            return

        destination = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier d'export",
        )

        if not destination:
            return

        try:
            target = self.current_hits[0].target if self.current_hits else viz_bridge.DEFAULT_TARGET

            export_dir = viz_bridge.export_visualization_results(
                target,
                {"results": self.hit_results, "errors": self.batch_errors},
                Path(destination) / "export_visualisation",
            )

            stats_note = ""

            if self.analysis_page is not None and getattr(self.analysis_page, "statistics_result", None):

                import json

                stats_path = export_dir / "analyse_statistique.json"

                with stats_path.open("w", encoding="utf-8") as handle:
                    json.dump(
                        self.analysis_page.statistics_result,
                        handle,
                        default=str,
                        ensure_ascii=False,
                        indent=2,
                    )

                stats_note = " (analyse statistique incluse)"

            QMessageBox.information(
                self,
                "Export",
                f"Export terminé dans :\n{export_dir}{stats_note}",
            )

        except Exception as exc:
            QMessageBox.critical(self, "Erreur export", str(exc))

# ============================================================================
# PAGE PROJET
# ============================================================================

class ProjectPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(
            make_label(
                "Projet",
                "SectionTitle",
            )
        )

        layout.addWidget(
            make_label(
                "Vue générale du projet de docking moléculaire.",
                "SectionDescription",
            )
        )

        panel = QFrame()
        panel.setObjectName("ContentPanel")

        grid = QGridLayout(panel)
        grid.setContentsMargins(22, 22, 22, 22)
        grid.setSpacing(14)

        data = [
            ("Nom du projet", "Nouveau projet"),
            ("Récepteur", "—"),
            ("Bibliothèque", "—"),
            ("Dernière campagne", "—"),
            ("Résultats", "—"),
        ]

        for row, (key, value) in enumerate(data):

            label = make_label(key)
            label.setStyleSheet(
                f"color: {COLORS['text_secondary']};"
            )

            value_label = make_label(value)

            grid.addWidget(label, row, 0)
            grid.addWidget(value_label, row, 1)

        grid.setColumnStretch(1, 1)

        layout.addWidget(panel)
        layout.addStretch()


# ============================================================================
# FENETRE PRINCIPALE
# ============================================================================



def gui_debug(message):
    print("\n===== GUI DEBUG =====")
    print(message)
    print("====================\n")


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        try:
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

        self.retranslate_ui()

    def retranslate_ui(self, _code=None):
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

        if hasattr(self, "docking_page") and hasattr(self.docking_page, "retranslate"):
            self.docking_page.retranslate()

        if hasattr(self, "analysis_page") and hasattr(self.analysis_page, "secondary"):
            nav = self.analysis_page.secondary
            if hasattr(nav, "title_label"):
                nav.title_label.setText(t("side_analysis").upper())
            analysis_labels = [t("analysis_tab_results"), t("analysis_tab_type"), t("analysis_tab_results_analytics")]
            for btn, lbl in zip(nav.buttons, analysis_labels):
                btn.setText(lbl)

        if hasattr(self, "analysis_page") and hasattr(self.analysis_page, "retranslate"):
            self.analysis_page.retranslate()

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
            if hasattr(self.visualization_page, "retranslate_subtabs"):
                self.visualization_page.retranslate_subtabs()

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

        if hasattr(self, "lang_action"):
            self.lang_action.setText(self.lang_mgr.native_name())

        if hasattr(self, "status"):
            self.status.showMessage(t("status_ready"))

    def _on_toggle_language(self):
        self.lang_mgr.cycle_language()

    def closeEvent(self, event):

        try:
            viz_bridge.cleanup_visualization_outputs()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage visualisation : {exc}")

        try:
            end_session()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage fin de session : {exc}")

        super().closeEvent(event)

    # ------------------------------------------------------------------
    # MENU
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # ANALYSE SCIENTIFIQUE CSV
    # ------------------------------------------------------------------

    def load_statistics_analysis(self):

        csv_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier CSV scientifique",
            "",
            "CSV (*.csv)"
        )

        if not csv_path:
            return

        try:

            result = run_statistics_pipeline(
                csv_path
            )

            self.status.showMessage(
                f"Analyse terminée — mode {result['mode']}"
            )

            QMessageBox.information(
                self,
                "Analyse scientifique",
                (
                    f"Analyse terminée\n\n"
                    f"Mode : {result['mode']}\n"
                    f"Molécules : {len(result['data'])}"
                )
            )

            self.statistics_result = result

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erreur analyse scientifique",
                str(e)
            )



    def create_menu(self):

        menu = self.menuBar()

        file_menu = menu.addMenu("Fichier")
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
        self.menu_help = help_menu

        quit_action = QAction("Quitter", self)

        quit_action.triggered.connect(
            self.close
        )

        file_menu.addAction(quit_action)

        prepare_action = QAction(
            "Préparer les ligands…", self
        )

        prepare_action.triggered.connect(
            lambda: self.primary_navigation.buttons[0].click()
        )

        docking_menu.addAction(prepare_action)

        launch_action = QAction(
            "Lancer une campagne de docking", self
        )

        launch_action.triggered.connect(
            lambda: self.primary_navigation.buttons[0].click()
        )

        docking_menu.addAction(launch_action)

        analysis_action = QAction(
            "Charger une analyse CSV",
            self
        )

        analysis_action.triggered.connect(
            self.load_statistics_analysis
        )

        analysis_menu.addAction(
            analysis_action
        )

        results_action = QAction(
            "Voir les résultats", self
        )

        results_action.triggered.connect(
            lambda: self.primary_navigation.buttons[1].click()
        )

        analysis_menu.addAction(results_action)

        visualization_action = QAction(
            "Ouvrir la visualisation", self
        )

        visualization_action.triggered.connect(
            lambda: self.primary_navigation.buttons[2].click()
        )

        visualization_menu.addAction(visualization_action)

        preferences_action = QAction(
            "Préférences (bientôt disponible)", self
        )

        preferences_action.setEnabled(False)

        tools_menu.addAction(preferences_action)

        about_action = QAction(
            "À propos de VINA Studio", self
        )

        about_action.triggered.connect(
            self.show_about_dialog
        )

        help_menu.addAction(about_action)

    def show_about_dialog(self):

        QMessageBox.about(
            self,
            "À propos de VINA Studio",
            "VINA Studio\n"
            "Molecular Docking & Interaction Analysis\n\n"
            "Pipeline complet : préparation des ligands, docking "
            "AutoDock Vina, analyse statistique (MexB/MexR) et "
            "visualisation des interactions.",
        )

    # ------------------------------------------------------------------
    # TOOLBAR
    # ------------------------------------------------------------------

    def create_toolbar(self):

        toolbar = self.addToolBar(
            "Outils principaux"
        )

        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))

        def add_navigation_action(label, page_index):

            action = QAction(label, self)

            action.triggered.connect(
                lambda checked=False, i=page_index: (
                    self.primary_navigation.buttons[i].click()
                )
            )

            toolbar.addAction(action)

            return action

        self.nav_action_prepare = add_navigation_action("Préparer les ligands", 0)
        self.nav_action_docking = add_navigation_action("Lancer le docking", 0)

        toolbar.addSeparator()

        self.nav_action_analysis = add_navigation_action("Analyse", 1)
        self.nav_action_visualization = add_navigation_action("Visualisation", 2)

        toolbar.addSeparator()

        self.lang_action = QAction(self.lang_mgr.native_name(), self)
        self.lang_action.setToolTip("Changer la langue de l'interface")
        self.lang_action.triggered.connect(self._on_toggle_language)
        toolbar.addAction(self.lang_action)

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------

    def build_interface(self):

        central = QWidget()

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --------------------------------------------------------------
        # HEADER
        # --------------------------------------------------------------

        header = QFrame()
        header.setObjectName("TopHeader")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            20, 13, 20, 13
        )

        branding = QVBoxLayout()
        branding.setSpacing(1)

        self.app_name_label = make_label(
            "VINA Studio",
            "ApplicationName",
        )
        branding.addWidget(self.app_name_label)

        self.app_subtitle_label = make_label(
            "Molecular Docking & Interaction Analysis",
            "ApplicationSubtitle",
        )
        branding.addWidget(self.app_subtitle_label)

        header_layout.addLayout(branding)
        header_layout.addStretch()

        target_label = make_label(
            "Cible active"
        )

        target_label.setStyleSheet(
            f"font-size: 10px; "
            f"color: {COLORS['text_muted']};"
        )

        self.header_target_label = make_label(
            "MexB"
        )

        self.header_target_label.setStyleSheet(
            f"font-weight: 650; "
            f"color: {COLORS['accent_dark']};"
        )

        header_layout.addWidget(
            target_label
        )

        header_layout.addSpacing(8)

        header_layout.addWidget(
            self.header_target_label
        )

        outer.addWidget(header)

        # --------------------------------------------------------------
        # BODY
        # --------------------------------------------------------------

        body = QWidget()

        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.primary_navigation = PrimaryNavigation(
            self.switch_primary
        )

        body_layout.addWidget(
            self.primary_navigation
        )

        self.workspace = QStackedWidget()

        self.docking_page = DockingPage(lang_mgr=self.lang_mgr)

        self.workspace.addWidget(
            self.docking_page
        )

        self.analysis_page = AnalysisPage(lang_mgr=self.lang_mgr)

        # Liaison directe Docking -> Analyse
        self.docking_page.analysis_page = self.analysis_page

        # Liaison directe Docking -> en-tête (cible active affichée)
        self.docking_page.target_combo.currentTextChanged.connect(
            self.header_target_label.setText
        )

        self.header_target_label.setText(
            self.docking_page.target_combo.currentText()
        )

        self.workspace.addWidget(
            self.analysis_page
        )

        self.visualization_page = VisualizationPage(
            docking_page=getattr(self, "docking_page", None),
            analysis_page=getattr(self, "analysis_page", None),
            lang_mgr=getattr(self, "lang_mgr", None),
        )

        self.workspace.addWidget(
            self.visualization_page
        )

        body_layout.addWidget(
            self.workspace,
            1,
        )

        outer.addWidget(
            body,
            1,
        )

        self.setCentralWidget(
            central
        )

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------

    def switch_primary(self, index):

        self.workspace.setCurrentIndex(
            index
        )

        names = [
            "Docking",
            "Analyse",
            "Visualisation",
        ]

        if 0 <= index < len(names):

            self.status.showMessage(
                f"{names[index]} — espace de travail actif"
            )

        if index == 2 and hasattr(self, "visualization_page"):
            self.visualization_page.ensure_batch_started()


# ============================================================================
# APPLICATION
# ============================================================================

def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "VINA Studio"
    )

    app.setOrganizationName(
        "VINA Studio"
    )

    app.setStyle(
        "Fusion"
    )

    app.setStyleSheet(
        APP_STYLE
    )

    font = QFont(
        "Noto Sans",
        10,
    )

    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
