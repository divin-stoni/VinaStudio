# -*- coding: utf-8 -*-

from __future__ import annotations
from src.session_runtime import start_new_session, end_session
from src.session_manager import SessionManager
from src.i18n.language_manager import LanguageManager

import sys
import shutil
import json
from pathlib import Path

from PySide6.QtCore import (
    Qt, QSize, QThread, QObject, Signal, Slot, QEvent, QRectF, QTimer,
    Property, QSettings,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import (
    QAction, QFont, QIcon, QColor, QPixmap, QPalette,
    QPainterPath, QRegion, QPainter, QLinearGradient, QPen,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
# ============================================================================
# BACKEND SCIENTIFIQUE
# ============================================================================

from src.docking.sdf_preparer import prepare_sdf
from src.docking.vina_engine import VinaEngine, create_target_config
from src.docking.vina_worker import DockingWorker
from src.docking.receptor_profile import (
    resolve_target_profile,
    GridBox,
    ReceptorProfile,
    list_profile_ids,
    save_user_profile,
    save_user_grid_override,
    clear_user_grid_override,
    short_label,
    list_pairs,
    make_pair_key,
    parse_pair_key,
    is_pair_key,
    resolve_pair,
    normalize_role,
)
from src.docking.receptor_manager import ReceptorManager
from src.gui.viewer_template import VIEWER_HTML
from src.analysis.statistics_pipeline import run_statistics_pipeline
from src.analysis.analysis_controller import analyze_docking_csv
from src.gui import visualization_bridge as viz_bridge
from src.gui.credits_page import CreditsPage
from src.gui.phyto_page import PhytoPage  # --- patch16 phytomolecules tab ---


class _ViewerDragRepaintPoller:
    """
    Sonde l'etat global de la souris via un QTimer, sans jamais
    passer par le systeme d'evenements Qt.
    """
    def __init__(self, viewer_widget, interval_ms=33):
        from PySide6.QtCore import QTimer
        self.viewer = viewer_widget
        self.timer = QTimer()
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt

        # On vérifie si la souris est pressée, mais on ajoute une vérification 
        # de visibilité pour être sûr.
        if self.viewer is None or not self.viewer.isVisible():
            return
        
        # Le rafraîchissement doit être constant pendant l'interaction
        # On force le rendu JS.
        # Ne rend que pendant un vrai glisser de souris (sinon 60 appels JS/s
        # en permanence saturent QtWebEngine et gelent l'interface).
        if QApplication.mouseButtons() == Qt.NoButton:
            return
        self.viewer.page().runJavaScript("if (typeof viewer !== 'undefined') { viewer.render(); }")


class _ResidueHoverBridge(QObject):
    """
    Objet exposé au JavaScript du visualiseur via QWebChannel. Le JS
    (3Dmol.js, setHoverable) appelle onResidueHover(chain, resn, resi)
    à chaque survol/sortie de survol d'un atome ; ce signal Qt est
    ensuite relayé vers le panneau d'info Python.
    """

    residueHovered = Signal(str, str, str)

    @Slot(str, str, str)
    def onResidueHover(self, chain, resn, resi):
        self.residueHovered.emit(chain, resn, resi)

from PySide6.QtWidgets import QDialog, QCheckBox, QDialogButtonBox, QLabel as _QLabelChainDialog


class _ChainSelectionDialog(QDialog):
    """
    Boîte de dialogue affichée lors de l'import d'un fichier PDB brut :
    liste toutes les chaînes détectées avec leur nombre de résidus, et
    laisse l'utilisateur cocher celle(s) à garder (monomère = 1 case
    cochée, dimère = 2, etc.). Aucune sélection biologique n'est faite
    à sa place.
    """

    def __init__(self, chain_residues: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélection des chaînes à conserver")

        layout = QVBoxLayout(self)
        layout.addWidget(_QLabelChainDialog(
            "Ce fichier PDB contient plusieurs chaînes. Coche celle(s) à "
            "garder pour le docking.\n"
            "L'eau, les hétéroatomes et les ligands co-cristallisés "
            "seront supprimés automatiquement, quelle que soit la "
            "sélection."
        ))

        self._checkboxes = {}
        for chain_id in sorted(chain_residues):
            n_res = chain_residues[chain_id]
            checkbox = QCheckBox(f"Chaîne {chain_id} — {n_res} résidu(s)")
            layout.addWidget(checkbox)
            self._checkboxes[chain_id] = checkbox

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_chains(self) -> list[str]:
        return [
            chain_id
            for chain_id, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]


class _MoleculeFamilyDialog(QDialog):
    """Sélecteur compact de sept familles maximum, une famille par dossier."""

    MAX_FAMILIES = 7

    def __init__(self, parent=None, title="Choisir les familles de molécules"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(700)
        self._rows = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Active une ou plusieurs familles, donne-leur un nom, puis "
            "choisis le dossier qui contient leurs molécules."
        ))

        grid = QGridLayout()
        grid.addWidget(QLabel("Actif"), 0, 0)
        grid.addWidget(QLabel("Famille"), 0, 1)
        grid.addWidget(QLabel("Dossier"), 0, 2)

        for index in range(1, self.MAX_FAMILIES + 1):
            checkbox = QCheckBox()
            name = QLineEdit(f"Famille {index}")
            folder = QLineEdit()
            folder.setReadOnly(True)
            choose = QPushButton("Choisir…")
            choose.clicked.connect(
                lambda checked=False, field=folder: self._choose_folder(field)
            )
            grid.addWidget(checkbox, index, 0)
            grid.addWidget(name, index, 1)
            grid.addWidget(folder, index, 2)
            grid.addWidget(choose, index, 3)
            self._rows.append((checkbox, name, folder))

        layout.addLayout(grid)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _choose_folder(field):
        folder = QFileDialog.getExistingDirectory(
            field.window(), "Sélectionner le dossier de la famille", ""
        )
        if folder:
            field.setText(str(Path(folder).resolve()))

    def _accept_if_valid(self):
        selected = [row for row in self._rows if row[0].isChecked()]
        if not selected:
            QMessageBox.warning(self, "Familles", "Sélectionne au moins une famille.")
            return
        missing = [row[1].text().strip() for row in selected if not row[2].text().strip()]
        if missing:
            QMessageBox.warning(
                self, "Dossiers manquants",
                "Choisis un dossier pour chaque famille active."
            )
            return
        self.accept()

    def families(self):
        return [
            (name.text().strip() or f"Famille {index}", Path(folder.text()))
            for index, (checkbox, name, folder) in enumerate(self._rows, 1)
            if checkbox.isChecked()
        ]

class _ReceptorChoiceCardDialog(QDialog):
    """
    Boîte de dialogue compacte pour un choix à 2-3 options, sous forme
    de cartes cliquables plutôt qu'une liste déroulante native — même
    esprit visuel que les cartes Mode 1 / Mode 2 déjà présentes
    ailleurs dans l'interface. Largeur fixe et raisonnable ; la hauteur
    suit uniquement le nombre d'options, jamais un long menu étiré.
    """

    def __init__(self, title, description, options, parent=None):
        """
        options : liste de tuples (clé, titre_carte, description_carte).
        La clé de l'option cliquée est récupérée via .chosen_key().
        """

        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(440)

        self._chosen_key = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("PanelTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("SectionDescription")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        layout.addSpacing(4)

        for key, card_title, card_description in options:
            layout.addWidget(
                self._build_card(key, card_title, card_description)
            )

        layout.addSpacing(2)

        cancel_row = QHBoxLayout()
        cancel_row.addStretch()

        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        cancel_row.addWidget(cancel_button)

        layout.addLayout(cancel_row)

    def _build_card(self, key, card_title, card_description) -> QFrame:

        card = QFrame()
        card.setObjectName("ChoiceCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(
            f"""
            QFrame#ChoiceCard {{
                background: {COLORS["glass_sheen"]};
                border-width: 1px;
                border-style: solid;
                border-top-color: {COLORS["bevel_light"]};
                border-left-color: {COLORS["bevel_light"]};
                border-right-color: {COLORS["bevel_dark"]};
                border-bottom-color: {COLORS["bevel_dark"]};
                border-radius: 16px;
            }}
            QFrame#ChoiceCard:hover {{
                background: {COLORS["accent_glass"]};
                border-color: {COLORS["accent"]};
            }}
            """
        )
        apply_glass_elevation(card, blur=22, y_offset=5, alpha=35)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 13, 16, 13)
        card_layout.setSpacing(3)

        title_label = QLabel(card_title)
        title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 650; color: {COLORS['text']}; "
            "border: none; background: transparent;"
        )
        title_label.setWordWrap(True)
        card_layout.addWidget(title_label)

        if card_description:
            desc_label = QLabel(card_description)
            desc_label.setStyleSheet(
                f"font-size: 11px; color: {COLORS['text_secondary']}; "
                "border: none; background: transparent;"
            )
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

        def _on_click(_event, chosen_key=key):
            self._chosen_key = chosen_key
            self.accept()

        card.mousePressEvent = _on_click

        return card

    def chosen_key(self):
        return self._chosen_key

    @staticmethod
    def ask(parent, title, description, options):
        """
        Affiche la boîte et retourne la clé choisie, ou None si
        l'utilisateur a annulé / fermé la fenêtre.
        """

        dialog = _ReceptorChoiceCardDialog(
            title, description, options, parent=parent
        )

        if dialog.exec() != QDialog.Accepted:
            return None

        return dialog.chosen_key()


class _ReceptorPickerDialog(QDialog):
    """
    Sélecteur de récepteur groupé par bactérie (espèce), avec un cadre
    par espèce et un filtre texte en haut — remplace la liste
    déroulante plate qui mélangeait pompes, dérépresseurs et couples
    sans aucun repère visuel. À l'intérieur de chaque cadre, l'ordre
    est toujours : la pompe d'efflux, son dérépresseur, puis le
    couple (filtre à double sélectivité).
    """

    def __init__(self, groups, current_index, parent=None):
        """
        groups : liste ordonnée de tuples (species_label, entries), où
        entries est une liste de tuples
        (combo_index, kind_label, title, subtitle, is_current).
        """

        super().__init__(parent)

        self.setWindowTitle("Choisir un récepteur")
        self.setModal(True)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {COLORS["dialog_bg"]};
                border: 1px solid {COLORS["border"]};
            }}
            QLabel {{
                color: {COLORS["text"]};
            }}
            """
        )
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)

        self._chosen_index = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 16)
        outer.setSpacing(10)

        title_label = QLabel("Choisir un récepteur")
        title_label.setObjectName("PanelTitle")
        outer.addWidget(title_label)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(
            "Filtrer par bactérie ou par nom de récepteur…"
        )
        self._search_box.textChanged.connect(self._apply_filter)
        outer.addWidget(self._search_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(14)

        # (species_label, frame, [(card, texte_recherchable), ...])
        self._species_frames = []

        for species_label, entries in groups:
            frame, cards = self._build_species_frame(
                species_label, entries
            )
            content_layout.addWidget(frame)
            self._species_frames.append((species_label, frame, cards))

        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        cancel_row = QHBoxLayout()
        cancel_row.addStretch()
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        cancel_row.addWidget(cancel_button)
        outer.addLayout(cancel_row)

    def _build_species_frame(self, species_label, entries):

        frame = QFrame()
        frame.setObjectName("SpeciesFrame")
        frame.setStyleSheet(
            f"""
            QFrame#SpeciesFrame {{
                background: {COLORS["glass"]};
                border-width: 1px;
                border-style: solid;
                border-top-color: {COLORS["bevel_light"]};
                border-left-color: {COLORS["bevel_light"]};
                border-right-color: {COLORS["bevel_dark"]};
                border-bottom-color: {COLORS["bevel_dark"]};
                border-radius: 18px;
            }}
            """
        )
        apply_glass_elevation(frame, blur=28, y_offset=6, alpha=30)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 14, 16, 14)
        frame_layout.setSpacing(8)

        header = QLabel(species_label)
        header.setStyleSheet(
            f"font-size: 13px; font-weight: 700; "
            f"color: {COLORS['accent_dark']}; "
            "border: none; background: transparent;"
        )
        header.setWordWrap(True)
        frame_layout.addWidget(header)

        cards = []

        for combo_index, kind_label, title, subtitle, is_current in entries:
            card = self._build_entry_card(
                combo_index, kind_label, title, subtitle, is_current
            )
            frame_layout.addWidget(card)
            searchable = (
                f"{species_label} {kind_label} {title} {subtitle}"
            ).lower()
            cards.append((card, searchable))

        return frame, cards

    def _build_entry_card(
        self, combo_index, kind_label, title, subtitle, is_current
    ):

        card = QFrame()
        card.setObjectName("ReceptorEntryCard")
        card.setCursor(Qt.PointingHandCursor)

        border_color = COLORS["accent"] if is_current else COLORS["border"]
        bg_color = (
            COLORS["accent_glass"] if is_current else COLORS["glass"]
        )
        border_width = "1.5px" if is_current else "1px"

        card.setStyleSheet(
            f"""
            QFrame#ReceptorEntryCard {{
                background: {bg_color};
                border-width: {border_width};
                border-style: solid;
                border-top-color: {COLORS["bevel_light"]};
                border-left-color: {COLORS["bevel_light"]};
                border-right-color: {border_color if is_current else COLORS["bevel_dark"]};
                border-bottom-color: {border_color if is_current else COLORS["bevel_dark"]};
                border-radius: 14px;
            }}
            QFrame#ReceptorEntryCard:hover {{
                background: {COLORS["accent_glass_hover"]};
                border-color: {COLORS["accent"]};
            }}
            """
        )
        apply_glass_elevation(card, blur=18, y_offset=4, alpha=28)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        kind_tag = QLabel(kind_label)
        kind_tag.setFixedWidth(96)
        kind_tag.setStyleSheet(
            f"font-size: 10px; font-weight: 700; "
            f"color: {COLORS['text_secondary']}; "
            "border: none; background: transparent;"
        )
        kind_tag.setWordWrap(True)
        layout.addWidget(kind_tag)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        title_label = QLabel(("✓ " if is_current else "") + title)
        title_color = COLORS["accent_ink"] if is_current else COLORS["text"]
        title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 650; "
            f"color: {title_color}; "
            "border: none; background: transparent;"
        )
        title_label.setWordWrap(True)
        text_col.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(
                f"font-size: 11px; color: {COLORS['text_secondary']}; "
                "border: none; background: transparent;"
            )
            subtitle_label.setWordWrap(True)
            text_col.addWidget(subtitle_label)

        layout.addLayout(text_col, 1)

        def _on_click(_event, idx=combo_index):
            self._chosen_index = idx
            self.accept()

        card.mousePressEvent = _on_click

        return card

    def _apply_filter(self, text):

        needle = text.strip().lower()

        for _species_label, frame, cards in self._species_frames:
            any_visible = False
            for card, searchable in cards:
                match = (not needle) or (needle in searchable)
                card.setVisible(match)
                any_visible = any_visible or match
            frame.setVisible(any_visible)

    def chosen_index(self):
        return self._chosen_index

    @staticmethod
    def ask(parent, groups, current_index):
        dialog = _ReceptorPickerDialog(groups, current_index, parent=parent)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.chosen_index()


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
    QDoubleSpinBox,
    QSlider,
    QInputDialog,
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
    QToolBar,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QAbstractItemView,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QGraphicsDropShadowEffect,
    QStylePainter,
    QStyleOptionButton,
    QStyleOptionToolButton,
    QStyle,
    QColorDialog,
    QDialogButtonBox,
    QFormLayout,
)


# ============================================================================
# PALETTE
# ============================================================================

_PREFERENCES = QSettings("VINA Studio", "VINA Studio")
GLASS_PREFERENCES = {
    "tint": _PREFERENCES.value("glass/tint", "#6bd18d"),
    "panel_tint": _PREFERENCES.value("glass/panel_tint", "#6bd18d"),
    "button_tint": _PREFERENCES.value("glass/button_tint", "#6bd18d"),
    "text_color": _PREFERENCES.value("glass/text_color", "#edf5ff"),
    "scrollbar_tint": _PREFERENCES.value("glass/scrollbar_tint", "#6bd18d"),
    "accent_green": _PREFERENCES.value("glass/accent_green", "#3d915e"),
    "opacity": int(_PREFERENCES.value("glass/opacity", 58)),
    "panel_opacity": int(_PREFERENCES.value("glass/panel_opacity", 58)),
    "button_opacity": int(_PREFERENCES.value("glass/button_opacity", 66)),
    "scrollbar_opacity": int(_PREFERENCES.value("glass/scrollbar_opacity", 70)),
    "reflection": int(_PREFERENCES.value("glass/reflection", 72)),
    "radius": int(_PREFERENCES.value("glass/radius", 16)),
    "refraction": float(_PREFERENCES.value("glass/refraction", 1.33)),
    "theme_index": int(_PREFERENCES.value("theme/index", 0)),
}


# ============================================================================
# SCHEMA DES REGLAGES D'APPARENCE  —  UNE SEULE SOURCE DE VERITE
# ----------------------------------------------------------------------------
# Tout ce qui est modifiable depuis « Paramètres » est déclaré ICI : clé,
# libellé, type, valeur par défaut, onglet du dialogue. Le dialogue est généré
# automatiquement depuis cette liste. Pour rendre un nouvel élément réglable :
#   1) ajouter une ligne dans _THEME_SCHEMA ;
#   2) lire GLASS_PREFERENCES["ma_cle"] là où l'élément est dessiné
#      (feuille de style ou paintEvent).
# Les valeurs par défaut reproduisent l'apparence d'origine du logiciel.
# ============================================================================

def _spec(key, label, kind, default, group, lo=0, hi=100, auto=False):
    return {
        "key": key, "label": label, "kind": kind, "default": default,
        "group": group, "lo": lo, "hi": hi, "auto": auto,
    }


_G_MAT = "Matériau"
_G_TXT = "Style du texte"
_G_TAB = "Onglets"
_G_BTN = "Boutons"
_G_POP = "Menus et flou"
_G_DARK = "Zones sombres"

_THEME_SCHEMA = [
    _spec("tint", "Couleur d'accent générale", "color", "#6bd18d", _G_MAT),
    _spec("panel_tint", "Couleur des panneaux", "color", "#6bd18d", _G_MAT),
    _spec("scrollbar_tint", "Couleur du défilement", "color", "#6bd18d", _G_MAT),
    _spec("accent_green", "Cases, curseurs, barre d'état", "color", "#3d915e", _G_MAT),
    _spec("panel_opacity", "Transparence des panneaux", "int", 58, _G_MAT, 10, 95),
    _spec("opacity", "Transparence générale du verre", "int", 58, _G_MAT, 10, 95),
    _spec("scrollbar_opacity", "Transparence du défilement", "int", 70, _G_MAT, 10, 95),
    _spec("reflection", "Réflexion de lumière", "int", 72, _G_MAT, 10, 100),
    _spec("radius", "Rayon des bords (panneaux)", "int", 16, _G_MAT, 6, 36),
    _spec("refraction", "Indice de réfraction", "float", 1.33, _G_MAT, 1.0, 2.5),
    _spec("bg_veil_color", "Voile sur l'image de fond", "color", "#070f18", _G_MAT),
    _spec("bg_veil_opacity", "Opacité du voile de fond", "int", 70, _G_MAT, 0, 100),
    _spec("font_family", "Police de l'interface", "font", "Noto Sans", _G_TXT),
    _spec("font_size", "Taille du texte (px)", "int", 13, _G_TXT, 9, 24),
    _spec("title_size", "Taille des titres (px)", "int", 17, _G_TXT, 12, 36),
    _spec("text_color", "Texte principal", "color", "#edf5ff", _G_TXT),
    _spec("text_secondary_color", "Texte secondaire (descriptions)", "color", "#bfd3e6", _G_TXT),
    _spec("text_muted_color", "Texte discret (étiquettes)", "color", "#8ea8bc", _G_TXT),
    _spec("title_color", "Titres", "color", "", _G_TXT, auto=True),
    _spec("accent_text", "Texte accentué (cible active, statuts)", "color", "", _G_TXT, auto=True),
    _spec("success_color", "Message : succès", "color", "#5fd3a1", _G_TXT),
    _spec("warning_color", "Message : avertissement", "color", "#f4c66b", _G_TXT),
    _spec("danger_color", "Message : erreur", "color", "#ff8a8a", _G_TXT),
    _spec("status_text_color", "Texte de la barre d'état", "color", "#dfffea", _G_TXT),
    _spec("tab_tint", "Couleur des onglets", "color", "#6bd18d", _G_TAB),
    _spec("tab_hover_tint", "Couleur au survol", "color", "", _G_TAB, auto=True),
    _spec("tab_active_tint", "Couleur de l'onglet actif", "color", "#51c981", _G_TAB),
    _spec("tab_opacity", "Transparence des onglets", "int", 66, _G_TAB, 10, 100),
    _spec("tab_hover_opacity", "Intensité au survol", "int", 28, _G_TAB, 0, 100),
    _spec("tab_active_opacity", "Intensité de l'onglet actif", "int", 23, _G_TAB, 0, 100),
    _spec("tab_text_color", "Texte des onglets", "color", "", _G_TAB, auto=True),
    _spec("tab_text_hover_color", "Texte au survol", "color", "", _G_TAB, auto=True),
    _spec("tab_text_active_color", "Texte de l'onglet actif", "color", "", _G_TAB, auto=True),
    _spec("tab_border_color", "Liseré des onglets", "color", "#ffffff", _G_TAB),
    _spec("tab_border_opacity", "Opacité du liseré", "int", 71, _G_TAB, 0, 100),
    _spec("tab_radius", "Rayon des onglets", "int", 12, _G_TAB, 2, 26),
    _spec("tab_shimmer", "Reflet animé au survol", "bool", True, _G_TAB),
    _spec("button_tint", "Couleur des boutons", "color", "#6bd18d", _G_BTN),
    _spec("button_hover_tint", "Couleur au survol", "color", "", _G_BTN, auto=True),
    _spec("button_pressed_tint", "Couleur au clic", "color", "#51c981", _G_BTN),
    _spec("button_opacity", "Transparence des boutons", "int", 66, _G_BTN, 10, 100),
    _spec("button_hover_opacity", "Intensité au survol", "int", 28, _G_BTN, 0, 100),
    _spec("button_pressed_opacity", "Intensité au clic", "int", 23, _G_BTN, 0, 100),
    _spec("button_text_color", "Texte des boutons", "color", "", _G_BTN, auto=True),
    _spec("button_text_hover_color", "Texte au survol", "color", "", _G_BTN, auto=True),
    _spec("button_border_color", "Liseré des boutons", "color", "#ffffff", _G_BTN),
    _spec("button_border_opacity", "Opacité du liseré", "int", 74, _G_BTN, 0, 100),
    _spec("button_radius", "Rayon des boutons", "int", 12, _G_BTN, 2, 26),
    _spec("button_shimmer", "Reflet animé au survol", "bool", True, _G_BTN),
    _spec("popup_blur", "Flou de l'arrière-plan (0 = aucun)", "int", 22, _G_POP, 0, 60),
    _spec("popup_tint", "Teinte du verre", "color", "#0f1c2a", _G_POP),
    _spec("popup_opacity", "Opacité de la teinte", "int", 55, _G_POP, 0, 100),
    _spec("popup_reflection", "Reflet supérieur", "int", 30, _G_POP, 0, 100),
    _spec("popup_radius", "Rayon des coins", "int", 14, _G_POP, 0, 28),
    _spec("popup_border_color", "Couleur du liseré", "color", "#dcffe7", _G_POP),
    _spec("popup_border_opacity", "Opacité du liseré", "int", 40, _G_POP, 0, 100),
    _spec("popup_text_color", "Texte des menus", "color", "", _G_POP, auto=True),
    _spec("popup_hover_tint", "Couleur de l'élément survolé", "color", "", _G_POP, auto=True),
    _spec("popup_hover_opacity", "Intensité de l'élément survolé", "int", 45, _G_POP, 0, 100),
    _spec("popup_hover_text_color", "Texte de l'élément survolé", "color", "", _G_POP, auto=True),
    _spec("popup_tooltips", "Appliquer aussi aux info-bulles", "bool", True, _G_POP),
    _spec("base_color", "Fond de base (visible sous les zones transparentes)", "color", "#0f1c2a", _G_DARK),
    _spec("window_color", "Fond de la fenêtre principale", "color", "#0f1721", _G_DARK),
    _spec("field_color", "Champs des fenêtres (saisie, listes, compteurs)", "color", "#0f1c2a", _G_DARK),
    _spec("field_opacity", "Opacité des champs (0 = invisible)", "int", 100, _G_DARK, 0, 100),
    _spec("dialog_color", "Fond des boîtes de dialogue", "color", "", _G_DARK, auto=True),
    _spec("dialog_opacity", "Opacité des dialogues (si couleur choisie)", "int", 100, _G_DARK, 0, 100),
    _spec("card_color", "Cartes et cadres de verre (choix, navigation)", "color", "#111c26", _G_DARK),
    _spec("card_opacity", "Opacité des cartes et cadres (0 = invisible)", "int", 63, _G_DARK, 0, 100),
    _spec("header_color", "En-têtes de tableau", "color", "", _G_DARK, auto=True),
    _spec("header_opacity", "Opacité des en-têtes (si couleur choisie)", "int", 85, _G_DARK, 0, 100),
    _spec("header_text_color", "Texte des en-têtes de tableau", "color", "", _G_DARK, auto=True),
    _spec("viewer_color", "Cadre du visualiseur 3D", "color", "#0b1219", _G_DARK),
]

_THEME_DEFAULTS = {spec["key"]: spec["default"] for spec in _THEME_SCHEMA}


def _coerce_pref(spec, raw):
    """QSettings rend souvent des chaînes : on remet chaque valeur au bon type."""
    kind = spec["kind"]
    try:
        if kind == "int":
            return max(spec["lo"], min(spec["hi"], int(float(raw))))
        if kind == "float":
            return float(raw)
        if kind == "bool":
            if isinstance(raw, str):
                return raw.strip().lower() in ("1", "true", "yes", "on")
            return bool(raw)
        return str(raw)
    except (TypeError, ValueError):
        return spec["default"]


for _item in _THEME_SCHEMA:
    if _item["key"] not in GLASS_PREFERENCES:
        GLASS_PREFERENCES[_item["key"]] = _coerce_pref(
            _item, _PREFERENCES.value(f"glass/{_item['key']}", _item["default"])
        )



# ============================================================================
# MOTEUR D'APPARENCE
# Préférences -> couleurs partagées (COLORS) -> feuille de style -> popups floutés
# ============================================================================

import re as _re
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QMenu,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsBlurEffect,
    QFontComboBox,
    QAbstractButton,
    QGroupBox,
    QTabBar,
)

# Jetons de couleur de texte que les feuilles de style « en ligne » (posées
# widget par widget dans le code) reprennent : on les suit pour les mettre à
# jour en direct quand l'utilisateur change une couleur.
_TEXT_TOKENS = (
    "text", "text_secondary", "text_muted",
    "accent_dark", "accent_ink", "success", "warning", "danger",
    "panel", "surface", "surface_alt", "window", "window_gradient",
    "glass", "glass_soft", "glass_strong", "glass_sheen", "viewer", "dialog_bg",
)
_TOKEN_SEEN = {}
_PALETTE_STATE = {"last": None}
_DEBUG_ONCE = set()


def _debug_once(tag, exc):
    if tag in _DEBUG_ONCE:
        return
    _DEBUG_ONCE.add(tag)
    print(f"[apparence] {tag} : {exc!r}")


def _pct_alpha(pct):
    """Pourcentage 0-100 -> alpha Qt 0-255."""
    try:
        return max(0, min(255, int(round(float(pct) * 255.0 / 100.0))))
    except (TypeError, ValueError):
        return 0


def _rgba(color, alpha):
    return (
        f"rgba({color.red()}, {color.green()}, {color.blue()}, "
        f"{max(0, min(255, int(alpha)))})"
    )


# Réglages « Auto » : dérivés d'une autre couleur tant que l'utilisateur n'a
# pas choisi la sienne.
_THEME_AUTO = {
    "title_color": lambda: _theme_color("text_color"),
    "accent_text": lambda: _theme_color("tint").lighter(175),
    "tab_hover_tint": lambda: _theme_color("tab_tint").lighter(130),
    "tab_text_color": lambda: _theme_color("text_color"),
    "tab_text_hover_color": lambda: _theme_color("text_color"),
    "tab_text_active_color": lambda: _theme_color("tab_tint"),
    "button_hover_tint": lambda: _theme_color("button_tint").lighter(130),
    "button_text_color": lambda: _theme_color("text_color"),
    "button_text_hover_color": lambda: _theme_color("text_color"),
    "popup_text_color": lambda: _theme_color("text_color"),
    "popup_hover_tint": lambda: _theme_color("button_tint"),
    "popup_hover_text_color": lambda: _theme_color("text_color"),
    "dialog_color": lambda: _theme_color("panel_tint"),
    "header_color": lambda: _theme_color("button_tint"),
    "header_text_color": lambda: _theme_color("text_color"),
}


def _theme_color(key, fallback="#6bd18d"):
    """Couleur valide pour `key` (résout « Auto » et les valeurs invalides)."""
    raw = str(GLASS_PREFERENCES.get(key, "") or "").strip()
    color = QColor(raw) if raw else QColor()
    if color.isValid():
        return color
    auto = _THEME_AUTO.get(key)
    if auto is not None:
        return auto()
    default = QColor(str(_THEME_DEFAULTS.get(key) or ""))
    return default if default.isValid() else QColor(fallback)


def _overlay(color_key, pct_key):
    """Couleur `color_key` avec l'opacité (en %) donnée par `pct_key`."""
    color = _theme_color(color_key)
    color.setAlpha(_pct_alpha(GLASS_PREFERENCES.get(pct_key, 0)))
    return color


def _preference_color(key, fallback="#6bd18d"):
    return _theme_color(key, fallback)


def _remember_tokens():
    for key in _TEXT_TOKENS:
        _TOKEN_SEEN.setdefault(key, set()).add(str(COLORS[key]).lower())


def _clamp255(value):
    return max(0, min(255, int(value)))


def _dark_tokens(base, window, card, card_alpha):
    """
    Jetons sombres de COLORS déduits des réglages « Zones sombres ».
    base / window / card : tuples (r, g, b) ; card_alpha : 0-255.
    Avec les réglages par défaut, le résultat est IDENTIQUE aux anciennes
    constantes écrites en dur (l'apparence d'origine ne change pas).
    """
    def hexa(c, dr=0, dg=0, db=0):
        return "#%02x%02x%02x" % (
            _clamp255(c[0] + dr), _clamp255(c[1] + dg), _clamp255(c[2] + db)
        )

    def rgba(c, dr, dg, db, da):
        return "rgba(%d, %d, %d, %d)" % (
            _clamp255(c[0] + dr), _clamp255(c[1] + dg), _clamp255(c[2] + db),
            _clamp255(card_alpha + da),
        )

    return {
        "panel": hexa(base),
        "surface": hexa(base, 1, 1, 1),
        "surface_alt": hexa(base, 6, 11, 15),
        "window": hexa(window),
        "window_gradient": (
            "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 %s, stop:0.42 %s, stop:1 %s)"
            % (hexa(window, 2, 6, 9), hexa(window, 8, 19, 23), hexa(window, -2, 0, 0))
        ),
        "glass": rgba(card, 0, 0, 0, 0),
        "glass_soft": rgba(card, 2, 4, 6, 10),
        "glass_strong": rgba(card, 6, 7, 10, 22),
        "glass_sheen": (
            "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 %s, stop:0.5 %s, stop:1 %s)"
            % (rgba(card, 12, 15, 21, 50), rgba(card, 5, 6, 9, 25), rgba(card, -2, -4, -4, 15))
        ),
    }


def _refresh_preference_palette():
    """Synchronise les jetons partagés (COLORS) avec les préférences."""
    tint = QColor(str(GLASS_PREFERENCES["tint"]))
    if not tint.isValid():
        tint = QColor("#6bd18d")
        GLASS_PREFERENCES["tint"] = tint.name()
    COLORS["accent"] = tint.name()

    custom = str(GLASS_PREFERENCES.get("accent_text", "") or "").strip()
    if custom and QColor(custom).isValid():
        COLORS["accent_dark"] = QColor(custom).name()
        COLORS["accent_ink"] = QColor(custom).name()
    else:
        COLORS["accent_dark"] = tint.lighter(175).name()
        COLORS["accent_ink"] = tint.lighter(185).name()
    COLORS["accent_light"] = (
        f"rgba({tint.red()}, {tint.green()}, {tint.blue()}, 52)"
    )
    COLORS["accent_glass"] = (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(245, 255, 248, 190), "
        f"stop:0.4 rgba({tint.red()}, {tint.green()}, {tint.blue()}, 175), "
        f"stop:1 rgba({max(0, tint.red() // 2)}, "
        f"{max(0, tint.green() // 2)}, {max(0, tint.blue() // 2)}, 190))"
    )
    COLORS["accent_glass_hover"] = COLORS["accent_glass"]
    COLORS["accent_glass_pressed"] = COLORS["accent_glass"]

    green = QColor(str(GLASS_PREFERENCES["accent_green"]))
    if GLASS_PREFERENCES["accent_green"] == "#3d915e":
        green = QColor(str(GLASS_PREFERENCES["scrollbar_tint"]))
    if not green.isValid():
        green = QColor("#3d915e")

    COLORS["accent_green"] = (
        f"rgba({green.red()}, {green.green()}, {green.blue()}, 170)"
    )
    def _up(v, d):
        return max(0, min(255, v + d))
    COLORS["grad_stop0"] = f"rgba({_up(green.red(), 40)}, {_up(green.green(), 40)}, {_up(green.blue(), 40)}, 220)"
    COLORS["grad_stop1"] = f"rgba({green.red()}, {green.green()}, {green.blue()}, 180)"
    COLORS["grad_stop2"] = f"rgba({_up(green.red(), -30)}, {_up(green.green(), -30)}, {_up(green.blue(), -30)}, 150)"

    COLORS["text"] = _theme_color("text_color").name()
    COLORS["text_secondary"] = _theme_color("text_secondary_color").name()
    COLORS["text_muted"] = _theme_color("text_muted_color").name()
    COLORS["success"] = _theme_color("success_color").name()
    COLORS["warning"] = _theme_color("warning_color").name()
    COLORS["danger"] = _theme_color("danger_color").name()

    # Zones sombres : fond de base, fenêtre, cartes, visualiseur, dialogues.
    _P = GLASS_PREFERENCES
    _base = _theme_color("base_color", "#0f1c2a")
    _win = _theme_color("window_color", "#0f1721")
    _card = _theme_color("card_color", "#111c26")
    try:
        _card_alpha = int(float(_P.get("card_opacity", 63)) * 2.55)
    except (TypeError, ValueError):
        _card_alpha = 160
    COLORS.update(_dark_tokens(
        (_base.red(), _base.green(), _base.blue()),
        (_win.red(), _win.green(), _win.blue()),
        (_card.red(), _card.green(), _card.blue()),
        _card_alpha,
    ))
    COLORS["viewer"] = _theme_color("viewer_color", "#0b1219").name()
    _dlg = str(_P.get("dialog_color", "") or "").strip()
    if _dlg and QColor(_dlg).isValid():
        COLORS["dialog_bg"] = _rgba(QColor(_dlg), _pct_alpha(_P.get("dialog_opacity", 100)))
    else:
        COLORS["dialog_bg"] = _rgba(_base, 255)
    _remember_tokens()


def _tab_text_qss():
    """Texte des onglets à boutons (barre du haut, navigation latérale)."""
    normal = _theme_color("tab_text_color").name()
    hover = _theme_color("tab_text_hover_color").name()
    active = _theme_color("tab_text_active_color").name()
    names = ("TopTab", "SecondaryTab", "PrimaryNavigation")
    sel = lambda suffix: ", ".join(f"QToolButton#{n}{suffix}" for n in names)
    return f"""
    {sel("")} {{ color: {normal}; }}
    {sel(":hover")} {{ color: {hover}; }}
    {sel(":checked")} {{ color: {active}; }}
    {sel(":checked:hover")} {{ color: {active}; }}
    """


def _tab_bar_qss():
    """Onglets de type QTabBar (résultats d'analyse, dialogues…)."""
    P = GLASS_PREFERENCES
    panel = _theme_color("panel_tint")
    tab = _theme_color("tab_tint")
    hov = _theme_color("tab_hover_tint")
    act = _theme_color("tab_active_tint")
    border = _theme_color("tab_border_color")
    base_a = int(P["tab_opacity"])
    hover_a = min(255, base_a + _pct_alpha(P["tab_hover_opacity"]))
    active_a = min(255, base_a + _pct_alpha(P["tab_active_opacity"]))
    radius = int(P["tab_radius"])
    return f"""
    QTabWidget::pane {{
        background: {_rgba(panel, P['panel_opacity'])};
        border: 1px solid rgba(230, 255, 238, 145);
        border-radius: 16px;
    }}
    QTabBar::tab {{
        background: {_rgba(tab, base_a)};
        color: {_theme_color("tab_text_color").name()};
        border: 1px solid {_rgba(border, _pct_alpha(P['tab_border_opacity']))};
        border-bottom: none;
        padding: 9px 18px;
        margin-right: 4px;
        border-top-left-radius: {radius}px;
        border-top-right-radius: {radius}px;
    }}
    QTabBar::tab:hover {{
        background: {_rgba(hov, hover_a)};
        color: {_theme_color("tab_text_hover_color").name()};
    }}
    QTabBar::tab:selected {{
        background: {_rgba(act, active_a)};
        color: {_theme_color("tab_text_active_color").name()};
        border-bottom: 2px solid {act.name()};
    }}
    QTabBar::tab:selected:hover {{
        background: {_rgba(act, min(255, active_a + 22))};
        color: {_theme_color("tab_text_active_color").name()};
    }}
    """


def _popup_qss():
    """Menus contextuels, listes déroulantes, info-bulles : un seul thème."""
    P = GLASS_PREFERENCES
    tint = _rgba(_theme_color("popup_tint"), _pct_alpha(P["popup_opacity"]))
    border = _rgba(
        _theme_color("popup_border_color"), _pct_alpha(P["popup_border_opacity"])
    )
    text = _theme_color("popup_text_color")
    hover = _rgba(
        _theme_color("popup_hover_tint"), _pct_alpha(P["popup_hover_opacity"])
    )
    hover_text = _theme_color("popup_hover_text_color").name()
    radius = int(P["popup_radius"])
    item_radius = max(3, radius - 4)
    return f"""
    QMenu {{
        background: {tint};
        color: {text.name()};
        border: 1px solid {border};
        border-radius: {radius}px;
        padding: 8px;
        background-image: none;
    }}
    QMenu::item {{
        padding: 8px 28px 8px 14px;
        border-radius: {item_radius}px;
        margin: 1px 2px;
        color: {text.name()};
        background: transparent;
    }}
    QMenu::item:selected {{
        background: {hover};
        color: {hover_text};
    }}
    QMenu::item:disabled {{
        color: {_rgba(text, 110)};
        background: transparent;
    }}
    QMenu::separator {{
        height: 1px;
        background: {border};
        margin: 6px 8px;
    }}
    QComboBoxPrivateContainer {{
        background: {tint};
        border: 1px solid {border};
        border-radius: {radius}px;
        padding: 4px;
    }}
    QComboBox QAbstractItemView {{
        background: transparent;
        color: {text.name()};
        border: none;
        outline: none;
        padding: 0px;
        selection-background-color: transparent;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 7px 10px;
        border-radius: {item_radius}px;
        color: {text.name()};
        background: transparent;
    }}
    QComboBox QAbstractItemView::item:selected,
    QComboBox QAbstractItemView::item:hover {{
        background: {hover};
        color: {hover_text};
    }}
    QToolTip {{
        background: {tint};
        color: {text.name()};
        border: 1px solid {border};
        border-radius: {item_radius}px;
        padding: 6px 10px;
    }}
    """


def _runtime_preferences_style():
    """Feuille de style dérivée des préférences (appliquée APRÈS le style de base)."""
    P = GLASS_PREFERENCES
    panel = _theme_color("panel_tint")
    button = _theme_color("button_tint")
    text = _theme_color("text_color")
    title = _theme_color("title_color")
    scroll = _theme_color("scrollbar_tint")
    panel_a = int(P["panel_opacity"])
    button_a = int(P["button_opacity"])

    size = int(P["font_size"])
    ratio = size / 13.0
    title_px = int(P["title_size"])
    family = str(P["font_family"]).replace('"', "").replace("\\", "")

    btn_border = _rgba(_theme_color("button_border_color"), _pct_alpha(P["button_border_opacity"]))
    btn_hover = _rgba(
        _theme_color("button_hover_tint"),
        min(255, button_a + _pct_alpha(P["button_hover_opacity"])),
    )
    btn_pressed = _rgba(
        _theme_color("button_pressed_tint"),
        min(255, button_a + _pct_alpha(P["button_pressed_opacity"])),
    )
    btn_text = _theme_color("button_text_color").name()
    btn_text_hover = _theme_color("button_text_hover_color").name()

    # --- Zones sombres : champs des fenêtres, dialogues, en-têtes de tableau ---
    _field = QColor(str(P.get("field_color") or "#0f1c2a"))
    if not _field.isValid():
        _field = QColor("#0f1c2a")
    _field_bg = _rgba(_field, _pct_alpha(P.get("field_opacity", 100)))
    dark_qss = f"""
    QDialog QLineEdit, QDialog QComboBox, QDialog QSpinBox, QDialog QDoubleSpinBox,
    QDialog QLineEdit:focus, QDialog QComboBox:focus,
    QDialog QSpinBox:focus, QDialog QDoubleSpinBox:focus {{
        color: {text.name()};
        background: {_field_bg};
    }}
    QHeaderView::section {{
        color: {_theme_color("header_text_color").name()};
    }}
    """
    _dlg_raw = str(P.get("dialog_color", "") or "").strip()
    if _dlg_raw and QColor(_dlg_raw).isValid():
        dark_qss += f"""
    QDialog {{
        background: {COLORS["dialog_bg"]};
        border: 1px solid rgba(230, 255, 238, 175);
    }}
    """
    _hdr_raw = str(P.get("header_color", "") or "").strip()
    if _hdr_raw and QColor(_hdr_raw).isValid():
        dark_qss += f"""
    QHeaderView::section {{
        background: {_rgba(QColor(_hdr_raw), _pct_alpha(P.get("header_opacity", 85)))};
    }}
    """

    return f"""
    QWidget {{
        font-family: "{family}", "Noto Sans", "Segoe UI", sans-serif;
        font-size: {size}px;
        color: {text.name()};
    }}
    QLabel#ApplicationName {{ font-size: {title_px + 2}px; color: {title.name()}; }}
    QLabel#SectionTitle {{ font-size: {title_px}px; color: {title.name()}; }}
    QLabel#PanelTitle {{ font-size: {size}px; color: {title.name()}; }}
    QLabel#ApplicationSubtitle {{
        font-size: {max(7, round(11 * ratio))}px; color: {COLORS['text_secondary']};
    }}
    QLabel#SectionDescription {{
        font-size: {max(7, round(12 * ratio))}px; color: {COLORS['text_secondary']};
    }}
    QStatusBar {{ color: {_theme_color("status_text_color").name()}; }}

    QFrame#ContentPanel, QFrame#ToolbarPanel, QFrame#TopHeader {{
        background: {_rgba(panel, panel_a)};
        border-color: rgba(235, 255, 242, 150);
    }}
    QPushButton, QToolButton {{
        color: {btn_text};
        background: {_rgba(button, button_a)};
        border: 1px solid {btn_border};
    }}
    QPushButton:hover, QToolButton:hover {{
        color: {btn_text_hover};
        background: {btn_hover};
    }}
    QPushButton:pressed, QToolButton:pressed {{
        background: {btn_pressed};
    }}
    QPushButton[liquid_glass="true"], QToolButton[liquid_glass="true"],
    QPushButton[liquid_glass="true"]:hover, QToolButton[liquid_glass="true"]:hover,
    QPushButton[liquid_glass="true"]:pressed, QToolButton[liquid_glass="true"]:pressed {{
        background: transparent;
        border: none;
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        color: {text.name()};
        background: {_rgba(panel, panel_a)};
        border-color: rgba(230, 255, 238, 175);
    }}
    QTableWidget {{
        color: {text.name()};
        background: {_rgba(panel, panel_a)};
        border-color: rgba(230, 255, 238, 145);
    }}
    QDialog {{
        color: {text.name()};
        background: {_rgba(panel, panel_a + 120)};
        border: 1px solid rgba(230, 255, 238, 175);
    }}
    QHeaderView::section {{
        color: {text.name()};
        background: {_rgba(button, button_a)};
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {_rgba(scroll, P['scrollbar_opacity'])};
        border: 1px solid rgba(230, 255, 238, 165);
    }}
    QProgressBar {{
        color: {text.name()};
        background: {_rgba(panel, panel_a)};
    }}
    """ + dark_qss + _tab_text_qss() + _tab_bar_qss() + _popup_qss()


def _runtime_results_tab_style():
    """Conservé pour compatibilité : le style des onglets est désormais global."""
    return _tab_bar_qss()


# ---------------------------------------------------------------------------
# Feuilles de style « en ligne » : elles sont posées widget par widget dans le
# code (labels de statut, cartes…). On les réécrit à partir de leur version
# d'origine pour qu'elles suivent la taille et les couleurs de texte choisies.
# ---------------------------------------------------------------------------

def _inline_color_map():
    owners = {}
    for key, values in _TOKEN_SEEN.items():
        for value in values:
            owners.setdefault(value, set()).add(key)
    mapping = {}
    for key, values in _TOKEN_SEEN.items():
        current = str(COLORS[key]).lower()
        for value in values:
            if value != current and len(owners[value]) == 1:
                mapping[value] = current
    return mapping


def _rewrite_inline(css, mapping, ratio):
    if mapping:
        pattern = _re.compile("|".join(_re.escape(k) for k in mapping), _re.IGNORECASE)
        css = pattern.sub(lambda m: mapping[m.group(0).lower()], css)
    return _re.sub(
        r"font-size:\s*(\d+)px",
        lambda m: f"font-size: {max(7, int(round(int(m.group(1)) * ratio)))}px",
        css,
    )


def _restyle_widget(widget, mapping=None, ratio=None):
    try:
        current = widget.styleSheet()
        if not current or isinstance(widget, QTabWidget):
            return
        if mapping is None:
            mapping = _inline_color_map()
        if ratio is None:
            ratio = int(GLASS_PREFERENCES["font_size"]) / 13.0
        if current != widget.property("_ss_last"):
            widget.setProperty("_ss_orig", current)   # nouvelle version posée par le code
        original = widget.property("_ss_orig") or current
        updated = _rewrite_inline(original, mapping, ratio)
        if updated != current:
            widget.setStyleSheet(updated)
        widget.setProperty("_ss_last", updated)
    except Exception as exc:
        _debug_once("restyle", exc)


def _apply_app_palette(app):
    state = (
        COLORS["text"], COLORS["text_muted"], COLORS["window"],
        COLORS["panel"], COLORS["surface"], COLORS["surface_alt"],
    )
    if _PALETTE_STATE["last"] == state:
        return
    _PALETTE_STATE["last"] = state
    palette = app.palette()
    text = QColor(COLORS["text"])
    muted = QColor(COLORS["text_muted"])
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(role, text)
        palette.setColor(QPalette.Disabled, role, muted)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.PlaceholderText, muted)
    palette.setColor(QPalette.Window, QColor(COLORS["window"]))
    palette.setColor(QPalette.Base, QColor(COLORS["panel"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["panel"]))
    app.setPalette(palette)


def apply_runtime_preferences():
    """Reconstruit la feuille de style vivante : tous les widgets suivent."""
    _refresh_preference_palette()
    app = QApplication.instance()
    if app is None:
        return
    _apply_app_palette(app)
    app.setStyleSheet(_build_app_style() + _runtime_preferences_style())
    mapping = _inline_color_map()
    ratio = int(GLASS_PREFERENCES["font_size"]) / 13.0
    for widget in app.allWidgets():
        _restyle_widget(widget, mapping, ratio)
    apply_text_overrides()


# ---------------------------------------------------------------------------
# Popups (menus contextuels, listes déroulantes, info-bulles) : vrai flou.
# Qt Widgets n'a pas de « backdrop-filter » : on photographie ce qui se trouve
# réellement derrière le popup, on le floute (rayon réglable) et on le peint
# SOUS la teinte translucide du popup.
# ---------------------------------------------------------------------------

class _PopupBackdrop(QObject):
    """Peint, sous un popup, l'arrière-plan réellement flouté."""

    def __init__(self, popup):
        super().__init__(popup)
        self.setObjectName("GlassPopupBackdrop")
        self._pixmap = None
        self._stamp = None
        popup.installEventFilter(self)

    def invalidate(self):
        self._pixmap = None
        self._stamp = None

    @staticmethod
    def _source_window(popup, point):
        candidates = []
        parent = popup.parentWidget()
        if parent is not None:
            candidates.append(parent.window())
        active = QApplication.activeWindow()
        if active is not None:
            candidates.append(active)
        candidates.extend(QApplication.topLevelWidgets())
        for widget in candidates:
            if widget is None or widget is popup or not widget.isVisible():
                continue
            if widget.windowType() in (Qt.Popup, Qt.ToolTip):
                continue
            if widget.frameGeometry().contains(point):
                return widget
        return None

    @staticmethod
    def _over_native_surface(source, local_point):
        """Vue web / OpenGL : on ne peut pas la photographier -> pas de flou."""
        widget = source.childAt(local_point)
        while widget is not None:
            name = widget.metaObject().className()
            if "WebEngine" in name or "QQuick" in name:
                return True
            widget = widget.parentWidget()
        return False

    @staticmethod
    def _blur(image, radius):
        dpr = image.devicePixelRatio() or 1.0
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap.fromImage(image))
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(float(radius))
        effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.setDevicePixelRatio(dpr)
        result.fill(Qt.transparent)
        logical = QRectF(0, 0, image.width() / dpr, image.height() / dpr)
        painter = QPainter(result)
        scene.render(painter, logical, logical)
        painter.end()
        return result

    def _capture(self, popup):
        P = GLASS_PREFERENCES
        blur = int(P.get("popup_blur", 0))
        size = popup.size()
        if blur <= 0 or size.width() < 4 or size.height() < 4:
            return None
        dpr = popup.devicePixelRatioF()
        origin = popup.mapToGlobal(QPoint(0, 0))
        popup_rect = QRect(origin, size)
        source = self._source_window(popup, popup_rect.center())
        if source is None:
            return None
        source_origin = source.mapToGlobal(QPoint(0, 0))
        if self._over_native_surface(source, popup_rect.center() - source_origin):
            return None

        pad = int(blur * 2) + 2
        wanted = popup_rect.adjusted(-pad, -pad, pad, pad)
        local = wanted.translated(-source_origin)
        visible = local.intersected(source.rect())
        if visible.isEmpty():
            return None
        grabbed = source.grab(visible)

        canvas = QImage(
            max(1, int(round(wanted.width() * dpr))),
            max(1, int(round(wanted.height() * dpr))),
            QImage.Format_ARGB32_Premultiplied,
        )
        canvas.setDevicePixelRatio(dpr)
        canvas.fill(_theme_color("popup_tint"))
        painter = QPainter(canvas)
        painter.drawPixmap(visible.topLeft() - local.topLeft(), grabbed)
        painter.end()

        blurred = self._blur(canvas, blur)
        crop = QRect(
            int(round(pad * dpr)), int(round(pad * dpr)),
            int(round(size.width() * dpr)), int(round(size.height() * dpr)),
        )
        cropped = blurred.copy(crop)
        cropped.setDevicePixelRatio(dpr)

        final = QImage(cropped.size(), QImage.Format_ARGB32_Premultiplied)
        final.setDevicePixelRatio(dpr)
        final.fill(Qt.transparent)
        painter = QPainter(final)
        painter.setRenderHint(QPainter.Antialiasing)
        radius = float(P.get("popup_radius", 14))
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, size.width(), size.height()), radius, radius)
        painter.setClipPath(path)
        painter.drawImage(0, 0, cropped)
        shine = int(P.get("popup_reflection", 0))
        if shine > 0:
            height = size.height() * 0.55
            gradient = QLinearGradient(0, 0, 0, height)
            gradient.setColorAt(0.0, QColor(255, 255, 255, _pct_alpha(shine * 0.6)))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(QRectF(0, 0, size.width(), height), gradient)
        painter.end()
        return QPixmap.fromImage(final)

    def _paint_under(self, popup):
        origin = popup.mapToGlobal(QPoint(0, 0))
        P = GLASS_PREFERENCES
        stamp = (
            popup.width(), popup.height(), origin.x(), origin.y(),
            P.get("popup_blur"), P.get("popup_radius"), P.get("popup_reflection"),
            P.get("popup_tint"),
        )
        if stamp != self._stamp:
            self._stamp = stamp
            self._pixmap = self._capture(popup)
        if self._pixmap is not None and not self._pixmap.isNull():
            painter = QPainter(popup)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.end()

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind == QEvent.Paint:
            obj.event(event)          # le popup se peint d'abord : teinte, liseré, texte
            try:
                self._paint_under(obj)   # puis le flou est glissé DESSOUS
            except Exception as exc:
                _debug_once("flou popup", exc)
            return True
        if kind in (QEvent.Show, QEvent.Move, QEvent.Resize, QEvent.Hide):
            self.invalidate()
        return False


class GlassPopupManager(QObject):
    """Filtre d'application : rend translucides et floute les popups Qt."""

    def __init__(self, app):
        super().__init__(app)
        # PAS de app.installEventFilter(self) : un filtre global plante
        # PySide6 6.11 + QtWebEngine (segfault). Le role est tenu par
        # _GlassProxyStyle.polish() (widgets uniquement, thread principal).

    @staticmethod
    def _kind(obj):
        try:
            if not obj.isWidgetType():
                return None
            name = obj.metaObject().className()
        except Exception:
            return None
        if name == "QComboBoxPrivateContainer":
            return "combo"
        if name == "QTipLabel":
            return "tip"
        if isinstance(obj, QMenu):
            return "menu"
        return None

    @staticmethod
    def _prepare(popup, kind):
        if kind == "tip" and not GLASS_PREFERENCES.get("popup_tooltips", True):
            return
        if popup.property("_glass_prepared"):
            return
        popup.setProperty("_glass_prepared", True)
        popup.setWindowFlags(
            popup.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        popup.setAttribute(Qt.WA_TranslucentBackground, True)
        if kind == "combo":
            for view in popup.findChildren(QAbstractItemView):
                view.setFrameShape(QFrame.NoFrame)
                view.viewport().setAutoFillBackground(False)
        _PopupBackdrop(popup)

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype == QEvent.Show:
            try:
                if _TEXT_OVERRIDES and obj.isWidgetType() and obj.isWindow():
                    apply_text_overrides([obj] + obj.findChildren(QWidget))
            except Exception as exc:
                _debug_once("libellés (show)", exc)
            return False
        if etype != QEvent.Polish:
            return False
        try:
            kind = self._kind(obj)
            if kind is not None:
                self._prepare(obj, kind)
            elif obj.isWidgetType() and obj.styleSheet():
                _restyle_widget(obj)
        except Exception as exc:
            _debug_once("popup", exc)
        return False


from PySide6.QtWidgets import QProxyStyle as _QProxyStyle

try:
    import shiboken6 as _shiboken6
except Exception:
    _shiboken6 = None

_GLASS_DEFERRED_ACTIVE = False


def _glass_alive(widget):
    if _shiboken6 is None:
        return True
    try:
        return bool(_shiboken6.isValid(widget))
    except Exception:
        return False


def _glass_deferred_restyle(widget):
    global _GLASS_DEFERRED_ACTIVE
    if not _glass_alive(widget):
        return
    _GLASS_DEFERRED_ACTIVE = True
    try:
        _restyle_widget(widget)
    except Exception as exc:
        _debug_once("restyle (polish)", exc)
    finally:
        _GLASS_DEFERRED_ACTIVE = False


def _glass_deferred_texts(widget):
    if not _glass_alive(widget):
        return
    try:
        if _TEXT_OVERRIDES:
            apply_text_overrides([widget] + widget.findChildren(QWidget))
    except Exception as exc:
        _debug_once("libellés (polish)", exc)


class _GlassProxyStyle(_QProxyStyle):
    """
    Remplace le filtre d'evenements GLOBAL de GlassPopupManager.
    polish() n'est appele que pour de vrais QWidget, dans le thread
    principal : aucun objet interne de Chromium/QtWebEngine ne passe
    par Python, donc plus de segfault.
    """

    def polish(self, arg):
        result = super().polish(arg)
        if isinstance(arg, QWidget):
            try:
                self._glass_hook(arg)
            except Exception as exc:
                _debug_once("polish (style)", exc)
        return result

    @staticmethod
    def _glass_hook(widget):
        kind = GlassPopupManager._kind(widget)
        if kind is not None:
            GlassPopupManager._prepare(widget, kind)
            return
        if _GLASS_DEFERRED_ACTIVE:
            return
        if widget.styleSheet() and not getattr(widget, "_glass_restyle_done", False):
            widget._glass_restyle_done = True
            QTimer.singleShot(0, lambda w=widget: _glass_deferred_restyle(w))
        if (
            _TEXT_OVERRIDES
            and widget.isWindow()
            and not getattr(widget, "_glass_texts_done", False)
        ):
            widget._glass_texts_done = True
            QTimer.singleShot(0, lambda w=widget: _glass_deferred_texts(w))


def install_glass_proxy_style(app=None):
    """Installe (une seule fois) le style Fusion enveloppe par _GlassProxyStyle."""
    app = app or QApplication.instance()
    if app is None:
        return None
    style = getattr(app, "_glass_proxy_style", None)
    if style is None:
        style = _GlassProxyStyle("Fusion")
        app.setStyle(style)
        app._glass_proxy_style = style
    return style


def install_glass_popup_manager(app=None):
    """Installe (une seule fois) le gestionnaire de popups floutés."""
    app = app or QApplication.instance()
    if app is None:
        return None
    manager = getattr(app, "_glass_popup_manager", None)
    if manager is None:
        manager = GlassPopupManager(app)
        app._glass_popup_manager = manager
        install_glass_proxy_style(app)
        _install_text_timer(app)
    for widget in app.allWidgets():
        if isinstance(widget, QComboBox):
            try:
                container = widget.view().window()
                if container is not None and container is not widget.window():
                    GlassPopupManager._prepare(container, "combo")
            except Exception as exc:
                _debug_once("liste déroulante", exc)
    return manager





# ============================================================================
# LIBELLES — tous les textes de l'interface peuvent être remplacés
# ----------------------------------------------------------------------------
# Principe : on ne touche à aucun appel du code. Chaque texte affiché (étiquette,
# bouton, onglet, menu, info-bulle, titre de fenêtre, en-tête de tableau…) est
# repéré tel que le code l'a posé (le « texte d'origine »). Si l'utilisateur a
# défini un remplacement pour ce texte, c'est lui qui s'affiche. Le remplacement
# suit donc aussi les changements de langue (il est propre à chaque texte d'origine).
# ============================================================================

import json as _json

try:
    _TEXT_OVERRIDES = {
        str(k): str(v)
        for k, v in _json.loads(
            str(_PREFERENCES.value("texts/overrides", "{}") or "{}")
        ).items()
        if str(v).strip()
    }
except (ValueError, TypeError, AttributeError):
    _TEXT_OVERRIDES = {}

_TEXT_RAW = {}          # méthodes Qt d'origine (non interceptées)
_TEXT_KINDS = {
    "label": "Étiquette", "button": "Bouton", "group": "Groupe",
    "tab": "Onglet", "header": "En-tête de tableau",
    "placeholder": "Champ de saisie", "tooltip": "Info-bulle",
    "title": "Titre de fenêtre", "action": "Menu / action",
}


def _text_eligible(text):
    """Ni vide, ni riche (HTML), ni purement numérique / symbolique."""
    if not isinstance(text, str):
        return False
    value = text.strip()
    if not value or len(value) > 400:
        return False
    if _re.search(r"</?[A-Za-z][^>]*>", value):
        return False
    return any(ch.isalpha() for ch in value)


def _slot_get(kind, obj, idx):
    if kind in ("label", "button", "action"):
        return obj.text()
    if kind == "group":
        return obj.title()
    if kind == "tab":
        return obj.tabText(idx)
    if kind == "header":
        item = obj.horizontalHeaderItem(idx)
        return item.text() if item is not None else ""
    if kind == "placeholder":
        return obj.placeholderText()
    if kind == "tooltip":
        return obj.toolTip()
    if kind == "title":
        return obj.windowTitle()
    return ""


def _slot_put(kind, obj, idx, text):
    if kind in ("label", "button", "group", "action", "placeholder", "tooltip", "title"):
        _TEXT_RAW[kind](obj, text)          # méthode d'origine : pas de ré-interception
    elif kind == "tab":
        QTabBar.setTabText(obj, idx, text)
    elif kind == "header":
        item = obj.horizontalHeaderItem(idx)
        if item is not None:
            item.setText(text)


def _slot_note(kind, obj, idx, text):
    """Appelé quand le CODE pose un texte : on retient l'original, on affiche le remplaçant."""
    shown = _TEXT_OVERRIDES.get(text, text) if _text_eligible(text) else text
    obj.setProperty(f"_txo_{kind}{idx}", text)
    obj.setProperty(f"_txl_{kind}{idx}", shown)
    return shown


def _make_text_hook(kind, raw):
    def hook(self, text, *args):
        if isinstance(text, str):
            text = _slot_note(kind, self, 0, text)
        return raw(self, text, *args)
    return hook


def _install_text_hooks():
    if _TEXT_RAW:
        return
    try:
        specs = (
            ("label", QLabel, "setText"),
            ("button", QAbstractButton, "setText"),
            ("group", QGroupBox, "setTitle"),
            ("action", QAction, "setText"),
            ("placeholder", QLineEdit, "setPlaceholderText"),
            ("tooltip", QWidget, "setToolTip"),
            ("title", QWidget, "setWindowTitle"),
        )
        for kind, cls, name in specs:
            raw = getattr(cls, name)
            _TEXT_RAW[kind] = raw
            setattr(cls, name, _make_text_hook(kind, raw))
        raw_tab = QTabWidget.setTabText

        def tab_hook(self, index, text):
            if isinstance(text, str):
                text = _slot_note("tab", self.tabBar(), index, text)
            return raw_tab(self, index, text)

        QTabWidget.setTabText = tab_hook
    except Exception as exc:          # le balayage périodique prend le relais
        _debug_once("libellés (crochets)", exc)


def _text_excluded(widget):
    top = widget.window()
    return top is not None and bool(top.property("_no_text_override"))


def _iter_text_slots(widgets):
    seen = set()
    for w in widgets:
        try:
            if _text_excluded(w):
                continue
            if isinstance(w, QLabel):
                yield ("label", w, 0)
            elif isinstance(w, QAbstractButton):
                if not (isinstance(w, QToolButton) and w.defaultAction() is not None):
                    yield ("button", w, 0)
            elif isinstance(w, QGroupBox):
                yield ("group", w, 0)
            elif isinstance(w, QTabBar):
                for i in range(w.count()):
                    yield ("tab", w, i)
            elif isinstance(w, QTableWidget):
                for i in range(w.columnCount()):
                    if w.horizontalHeaderItem(i) is not None:
                        yield ("header", w, i)
            elif isinstance(w, QLineEdit):
                yield ("placeholder", w, 0)
            if w.toolTip():
                yield ("tooltip", w, 0)
            if w.isWindow():
                yield ("title", w, 0)
            for action in w.actions():
                if id(action) not in seen:
                    seen.add(id(action))
                    yield ("action", action, 0)
        except RuntimeError:
            continue


def _sync_text_slot(kind, obj, idx):
    """Aligne le texte affiché sur les remplacements ; renvoie le texte d'origine."""
    current = _slot_get(kind, obj, idx)
    key_orig, key_last = f"_txo_{kind}{idx}", f"_txl_{kind}{idx}"
    if current != obj.property(key_last):
        original = current                    # posé par le code (ou premier passage)
        obj.setProperty(key_orig, original)
    else:
        original = obj.property(key_orig)
        if original is None:
            original = current
    wanted = _TEXT_OVERRIDES.get(original, original) if _text_eligible(original) else original
    if wanted != current:
        _slot_put(kind, obj, idx, wanted)
    obj.setProperty(key_last, wanted)
    return original


def apply_text_overrides(widgets=None):
    app = QApplication.instance()
    if app is None:
        return
    for kind, obj, idx in _iter_text_slots(widgets if widgets is not None else app.allWidgets()):
        try:
            _sync_text_slot(kind, obj, idx)
        except Exception as exc:
            _debug_once("libellés", exc)


def collect_interface_texts():
    """{texte d'origine: {types}} pour tout ce qui est affiché en ce moment."""
    app = QApplication.instance()
    found = {}
    if app is None:
        return found
    for kind, obj, idx in _iter_text_slots(app.allWidgets()):
        try:
            original = _sync_text_slot(kind, obj, idx)
        except Exception:
            continue
        if _text_eligible(original):
            found.setdefault(original, set()).add(kind)
    return found


def _install_text_timer(app):
    """Rattrape les textes changés côté C++ ou par le code (ex. changement de langue)."""
    if getattr(app, "_glass_text_timer", None) is not None:
        return
    timer = QTimer(app)
    timer.setInterval(1000)
    timer.timeout.connect(lambda: apply_text_overrides() if _TEXT_OVERRIDES else None)
    timer.start()
    app._glass_text_timer = timer


_install_text_hooks()



COLORS = {
    "window": "#0f1721",
    "window_gradient": (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 #111d2a, stop:0.42 #172a38, stop:1 #0d1721)"
    ),

    "glass": "rgba(17, 28, 38, 160)",
    "glass_soft": "rgba(19, 32, 44, 170)",
    "glass_strong": "rgba(23, 35, 48, 182)",
    "glass_sheen": (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 rgba(29, 43, 59, 210), "
        "stop:0.5 rgba(22, 34, 47, 185), "
        "stop:1 rgba(15, 24, 34, 175))"
    ),
    "bevel_light": "rgba(255, 255, 255, 220)",
    "bevel_dark": "rgba(76, 111, 139, 180)",
    "glass_edge": "rgba(235, 248, 255, 210)",

    "surface": "#101d2b",
    "surface_alt": "#152739",
    "panel": "#0f1c2a",

    "border": "rgba(131, 154, 177, 90)",
    "border_dark": "rgba(96, 118, 140, 120)",

    "text": "#edf5ff",
    "text_secondary": "#bfd3e6",
    "text_muted": "#8ea8bc",

    "accent": "#6bd18d",
    "accent_dark": "#dcffe8",
    "accent_ink": "#d9ffe5",
    "accent_light": "rgba(107, 209, 141, 52)",
    "accent_glass": (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 rgba(232, 255, 240, 190), "
        "stop:0.4 rgba(118, 222, 151, 175), "
        "stop:1 rgba(42, 139, 79, 185))"
    ),
    "accent_glass_hover": (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 rgba(250, 255, 251, 220), "
        "stop:0.4 rgba(151, 239, 178, 195), "
        "stop:1 rgba(61, 170, 96, 200))"
    ),
    "accent_glass_pressed": (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 rgba(151, 235, 176, 220), "
        "stop:1 rgba(33, 115, 64, 220))"
    ),

    "success": "#5fd3a1",
    "success_light": "rgba(95, 211, 161, 30)",

    "warning": "#f4c66b",
    "warning_light": "rgba(244, 198, 107, 25)",

    "danger": "#ff8a8a",
    "danger_light": "rgba(255, 138, 138, 35)",

    "viewer": "#0b1219",
}

_refresh_preference_palette()


# ============================================================================
# STYLE
# ============================================================================

def _build_app_style():
    """Feuille de style de base, reconstruite à chaque changement de réglage."""
    return f"""
QMainWindow {{
    background: {COLORS["window_gradient"]};
}}

QWidget {{
    font-family: "{GLASS_PREFERENCES["font_family"]}", "Noto Sans", "Segoe UI", sans-serif;
    font-size: {int(GLASS_PREFERENCES["font_size"])}px;
    color: {COLORS["text"]};
}}

QToolTip {{
    background: {COLORS["glass"]};
    color: {COLORS["text"]};
    border: 1px solid rgba(220, 255, 231, 175);
    border-radius: 8px;
    padding: 6px 10px;
}}

QMenuBar {{
    background: {COLORS["panel"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 3px 8px;
}}

QMenuBar::item {{
    padding: 7px 12px;
    margin: 2px;
    border-radius: 8px;
    background: transparent;
}}

QMenuBar::item:selected {{
    background: {COLORS["accent_light"]};
    color: {COLORS["accent_dark"]};
}}

QMenu {{
    background: {COLORS["panel"]};
    color: {COLORS["text"]};
    border: 1px solid rgba(220, 255, 231, 175);
    border-radius: 14px;
    padding: 8px;
}}

QMenu::item {{
    padding: 8px 28px 8px 14px;
    border-radius: 9px;
    margin: 1px 2px;
}}

QMenu::item:selected {{
    background: {COLORS["accent_light"]};
    color: {COLORS["accent_dark"]};
}}

QDialog {{
    background: {COLORS["panel"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
}}

QDialog QLineEdit,
QDialog QComboBox,
QDialog QSpinBox,
QDialog QDoubleSpinBox {{
    background: {COLORS["panel"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
}}

QDialog QLabel {{
    color: {COLORS["text"]};
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 6px 8px;
}}

QToolBar {{
    background: rgba(31, 104, 76, 92);
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    spacing: 8px;
    padding: 7px 12px;
}}

QFrame[green_glass="true"],
QToolBar[green_glass="true"] {{
    background: transparent;
    border: none;
}}

QToolButton {{
    border: 1px solid rgba(255, 255, 255, 175);
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(247, 255, 250, 220),
        stop:0.16 rgba(216, 247, 227, 180),
        stop:0.58 rgba(133, 211, 160, 150),
        stop:1 rgba(53, 137, 91, 165)
    );
    color: #103a28;
    padding: 7px 13px;
    border-radius: 11px;
}}
    QPushButton[liquid_glass="true"],
    QToolButton[liquid_glass="true"] {{
        background: transparent;
        border: none;
        padding: 8px 16px;
    }}

QToolButton:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 245),
        stop:0.2 rgba(229, 255, 239, 220),
        stop:0.62 rgba(165, 236, 190, 195),
        stop:1 rgba(72, 166, 108, 185)
    );
    border-color: rgba(255, 255, 255, 235);
}}

QToolButton:pressed {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(142, 218, 166, 190),
        stop:1 rgba(42, 125, 78, 200)
    );
    border-top-color: rgba(83, 133, 164, 200);
    border-left-color: rgba(100, 155, 190, 180);
}}

QToolButton#TopTab {{
    border: 1px solid rgba(255, 255, 255, 155);
    border-radius: 12px;
    margin: 1px 2px;
    padding: 9px 19px;
    font-weight: 600;
    color: #17344c;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(247, 253, 255, 205),
        stop:0.45 rgba(201, 230, 243, 165),
        stop:1 rgba(89, 143, 174, 145)
    );
}}

QToolButton#TopTab:hover {{
    background: rgba(246, 253, 255, 235);
    color: #0b263d;
    border-color: rgba(255, 255, 255, 235);
}}

QToolButton#TopTab:checked {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 238),
        stop:0.18 rgba(190, 232, 252, 220),
        stop:0.62 rgba(97, 177, 220, 205),
        stop:1 rgba(36, 106, 153, 195)
    );
    color: {COLORS["accent_ink"]};
    border: 1px solid rgba(255, 255, 255, 245);
    font-weight: 650;
}}

QFrame#TopHeader {{
    background: transparent;
    border: none;
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
    background: {COLORS["glass_soft"]};
    border-right: 1px solid {COLORS["border"]};
}}

QFrame#NavigationHeader {{
    background: transparent;
    border-bottom: 1px solid {COLORS["border"]};
}}

QToolButton#PrimaryNavigation {{
    text-align: left;
    border: 1px solid transparent;
    border-radius: 12px;
    margin: 2px 8px;
    padding: 11px 13px;
    color: {COLORS["text_secondary"]};
    background: transparent;
}}

QToolButton#PrimaryNavigation:hover {{
    background: {COLORS["glass_strong"]};
    color: {COLORS["text"]};
}}

QToolButton#PrimaryNavigation:checked {{
    background: {COLORS["accent_glass"]};
    color: {COLORS["accent_ink"]};
    border-width: 1px;
    border-style: solid;
    border-top-color: {COLORS["bevel_light"]};
    border-left-color: {COLORS["bevel_light"]};
    border-right-color: {COLORS["bevel_dark"]};
    border-bottom-color: {COLORS["bevel_dark"]};
    font-weight: 650;
}}

QFrame#SecondaryNavigation {{
    background: {COLORS["glass"]};
    border-right: 1px solid {COLORS["border"]};
}}

QToolButton#SecondaryTab {{
    text-align: left;
    border: 1px solid transparent;
    border-radius: 10px;
    margin: 1px 6px;
    padding: 7px 10px;
    min-height: 30px;
    color: {COLORS["text_secondary"]};
    background: transparent;
}}

QToolButton#SecondaryTab:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 235),
        stop:0.2 rgba(226, 246, 255, 210),
        stop:0.62 rgba(161, 211, 235, 180),
        stop:1 rgba(70, 130, 164, 170)
    );
    color: #102d45;
    border-top-width: 2px;
    border-left-width: 1px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-style: solid;
    border-top-color: rgba(170, 208, 245, 170);
    border-left-color: rgba(150, 190, 230, 145);
    border-right-color: rgba(72, 102, 132, 170);
    border-bottom-color: rgba(62, 90, 118, 180);
}}

QToolButton#SecondaryTab:checked {{
    color: #0b2d48;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 242),
        stop:0.18 rgba(196, 235, 253, 225),
        stop:0.6 rgba(105, 184, 226, 210),
        stop:1 rgba(42, 112, 161, 200)
    );
    border-top-width: 2px;
    border-left-width: 1px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-style: solid;
    border-top-color: rgba(188, 222, 255, 190);
    border-left-color: rgba(160, 205, 250, 170);
    border-right-color: rgba(25, 67, 112, 200);
    border-bottom-color: rgba(20, 57, 98, 210);
    font-weight: 650;
}}

QFrame#Workspace {{
    background: transparent;
}}

QFrame#ContentPanel {{
    background: rgba(47, 143, 103, 68);
    border: 1px solid rgba(225, 255, 238, 130);
    border-radius: 16px;
}}

QFrame#ToolbarPanel {{
    background: rgba(53, 161, 114, 72);
    border: 1px solid rgba(225, 255, 238, 135);
    border-radius: 12px;
}}

QPushButton {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 226),
        stop:0.18 rgba(227, 245, 253, 198),
        stop:0.6 rgba(160, 207, 229, 170),
        stop:1 rgba(72, 128, 161, 165)
    );
    border: 1px solid rgba(255, 255, 255, 205);
    border-radius: 10px;
    padding: 9px 18px;
    min-height: 18px;
    color: #112d44;
}}

QPushButton:hover {{
    background: rgba(250, 254, 255, 242);
    border-color: rgba(255, 255, 255, 245);
}}

QPushButton:pressed {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(142, 197, 226, 190),
        stop:1 rgba(56, 109, 143, 190)
    );
    border-color: rgba(82, 135, 168, 215);
}}

QPushButton:disabled {{
    background: {COLORS["glass_soft"]};
    color: {COLORS["text_muted"]};
    border-color: {COLORS["border"]};
}}

QPushButton#PrimaryButton {{
    background: {COLORS["accent_glass"]};
    color: {COLORS["accent_ink"]};
    border-width: 1px;
    border-style: solid;
    border-top-color: {COLORS["bevel_light"]};
    border-left-color: {COLORS["bevel_light"]};
    border-right-color: {COLORS["bevel_dark"]};
    border-bottom-color: {COLORS["bevel_dark"]};
    font-weight: 640;
    padding: 9px 22px;
}}

QPushButton#PrimaryButton:hover {{
    background: {COLORS["accent_glass_hover"]};
}}

QPushButton#PrimaryButton:pressed {{
    background: {COLORS["accent_glass_pressed"]};
}}

QPushButton#PrimaryButton[liquid_glass="true"],
QToolButton#TopTab[liquid_glass="true"],
QToolButton#SecondaryTab[liquid_glass="true"] {{
    background: transparent;
    border: none;
}}

QPushButton#DangerButton {{
    color: {COLORS["danger"]};
}}

QPushButton#DangerButton:hover {{
    border-color: {COLORS["danger"]};
    background: {COLORS["danger_light"]};
}}

QLineEdit,
QComboBox {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLORS["grad_stop0"]},
        stop:0.4 {COLORS["grad_stop1"]},
        stop:1 {COLORS["grad_stop2"]}
    );
    border-top-width: 2px;
    border-left-width: 1px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-style: solid;
    border-top-color: rgba(255, 255, 255, 235);
    border-left-color: rgba(255, 255, 255, 180);
    border-right-color: rgba(62, 107, 138, 180);
    border-bottom-color: rgba(46, 86, 116, 195);
    color: #123a27;
    border-radius: 10px;
    padding: 8px 12px;
    min-height: 18px;
    selection-background-color: {COLORS["accent_light"]};
}}

QLineEdit:hover,
QComboBox:hover {{
    background: {COLORS["glass_edge"]};
}}

QLineEdit:focus,
QComboBox:focus {{
    border: 1.5px solid {COLORS["accent"]};
    background: {COLORS["panel"]};
}}

QSpinBox,
QDoubleSpinBox {{
    background: {COLORS["grad_stop0"]};
    color: #123a27;
    border: 1px solid rgba(255, 255, 255, 190);
    border-radius: 10px;
    padding: 8px 12px;
    min-height: 18px;
}}

QSpinBox:focus,
QDoubleSpinBox:focus {{
    border: 1.5px solid {COLORS["accent"]};
    background: {COLORS["panel"]};
}}

QSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button {{
    background: transparent;
    border-left: 1px solid {COLORS["border"]};
    width: 18px;
}}

QSpinBox::up-button:hover,
QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover {{
    background: {COLORS["accent_light"]};
}}

QCheckBox {{
    color: {COLORS["text"]};
    spacing: 9px;
    padding: 3px 0px;
}}

QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid {COLORS["border_dark"]};
    border-radius: 6px;
    background: {COLORS["grad_stop1"]};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {COLORS["accent"]};
}}

QCheckBox::indicator:checked {{
    background: {COLORS["accent_green"]};
    border: 1px solid rgba(225, 255, 235, 220);
}}

QCheckBox::indicator:disabled {{
    background: {COLORS["glass_soft"]};
    border: 1px solid {COLORS["border"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 26px;
}}

QComboBox QAbstractItemView {{
    background: rgba(35, 118, 73, 235);
    color: #effff4;
    border: 1px solid rgba(218, 255, 229, 180);
    border-radius: 12px;
    outline: none;
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    padding: 7px 10px;
    border-radius: 8px;
    color: #effff4;
    background: transparent;
}}

QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:hover {{
    background: rgba(185, 255, 207, 100);
    color: #0d3521;
}}

QTableWidget {{
    background: rgba(18, 69, 47, 105);
    border: 1px solid rgba(190, 255, 213, 135);
    border-radius: 12px;
    gridline-color: rgba(177, 239, 199, 75);
    selection-background-color: rgba(102, 222, 143, 78);
    selection-color: {COLORS["text"]};
    alternate-background-color: rgba(56, 145, 91, 58);
}}

QTableWidget::item {{
    padding: 8px 7px;
    border-bottom: 1px solid rgba(174, 239, 197, 58);
}}

QTableWidget::item:hover {{
    background: rgba(226, 255, 236, 95);
}}

QHeaderView::section {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 242),
        stop:0.2 rgba(226, 255, 237, 225),
        stop:1 rgba(72, 166, 106, 195)
    );
    color: {COLORS["text"]};
    border: none;
    border-right: 1px solid {COLORS["border"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 8px;
    font-weight: 620;
}}

QHeaderView::section:first {{
    border-top-left-radius: 14px;
}}

QHeaderView::section:last {{
    border-top-right-radius: 14px;
}}

QTableCornerButton::section {{
    background: {COLORS["surface_alt"]};
    border: none;
    border-right: 1px solid {COLORS["border"]};
    border-bottom: 1px solid {COLORS["border"]};
    border-top-left-radius: 14px;
}}

QSlider::groove:horizontal {{
    height: 8px;
    border: 1px solid rgba(255, 255, 255, 150);
    border-radius: 4px;
    background: rgba(204, 244, 217, 165);
}}

QSlider::sub-page:horizontal {{
    border: 1px solid rgba(255, 255, 255, 185);
    border-radius: 4px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 230),
        stop:0.35 rgba(143, 229, 169, 225),
        stop:1 {COLORS["accent_green"]}
    );
}}

QSlider::add-page:horizontal {{
    border-radius: 4px;
    background: {COLORS["accent_green"]};
}}

QSlider::handle:horizontal {{
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border: 1.5px solid {COLORS["border"]};
    border-radius: 6px;
    background: {COLORS["accent_green"]};
}}

QSlider::handle:horizontal:hover {{
    border-color: {COLORS["text"]};
    background: {COLORS["accent"]};
}}

QProgressBar {{
    background: rgba(44, 126, 77, 100);
    border: 1px solid rgba(213, 255, 226, 145);
    border-radius: 6px;
    height: 12px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(240, 255, 245, 220),
        stop:1 {COLORS["accent_green"]}
    );
    border-radius: 5px;
}}

QStatusBar {{
    background: {COLORS["accent_green"]};
    border-top: 1px solid rgba(210, 255, 225, 135);
    color: #dfffea;
}}

QSplitter::handle {{
    background: {COLORS["border"]};
    border-radius: 2px;
}}

QSplitter::handle:hover {{
    background: {COLORS["accent"]};
}}

QFrame#Viewer {{
    background: {COLORS["viewer"]};
    border: 1px solid #151b20;
    border-radius: 18px;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollArea#DockingScrollArea,
QScrollArea#DockingScrollArea > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 2px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: rgba(127, 218, 154, 150);
    min-height: 28px;
    border-radius: 5px;
    margin: 1px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(224, 255, 233, 220);
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
    background: transparent;
    height: 11px;
    margin: 2px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: rgba(127, 218, 154, 150);
    min-width: 28px;
    border-radius: 5px;
    margin: 1px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(224, 255, 233, 220);
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
    background: {COLORS["window_gradient"]};
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
    min-width: 76px;
}}
"""


APP_STYLE = _build_app_style()


# ============================================================================
# EFFET "VERRE LIQUIDE" — ombre portée douce simulant l'élévation d'une
# carte de verre au-dessus du dégradé de fond. QSS seul ne sait pas
# dessiner d'ombre portée : on utilise QGraphicsDropShadowEffect, qui ne
# coûte rien en fiabilité (aucun rendu OpenGL requis) et fonctionne sur
# n'importe quelle plateforme supportée par Qt.
# ============================================================================

def apply_glass_elevation(widget, blur=36, y_offset=10, alpha=55):
    """
    Applique une ombre portée douce à `widget` pour lui donner l'aspect
    d'une carte de verre flottant au-dessus du fond. Sans effet sur la
    couleur/texte du widget : uniquement l'ombre derrière lui.
    """
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(20, 30, 60, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def apply_glass_elevation_to_children(root, object_names, blur=32, y_offset=8, alpha=50):
    """
    Parcourt les enfants de `root` et applique apply_glass_elevation() à
    tout QFrame dont l'objectName figure dans `object_names`. Pratique
    pour habiller d'un coup tous les panneaux existants (ContentPanel,
    ToolbarPanel, ...) sans toucher à chacun de leurs points de création.
    """
    for frame in root.findChildren(QFrame):
        if (
            frame.objectName() in object_names
            and not frame.property("skip_glass_elevation")
        ):
            apply_glass_elevation(frame, blur=blur, y_offset=y_offset, alpha=alpha)


# ============================================================================
# DECOUPAGE REEL AUX COINS ARRONDIS
# ----------------------------------------------------------------------------
# `border-radius` en QSS ne dessine qu'un contour arrondi : le contenu
# (fond des onglets, tableaux, etc.) reste un rectangle plein et ses
# coins depassent visuellement l'arc des que le rayon depasse la
# largeur de la bordure. Le seul moyen fiable de vraiment DECOUPER le
# contenu a la forme arrondie est un masque (QRegion) applique au
# widget, recalcule a chaque redimensionnement.
# ============================================================================

class _RoundedClipFilter(QObject):

    def __init__(self, widget, radius):
        super().__init__(widget)
        self.radius = radius
        widget.installEventFilter(self)
        self._apply(widget)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            self._apply(obj)
        return False

    def _apply(self, widget):
        if widget.width() <= 0 or widget.height() <= 0:
            return
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(widget.rect()), self.radius, self.radius
        )
        widget.setMask(QRegion(path.toFillPolygon().toPolygon()))


def apply_rounded_clip(widget, radius=14):
    """
    Force `widget` (et tout son contenu) a etre reellement decoupe en
    rectangle a coins arrondis de rayon `radius`, quel que soit le
    fond peint par ses enfants. A utiliser sur tout widget dont le
    QSS declare deja un `border-radius` mais dont le contenu carre
    depasse visuellement de l'arc (ex: QTabWidget::pane).
    """
    return _RoundedClipFilter(widget, radius)


def configure_glass_table(table, visible_rows=10, maximum_rows=12):
    """Applique une découpe arrondie et une hauteur stable aux tableaux."""
    if table.property("glass_table"):
        return table
    table.setProperty("glass_table", True)
    table.setAlternatingRowColors(True)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.verticalHeader().setDefaultSectionSize(30)
    table.verticalHeader().setMinimumSectionSize(30)
    table.setMinimumHeight(42 + visible_rows * 30)
    table.setMaximumHeight(42 + maximum_rows * 30)
    apply_rounded_clip(table, radius=14)
    return table


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


_GLASS_KINDS = {
    "button": ("button_tint", "button_opacity", 66),
    "button_hover": ("button_hover_tint", "button_opacity", 66),
    "panel": ("panel_tint", "panel_opacity", 58),
    "tab": ("tab_tint", "tab_opacity", 66),
    "tab_hover": ("tab_hover_tint", "tab_opacity", 66),
    "tab_active": ("tab_active_tint", "tab_opacity", 66),
}


def _glass_tint(alpha, factor=1.0, kind="button"):
    color_key, opacity_key, base_opacity = _GLASS_KINDS.get(kind, _GLASS_KINDS["button"])
    alpha = int(alpha * GLASS_PREFERENCES.get(opacity_key, base_opacity) / base_opacity)
    color = _theme_color(color_key)
    if not color.isValid():
        color = QColor("#6bd18d")
    color.setRed(max(0, min(255, int(color.red() * factor))))
    color.setGreen(max(0, min(255, int(color.green() * factor))))
    color.setBlue(max(0, min(255, int(color.blue() * factor))))
    color.setAlpha(max(0, min(255, int(alpha))))
    return color


class LiquidGlassButton(QPushButton):
    """Bouton natif avec face translucide et liseré de verre poli."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setProperty("liquid_glass", True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._glass_flux = 0.0
        self._glass_flux_timer = QTimer(self)
        self._glass_flux_timer.setInterval(24)
        self._glass_flux_timer.timeout.connect(self._advance_glass_flux)
        self.setMouseTracking(True)

    def _get_glass_flux(self):
        return self._glass_flux

    def _set_glass_flux(self, value):
        self._glass_flux = float(value)
        self.update()

    glassFlux = Property(float, _get_glass_flux, _set_glass_flux)

    def enterEvent(self, event):
        if GLASS_PREFERENCES.get("button_shimmer", True):
            self._glass_flux_timer.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._glass_flux_timer.stop()
        self._set_glass_flux(0.0)
        super().leaveEvent(event)

    def _advance_glass_flux(self):
        self._set_glass_flux((self._glass_flux + 0.018) % 1.18)

    def paintEvent(self, event):
        if self.width() < 3 or self.height() < 3:
            return

        radius = float(GLASS_PREFERENCES.get("button_radius", 12))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = 2.0
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)

        painter.fillPath(path, _glass_tint(GLASS_PREFERENCES["opacity"] + 30, 1.35))

        painter.setPen(Qt.NoPen)
        painter.setBrush(_glass_tint(54, 0.48))
        painter.drawRoundedRect(QRectF(rect).translated(0, 2), radius, radius)
        face = QLinearGradient(0, rect.top(), 0, rect.bottom())
        face.setColorAt(0.0, QColor(255, 255, 255, 128))
        face.setColorAt(0.16, _glass_tint(92, 1.35))
        face.setColorAt(0.58, _glass_tint(72, 1.0))
        face.setColorAt(1.0, _glass_tint(88, 0.52))
        painter.setBrush(face)
        painter.drawPath(path)
        if self.isDown() or self.isChecked():
            painter.setBrush(_overlay("button_pressed_tint", "button_pressed_opacity"))
            painter.drawPath(path)
        if self.underMouse() and not self.isDown():
            painter.setBrush(_overlay("button_hover_tint", "button_hover_opacity"))
            painter.drawPath(path)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(_overlay("button_border_color", "button_border_opacity"))
        painter.drawPath(path)
        inner = QRectF(rect).adjusted(2.0, 2.0, -2.0, -2.0)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, max(1.0, radius - 2.0), max(1.0, radius - 2.0))
        painter.setPen(QPen(_glass_tint(GLASS_PREFERENCES["reflection"], 1.25), 1.0))
        painter.drawPath(inner_path)
        lower = QLinearGradient(0, rect.top(), 0, rect.bottom())
        lower.setColorAt(0.0, QColor(255, 255, 255, 0))
        lower.setColorAt(0.78, QColor(255, 255, 255, 0))
        lower.setColorAt(1.0, _glass_tint(98, 1.25))
        painter.setPen(QPen(lower, 2.0))
        painter.drawPath(path)

        if self.underMouse() and GLASS_PREFERENCES.get("button_shimmer", True):
            painter.save()
            painter.setClipPath(path)
            start_x = -self.width() * 0.45 + self.width() * self._glass_flux
            gradient = QLinearGradient(
                start_x, 0, start_x + self.width() * 0.42, 0
            )
            gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            gradient.setColorAt(0.45, QColor(255, 255, 255, 48))
            gradient.setColorAt(0.45, _glass_tint(68, 1.25, "button_hover"))
            gradient.setColorAt(0.58, QColor(255, 255, 255, 150))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillPath(path, gradient)
            painter.restore()

        painter.end()

        option = QStyleOptionButton()
        self.initStyleOption(option)
        content = QStylePainter(self)
        content.drawControl(QStyle.CE_PushButton, option)
        content.end()


class LiquidGlassToolButton(QToolButton):
    """Version du matériau liquide pour les onglets et outils Qt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("liquid_glass", True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._glass_flux = 0.0
        self._glass_flux_timer = QTimer(self)
        self._glass_flux_timer.setInterval(24)
        self._glass_flux_timer.timeout.connect(self._advance_glass_flux)
        self.setMouseTracking(True)

    def _get_glass_flux(self):
        return self._glass_flux

    def _set_glass_flux(self, value):
        self._glass_flux = float(value)
        self.update()

    glassFlux = Property(float, _get_glass_flux, _set_glass_flux)

    def enterEvent(self, event):
        if GLASS_PREFERENCES.get("tab_shimmer", True):
            self._glass_flux_timer.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._glass_flux_timer.stop()
        self._set_glass_flux(0.0)
        super().leaveEvent(event)

    def _advance_glass_flux(self):
        self._set_glass_flux((self._glass_flux + 0.018) % 1.18)

    def paintEvent(self, event):
        if self.width() < 3 or self.height() < 3:
            return

        radius = float(GLASS_PREFERENCES.get("tab_radius", 12))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)

        painter.fillPath(path, _glass_tint(GLASS_PREFERENCES["opacity"] + 24, 1.35, "tab"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(_glass_tint(48, 0.48, "tab"))
        painter.drawRoundedRect(QRectF(rect).translated(0, 2), radius, radius)
        face = QLinearGradient(0, rect.top(), 0, rect.bottom())
        face.setColorAt(0.0, QColor(255, 255, 255, 126))
        face.setColorAt(0.18, _glass_tint(86, 1.35, "tab"))
        face.setColorAt(0.62, _glass_tint(68, 1.0, "tab"))
        face.setColorAt(1.0, _glass_tint(84, 0.52, "tab"))
        painter.setBrush(face)
        painter.drawPath(path)
        if self.isDown() or self.isChecked():
            painter.setBrush(_overlay("tab_active_tint", "tab_active_opacity"))
            painter.drawPath(path)
        if self.underMouse() and not self.isDown():
            painter.setBrush(_overlay("tab_hover_tint", "tab_hover_opacity"))
            painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(_overlay("tab_border_color", "tab_border_opacity"))
        painter.drawPath(path)
        inner = QRectF(rect).adjusted(2.0, 2.0, -2.0, -2.0)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, max(1.0, radius - 2.0), max(1.0, radius - 2.0))
        painter.setPen(QPen(_glass_tint(GLASS_PREFERENCES["reflection"], 1.25, "tab"), 1.0))
        painter.drawPath(inner_path)

        if self.underMouse() and GLASS_PREFERENCES.get("tab_shimmer", True):
            painter.save()
            painter.setClipPath(path)
            start_x = -self.width() * 0.45 + self.width() * self._glass_flux
            gradient = QLinearGradient(
                start_x, 0, start_x + self.width() * 0.42, 0
            )
            gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            gradient.setColorAt(0.5, QColor(255, 255, 255, 48))
            gradient.setColorAt(0.5, _glass_tint(68, 1.25, "tab_hover"))
            gradient.setColorAt(0.62, QColor(255, 255, 255, 150))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillPath(path, gradient)
            painter.restore()
        painter.end()

        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        content = QStylePainter(self)
        content.drawComplexControl(QStyle.CC_ToolButton, option)
        content.end()


class GlassPanel(QFrame):
    """Reusable green-tinted glass container for rails, cards, and headers."""

    def __init__(self, parent=None, radius=16, blur_strength=1.0):
        super().__init__(parent)
        self._glass_radius = int(GLASS_PREFERENCES["radius"] or radius)
        self._blur_strength = blur_strength
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("green_glass", True)

    def paintEvent(self, event):
        if self.width() < 3 or self.height() < 3:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self._glass_radius, self._glass_radius)

        # Qt Widgets has no backdrop-filter. The translucent face keeps the
        # photographic background visible while the veil remains readable.
        painter.setPen(Qt.NoPen)
        painter.setBrush(_glass_tint(int(42 * self._blur_strength), 1.0, "panel"))
        painter.drawPath(path)

        face = QLinearGradient(0, rect.top(), 0, rect.bottom())
        face.setColorAt(0.0, QColor(236, 255, 245, 105))
        face.setColorAt(0.18, _glass_tint(62, 1.25, "panel"))
        face.setColorAt(0.58, _glass_tint(52, 0.88, "panel"))
        face.setColorAt(1.0, _glass_tint(76, 0.48, "panel"))
        painter.setBrush(face)
        painter.drawPath(path)

        # White-green edge highlights: top-left and bottom-right curvature.
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(_glass_tint(GLASS_PREFERENCES["reflection"] + 85, 1.35, "panel"), 1.6))
        painter.drawPath(path)
        inner = rect.adjusted(2.5, 2.5, -2.5, -2.5)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, max(4.0, self._glass_radius - 2.0), max(4.0, self._glass_radius - 2.0))
        painter.setPen(QPen(_glass_tint(GLASS_PREFERENCES["reflection"], 1.2, "panel"), 1.0))
        painter.drawPath(inner_path)

        painter.end()
        super().paintEvent(event)


class GlassToolBar(QToolBar):
    """Glass-painted toolbar used by the primary navigation rail."""

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("green_glass", True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_glass_tint(70, 1.0, "panel"))
        painter.drawPath(path)
        face = QLinearGradient(0, rect.top(), 0, rect.bottom())
        face.setColorAt(0.0, QColor(239, 255, 247, 122))
        face.setColorAt(0.2, _glass_tint(70, 1.25, "panel"))
        face.setColorAt(1.0, _glass_tint(88, 0.48, "panel"))
        painter.setBrush(face)
        painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(_glass_tint(GLASS_PREFERENCES["reflection"] + 90, 1.35, "panel"), 1.5))
        painter.drawPath(path)
        painter.setPen(QPen(_glass_tint(GLASS_PREFERENCES["reflection"], 1.2, "panel"), 1.0))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)
        painter.end()
        super().paintEvent(event)


from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QAbstractItemView as _QAIV


class GlassPreferencesDialog(QDialog):
    """Éditeur en direct de TOUS les réglages d'apparence et des libellés.

    Les onglets « Matériau », « Style du texte », « Onglets », « Boutons » et
    « Menus & flou » sont générés automatiquement depuis _THEME_SCHEMA ;
    l'onglet « Libellés » liste chaque texte affiché par l'interface.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("_no_text_override", True)   # cette fenêtre n'est pas renommable
        self.setWindowTitle("Paramètres d'apparence")
        self.setModal(True)
        self.resize(740, 780)
        self._original = dict(GLASS_PREFERENCES)
        self._original_texts = dict(_TEXT_OVERRIDES)
        self._controls = {}
        self._filling = False

        self._style_timer = QTimer(self)
        self._style_timer.setSingleShot(True)
        self._style_timer.setInterval(120)
        self._style_timer.timeout.connect(self._apply_now)
        self._text_timer = QTimer(self)
        self._text_timer.setSingleShot(True)
        self._text_timer.setInterval(250)
        self._text_timer.timeout.connect(apply_text_overrides)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        title = QLabel("Apparence du logiciel")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        description = QLabel(
            "Chaque élément visible se règle ici, avec aperçu immédiat. "
            "« Auto » = couleur dérivée automatiquement d'une autre."
        )
        description.setObjectName("SectionDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.tabs = QTabWidget()
        groups = []
        for spec in _THEME_SCHEMA:
            if spec["group"] not in groups:
                groups.append(spec["group"])
        for group in groups:
            self.tabs.addTab(self._build_page(group), group)
        self.tabs.addTab(self._build_texts_page(), "Libellés")
        layout.addWidget(self.tabs, 1)

        self.preview = GlassPanel(radius=GLASS_PREFERENCES["radius"])
        self.preview.setMinimumHeight(110)
        preview_layout = QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(18, 14, 18, 14)
        preview_layout.addWidget(QLabel("Aperçu"))
        row = QHBoxLayout()
        sample_button = LiquidGlassButton("Bouton d'exemple")
        sample_button.setMinimumHeight(40)
        row.addWidget(sample_button)
        sample_tab = LiquidGlassToolButton()
        sample_tab.setText("Onglet")
        sample_tab.setCheckable(True)
        sample_tab.setChecked(True)
        sample_tab.setMinimumHeight(40)
        row.addWidget(sample_tab)
        sample_combo = QComboBox()
        sample_combo.addItems(["Liste déroulante", "Deuxième choix", "Troisième choix"])
        row.addWidget(sample_combo)
        self.menu_button = LiquidGlassButton("Tester un menu")
        self.menu_button.setMinimumHeight(40)
        self.menu_button.clicked.connect(self._show_sample_menu)
        row.addWidget(self.menu_button)
        preview_layout.addLayout(row)
        layout.addWidget(self.preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        buttons.button(QDialogButtonBox.Save).setText("Enregistrer")
        buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        buttons.button(QDialogButtonBox.RestoreDefaults).setText("Réinitialiser")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._restore_defaults)
        layout.addWidget(buttons)

        self._fill_texts()      # une fois tous les widgets rattachés au dialogue

    def _build_page(self, group):
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(14, 14, 14, 14)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        for spec in _THEME_SCHEMA:
            if spec["group"] == group:
                form.addRow(spec["label"], self._build_control(spec))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _build_control(self, spec):
        key, kind = spec["key"], spec["kind"]
        value = GLASS_PREFERENCES[key]
        if kind == "color":
            box = QWidget()
            row = QHBoxLayout(box)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            button = QPushButton()
            button.setMinimumWidth(150)
            button.clicked.connect(lambda _c=False, k=key: self._pick_color(k))
            row.addWidget(button)
            if spec["auto"]:
                auto = QPushButton("Auto")
                auto.setToolTip("Revenir à la couleur automatique")
                auto.clicked.connect(lambda _c=False, k=key: self._set_value(k, ""))
                row.addWidget(auto)
            row.addStretch(1)

            def refresh(v, k=key, b=button):
                color = _theme_color(k)
                swatch = QPixmap(20, 14)
                swatch.fill(color)
                b.setIcon(QIcon(swatch))
                b.setText(str(v) if str(v).strip() else "Auto")

            widget = box
        elif kind == "int":
            box = QWidget()
            row = QHBoxLayout(box)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(spec["lo"], spec["hi"])
            slider.setMinimumWidth(240)
            label = QLabel()
            label.setMinimumWidth(34)
            row.addWidget(slider, 1)
            row.addWidget(label)

            def on_slide(v, k=key, lab=label):
                lab.setText(str(v))
                self._set_value(k, int(v), refresh=False)

            slider.valueChanged.connect(on_slide)

            def refresh(v, s=slider, lab=label):
                s.blockSignals(True)
                s.setValue(int(v))
                s.blockSignals(False)
                lab.setText(str(int(v)))

            widget = box
        elif kind == "float":
            spin = QDoubleSpinBox()
            spin.setRange(spec["lo"], spec["hi"])
            spin.setSingleStep(0.01)
            spin.setDecimals(2)
            spin.valueChanged.connect(lambda v, k=key: self._set_value(k, float(v), refresh=False))

            def refresh(v, s=spin):
                s.blockSignals(True)
                s.setValue(float(v))
                s.blockSignals(False)

            widget = spin
        elif kind == "bool":
            check = QCheckBox()
            check.toggled.connect(lambda v, k=key: self._set_value(k, bool(v), refresh=False))

            def refresh(v, c=check):
                c.blockSignals(True)
                c.setChecked(bool(v))
                c.blockSignals(False)

            widget = check
        else:  # font
            combo = QFontComboBox()
            combo.currentFontChanged.connect(
                lambda f, k=key: self._set_value(k, f.family(), refresh=False)
            )

            def refresh(v, c=combo):
                c.blockSignals(True)
                c.setCurrentFont(QFont(str(v)))
                c.blockSignals(False)

            widget = combo
        refresh(value)
        self._controls[key] = refresh
        return widget

    def _pick_color(self, key):
        color = QColorDialog.getColor(_theme_color(key), self, "Choisir une couleur")
        if color.isValid():
            self._set_value(key, color.name())

    def _set_value(self, key, value, refresh=True):
        GLASS_PREFERENCES[key] = value
        if refresh:
            self._controls[key](value)
        if not self._style_timer.isActive():     # rafraîchit pendant le glissement, sans saturer
            self._style_timer.start()

    def _build_texts_page(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(14, 14, 14, 14)
        box.setSpacing(10)
        hint = QLabel(
            "Chaque texte affiché par l'interface est listé ici. Écris le nouveau "
            "texte dans la colonne de droite (vide = texte d'origine) : le "
            "changement est immédiat. Un remplacement est lié au texte d'origine, "
            "donc propre à chaque langue."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SectionDescription")
        box.addWidget(hint)
        self.text_search = QLineEdit()
        self.text_search.setPlaceholderText("Filtrer les textes…")
        self.text_search.textChanged.connect(self._filter_texts)
        box.addWidget(self.text_search)
        self.text_table = QTableWidget(0, 3)
        self.text_table.setHorizontalHeaderLabels(["Type", "Texte d'origine", "Nouveau texte"])
        self.text_table.verticalHeader().setVisible(False)
        self.text_table.setWordWrap(True)
        self.text_table.setSelectionBehavior(_QAIV.SelectRows)
        header = self.text_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.text_table.itemChanged.connect(self._on_text_edited)
        box.addWidget(self.text_table, 1)
        row = QHBoxLayout()
        refresh = QPushButton("Actualiser la liste")
        refresh.clicked.connect(self._fill_texts)
        restore = QPushButton("Rétablir tous les textes d'origine")
        restore.clicked.connect(self._restore_texts)
        row.addWidget(refresh)
        row.addWidget(restore)
        row.addStretch(1)
        box.addLayout(row)
        return page

    def _fill_texts(self):
        self._filling = True
        found = collect_interface_texts()
        keys = sorted(set(found) | set(_TEXT_OVERRIDES), key=lambda t: t.lower())
        self.text_table.setRowCount(len(keys))
        for row, original in enumerate(keys):
            kinds = ", ".join(sorted(_TEXT_KINDS[k] for k in found.get(original, ()))) or "(non affiché)"
            for col, text in ((0, kinds), (1, original)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.text_table.setItem(row, col, item)
            self.text_table.setItem(row, 2, QTableWidgetItem(_TEXT_OVERRIDES.get(original, "")))
        self._filling = False
        self._filter_texts(self.text_search.text())

    def _filter_texts(self, query=""):
        needle = str(query).strip().lower()
        for row in range(self.text_table.rowCount()):
            original = self.text_table.item(row, 1)
            new = self.text_table.item(row, 2)
            hay = f"{original.text()} {new.text() if new else ''}".lower()
            self.text_table.setRowHidden(row, bool(needle) and needle not in hay)

    def _on_text_edited(self, item):
        if self._filling or item.column() != 2:
            return
        original = self.text_table.item(item.row(), 1).text()
        value = item.text()
        if value.strip() and value != original:
            _TEXT_OVERRIDES[original] = value
        else:
            _TEXT_OVERRIDES.pop(original, None)
        self._text_timer.start()

    def _restore_texts(self):
        _TEXT_OVERRIDES.clear()
        apply_text_overrides()
        self._fill_texts()

    def _show_sample_menu(self):
        menu = QMenu(self)
        for label in ("Copier", "Coller", "Tout sélectionner"):
            menu.addAction(label)
        menu.addSeparator()
        menu.addAction("Action désactivée").setEnabled(False)
        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def _apply_now(self):
        apply_runtime_preferences()
        radius = int(GLASS_PREFERENCES["radius"])
        for widget in QApplication.instance().allWidgets():
            if isinstance(widget, GlassPanel):
                widget._glass_radius = radius
            if (
                widget.property("liquid_glass")
                or widget.property("green_glass")
                or isinstance(widget, ThemeBackground)
            ):
                widget.update()

    def _restore_defaults(self):
        for spec in _THEME_SCHEMA:
            self._set_value(spec["key"], spec["default"])
        self._style_timer.stop()
        self._apply_now()

    def _save(self):
        self._style_timer.stop()
        self._text_timer.stop()
        self._apply_now()
        apply_text_overrides()
        for spec in _THEME_SCHEMA:
            _PREFERENCES.setValue(f"glass/{spec['key']}", GLASS_PREFERENCES[spec["key"]])
        _PREFERENCES.setValue(
            "texts/overrides", _json.dumps(_TEXT_OVERRIDES, ensure_ascii=False)
        )
        _PREFERENCES.sync()
        self.accept()

    def reject(self):
        self._style_timer.stop()
        self._text_timer.stop()
        GLASS_PREFERENCES.clear()
        GLASS_PREFERENCES.update(self._original)
        _TEXT_OVERRIDES.clear()
        _TEXT_OVERRIDES.update(self._original_texts)
        self._apply_now()
        apply_text_overrides()
        super().reject()


def create_button(text, primary=False):
    button = LiquidGlassButton(text)

    if primary:
        button.setObjectName("PrimaryButton")
        # Ombre douce : le bouton principal flotte au-dessus du fond,
        # comme une pastille de verre — pas seulement pose dessus.
        apply_glass_elevation(button, blur=14, y_offset=3, alpha=34)

    return button


# ============================================================================
# NAVIGATION PRINCIPALE
# ============================================================================

from src.visualization.visualization_manager import VisualizationManager
class PrimaryNavigation(GlassPanel):

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
            button = LiquidGlassToolButton()
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
            "VINA Studio\nDocking moléculaire & Analyse"
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

class SecondaryNavigation(GlassPanel):

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

            button = LiquidGlassToolButton()
            button.setObjectName("SecondaryTab")
            button.setText(text)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setMinimumHeight(42)

            button.clicked.connect(
                lambda checked, i=index: callback(i)
            )

            # Ombre douce : detache le bouton du fond pour qu'il
            # "flotte" comme une pastille de verre, meme non selectionne.
            apply_glass_elevation(button, blur=14, y_offset=3, alpha=30)

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

        # Workspace de session : tout fichier importé ou généré
        # pendant la session vit ici tant qu'il n'est pas exporté
        # explicitement (bouton "Tout exporter la session").
        # Supprimé à la fermeture de l'application.
        self._session_manager = SessionManager(self.project_root)
        self._session_manager.create_session()

        self.sdf_files = []
        self.sdf_families = {}
        self.prepared_ligands = []
        self.pdbqt_families = {}
        self._pdbqt_family_columns = []

        # Ligands PDBQT explicitement sélectionnés
        # par l'utilisateur pour la campagne de docking.
        self.selected_ligands = []

        self.thread = None
        self.worker = None
        self.engine = None

        # Un ReceptorProfile vivant PAR PROTÉINE (pas un seul actif
        # partagé) : chacune garde son propre état indépendamment de la
        # cible actuellement affichée. Chargés paresseusement au premier
        # appel de update_target_parameters().
        self.mexb_profile = None
        self.mexr_profile = None

        # Cible actuellement affichée seule dans le visualiseur (None si
        # aucune cible unique n'est active, ex. mode double cible).
        self.current_single_target = None

        # Panneaux de grid box génériques (récepteurs ajoutés après
        # MexB/MexR, étape 7) : target_key -> {panel, fields, sliders,
        # scales, profile}. Peuplé dans create_docking_page().
        self.generic_panels = {}

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

    @staticmethod
    def _t_resolve(translated, key, fallback):
        """
        Repli de securite : si la cle de traduction n'existe pas encore
        dans src/translations.py, lang_mgr.t() renvoie la cle brute
        (ex. "dock_grid_activate_btn") au lieu d'un texte lisible. On ne
        montre jamais ca a l'utilisateur : on retombe sur le texte de
        repli fourni au code.
        """
        if not translated or translated == key:
            return fallback
        return translated

    def _t_label(self, key, fallback, object_name=None):
        text = self._t_resolve(
            self.lang_mgr.t(key) if self.lang_mgr else fallback, key, fallback
        )
        label = make_label(text, object_name)
        self._i18n.append((label, key, fallback))
        return label

    def _t_button(self, key, fallback, primary=False):
        text = self._t_resolve(
            self.lang_mgr.t(key) if self.lang_mgr else fallback, key, fallback
        )
        button = create_button(text, primary=primary)
        self._i18n.append((button, key, fallback))
        return button

    def _pdbqt_table_headers(self):
        family_columns = getattr(self, "_pdbqt_family_columns", [])
        if self.lang_mgr:
            return [
                self.lang_mgr.t("pdbqt_col_index"),
                *family_columns,
                self.lang_mgr.t("pdbqt_col_status"),
            ]
        return ["#", *family_columns, "Statut"]

    def retranslate(self):
        for widget, key, fallback in self._i18n:
            text = self._t_resolve(
                self.lang_mgr.t(key) if self.lang_mgr else fallback, key, fallback
            )
            widget.setText(text)

        if hasattr(self, "pdbqt_table"):
            self.pdbqt_table.setHorizontalHeaderLabels(self._pdbqt_table_headers())

        if hasattr(self, "sdf_naming_mode") and self.lang_mgr:
            combo = self.sdf_naming_mode
            current_data = combo.currentData()
            naming_keys = ["sdf_naming_preserve", "sdf_naming_clean", "sdf_naming_cid"]
            for i, key in enumerate(naming_keys):
                if i < combo.count():
                    combo.setItemText(i, self.lang_mgr.t(key))
            restored_index = combo.findData(current_data)
            if restored_index != -1:
                combo.setCurrentIndex(restored_index)

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

        choose_families = self._t_button(
            "sdf_btn_choose_families",
            "Choisir les familles de molécules",
        )
        choose_families.clicked.connect(self.select_sdf_families)

        clear = self._t_button(
            "sdf_btn_clear_selection",
            "Vider la sélection",
        )

        clear.clicked.connect(
            self.clear_sdf_selection
        )

        buttons.addWidget(add_files)
        buttons.addWidget(add_folder)
        buttons.addWidget(choose_families)
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

        self.sdf_list = QTableWidget(0, 1)
        self.sdf_list.setHorizontalHeaderLabels(["Type"])
        self._sdf_family_columns = []
        self.sdf_list.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        self.sdf_list.verticalHeader().setVisible(False)

        self.sdf_list.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.sdf_list.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.sdf_list.setAlternatingRowColors(
            True
        )

        self.sdf_list.setMinimumHeight(150)
        self.sdf_list.setMaximumHeight(350)

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

        naming_row = QHBoxLayout()
        naming_row.addWidget(QLabel("Nommage des ligands"))
        self.sdf_naming_mode = QComboBox()
        self.sdf_naming_mode.addItem(self.lang_mgr.t("sdf_naming_preserve") if self.lang_mgr else "Conserver le nom du fichier", "preserve")
        self.sdf_naming_mode.addItem(self.lang_mgr.t("sdf_naming_clean") if self.lang_mgr else "Nettoyer le nom", "clean")
        self.sdf_naming_mode.addItem(self.lang_mgr.t("sdf_naming_cid") if self.lang_mgr else "Détecter les identifiants CID", "cid")
        self.sdf_naming_mode.currentIndexChanged.connect(
            lambda: self.sdf_cleanup_text.setEnabled(
                self.sdf_naming_mode.currentData() == "clean"
            )
        )
        naming_row.addWidget(self.sdf_naming_mode)
        self.sdf_cleanup_text = QLineEdit()
        self.sdf_cleanup_text.setPlaceholderText(
            "Texte(s) à supprimer, séparés par des virgules"
        )
        self.sdf_cleanup_text.setEnabled(False)
        naming_row.addWidget(self.sdf_cleanup_text, 1)
        panel_layout.addLayout(naming_row)

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

        scroll = QScrollArea()
        scroll.setObjectName("SdfScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

    # ------------------------------------------------------------------
    # SELECTION SDF
    # ------------------------------------------------------------------

    def select_sdf_families(self):
        dialog = _MoleculeFamilyDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        families = {}
        all_files = []
        for family_name, folder in dialog.families():
            files = sorted(
                path.resolve()
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() == ".sdf"
            ) if folder.is_dir() else []
            if not files:
                QMessageBox.warning(
                    self, "Famille vide",
                    f"Le dossier de « {family_name} » ne contient aucun fichier SDF."
                )
                return
            families[family_name] = files
            all_files.extend(files)

        self.sdf_families = families
        self.sdf_files = list(dict.fromkeys(all_files))
        self.refresh_sdf_selection()
        self.sdf_log.setText(
            f"{len(families)} famille(s), {len(self.sdf_files)} fichier(s) SDF ajouté(s)."
        )

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

        self.sdf_families.setdefault("Sans famille", [])
        for file_path in files:
            path = Path(file_path).resolve()
            if path not in self.sdf_families["Sans famille"]:
                self.sdf_families["Sans famille"].append(path)

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

        self.sdf_families.setdefault(path.name, [])
        self.sdf_families[path.name].extend(
            item for item in sdf_files if item not in self.sdf_families[path.name]
        )

        self.refresh_sdf_selection()

        self.sdf_log.setText(
            f"Dossier ajouté : {added} fichier(s) SDF trouvé(s)."
        )

    def clear_sdf_selection(self):

        self.sdf_files.clear()
        self.sdf_families.clear()

        self.refresh_sdf_selection()

        self.sdf_log.setText(
            "Sélection SDF vidée."
        )

    def refresh_sdf_selection(self):
        families = [
            (name, paths)
            for name, paths in self.sdf_families.items()
            if paths
        ]
        self._sdf_family_columns = [name for name, _ in families]
        self.sdf_list.setColumnCount(1 + len(families))
        self.sdf_list.setHorizontalHeaderLabels(
            ["Type"] + self._sdf_family_columns
        )
        self.sdf_list.setRowCount(
            max((len(paths) for _, paths in families), default=0)
        )

        self.sdf_list.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        for column in range(1, 1 + len(families)):
            self.sdf_list.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.Stretch
            )

        for row in range(self.sdf_list.rowCount()):
            self.sdf_list.setItem(row, 0, QTableWidgetItem("Fichier SDF"))
        for column, (_, paths) in enumerate(families, 1):
            for row, path in enumerate(paths):
                item = QTableWidgetItem(path.name)
                item.setData(Qt.UserRole, str(path))
                item.setToolTip(str(path))
                self.sdf_list.setItem(row, column, item)

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

            generated = []
            generated_family_map = {}
            family_inputs = [
                (family, paths)
                for family, paths in self.sdf_families.items()
                if paths
            ]
            if not family_inputs:
                family_inputs = [("Sans famille", self.sdf_files)]

            for family, inputs in family_inputs:
                family_generated = prepare_sdf_files(
                    inputs,
                    output_dir,
                    naming_mode=self.sdf_naming_mode.currentData(),
                    cleanup_text=self.sdf_cleanup_text.text(),
                )
                generated.extend(Path(path) for path in family_generated)
                generated_family_map.update({
                    Path(path).resolve(): family
                    for path in family_generated
                })

            self.prepared_ligands = [
                Path(p)
                for p in generated
            ]
            self.pdbqt_families.update(generated_family_map)

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

        add_families = self._t_button(
            "pdbqt_btn_choose_families",
            "Choisir les familles",
        )
        add_families.clicked.connect(self.add_pdbqt_families)

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
        toolbar_layout.addWidget(add_families)
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

        self.pdbqt_table = QTableWidget(0, 2)
        self.pdbqt_table.setHorizontalHeaderLabels(["#", "Statut"])

        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
        )

        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents,
        )

        self.pdbqt_table.setAlternatingRowColors(True)
        self.pdbqt_table.verticalHeader().setVisible(False)

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

        scroll = QScrollArea()
        scroll.setObjectName("PdbqtScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

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
        self.pdbqt_families = {
            path: family
            for path, family in self.pdbqt_families.items()
            if path in {file.resolve() for file in files}
        }
        family_names = []
        for family in self.pdbqt_families.values():
            if family not in family_names:
                family_names.append(family)
        if not family_names and files:
            family_names = ["Sans famille"]
        self._pdbqt_family_columns = family_names
        self.pdbqt_table.setColumnCount(2 + len(family_names))
        self.pdbqt_table.setHorizontalHeaderLabels(
            self._pdbqt_table_headers()
        )
        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        for column in range(1, 1 + len(family_names)):
            self.pdbqt_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.Stretch
            )
        self.pdbqt_table.horizontalHeader().setSectionResizeMode(
            1 + len(family_names), QHeaderView.ResizeToContents
        )

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

        grouped = {family: [] for family in family_names}
        for ligand in files:
            family = self.pdbqt_families.get(ligand.resolve(), "Sans famille")
            grouped.setdefault(family, []).append(ligand)

        self.pdbqt_table.setRowCount(max((len(items) for items in grouped.values()), default=0))
        for row in range(self.pdbqt_table.rowCount()):
            self.pdbqt_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            status = QTableWidgetItem("Prêt")
            status.setTextAlignment(Qt.AlignCenter)
            self.pdbqt_table.setItem(row, 1 + len(family_names), status)

        for column, family in enumerate(family_names, 1):
            for row, ligand in enumerate(grouped[family]):
                item = QTableWidgetItem(ligand.name)
                item.setData(Qt.UserRole, str(ligand))
                item.setToolTip(str(ligand))
                self.pdbqt_table.setItem(row, column, item)

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
            for column in range(1, 1 + len(self._pdbqt_family_columns)):
                item = self.pdbqt_table.item(row, column)
                if item is None:
                    continue
                path_value = item.data(Qt.UserRole)
                if path_value:
                    path = Path(str(path_value)).resolve()
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

                self.pdbqt_families[target.resolve()] = "Sans famille"

                copied += 1

        self.refresh_pdbqt_table()

        self.status_message(
            f"{copied} ligand(s) ajouté(s)."
        )

    def add_pdbqt_families(self):
        dialog = _MoleculeFamilyDialog(
            self, "Choisir les familles de ligands PDBQT"
        )
        if dialog.exec() != QDialog.Accepted:
            return

        destination = self.project_root / "docking" / "ligands" / "prepared"
        destination.mkdir(parents=True, exist_ok=True)
        copied = 0

        for family_name, folder in dialog.families():
            files = sorted(
                path.resolve()
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() == ".pdbqt"
            ) if folder.is_dir() else []
            if not files:
                QMessageBox.warning(
                    self, "Famille vide",
                    f"Le dossier de « {family_name} » ne contient aucun fichier PDBQT."
                )
                return

            for source in files:
                target = destination / source.name
                if source != target.resolve():
                    shutil.copy2(source, target)
                    copied += 1
                self.pdbqt_families[target.resolve()] = family_name

        self.refresh_pdbqt_table()
        self.status_message(
            f"{len(dialog.families())} famille(s), {copied} ligand(s) PDBQT ajouté(s)."
        )

    # ------------------------------------------------------------------
    # DOCKING
    # ------------------------------------------------------------------

    def create_docking_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)

        # Conservé pour pouvoir ajouter dynamiquement un nouveau panneau
        # de grid box après un import Mode 2, sans reconstruire toute
        # la page.
        self._docking_layout = layout

        # ------------------------------------------------------------
        # BARRE D'OUTILS FIXE — import de récepteur (PDB ou PDBQT),
        # toujours visible en haut de la page. Remplace l'ancienne
        # entrée cachée dans le menu déroulant target_combo.
        # ------------------------------------------------------------

        _import_toolbar = QHBoxLayout()
        _import_toolbar.setContentsMargins(0, 0, 0, 0)

        self._import_receptor_button = QPushButton(
            "➕ Importer un récepteur (PDB / PDBQT)"
        )
        self._import_receptor_button.clicked.connect(
            self._import_receptor_dialog
        )
        _import_toolbar.addWidget(self._import_receptor_button)
        _import_toolbar.addStretch(1)

        self._export_session_button = QPushButton(
            "Tout exporter la session"
        )
        self._export_session_button.clicked.connect(
            self._export_session_dialog
        )
        _import_toolbar.addWidget(self._export_session_button)

        layout.addLayout(_import_toolbar)

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
            18, 16, 18, 16
        )

        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(9)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 0)
        grid.setColumnStretch(4, 1)

        grid.addWidget(
            self._t_label("dock_target_panel_title", "Cible biologique", "PanelTitle"),
            0, 0, 1, 4
        )

        grid.addWidget(
            self._t_label("dock_receptor_label", "Récepteur"),
            1, 0
        )

        self.target_combo = QComboBox()

        self.target_combo.addItem("MexB", "MexB")
        self.target_combo.addItem("MexR", "MexR")
        self.target_combo.addItem("MexB + MexR", "MexB + MexR")

        # Découverte automatique de tous les autres profils (built_in ou
        # user_defined) — MexB/MexR gardent leur logique dédiée
        # ci-dessus, tout le reste vient de receptor_profiles/*.json,
        # sans plus jamais avoir à modifier ce fichier pour un nouveau
        # profil (Section 7 du protocole, et Mode 2 ci-dessous).
        try:
            _declared_pairs = list_pairs()
        except Exception:
            _declared_pairs = []
        _paired_profile_ids = {
            profile_id
            for pair in _declared_pairs
            for profile_id in pair
        }

        for _pid in list_profile_ids():
            if _pid in ("mexb_paeruginosa", "mexr_paeruginosa"):
                continue
            try:
                _profile = resolve_target_profile(_pid)
            except Exception:
                continue
            if _pid not in _paired_profile_ids:
                continue
            if _profile.profile_type != "built_in":
                # Récepteur importé (Mode 2) : lié au workspace de
                # session, supprimé à la fermeture — ne doit pas
                # réapparaître au prochain lancement une fois son
                # fichier réel effacé. Un import fait PENDANT la
                # session en cours reste visible : il est ajouté
                # au menu ailleurs, dans _import_receptor_dialog.
                continue
            _prefix = "" if _profile.validated else "⚠ "
            # Nom court robuste (short_name du profil, sinon decoupage
            # sur tous les separateurs usuels) — l'ancien decoupage ne
            # gerait que « — » et laissait passer des libelles longs.
            _short_label = short_label(_profile)
            _combo_index = self.target_combo.count()
            self.target_combo.addItem(
                f"{_prefix}{_short_label}", _pid
            )
            self.target_combo.setItemData(
                _combo_index,
                _profile.display_name,
                Qt.ToolTipRole,
            )

        # ------------------------------------------------------------
        # CAMPAGNES DE COUPLE (filtre à double sélectivité)
        # ------------------------------------------------------------
        # La raison d'être du logiciel est de docker ensemble une pompe
        # d'efflux ET son dérépresseur. « MexB + MexR » n'est plus un
        # cas particulier écrit en dur : chaque couple déclaré dans les
        # profils (partner_id + role) obtient ici sa propre campagne.
        self.pair_targets = {}

        for _pump_id, _repressor_id in _declared_pairs:

            if {_pump_id, _repressor_id} == {
                "mexb_paeruginosa",
                "mexr_paeruginosa",
            }:
                # Déjà présent sous sa forme historique « MexB + MexR ».
                continue

            try:
                _pump = resolve_target_profile(_pump_id)
                _repressor = resolve_target_profile(_repressor_id)
            except Exception:
                continue

            _pair_key = make_pair_key(_pump_id, _repressor_id)

            self.pair_targets[_pair_key] = (_pump_id, _repressor_id)

            _pair_prefix = (
                ""
                if (_pump.validated and _repressor.validated)
                else "⚠ "
            )

            _pair_index = self.target_combo.count()

            self.target_combo.addItem(
                f"{_pair_prefix}{short_label(_pump)} + "
                f"{short_label(_repressor)}",
                _pair_key,
            )

            self.target_combo.setItemData(
                _pair_index,
                (
                    f"Filtre à double sélectivité — "
                    f"{_pump.display_name} + {_repressor.display_name}"
                ),
                Qt.ToolTipRole,
            )

        # Le point d'entrée d'import n'est plus dans ce menu — voir le
        # bouton fixe ajouté dans la barre d'outils de create_docking_page.

        self.target_combo.currentIndexChanged.connect(
            self._on_target_combo_index_changed
        )
        self.target_combo.currentIndexChanged.connect(
            self._sync_receptor_picker_button
        )

        self._receptor_picker_button = QPushButton(
            "Choisir un récepteur…"
        )
        self._receptor_picker_button.setCursor(Qt.PointingHandCursor)
        self._receptor_picker_button.clicked.connect(
            self._open_receptor_picker
        )
        self._sync_receptor_picker_button()

        grid.addWidget(
            self._receptor_picker_button,
            1, 1, 1, 3
        )

        self._mexb_gridbox_title = self._t_label(
            "dock_gridbox_panel_title", "Grid box", "PanelTitle"
        )
        grid.addWidget(
            self._mexb_gridbox_title,
            2, 0, 1, 4
        )

        # Widgets du bloc "Grid box" de MexB (titre + labels + champs) —
        # affichés/masqués ENSEMBLE selon la cible choisie, exactement
        # comme self.mexr_panel, pour qu'un seul panneau de paramètres
        # soit visible à la fois quand une seule cible est sélectionnée.
        self._mexb_gridbox_widgets = [self._mexb_gridbox_title]

        # ----------------------------------------------------------
        # CONFIGURATIONS MULTI-CIBLES
        # ----------------------------------------------------------

        self.mexb_fields = {}
        self.mexr_fields = {}

        # Compatibilité ancienne interface
        self.grid_fields = self.mexb_fields

        # Sliders synchronisés avec self.grid_fields (même clés), et le
        # facteur d'échelle utilisé pour convertir chaque valeur flottante
        # en entier (les QSlider Qt ne travaillent qu'en int).
        self.grid_sliders = {}
        self.grid_scales = {}

        # Jeu de sliders/échelles séparé pour MexR — jamais recyclé
        # avec celui de MexB.
        self.mexr_grid_sliders = {}
        self.mexr_grid_scales = {}

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

            _mexb_row_label = self._t_label(tr_key, label)
            grid.addWidget(
                _mexb_row_label,
                row,
                col,
            )
            self._mexb_gridbox_widgets.append(_mexb_row_label)

            field = QDoubleSpinBox()
            field.setMaximumWidth(130)

            if key.startswith("center_"):
                field.setRange(-1000.0, 1000.0)
                field.setDecimals(3)
                field.setSingleStep(0.1)
                scale = 1000
            else:
                field.setRange(1.0, 200.0)
                field.setDecimals(2)
                field.setSingleStep(0.5)
                scale = 100

            self.grid_scales[key] = scale

            slider = QSlider(Qt.Horizontal)
            slider.setMinimumWidth(110)
            slider.setMaximumWidth(160)
            slider.setMinimum(int(round(field.minimum() * scale)))
            slider.setMaximum(int(round(field.maximum() * scale)))
            slider.setValue(int(round(field.value() * scale)))

            def _make_spinbox_to_slider(sl=slider, sc=scale):
                def _sync(value):
                    sl.blockSignals(True)
                    sl.setValue(int(round(value * sc)))
                    sl.blockSignals(False)
                return _sync

            def _make_slider_to_spinbox(spinbox=field, sc=scale):
                def _sync(value):
                    spinbox.blockSignals(True)
                    spinbox.setValue(value / sc)
                    spinbox.blockSignals(False)
                    self._on_mexb_grid_changed()
                return _sync

            field.valueChanged.connect(_make_spinbox_to_slider())
            field.valueChanged.connect(self._on_mexb_grid_changed)
            slider.valueChanged.connect(_make_slider_to_spinbox())

            self.grid_fields[key] = field
            self.grid_sliders[key] = slider

            field_container = QWidget()
            field_container_layout = QVBoxLayout(field_container)
            field_container_layout.setContentsMargins(0, 0, 0, 0)
            field_container_layout.setSpacing(2)
            field_container_layout.addWidget(field)
            field_container_layout.addWidget(slider)

            grid.addWidget(
                field_container,
                row,
                col + 1,
            )
            self._mexb_gridbox_widgets.append(field_container)

        grid.addWidget(
            self._t_label("dock_vina_params_panel_title", "Paramètres Vina", "PanelTitle"),
            6, 0, 1, 4
        )

        grid.addWidget(
            make_label("Exhaustivité"),
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

        mexb_override_row, mexb_activate_btn, mexb_default_btn = (
            self._build_grid_override_row(
                get_profile=lambda: self.mexb_profile,
                is_current=lambda: self.current_single_target == "MexB",
                fields=self.grid_fields,
                sliders=self.grid_sliders,
                scales=self.grid_scales,
            )
        )
        grid.addLayout(mexb_override_row, 8, 0, 1, 4)
        self._mexb_gridbox_widgets.append(mexb_activate_btn)
        self._mexb_gridbox_widgets.append(mexb_default_btn)

        # ------------------------------------------------------
        # DISPOSITION CÔTE-À-CÔTE — config à gauche (largeur
        # plafonnée), visualiseur 3D à droite (extensible).
        # Objectif : voir l'effet d'un réglage de grid box sur
        # le visualiseur sans avoir à scroller, et récupérer
        # l'espace qui restait vide à droite du panneau de
        # config.
        # ------------------------------------------------------

        split_row = QHBoxLayout()
        split_row.setSpacing(18)

        left_column = QWidget()
        left_column_layout = QVBoxLayout(left_column)
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        left_column_layout.setSpacing(18)
        left_column.setMaximumWidth(520)

        # Cible d'insertion pour les panneaux génériques ajoutés
        # à chaud après un import (voir _import_receptor_dialog).
        self._docking_left_layout = left_column_layout

        right_column = QWidget()
        right_column_layout = QVBoxLayout(right_column)
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        self._docking_right_layout = right_column_layout

        split_row.addWidget(left_column, 0)
        split_row.addWidget(right_column, 1)

        layout.addLayout(split_row)

        left_column_layout.addWidget(
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

        # ----------------------------------------------------------
        # GRID BOX MEXR — panneau INDÉPENDANT de celui de MexB,
        # jamais recyclé : chaque protéine garde son propre état.
        # ----------------------------------------------------------

        mexr_grid = QGridLayout()
        mexr_grid.setHorizontalSpacing(18)
        mexr_grid.setVerticalSpacing(12)
        mexr_grid.setColumnStretch(0, 0)
        mexr_grid.setColumnStretch(1, 0)
        mexr_grid.setColumnStretch(2, 0)
        mexr_grid.setColumnStretch(3, 0)
        mexr_grid.setColumnStretch(4, 1)

        mexr_names = [
            ("Centre X", "center_x", "grid_center_x"),
            ("Centre Y", "center_y", "grid_center_y"),
            ("Centre Z", "center_z", "grid_center_z"),
            ("Taille X", "size_x", "grid_size_x"),
            ("Taille Y", "size_y", "grid_size_y"),
            ("Taille Z", "size_z", "grid_size_z"),
        ]

        for index, (label, key, tr_key) in enumerate(mexr_names):

            row = index // 2
            col = (index % 2) * 2

            mexr_grid.addWidget(
                self._t_label(tr_key, label),
                row,
                col,
            )

            mexr_field = QDoubleSpinBox()
            mexr_field.setMaximumWidth(130)

            if key.startswith("center_"):
                mexr_field.setRange(-1000.0, 1000.0)
                mexr_field.setDecimals(3)
                mexr_field.setSingleStep(0.1)
                mexr_scale = 1000
            else:
                mexr_field.setRange(1.0, 200.0)
                mexr_field.setDecimals(2)
                mexr_field.setSingleStep(0.5)
                mexr_scale = 100

            self.mexr_grid_scales[key] = mexr_scale

            mexr_slider = QSlider(Qt.Horizontal)
            mexr_slider.setMinimumWidth(110)
            mexr_slider.setMaximumWidth(160)
            mexr_slider.setMinimum(int(round(mexr_field.minimum() * mexr_scale)))
            mexr_slider.setMaximum(int(round(mexr_field.maximum() * mexr_scale)))
            mexr_slider.setValue(int(round(mexr_field.value() * mexr_scale)))

            def _make_mexr_spinbox_to_slider(sl=mexr_slider, sc=mexr_scale):
                def _sync(value):
                    sl.blockSignals(True)
                    sl.setValue(int(round(value * sc)))
                    sl.blockSignals(False)
                return _sync

            def _make_mexr_slider_to_spinbox(spinbox=mexr_field, sc=mexr_scale):
                def _sync(value):
                    spinbox.blockSignals(True)
                    spinbox.setValue(value / sc)
                    spinbox.blockSignals(False)
                    self._on_mexr_grid_changed()
                return _sync

            mexr_field.valueChanged.connect(_make_mexr_spinbox_to_slider())
            mexr_field.valueChanged.connect(self._on_mexr_grid_changed)
            mexr_slider.valueChanged.connect(_make_mexr_slider_to_spinbox())

            self.mexr_fields[key] = mexr_field
            self.mexr_grid_sliders[key] = mexr_slider

            mexr_field_container = QWidget()
            mexr_field_container_layout = QVBoxLayout(mexr_field_container)
            mexr_field_container_layout.setContentsMargins(0, 0, 0, 0)
            mexr_field_container_layout.setSpacing(2)
            mexr_field_container_layout.addWidget(mexr_field)
            mexr_field_container_layout.addWidget(mexr_slider)

            mexr_grid.addWidget(
                mexr_field_container,
                row,
                col + 1,
            )

        mexr_layout.addLayout(mexr_grid)

        mexr_override_row, _, _ = self._build_grid_override_row(
            get_profile=lambda: self.mexr_profile,
            is_current=lambda: self.current_single_target == "MexR",
            fields=self.mexr_fields,
            sliders=self.mexr_grid_sliders,
            scales=self.mexr_grid_scales,
        )
        mexr_layout.addLayout(mexr_override_row)


        left_column_layout.addWidget(
            self.mexr_panel
        )


        # ----------------------------------------------------------
        # PANNEAUX GÉNÉRIQUES (récepteurs ajoutés après MexB/MexR)
        # ----------------------------------------------------------

        for _pid in list_profile_ids():
            if _pid in ("mexb_paeruginosa", "mexr_paeruginosa"):
                continue
            try:
                _profile = resolve_target_profile(_pid)
            except Exception:
                continue
            if _profile.profile_type != "built_in":
                # Récepteur importé (Mode 2) : lié au workspace de
                # session, supprimé à la fermeture — ne doit pas
                # réapparaître au prochain lancement une fois son
                # fichier réel effacé. Un import fait PENDANT la
                # session en cours reste visible : il est ajouté
                # au menu ailleurs, dans _import_receptor_dialog.
                continue
            _panel_title = _profile.display_name
            if not _profile.validated:
                _panel_title += " — NON validé expérimentalement"
            left_column_layout.addWidget(
                self._build_generic_grid_panel(_pid, _panel_title)
            )


        # ----------------------------------------------------------
        # VISUALISATION 3D (étape 4) — provisoire dans cet onglet,
        # sera déplacée dans un onglet "Configuration" dédié plus tard.
        # ----------------------------------------------------------

        viewer_panel = QFrame()
        viewer_panel.setObjectName("ContentPanel")
        viewer_panel.setProperty("skip_glass_elevation", True)

        viewer_layout = QVBoxLayout(viewer_panel)
        viewer_layout.setContentsMargins(22, 18, 22, 18)

        viewer_layout.addWidget(
            self._t_label("dock_viewer_panel_title", "Visualisation 3D", "PanelTitle")
        )

        _fpocket_toolbar = QHBoxLayout()
        _fpocket_toolbar.setContentsMargins(0, 0, 0, 0)

        self._fpocket_button = QPushButton("Détecter les poches (fpocket)")
        self._fpocket_button.clicked.connect(self._run_fpocket_detection)
        _fpocket_toolbar.addWidget(self._fpocket_button)

        self._fpocket_status_label = make_label("", "SectionDescription")
        self._fpocket_status_label.setWordWrap(True)
        _fpocket_toolbar.addWidget(self._fpocket_status_label, 1)

        viewer_layout.addLayout(_fpocket_toolbar)

        # Selecteur de poche compact : un menu deroulant (une seule
        # ligne, quel que soit le nombre de poches) + navigation
        # precedente/suivante, plutot qu'une liste cochable qui
        # prenait une case fixe encombrante avec beaucoup de poches.
        self._pocket_overview_active = False

        _pocket_selector_row = QHBoxLayout()
        _pocket_selector_row.setContentsMargins(0, 0, 0, 0)

        self._pocket_prev_button = QToolButton()
        self._pocket_prev_button.setText("◀")
        self._pocket_prev_button.setVisible(False)
        self._pocket_prev_button.clicked.connect(self._select_previous_pocket)
        _pocket_selector_row.addWidget(self._pocket_prev_button)

        self._pocket_combo = QComboBox()
        self._pocket_combo.setVisible(False)
        self._pocket_combo.currentIndexChanged.connect(self._on_pocket_combo_changed)
        _pocket_selector_row.addWidget(self._pocket_combo, 1)

        self._pocket_next_button = QToolButton()
        self._pocket_next_button.setText("▶")
        self._pocket_next_button.setVisible(False)
        self._pocket_next_button.clicked.connect(self._select_next_pocket)
        _pocket_selector_row.addWidget(self._pocket_next_button)

        viewer_layout.addLayout(_pocket_selector_row)

        _pocket_mode_row = QHBoxLayout()
        _pocket_mode_row.setContentsMargins(0, 0, 0, 0)

        self._pocket_overview_button = QPushButton("Aperçu global (tout afficher)")
        self._pocket_overview_button.setVisible(False)
        self._pocket_overview_button.clicked.connect(self._show_all_pockets)
        _pocket_mode_row.addWidget(self._pocket_overview_button)

        self._pocket_detail_button = QPushButton("Revenir à une poche")
        self._pocket_detail_button.setVisible(False)
        self._pocket_detail_button.clicked.connect(self._return_to_single_pocket)
        _pocket_mode_row.addWidget(self._pocket_detail_button)

        _pocket_mode_row.addStretch(1)
        viewer_layout.addLayout(_pocket_mode_row)

        self._pocket_list_hint = make_label(
            "Choisis une poche (ou navigue avec les flèches) : elle "
            "s'affiche seule, caméra recadrée — pratique pour une "
            "capture d'écran nette.",
            "SectionDescription",
        )
        self._pocket_list_hint.setWordWrap(True)
        self._pocket_list_hint.setVisible(False)
        viewer_layout.addWidget(self._pocket_list_hint)

        self.viewer_stack = QStackedWidget()

        self.receptor_viewer = QWebEngineView()
        self.receptor_viewer.setMinimumHeight(380)
        self._viewer_loaded = False
        self._current_viewer_profile = None
        self._pending_viewer_box = None
        self._viewer_box_update_timer = QTimer(self)
        self._viewer_box_update_timer.setSingleShot(True)
        self._viewer_box_update_timer.setInterval(24)
        self._viewer_box_update_timer.timeout.connect(
            self._flush_viewer_box_update
        )
        self.receptor_viewer.loadFinished.connect(self._on_viewer_loaded)
        self.receptor_viewer.setHtml(VIEWER_HTML)

        self._hover_bridge = _ResidueHoverBridge()
        self._web_channel = QWebChannel()
        self._web_channel.registerObject("bridge", self._hover_bridge)
        self.receptor_viewer.page().setWebChannel(self._web_channel)

        self.viewer_placeholder = make_label(
            "Visualisation désactivée en mode double cible."
        )
        self.viewer_placeholder.setAlignment(Qt.AlignCenter)
        self.viewer_placeholder.setStyleSheet(
            f"color: {COLORS['text_secondary']}; padding: 60px;"
        )

        self.viewer_stack.addWidget(self.receptor_viewer)
        self.viewer_stack.addWidget(self.viewer_placeholder)

        viewer_layout.addWidget(self.viewer_stack)

        right_column_layout.addWidget(viewer_panel)
        left_column_layout.addStretch(1)


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

        self.docking_log.verticalHeader().setVisible(False)

        self.docking_log.setMinimumHeight(150)
        self.docking_log.setWordWrap(True)
        self.docking_log.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        log_layout.addWidget(
            self.docking_log,
            1,
        )

        layout.addWidget(
            log_panel
        )

        self.cancel_button.setEnabled(False)

        self.update_target_parameters(
            self.target_combo.currentData()
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

    def _on_target_combo_index_changed(self, index):
        """
        Adaptateur pour currentIndexChanged : récupère la clé technique
        (itemData) plutôt que le texte affiché (qui est maintenant un
        nom lisible, pas la clé interne utilisée partout ailleurs).
        """
        target = self.target_combo.itemData(index)
        if target is not None:
            self._last_valid_target_index = index
            self.update_target_parameters(target)

    def _build_receptor_groups_from_combo(self):
        """
        Regroupe les entrées actuelles de target_combo par espèce
        bactérienne, dans l'ordre pompe -> dérépresseur -> couple à
        l'intérieur de chaque cadre. Reconstruit à chaque ouverture du
        sélecteur, donc reflète automatiquement tout import fait en
        cours de session, sans rien à synchroniser ailleurs.
        """

        OTHER_LABEL = "Espèce non précisée"

        order = []
        buckets = {}

        for i in range(self.target_combo.count()):
            data = self.target_combo.itemData(i)
            text = self.target_combo.itemText(i)
            tooltip = self.target_combo.itemData(i, Qt.ToolTipRole) or ""

            is_warning = text.startswith("⚠ ")
            clean_title = text[2:] if is_warning else text
            warning_note = "⚠ Non validé" if is_warning else ""

            species_label = OTHER_LABEL
            kind_label = "Récepteur"
            sort_rank = 3

            try:
                if data and is_pair_key(data):
                    pump_id, repressor_id = parse_pair_key(data)
                    pump = resolve_target_profile(pump_id)
                    repressor = resolve_target_profile(repressor_id)
                    species_label = (
                        pump.species or repressor.species or OTHER_LABEL
                    )
                    kind_label = "Couple"
                    sort_rank = 2
                elif data:
                    profile = resolve_target_profile(data)
                    species_label = profile.species or OTHER_LABEL
                    role = normalize_role(profile.role)
                    if role == "pump":
                        kind_label = "Pompe d'efflux"
                        sort_rank = 0
                    elif role == "repressor":
                        kind_label = "Dérépresseur"
                        sort_rank = 1
                    else:
                        kind_label = "Récepteur"
                        sort_rank = 3
            except Exception:
                pass

            subtitle = warning_note or tooltip

            if species_label not in buckets:
                buckets[species_label] = []
                order.append(species_label)

            buckets[species_label].append(
                (sort_rank, i, kind_label, clean_title, subtitle)
            )

        current_index = self.target_combo.currentIndex()
        groups = []

        for species_label in order:
            entries_raw = sorted(
                buckets[species_label], key=lambda e: (e[0], e[1])
            )
            entries = [
                (idx, kind_label, title, subtitle, idx == current_index)
                for (_rank, idx, kind_label, title, subtitle)
                in entries_raw
            ]
            groups.append((species_label, entries))

        return groups

    def _open_receptor_picker(self):
        groups = self._build_receptor_groups_from_combo()
        chosen = _ReceptorPickerDialog.ask(
            self, groups, self.target_combo.currentIndex()
        )
        if chosen is not None:
            self.target_combo.setCurrentIndex(chosen)

    def _sync_receptor_picker_button(self, _index=None):
        if not hasattr(self, "_receptor_picker_button"):
            return
        text = self.target_combo.currentText()
        self._receptor_picker_button.setText(
            text or "Choisir un récepteur…"
        )

    def update_target_parameters(self, target):

        try:

            # Chargement paresseux des deux profils (une seule fois) :
            # chaque protéine garde ensuite son propre état, indépendant
            # de la cible actuellement affichée dans l'interface.
            if self.mexb_profile is None:
                self.mexb_profile = resolve_target_profile("MexB")
                self._load_profile_into_fields(
                    self.mexb_profile,
                    self.mexb_fields,
                    self.grid_sliders,
                    self.grid_scales,
                )

            if self.mexr_profile is None:
                self.mexr_profile = resolve_target_profile("MexR")
                self._load_profile_into_fields(
                    self.mexr_profile,
                    self.mexr_fields,
                    self.mexr_grid_sliders,
                    self.mexr_grid_scales,
                )

            is_dual = target == "MexB + MexR"
            is_mexb_only = target == "MexB"
            is_mexr_only = target == "MexR"
            is_generic = target in self.generic_panels

            # Campagne de couple générique (« A + B »), équivalent de
            # « MexB + MexR » pour tout autre couple pompe/dérépresseur.
            pair_members = getattr(self, "pair_targets", {}).get(target)
            is_generic_pair = pair_members is not None

            if is_generic_pair:
                # Les deux protéines du couple doivent être chargées et
                # affichées avec leurs valeurs PRÉDÉFINIES, jamais des
                # valeurs éditées — même règle qu'en mode MexB + MexR.
                for member_key in pair_members:
                    if member_key in self.generic_panels:
                        self._load_generic_panel(member_key)

            # Chargement paresseux des profils génériques (une seule fois
            # chacun) — même principe que MexB/MexR : chaque cible garde
            # son propre état indépendant, jamais partagé avec une autre.
            if is_generic and self.generic_panels[target]["profile"] is None:
                self._load_generic_panel(target)

            # Mode double cible : la grid box de chaque protéine n'est
            # JAMAIS modifiable à la main — on réaffiche les valeurs
            # PRÉDÉFINIES (pas d'éventuelles valeurs éditées) et on
            # verrouille les deux panneaux.
            if is_dual:
                self._load_profile_into_fields(
                    resolve_target_profile("MexB"),
                    self.mexb_fields,
                    self.grid_sliders,
                    self.grid_scales,
                )
                self._load_profile_into_fields(
                    resolve_target_profile("MexR"),
                    self.mexr_fields,
                    self.mexr_grid_sliders,
                    self.mexr_grid_scales,
                )

            self._set_fields_enabled(
                self.mexb_fields, self.grid_sliders, is_mexb_only
            )
            self._set_fields_enabled(
                self.mexr_fields, self.mexr_grid_sliders, is_mexr_only
            )

            # Panneau MexR visible en mode MexR seul, ou en double cible
            # (verrouillé, affiché à titre informatif dans ce cas).
            self.mexr_panel.setVisible(is_mexr_only or is_dual)

            # Même règle que mexr_panel : le bloc "Grid box" de MexB
            # (titre + 6 champs) est masqué en bloc dès qu'une AUTRE
            # cible unique est choisie, au lieu de rester affiché en
            # grisé à côté du nouveau panneau — un seul panneau de
            # paramètres visible à la fois pour une cible unique.
            _mexb_gridbox_visible = is_mexb_only or is_dual
            for _mexb_widget in self._mexb_gridbox_widgets:
                _mexb_widget.setVisible(_mexb_gridbox_visible)

            # Un seul panneau générique visible à la fois — celui de la
            # cible actuellement sélectionnée, s'il y en a une.
            for panel_key, panel_data in self.generic_panels.items():

                if is_generic_pair:
                    visible = panel_key in pair_members
                else:
                    visible = is_generic and target == panel_key

                panel_data["panel"].setVisible(visible)

                # En campagne de couple, la grid box de chaque protéine
                # est verrouillée sur ses valeurs prédéfinies.
                if is_generic_pair and visible:
                    self._set_fields_enabled(
                        panel_data["fields"],
                        panel_data["sliders"],
                        False,
                    )
                elif visible:
                    self._set_fields_enabled(
                        panel_data["fields"],
                        panel_data["sliders"],
                        True,
                    )

            if is_dual or is_generic_pair:
                # Deux protéines à la fois : le visualiseur 3D n'a pas
                # de cible unique à afficher.
                self.current_single_target = None
                self.viewer_stack.setCurrentWidget(self.viewer_placeholder)
            elif is_generic:
                self.current_single_target = target
                self.viewer_stack.setCurrentWidget(self.receptor_viewer)
                self._load_viewer_receptor(self.generic_panels[target]["profile"])
            else:
                self.current_single_target = "MexR" if is_mexr_only else "MexB"
                self.viewer_stack.setCurrentWidget(self.receptor_viewer)
                active_profile = (
                    self.mexr_profile if is_mexr_only else self.mexb_profile
                )
                self._load_viewer_receptor(active_profile)

            if is_generic_pair:
                # La pompe sert de référence pour les paramètres de
                # recherche affichés (exhaustiveness, num_modes).
                config_target = pair_members[0]
            elif is_generic:
                config_target = target
            else:
                config_target = "MexR" if is_mexr_only else "MexB"

            config = create_target_config(
                config_target,
                results_root=(
                    self.project_root
                    / "docking"
                    / "results"
                    / "batch_vina_engine"
                ),
            )

            self.exhaustiveness_field.setText(
                str(config.exhaustiveness)
            )

            self.num_modes_field.setText(
                str(config.num_modes)
            )

            if is_mexr_only:
                self.mexr_receptor_label.setText(
                    f"Récepteur : {config.receptor.name}"
                )
            elif is_dual:
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

        except Exception as exc:

            self.execution_status.setText(
                f"Erreur configuration : {exc}"
            )

    def _sync_grid_profile(self, profile, fields_dict):
        """
        Reconstruit profile.grid_box à partir des valeurs actuelles des
        spinboxes de fields_dict. Utilisé séparément pour MexB et MexR —
        deux profils, deux jeux de widgets, jamais recyclés entre eux.
        """

        if profile is None:
            return

        try:
            new_grid_box = GridBox(
                center=(
                    fields_dict["center_x"].value(),
                    fields_dict["center_y"].value(),
                    fields_dict["center_z"].value(),
                ),
                size=(
                    fields_dict["size_x"].value(),
                    fields_dict["size_y"].value(),
                    fields_dict["size_z"].value(),
                ),
            )
        except (KeyError, RuntimeError):
            # Widgets pas encore tous construits (appel pendant
            # l'initialisation de la page) — on ignore silencieusement.
            return

        profile.grid_box = new_grid_box

    def _on_mexb_grid_changed(self, _value=None):
        self._sync_grid_profile(self.mexb_profile, self.mexb_fields)
        if self.current_single_target == "MexB" and self.mexb_profile is not None:
            self._update_viewer_box(self.mexb_profile.grid_box)

    def _on_mexr_grid_changed(self, _value=None):
        self._sync_grid_profile(self.mexr_profile, self.mexr_fields)
        if self.current_single_target == "MexR" and self.mexr_profile is not None:
            self._update_viewer_box(self.mexr_profile.grid_box)

    def _load_profile_into_fields(self, profile, fields_dict, sliders_dict, scales_dict):
        """
        Peuple fields_dict/sliders_dict avec les valeurs de
        profile.grid_box, sans redéclencher les callbacks de
        synchronisation (blockSignals).
        """

        values = {
            "center_x": profile.grid_box.center[0],
            "center_y": profile.grid_box.center[1],
            "center_z": profile.grid_box.center[2],
            "size_x": profile.grid_box.size[0],
            "size_y": profile.grid_box.size[1],
            "size_z": profile.grid_box.size[2],
        }

        for key, value in values.items():

            field = fields_dict.get(key)

            if field:
                field.blockSignals(True)
                field.setValue(float(value))
                field.blockSignals(False)

            slider = sliders_dict.get(key)

            if slider:
                scale = scales_dict.get(key, 1)
                slider.blockSignals(True)
                slider.setValue(int(round(float(value) * scale)))
                slider.blockSignals(False)

    def _set_fields_enabled(self, fields_dict, sliders_dict, enabled):
        """Active/désactive un jeu de spinbox+slider (verrouillage dual)."""

        for field in fields_dict.values():
            field.setEnabled(enabled)

        for slider in sliders_dict.values():
            slider.setEnabled(enabled)

    # ------------------------------------------------------------------
    # PERSONNALISATION DE LA GRID BOX (recepteurs deja integres)
    # ------------------------------------------------------------------

    def _build_grid_override_row(self, get_profile, is_current, fields, sliders, scales):
        """
        Ligne de deux boutons pour le panneau de grid box d'un récepteur
        déjà intégré au logiciel :
        - "Activer cette configuration" enregistre la position/taille
          actuelle comme configuration personnelle de l'utilisateur,
          reprise automatiquement à chaque démarrage pour ce récepteur ;
        - "Configuration par défaut" efface cette personnalisation et
          revient aux valeurs d'origine fournies avec le logiciel.
        Réutilisée pour MexB, MexR et chaque récepteur générique — un
        seul mécanisme, jamais dupliqué par cible.

        get_profile() : callable -> ReceptorProfile actuel (ou None).
        is_current() : callable -> bool, True si ce récepteur est celui
        actuellement affiché dans le visualiseur 3D (pour rafraîchir la
        boîte affichée après un retour à la configuration par défaut).
        """

        activate_button = self._t_button(
            "dock_grid_activate_btn", "✓ Enregistrer", primary=True
        )
        default_button = self._t_button(
            "dock_grid_default_btn", "↺ Réinitialiser"
        )
        activate_button.setToolTip(
            "Enregistre la position/taille actuelle de la grid box : "
            "elle sera reprise à chaque démarrage pour ce récepteur."
        )
        default_button.setToolTip(
            "Revient à la configuration d'origine de ce récepteur, "
            "celle fournie avec le logiciel."
        )

        def _activate():
            profile = get_profile()
            if profile is None:
                return
            self._sync_grid_profile(profile, fields)
            try:
                save_user_grid_override(profile.profile_id, profile.grid_box)
            except Exception as exc:
                self.execution_status.setText(
                    f"Erreur enregistrement configuration : {exc}"
                )
                return
            self.execution_status.setText(
                f"Configuration personnalisée activée pour {profile.display_name}."
            )

        def _restore_default():
            profile = get_profile()
            if profile is None:
                return
            try:
                clear_user_grid_override(profile.profile_id)
                fresh_profile = resolve_target_profile(profile.profile_id)
            except Exception as exc:
                self.execution_status.setText(
                    f"Erreur restauration configuration par défaut : {exc}"
                )
                return
            profile.grid_box = fresh_profile.grid_box
            self._load_profile_into_fields(profile, fields, sliders, scales)
            if is_current():
                self._update_viewer_box(profile.grid_box)
            self.execution_status.setText(
                f"Configuration par défaut restaurée pour {profile.display_name}."
            )

        activate_button.clicked.connect(_activate)
        default_button.clicked.connect(_restore_default)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(activate_button)
        row.addWidget(default_button)
        row.addStretch(1)

        return row, activate_button, default_button

    # ------------------------------------------------------------------
    # PANNEAUX GÉNÉRIQUES (récepteurs ajoutés après MexB/MexR — étape 7)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_pdb_chains(pdb_path: Path) -> dict:
        """Retourne {chain_id: nombre de résidus} depuis un PDB brut."""

        chain_residues = {}
        seen_residue_keys = set()

        with open(pdb_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith("ATOM"):
                    continue
                chain_id = line[21:22].strip() or "_"
                res_seq = line[22:26].strip()
                key = (chain_id, res_seq)
                if key in seen_residue_keys:
                    continue
                seen_residue_keys.add(key)
                chain_residues[chain_id] = chain_residues.get(chain_id, 0) + 1

        return chain_residues

    def _prepare_pdbqt_from_pdb(self, pdb_path: Path):
        """
        Prépare un PDBQT prêt pour le docking à partir d'un PDB brut :
        détecte les chaînes, demande à l'utilisateur lesquelles garder,
        supprime l'eau/les hétéroatomes/les ligands (aucune ligne
        HETATM n'est conservée, quelle que soit son identité), fusionne
        les chaînes choisies dans un seul fichier nettoyé, puis
        convertit en PDBQT via Open Babel (charges Gasteiger).

        Retourne (pdbqt_path, cleaned_pdb_path) ou None si annulé/échec.
        """

        chain_residues = self._parse_pdb_chains(pdb_path)

        if not chain_residues:
            QMessageBox.warning(
                self,
                "Aucune chaîne détectée",
                f"Aucun atome ATOM valide détecté dans {pdb_path.name}.",
            )
            return None

        dialog = _ChainSelectionDialog(chain_residues, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return None

        selected_chains = dialog.selected_chains()

        if not selected_chains:
            QMessageBox.warning(
                self,
                "Aucune chaîne sélectionnée",
                "Sélectionne au moins une chaîne pour continuer.",
            )
            return None

        kept_lines = []
        with open(pdb_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("ATOM"):
                    chain_id = line[21:22].strip() or "_"
                    if chain_id in selected_chains:
                        kept_lines.append(line)
                elif line.startswith(("TER", "END")):
                    kept_lines.append(line)

        chains_suffix = "".join(selected_chains)
        cleaned_pdb_path = (
            self._session_manager.prepared_dir
            / f"{pdb_path.stem}_clean_{chains_suffix}.pdb"
        )
        cleaned_pdb_path.write_text("".join(kept_lines), encoding="utf-8")

        pdbqt_path = cleaned_pdb_path.with_suffix(".pdbqt")

        import subprocess

        try:
            result = subprocess.run(
                [
                    "obabel",
                    str(cleaned_pdb_path),
                    "-O", str(pdbqt_path),
                    "-xr",
                    "--partialcharge", "gasteiger",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "Open Babel introuvable",
                "La commande 'obabel' n'a pas été trouvée. Installe "
                "Open Babel pour pouvoir importer des fichiers PDB.",
            )
            return None

        if result.returncode != 0 or not pdbqt_path.exists():
            QMessageBox.critical(
                self,
                "Échec de la conversion",
                "Open Babel n'a pas pu convertir le fichier nettoyé en "
                "PDBQT :\n\n" + (result.stderr or "(pas de détail)"),
            )
            return None

        return pdbqt_path, cleaned_pdb_path

    def _export_session_dialog(self):
        """
        Exporte intégralement le workspace de session courant
        vers un dossier choisi par l'utilisateur. Le choix du
        dossier dans la boîte de dialogue EST le consentement
        explicite requis avant toute conservation durable.
        """

        if not self._session_manager.active:
            QMessageBox.information(
                self,
                "Rien à exporter",
                "Aucun workspace de session actif.",
            )
            return

        destination = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier de destination de l'export",
        )

        if not destination:
            return

        try:
            exported_root, exported_files = (
                self._session_manager.export_session(destination)
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Échec de l'export",
                f"Impossible d'exporter la session :\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Export terminé",
            f"{len(exported_files)} fichier(s) exporté(s) vers \n{exported_root}",
        )

    def _import_receptor_core(self, prompt_label="", also_taken=None):
        """
        Étapes communes à tout import de récepteur (Mode 2) : choix du
        fichier, nettoyage/conversion si PDB brut (avec sélection de
        chaîne(s) — monomère, dimère, etc., inchangée), validation
        technique, visualiseur optionnel, nom et espèce.

        NE demande PAS le rôle biologique et NE sauvegarde PAS le
        profil — c'est au choix de l'appelant (un seul récepteur, ou
        un couple pompe/dérépresseur) de décider ça après coup.

        `also_taken` : identifiants déjà réservés par un import en
        cours dans le MÊME appel groupé (couple), pour éviter que les
        deux récepteurs d'un couple se voient attribuer le même
        profile_id avant que le premier soit sauvegardé sur disque.

        Retourne un ReceptorProfile (role=None) ou None si annulé.
        """

        also_taken = set(also_taken or ())

        title_suffix = f" — {prompt_label}" if prompt_label else ""

        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Importer un récepteur{title_suffix} — fichier PDB ou PDBQT",
            "",
            "Récepteurs (*.pdbqt *.pdb);;Fichiers PDBQT (*.pdbqt);;Fichiers PDB (*.pdb)",
        )

        if not selected_path:
            return None

        selected_path = Path(selected_path)

        # ------------------------------------------------------------
        # BRANCHEMENT SELON LE TYPE DE FICHIER
        #
        # PDBQT : l'utilisateur sait ce qu'il fait — comportement
        #         inchangé, aucune étape supplémentaire imposée.
        # PDB   : fichier brut, potentiellement multi-chaînes — on
        #         demande la sélection de chaîne(s) (monomère, dimère,
        #         ou plus), on nettoie (eau/hétéroatomes/ligands
        #         supprimés) et on convertit.
        # ------------------------------------------------------------

        precomputed_viewer_path = None

        if selected_path.suffix.lower() == ".pdb":
            result = self._prepare_pdbqt_from_pdb(selected_path)
            if result is None:
                return None
            pdbqt_path, precomputed_viewer_path = result
        else:
            pdbqt_path = self._session_manager.import_file(
                selected_path
            )

        # ------------------------------------------------------------
        # VALIDATION TECHNIQUE MINIMALE
        # ------------------------------------------------------------

        manager = ReceptorManager(pdbqt_path)
        info = manager.validate()

        if not info.valid:
            QMessageBox.warning(
                self,
                "Récepteur invalide",
                "Ce fichier PDBQT n'a pas passé la validation technique "
                "minimale :\n\n" + "\n".join(info.errors or []),
            )
            return None

        if info.warnings:
            proceed = QMessageBox.question(
                self,
                "Avertissements",
                "Le récepteur est valide mais présente des avertissements "
                ":\n\n" + "\n".join(info.warnings) +
                "\n\nContinuer l'import malgré tout ?",
            )
            if proceed != QMessageBox.Yes:
                return None

        # ------------------------------------------------------------
        # PDB VIEWER OPTIONNEL
        # ------------------------------------------------------------

        if precomputed_viewer_path is not None:
            viewer_path = precomputed_viewer_path
        else:
            viewer_path_str, _ = QFileDialog.getOpenFileName(
                self,
                "Fichier PDB pour la visualisation 3D (optionnel — Annuler pour ignorer)",
                str(pdbqt_path.parent),
                "Fichiers PDB (*.pdb)",
            )
            viewer_path = (
                self._session_manager.import_file(
                    Path(viewer_path_str)
                )
                if viewer_path_str
                else None
            )

        # ------------------------------------------------------------
        # MÉTADONNÉES
        # ------------------------------------------------------------

        default_name = pdbqt_path.stem

        display_name, ok = QInputDialog.getText(
            self,
            f"Nom du récepteur{title_suffix}",
            "Nom affiché dans le menu :",
            text=default_name,
        )
        if not ok or not display_name.strip():
            return None
        display_name = display_name.strip()

        species, ok = QInputDialog.getText(
            self,
            "Espèce (optionnel)",
            "Espèce biologique (laisser vide si non applicable) :",
        )
        if not ok:
            species = ""

        # ------------------------------------------------------------
        # IDENTIFIANT UNIQUE
        # ------------------------------------------------------------

        base_slug = "".join(
            ch if ch.isalnum() else "_"
            for ch in display_name.lower()
        ).strip("_") or "recepteur_importe"

        existing_ids = set(list_profile_ids())
        profile_id = base_slug
        suffix = 2
        while (
            profile_id in existing_ids
            or profile_id in self.generic_panels
            or profile_id in also_taken
        ):
            profile_id = f"{base_slug}_{suffix}"
            suffix += 1

        # ------------------------------------------------------------
        # GRID BOX PAR DÉFAUT — centroïde géométrique (AUCUNE
        # signification biologique, à ajuster impérativement par
        # l'utilisateur avant tout docking réel).
        # ------------------------------------------------------------

        atoms = manager.parse_atoms()

        if atoms:
            cx = sum(atom.x for atom in atoms) / len(atoms)
            cy = sum(atom.y for atom in atoms) / len(atoms)
            cz = sum(atom.z for atom in atoms) / len(atoms)
        else:
            cx, cy, cz = 0.0, 0.0, 0.0

        return ReceptorProfile(
            profile_id=profile_id,
            display_name=display_name,
            profile_type="user_defined",
            pdbqt_path=pdbqt_path,
            grid_box=GridBox(center=(cx, cy, cz), size=(25.0, 25.0, 25.0)),
            species=species.strip() or None,
            role=None,
            pdb_path_for_viewer=viewer_path,
            validated=False,
            notes=(
                "Récepteur importé par l'utilisateur (Mode 2). Grid box "
                "par défaut = centroïde géométrique de tout le récepteur "
                "— AUCUNE signification biologique. À AJUSTER "
                "impérativement via les sliders avant tout docking réel."
            ),
        )

    def _register_imported_profile(self, profile, silent=False):
        """
        Branchement à chaud d'UN profil importé dans l'interface :
        entrée de menu (sauf en mode silencieux, utilisé pour les deux
        moitiés d'un couple — c'est l'appelant qui ajoute l'entrée de
        campagne combinée) + panneau de grid box.
        """

        insert_index = None

        if not silent:
            insert_index = self.target_combo.count()
            self.target_combo.insertItem(
                insert_index, f"⚠ {profile.display_name} (importé)", profile.profile_id
            )

        panel = self._build_generic_grid_panel(
            profile.profile_id, f"{profile.display_name} — importé, NON validé"
        )
        _insert_at = self._docking_left_layout.count() - 1
        if _insert_at < 0:
            _insert_at = 0
        self._docking_left_layout.insertWidget(_insert_at, panel)

        if not silent and insert_index is not None:
            self.target_combo.setCurrentIndex(insert_index)

    def _import_receptor_dialog_single(self):
        """
        Import d'UN SEUL récepteur : cible unique, docké seul — ce qui
        signifie forcément que c'est soit une pompe d'efflux seule,
        soit un dérépresseur seul (ou un récepteur "autre", hors
        philosophie du couple).
        """

        profile = self._import_receptor_core()

        if profile is None:
            return

        role, ok = QInputDialog.getItem(
            self,
            "Rôle du récepteur",
            "Rôle biologique :",
            ["pump", "derepressor", "other"],
            editable=False,
        )
        if not ok:
            return

        profile.role = role

        try:
            save_user_profile(profile)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur de sauvegarde",
                f"Impossible de sauvegarder le profil importé :\n{exc}",
            )
            return

        self._register_imported_profile(profile)

        QMessageBox.information(
            self,
            "Récepteur importé",
            f"« {profile.display_name} » a été importé avec succès.\n\n"
            "La grid box est actuellement centrée sur le centroïde "
            "géométrique du récepteur, sans aucune signification "
            "biologique — ajuste-la via les sliders avant tout docking.",
        )

    def _import_receptor_dialog_pair(self):
        """
        Import de DEUX récepteurs formant un couple pompe d'efflux /
        dérépresseur — jamais plus de deux. L'utilisateur DOIT désigner
        lequel est la pompe : aucun rôle "other" n'est proposé ici,
        contrairement à l'import d'un récepteur seul, puisque choisir
        deux récepteurs n'a de sens QUE dans la philosophie du filtre à
        double sélectivité du logiciel.

        Chacun des deux passe par exactement les mêmes étapes qu'un
        import simple (sélection de fichier, sélection de chaîne(s) —
        monomère/dimère/etc., validation, visualiseur, nom, espèce).
        """

        first = self._import_receptor_core(
            prompt_label="1er récepteur du couple"
        )

        if first is None:
            return

        second = self._import_receptor_core(
            prompt_label="2e récepteur du couple (son partenaire biologique)",
            also_taken={first.profile_id},
        )

        if second is None:
            QMessageBox.information(
                self,
                "Import du couple annulé",
                "Le second récepteur n'a pas été fourni : aucun des deux "
                "n'a été importé.",
            )
            return

        # --------------------------------------------------------
        # DÉSIGNATION FORCÉE : pompe d'efflux vs dérépresseur.
        # Un choix binaire, pas une liste de rôles libres — importer
        # deux récepteurs n'a de sens que pour former ce couple.
        # --------------------------------------------------------

        chosen = _ReceptorChoiceCardDialog.ask(
            self,
            "Désignation du couple",
            "Lequel des deux est la pompe d'efflux ? L'autre sera "
            "automatiquement désigné comme dérépresseur.",
            [
                (
                    "first",
                    first.display_name,
                    "Sera désigné comme pompe d'efflux.",
                ),
                (
                    "second",
                    second.display_name,
                    "Sera désigné comme pompe d'efflux.",
                ),
            ],
        )

        if chosen is None:
            return

        if chosen == "first":
            pump, repressor = first, second
        else:
            pump, repressor = second, first

        pump.role = "pump"
        repressor.role = "derepressor"

        pump.partner_id = repressor.profile_id
        pump.partner_ids = [repressor.profile_id]

        repressor.partner_id = pump.profile_id
        repressor.partner_ids = [pump.profile_id]

        try:
            save_user_profile(pump)
            save_user_profile(repressor)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur de sauvegarde",
                f"Impossible de sauvegarder le couple importé :\n{exc}",
            )
            return

        # --------------------------------------------------------
        # BRANCHEMENT À CHAUD — une seule entrée de campagne, comme
        # pour n'importe quel couple déclaré à l'avance (patch 4).
        # --------------------------------------------------------

        self._register_imported_profile(pump, silent=True)
        self._register_imported_profile(repressor, silent=True)

        pair_key = make_pair_key(pump.profile_id, repressor.profile_id)
        self.pair_targets[pair_key] = (pump.profile_id, repressor.profile_id)

        pair_index = self.target_combo.count()
        self.target_combo.addItem(
            f"⚠ {short_label(pump)} + {short_label(repressor)} (importé)",
            pair_key,
        )
        self.target_combo.setCurrentIndex(pair_index)

        QMessageBox.information(
            self,
            "Couple importé",
            f"« {pump.display_name} » (pompe) et « {repressor.display_name} » "
            "(dérépresseur) ont été importés et couplés avec succès.\n\n"
            "Chaque grid box est centrée sur le centroïde géométrique de "
            "son récepteur, sans aucune signification biologique — "
            "ajuste les DEUX via les sliders avant tout docking.",
        )

    def _import_receptor_dialog(self):
        """
        Mode 2 (import libre) — point d'entrée public.

        Demande d'abord combien de récepteurs importer : un seul
        (cible unique — pompe seule, ou dérépresseur seul), ou deux
        (jamais plus) — auquel cas l'utilisateur désigne lequel est la
        pompe et lequel est le dérépresseur, et le couple est docké
        ensemble selon le filtre à double sélectivité du logiciel.
        """

        chosen = _ReceptorChoiceCardDialog.ask(
            self,
            "Import de récepteur(s)",
            "Combien de récepteurs veux-tu importer ?",
            [
                (
                    "single",
                    "1 récepteur",
                    "Docké seul — pompe seule, ou dérépresseur seul, "
                    "selon le rôle que tu choisiras.",
                ),
                (
                    "pair",
                    "2 récepteurs (un couple)",
                    "Tu désigneras lequel est la pompe d'efflux et "
                    "lequel est le dérépresseur — le couple sera docké "
                    "ensemble (filtre à double sélectivité), avec les "
                    "mêmes étapes (fichier, chaîne(s)...) pour chacun.",
                ),
            ],
        )

        if chosen is None:
            return

        if chosen == "pair":
            self._import_receptor_dialog_pair()
        else:
            self._import_receptor_dialog_single()

    def _build_generic_grid_panel(self, target_key, title):
        """
        Construit un panneau de grid box indépendant pour un récepteur
        générique (pas MexB/MexR, qui gardent leur code dédié existant).

        Même principe d'isolation que MexB/MexR : ce panneau a son propre
        jeu de spinbox+slider et son propre ReceptorProfile vivant,
        jamais partagé avec un autre récepteur. Enregistré dans
        self.generic_panels[target_key].
        """

        panel = QFrame()
        panel.setObjectName("ContentPanel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)

        panel_layout.addWidget(make_label(title, "PanelTitle"))

        panel_grid = QGridLayout()
        panel_grid.setHorizontalSpacing(18)
        panel_grid.setVerticalSpacing(12)
        panel_grid.setColumnStretch(0, 0)
        panel_grid.setColumnStretch(1, 0)
        panel_grid.setColumnStretch(2, 0)
        panel_grid.setColumnStretch(3, 0)
        panel_grid.setColumnStretch(4, 1)

        names = [
            ("Centre X", "center_x"),
            ("Centre Y", "center_y"),
            ("Centre Z", "center_z"),
            ("Taille X", "size_x"),
            ("Taille Y", "size_y"),
            ("Taille Z", "size_z"),
        ]

        fields = {}
        sliders = {}
        scales = {}

        for index, (label, key) in enumerate(names):

            row = index // 2
            col = (index % 2) * 2

            panel_grid.addWidget(make_label(label), row, col)

            field = QDoubleSpinBox()
            field.setMaximumWidth(130)

            if key.startswith("center_"):
                field.setRange(-1000.0, 1000.0)
                field.setDecimals(3)
                field.setSingleStep(0.1)
                scale = 1000
            else:
                field.setRange(1.0, 200.0)
                field.setDecimals(2)
                field.setSingleStep(0.5)
                scale = 100

            scales[key] = scale

            slider = QSlider(Qt.Horizontal)
            slider.setMinimumWidth(110)
            slider.setMaximumWidth(160)
            slider.setMinimum(int(round(field.minimum() * scale)))
            slider.setMaximum(int(round(field.maximum() * scale)))
            slider.setValue(int(round(field.value() * scale)))

            def _make_spinbox_to_slider(sl=slider, sc=scale):
                def _sync(value):
                    sl.blockSignals(True)
                    sl.setValue(int(round(value * sc)))
                    sl.blockSignals(False)
                return _sync

            def _make_slider_to_spinbox(spinbox=field, sc=scale, tk=target_key):
                def _sync(value):
                    spinbox.blockSignals(True)
                    spinbox.setValue(value / sc)
                    spinbox.blockSignals(False)
                    self._on_generic_grid_changed(tk)
                return _sync

            def _make_spinbox_changed(tk=target_key):
                def _handler(_value=None):
                    self._on_generic_grid_changed(tk)
                return _handler

            field.valueChanged.connect(_make_spinbox_to_slider())
            field.valueChanged.connect(_make_spinbox_changed())
            slider.valueChanged.connect(_make_slider_to_spinbox())

            fields[key] = field
            sliders[key] = slider

            field_container = QWidget()
            field_container_layout = QVBoxLayout(field_container)
            field_container_layout.setContentsMargins(0, 0, 0, 0)
            field_container_layout.setSpacing(2)
            field_container_layout.addWidget(field)
            field_container_layout.addWidget(slider)

            panel_grid.addWidget(field_container, row, col + 1)

        panel_layout.addLayout(panel_grid)

        generic_override_row, _, _ = self._build_grid_override_row(
            get_profile=lambda tk=target_key: self.generic_panels[tk]["profile"],
            is_current=lambda tk=target_key: self.current_single_target == tk,
            fields=fields,
            sliders=sliders,
            scales=scales,
        )
        panel_layout.addLayout(generic_override_row)

        panel.setVisible(False)

        self.generic_panels[target_key] = {
            "panel": panel,
            "fields": fields,
            "sliders": sliders,
            "scales": scales,
            "profile": None,
        }

        return panel

    def _load_generic_panel(self, target_key):
        """Charge (paresseusement) le profil d'un récepteur générique."""

        panel_data = self.generic_panels[target_key]
        panel_data["profile"] = resolve_target_profile(target_key)

        self._load_profile_into_fields(
            panel_data["profile"],
            panel_data["fields"],
            panel_data["sliders"],
            panel_data["scales"],
        )

    def _on_generic_grid_changed(self, target_key):
        panel_data = self.generic_panels.get(target_key)

        if panel_data is None or panel_data["profile"] is None:
            return

        self._sync_grid_profile(panel_data["profile"], panel_data["fields"])

        if self.current_single_target == target_key:
            self._update_viewer_box(panel_data["profile"].grid_box)

    # ------------------------------------------------------------------
    # VISUALISEUR 3D
    # ------------------------------------------------------------------

    def _on_viewer_loaded(self, ok):
        """
        Appelé une fois que VIEWER_HTML a fini de charger dans
        QWebEngineView (chargement de la page HTML elle-même — pas
        encore un récepteur). Charge alors la cible actuellement
        affichée, si une cible unique est active.
        """

        self._viewer_loaded = bool(ok)

        if not self._viewer_loaded or self.current_single_target is None:
            return

        profile = (
            self.mexb_profile
            if self.current_single_target == "MexB"
            else self.mexr_profile
        )

        self._load_viewer_receptor(profile)

    def _load_viewer_receptor(self, profile):
        """
        Charge (ou recharge) le récepteur + la grid box d'un profil
        dans le visualiseur. Appelé au changement de cible unique.
        """

        if profile is None or not self._viewer_loaded:
            return

        pdb_path = profile.pdb_path_for_viewer

        self._current_viewer_profile = profile
        self._clear_pocket_list()

        if pdb_path is None or not pdb_path.exists():
            return

        pdb_text = pdb_path.read_text(encoding="utf-8", errors="ignore")

        cx, cy, cz = profile.grid_box.center
        sx, sy, sz = profile.grid_box.size

        script = (
            f"clearPockets();"
            f"loadReceptor({json.dumps(pdb_text)});"
            f"updateBox({cx}, {cy}, {cz}, {sx}, {sy}, {sz});"
        )

        self.receptor_viewer.page().runJavaScript(script)

    def _set_pocket_panel_visible(self, visible: bool):
        self._pocket_combo.setVisible(visible)
        self._pocket_prev_button.setVisible(visible)
        self._pocket_next_button.setVisible(visible)
        self._pocket_list_hint.setVisible(visible)
        if not visible:
            self._pocket_overview_button.setVisible(False)
            self._pocket_detail_button.setVisible(False)

    def _update_pocket_mode_buttons(self):
        has_pockets = self._pocket_combo.count() > 0
        self._pocket_overview_button.setVisible(has_pockets and not self._pocket_overview_active)
        self._pocket_detail_button.setVisible(has_pockets and self._pocket_overview_active)
        self._pocket_combo.setEnabled(not self._pocket_overview_active)
        self._pocket_prev_button.setEnabled(not self._pocket_overview_active)
        self._pocket_next_button.setEnabled(not self._pocket_overview_active)

    def _clear_pocket_list(self):
        self._pocket_combo.blockSignals(True)
        self._pocket_combo.clear()
        self._pocket_combo.blockSignals(False)
        self._pocket_overview_active = False
        self._set_pocket_panel_visible(False)

    def _populate_pocket_list(self, pockets):
        """
        Remplit le menu deroulant des poches détectées, avec un carré
        de couleur correspondant exactement à la couleur de la
        surface dans le visualiseur 3D (même palette, même ordre que
        POCKET_PALETTE dans viewer_template.py). La première poche
        (la mieux classée en druggabilité) est sélectionnée par
        défaut — c'est déjà celle affichée seule par updatePockets()
        côté JS, donc rien d'autre à déclencher ici.
        """
        palette = [
            "#00bcd4", "#e91e63", "#ff9800", "#8bc34a",
            "#9c27b0", "#ffc107", "#00e676", "#ff5252",
            "#536dfe", "#ffd740",
        ]

        self._pocket_combo.blockSignals(True)
        self._pocket_combo.clear()

        for idx, pocket in enumerate(pockets):
            color_hex = palette[idx % len(palette)]
            score = pocket.get("descriptors", {}).get("druggability_score")
            score_text = f"{score:.2f}" if isinstance(score, (int, float)) else "n/d"

            pixmap = QPixmap(14, 14)
            pixmap.fill(QColor(color_hex))

            self._pocket_combo.addItem(
                QIcon(pixmap),
                f"Poche {pocket['pocket_id']} — druggabilité {score_text}",
                pocket["pocket_id"],
            )

        if pockets:
            self._pocket_combo.setCurrentIndex(0)

        self._pocket_combo.blockSignals(False)
        self._pocket_overview_active = False
        self._set_pocket_panel_visible(bool(pockets))
        self._update_pocket_mode_buttons()

    def _on_pocket_combo_changed(self, index):
        if index < 0:
            return
        pocket_id = self._pocket_combo.itemData(index)
        if pocket_id is None:
            return
        self._pocket_overview_active = False
        self._update_pocket_mode_buttons()
        self.receptor_viewer.page().runJavaScript(f"isolatePocket({pocket_id});")

    def _select_previous_pocket(self):
        index = self._pocket_combo.currentIndex()
        if index > 0:
            self._pocket_combo.setCurrentIndex(index - 1)

    def _select_next_pocket(self):
        index = self._pocket_combo.currentIndex()
        if index < self._pocket_combo.count() - 1:
            self._pocket_combo.setCurrentIndex(index + 1)

    def _show_all_pockets(self):
        self._pocket_overview_active = True
        self._update_pocket_mode_buttons()
        self.receptor_viewer.page().runJavaScript("showAllPockets();")

    def _return_to_single_pocket(self):
        self._pocket_overview_active = False
        self._update_pocket_mode_buttons()
        index = self._pocket_combo.currentIndex()
        if index >= 0:
            pocket_id = self._pocket_combo.itemData(index)
            self.receptor_viewer.page().runJavaScript(f"isolatePocket({pocket_id});")

    def _update_viewer_box(self, grid_box):
        """
        Repositionne uniquement la grid box (pas de rechargement du
        récepteur) — appelé à chaque changement de slider/spinbox pour
        rester fluide même pendant un glissement continu.
        """

        if not self._viewer_loaded:
            return

        self._pending_viewer_box = (
            tuple(grid_box.center),
            tuple(grid_box.size),
        )
        if not self._viewer_box_update_timer.isActive():
            self._viewer_box_update_timer.start()

    def _flush_viewer_box_update(self):
        if not self._viewer_loaded or self._pending_viewer_box is None:
            return

        center, size = self._pending_viewer_box
        self._pending_viewer_box = None
        cx, cy, cz = center
        sx, sy, sz = size

        script = f"updateBox({cx}, {cy}, {cz}, {sx}, {sy}, {sz});"

        self.receptor_viewer.page().runJavaScript(script)

    def _run_fpocket_detection(self):
        """
        Lance fpocket sur le récepteur actuellement affiché dans le
        visualiseur 3D (self._current_viewer_profile, mis à jour par
        _load_viewer_receptor), puis pousse les poches détectées vers
        le viewer via updatePockets() (voir viewer_template.py).
        """

        profile = getattr(self, "_current_viewer_profile", None)

        if profile is None:
            QMessageBox.warning(
                self,
                "Aucun récepteur chargé",
                "Aucun récepteur n'est actuellement affiché dans le visualiseur 3D.",
            )
            return

        pdb_path = profile.pdb_path_for_viewer

        if pdb_path is None or not pdb_path.exists():
            QMessageBox.warning(
                self,
                "Fichier PDB introuvable",
                f"Aucun fichier PDB de visualisation disponible pour {profile.display_name}.",
            )
            return

        self._fpocket_button.setEnabled(False)
        self._fpocket_status_label.setText("Détection des poches en cours (fpocket)…")
        self._clear_pocket_list()
        QApplication.processEvents()

        try:
            import tempfile
            import json as _json
            from pathlib import Path as _Path
            from src.analysis.pocket_detector import detect_pockets, MIN_ALPHA_SPHERES

            workdir = _Path(tempfile.mkdtemp(prefix="vinastudio_fpocket_"))
            pockets = detect_pockets(pdb_path, workdir)

            if not pockets:
                self._fpocket_status_label.setText("Aucune poche détectée.")
                return

            payload = _json.dumps(pockets)
            self.receptor_viewer.page().runJavaScript(
                f"updatePockets({payload!r});"
            )

            self._populate_pocket_list(pockets)

            self._fpocket_status_label.setText(
                f"{len(pockets)} poche(s) détectée(s) "
                f"(seuil ≥ {MIN_ALPHA_SPHERES} sphères alpha)."
            )

        except FileNotFoundError:
            import sys as _vs_sys
            if _vs_sys.platform.startswith("win"):
                QMessageBox.critical(
                    self,
                    "fpocket introuvable",
                    "La détection des poches (fpocket) n'est disponible que sous Linux. "
                    "Cette fonctionnalité n'est pas proposée sous Windows.",
                )
            else:
                QMessageBox.critical(
                    self,
                    "fpocket introuvable",
                    "La commande 'fpocket' n'a pas été trouvée dans le PATH. "
                    "Installez fpocket (ex. 'sudo apt install fpocket') puis réessayez.",
                )
            self._fpocket_status_label.setText("")

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur fpocket",
                f"La détection des poches a échoué :\n{exc}",
            )
            self._fpocket_status_label.setText("")

        finally:
            self._fpocket_button.setEnabled(True)

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

        target = self.target_combo.currentData()

        try:

            # Mode double cible : utiliser MexB uniquement pour l'affichage GUI.
            # Les moteurs MexB et MexR seront créés séparément au lancement.
            pair_members = getattr(self, "pair_targets", {}).get(target)

            if target == "MexB + MexR":
                # Cible d'affichage uniquement : les deux moteurs sont
                # créés séparément plus bas.
                config_target = "MexB"
            elif pair_members is not None:
                config_target = pair_members[0]
            else:
                config_target = target

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
            # La grid box de l'interface n'est appliquée QUE pour une
            # cible unique (MexB seul ou MexR seul). En mode double cible,
            # chaque protéine garde ses valeurs prédéfinies — voir plus
            # bas, sub_config = create_target_config(sub_target, ...)
            # n'est jamais écrasé pour la grid box.
            if target == "MexB":
                target_fields = self.mexb_fields
            elif target == "MexR":
                target_fields = self.mexr_fields
            elif pair_members is not None:
                # Campagne de couple : chaque protéine garde sa grid box
                # prédéfinie, rien n'est repris de l'interface.
                target_fields = None
            elif target in self.generic_panels:
                target_fields = self.generic_panels[target]["fields"]
            else:
                target_fields = None

            if target_fields is not None:
                config.center_x = target_fields["center_x"].value()
                config.center_y = target_fields["center_y"].value()
                config.center_z = target_fields["center_z"].value()
                config.size_x = target_fields["size_x"].value()
                config.size_y = target_fields["size_y"].value()
                config.size_z = target_fields["size_z"].value()

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

        elif pair_members is not None:

            # ------------------------------------------------------
            # COUPLE GÉNÉRIQUE : pompe d'efflux + dérépresseur
            # ------------------------------------------------------
            # Même logique que « MexB + MexR » : un moteur par
            # protéine, paramètres de recherche communs, grid box
            # propre à chacune (poches différentes, jamais écrasées).

            for sub_target in pair_members:

                sub_config = create_target_config(
                    sub_target,
                    results_root=(
                        self.project_root
                        / "docking"
                        / "results"
                        / "batch_vina_engine"
                    ),
                )

                sub_config.exhaustiveness = config.exhaustiveness
                sub_config.num_modes = config.num_modes

                engines[sub_target] = VinaEngine(sub_config)

        elif target in self.generic_panels:

            engines[target] = VinaEngine(
                config
            )

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

        # Rôles transmis au worker : ils déterminent quelle protéine
        # alimente les colonnes « pompe » et laquelle alimente les
        # colonnes « dérépresseur » du CSV fusionné, donc l'indice de
        # double sélectivité.
        if pair_members is not None:
            pair_roles = {
                "pump": pair_members[0],
                "repressor": pair_members[1],
            }
        elif target == "MexB + MexR":
            pair_roles = {"pump": "MexB", "repressor": "MexR"}
        else:
            pair_roles = None

        # patch-familles : familles choisies dans l'interface -> colonne "groupe"
        from pathlib import Path as _FamPath
        ligand_groups = {}
        for _lig_path, _lig_family in getattr(self, "pdbqt_families", {}).items():
            _family = str(_lig_family or "").strip()
            if _family and _family.lower() != "sans famille":
                ligand_groups[str(_FamPath(_lig_path).resolve())] = _family

        self.worker = DockingWorker(
            engines=engines,
            ligands=ligands,
            results_root=self.project_root,
            ligand_groups=ligand_groups,
            pair_roles=pair_roles,
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

            selected_target = self.target_combo.currentData()
            pair_roles = None
            if is_pair_key(selected_target):
                pump_id, repressor_id = parse_pair_key(selected_target)
                pair_roles = {
                    "pump": pump_id,
                    "repressor": repressor_id,
                }

            grouped, global_csv = create_scientific_scores(
                csv_path,
                pair_roles=pair_roles,
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
                        str(grouped)  # patch-familles : le CSV global n'a pas de colonne groupe
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

        self.docking_log.resizeRowsToContents()
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

    # ------------------------------------------------------------------
    # CAMPAGNES DISPONIBLES SUR LE DISQUE
    # ------------------------------------------------------------------

    @staticmethod
    def _batch_root():
        return (
            Path(__file__).resolve().parents[2]
            / "docking"
            / "results"
            / "batch_vina_engine"
        )

    def _available_campaigns(self) -> list:
        """
        Campagnes exploitables : chaque cible ayant un docking_results.csv,
        plus le CSV fusionné du dernier couple docké s'il existe.
        """

        campaigns = []

        combined = (
            Path(__file__).resolve().parents[2]
            / "docking_results_combined.csv"
        )

        if combined.is_file():
            campaigns.append("Dernier couple (CSV fusionné)")

        batch_root = self._batch_root()

        if batch_root.is_dir():
            for child in sorted(batch_root.iterdir()):
                if (child / "docking_results.csv").is_file():
                    campaigns.append(child.name)

        return campaigns

    def _campaign_csv_path(self, label):
        """Chemin du CSV correspondant à une entrée du menu Campagne."""

        label = str(label or "").strip()

        if not label:
            return None

        if label.startswith("Dernier couple"):
            combined = (
                Path(__file__).resolve().parents[2]
                / "docking_results_combined.csv"
            )
            return str(combined) if combined.is_file() else None

        candidate = self._batch_root() / label / "docking_results.csv"

        return str(candidate) if candidate.is_file() else None

    def _refresh_campaign_combo(self):
        """Recharge le menu Campagne depuis les résultats sur le disque."""

        combo = getattr(self, "analysis_campaign_combo", None)

        if combo is None:
            return

        current = combo.currentText()

        combo.blockSignals(True)
        combo.clear()

        campaigns = self._available_campaigns()

        if campaigns:
            combo.addItems(campaigns)
        else:
            combo.addItem("Aucun résultat de docking")

        if current:
            index = combo.findText(current)
            if index >= 0:
                combo.setCurrentIndex(index)

        combo.blockSignals(False)

    def campaign_summary(self):
        # patch-entete : recepteurs de la campagne analysee
        result = getattr(self, "statistics_result", None)
        if result:
            labels = result.get("labels") or {}
            names = [n for n in (labels.get("x"), labels.get("y")) if n]
            if names:
                return " + ".join(names)
        csv_path = getattr(self, "docking_results_csv", None)
        if csv_path:
            try:
                from src.campaign_table import normalize_docking_csv, campaign_shape
                info = campaign_shape(normalize_docking_csv(csv_path))
                return " + ".join(
                    self._receptor_table_label(rid, info["labels"][rid])
                    for rid in info["receptors"]
                )
            except Exception:
                pass
        return "Aucune campagne"

    def run_docking_analysis(self):

        csv_path = getattr(
            self,
            "docking_results_csv",
            None
        )

        # patch-session : plus aucun repli sur d'anciens resultats du disque.
        # L'analyse ne porte que sur le docking de cette session (ou sur une
        # analyse chargee explicitement), jamais sur un fichier reste de la veille.

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


            from src.scientific_fusion import create_scientific_scores

            grouped_csv, _ = create_scientific_scores(csv_path)
            gui_debug("CSV SCIENTIFIQUE DYNAMIQUE : " + str(grouped_csv))

            self.statistics_result = run_statistics_pipeline(grouped_csv)


            gui_debug(
                "MODE ANALYSE : "
                + str(
                    self.statistics_result.get(
                        "mode"
                    )
                )
            )


            self.populate_statistics_results()

            # patch-entete : recharge le bandeau avec les recepteurs analyses
            try:
                self.window()._refresh_header_target()
            except Exception:
                pass

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

        # Menu « Campagne » : auparavant une liste écrite en dur
        # (MexB + MexR / MexB / MexR) stockée dans une variable locale
        # jamais relue — il laissait croire qu'on choisissait une
        # campagne alors que l'analyse portait toujours sur le dernier
        # docking. Il est désormais peuplé depuis les résultats
        # réellement présents sur le disque, et conservé.
        combo = QComboBox()
        self.analysis_campaign_combo = combo
        self._refresh_campaign_combo()

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
        table.verticalHeader().setVisible(False)
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

            self._set_neutral_table_headers(table)  # patch-entetes

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

            scroll = QScrollArea()
            scroll.setObjectName("ResultsEmptyScrollArea")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(page)

            return scroll

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

        # patch-table-dynamique : colonnes selon les recepteurs de la campagne
        try:
            self._fill_docking_table_dynamic(table, csv_path)
        except Exception as exc:
            gui_debug("TABLEAU DYNAMIQUE ignore : " + str(exc))

        layout.addWidget(table, 1)

        scroll = QScrollArea()
        scroll.setObjectName("ResultsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll



    def _set_neutral_table_headers(self, table):
        # patch-entetes : en-tetes neutres tant qu'aucune campagne n'est chargee
        headers = list(self._docking_results_headers())
        if len(headers) >= 6:
            headers[3] = "Récepteur 1 (kcal/mol)"
            headers[4] = "Récepteur 2 (kcal/mol)"
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        for col in range(len(headers)):
            table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.Stretch
            )

    def refresh_docking_results(self):
        # patch-table-dynamique : une colonne par recepteur de la campagne
        try:
            self._fill_docking_table_dynamic()
        except Exception as exc:
            gui_debug("TABLEAU DYNAMIQUE ignore : " + str(exc))
            self._refresh_docking_results_legacy()

    def _receptor_table_label(self, receptor_id, fallback):
        """Nom court du recepteur (AcrB, MexB...) tire de son profil."""
        try:
            from src.docking.receptor_profile import (
                resolve_target_profile,
                short_label,
            )
            return str(short_label(resolve_target_profile(receptor_id)))
        except Exception:
            return fallback

    def _fill_docking_table_dynamic(self, table=None, csv_path=None):
        from src.campaign_table import normalize_docking_csv, campaign_shape

        if table is None:
            table = getattr(self, "docking_results_table", None)
        if table is None:
            return
        if csv_path is None:
            csv_path = getattr(self, "docking_results_csv", None)
        if not csv_path or not Path(csv_path).exists():
            table.setRowCount(0)
            self._set_neutral_table_headers(table)  # patch-entetes
            return

        data = normalize_docking_csv(csv_path)
        info = campaign_shape(data)
        receptors = info["receptors"]
        labels = {
            rid: self._receptor_table_label(rid, info["labels"][rid])
            for rid in receptors
        }

        base = self._docking_results_headers()
        headers = (
            list(base[:3])
            + [labels[rid] + " (kcal/mol)" for rid in receptors]
            + [base[-1]]
        )

        # Tout est calcule avant de toucher au tableau.
        rows = []
        for rank, (molecule, sub) in enumerate(
            data.groupby("molecule", sort=False), start=1
        ):
            families = [g for g in sub["groupe"] if g]
            cells = [str(rank), molecule, families[0] if families else ""]
            problems = []
            for rid in receptors:
                rec = sub[sub["receptor_id"] == rid]
                if rec.empty:
                    cells.append("")
                    problems.append(labels[rid] + " : absent")
                    continue
                value = rec["best_affinity"].iloc[0]
                cells.append("" if value != value else "%.3f" % value)
                status = str(rec["status"].iloc[0])
                if status.upper() != "OK":
                    problems.append(labels[rid] + " : " + status)
            cells.append("OK" if not problems else " ; ".join(problems))
            rows.append(cells)

        table.setRowCount(0)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        for col in range(len(headers)):
            table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.Stretch
            )
        for cells in rows:
            row = table.rowCount()
            table.insertRow(row)
            for col, value in enumerate(cells):
                table.setItem(row, col, QTableWidgetItem(str(value)))

    def _refresh_docking_results_legacy(self):

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
                # Le nom du dossier EST la cible : c'est ainsi que
                # batch_vina_engine/<cible>/docking_results.csv est
                # écrit. L'ancienne règle (« MexR si MexR apparaît dans
                # le chemin, sinon MexB ») étiquetait tout récepteur
                # importé comme « MexB ».
                single_target = path.parent.name or "MexB"

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

        scroll = QScrollArea()
        scroll.setObjectName("AnalysisTypeScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll





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

            # patch-entete : recharge le bandeau avec les recepteurs analyses
            try:
                self.window()._refresh_header_target()
            except Exception:
                pass

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
            table.verticalHeader().setVisible(False)
            configure_glass_table(table)

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
                QColor(COLORS["accent_dark"])
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
                QColor(COLORS["accent_dark"])
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
                table.verticalHeader().setVisible(False)
                configure_glass_table(table)

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
                    QColor(COLORS["accent_dark"])
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
                    + "- SI percentile > " + ("%g" % dual.get("threshold_percentile", 50)) + "\n"
                    + "- ΔG " + str((result.get("labels") or {}).get("y", "MexR"))
                    + " meilleur que le seuil "
                    + str((getattr(classification, "attrs", None) or {}).get("ref_name", "pyocyanine")).replace("pyocyanine", "piocyanine")
                    + " (" + str((getattr(classification, "attrs", None) or {}).get("seuil_risque_absolu", -8.289)) + " kcal/mol)"  # patch-libelles-gui
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


        # Style des onglets : entièrement piloté par les réglages (Paramètres > Onglets).

        # Les coins du QTabWidget::pane sont arrondis en QSS mais le
        # contenu de chaque onglet reste rectangulaire : on force un
        # vrai decoupage au pixel pour que rien ne depasse de l'arc.
        self._results_tabs_clip = apply_rounded_clip(
            self.results_tabs, radius=14
        )


        layout.addWidget(
            self.results_tabs,
            1
        )

        scroll = QScrollArea()
        scroll.setObjectName("AnalysisResultsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll


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
        self._interaction_viewer_loaded = False
        self._pending_interaction_complex = None

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

        self.batch_progress = QProgressBar()
        self.batch_progress.setRange(0, 100)
        self.batch_progress.hide()
        toolbar.addWidget(self.batch_progress)

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
                "Interaction 3D",
            ],
            self.switch_tab,
        )

        body.addWidget(self.secondary)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self.stack.addWidget(self.residues_page())
        self.stack.addWidget(self.plip_page())
        self.stack.addWidget(self.interaction_page())
        self.stack.addWidget(self.interaction_3d_page())

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
            for candidate_target in viz_bridge.known_target_labels():
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
        self.batch_progress.setValue(0)
        self.batch_progress.show()

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
        self.batch_progress.setValue(int((index / total) * 100))

    def _on_batch_finished(self, payload):

        self.batch_running = False
        self.batch_progress.hide()
        self.hit_results = payload.get("results", {})
        self.batch_errors = payload.get("errors", [])

        rows = []
        for key, data in self.hit_results.items():
            for res in data["interactions"]["summary"]:
                rows.append(
                    (
                        res["residue"],
                        res["chain"],
                        str(res["residue_id"]),
                        res["interaction_types"],
                        key,
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
        table.verticalHeader().setVisible(False)
        configure_glass_table(table)

        table.setHorizontalHeaderLabels(
            self._residues_table_headers()
        )

        for col in range(5):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        self.residues_table = table

        layout.addWidget(table, 1)

        scroll = QScrollArea()
        scroll.setObjectName("ResiduesScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

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
        self.plip_errors_label.setWordWrap(True)
        self.plip_errors_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.plip_errors_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Zone defilante independante : le texte peut grandir avec le
        # nombre d'erreurs accumulees, sans jamais faire deborder le
        # panneau ni pousser le reste de l'interface hors de la fenetre.
        plip_errors_scroll = QScrollArea()
        plip_errors_scroll.setWidgetResizable(True)
        plip_errors_scroll.setFrameShape(QFrame.NoFrame)
        plip_errors_scroll.setMinimumHeight(90)
        plip_errors_scroll.setMaximumHeight(320)
        plip_errors_scroll.setWidget(self.plip_errors_label)

        panel_layout.addWidget(plip_errors_scroll)

        layout.addWidget(panel)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("PlipScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

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

        viewer.setMinimumHeight(390)
        layout.addWidget(viewer, 1)

        scroll = QScrollArea()
        scroll.setObjectName("InteractionScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

    def interaction_3d_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.addWidget(
            self._t_label(
                "viz_tab_interaction3d",
                "Interaction 3D",
                "SectionTitle",
            )
        )
        # --- Initialisation de la vue ---
        self.interaction_3d_viewer = QWebEngineView()
        self.interaction_3d_viewer.setMinimumHeight(520)
        self.interaction_3d_viewer.loadFinished.connect(
            self._on_interaction_viewer_loaded
        )
        self.interaction_3d_viewer.setHtml(VIEWER_HTML)

        # --- Initialisation du poller maintenant que le viewer existe ---
        self._interaction_3d_viewer_poller = _ViewerDragRepaintPoller(self.interaction_3d_viewer)
        header.addStretch()

        self.interaction_3d_molecule_combo = QComboBox()
        self.interaction_3d_molecule_combo.currentTextChanged.connect(
            self._on_3d_molecule_changed
        )
        header.addWidget(self.interaction_3d_molecule_combo)
        layout.addLayout(header)

        panel = QFrame()
        panel.setObjectName("ContentPanel")
        panel.setProperty("skip_glass_elevation", True)  # patch-interaction3d : pas d'ombre portee sur un QWebEngineView
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 12, 14, 14)
        panel_layout.setSpacing(8)
        panel_layout.addWidget(
            self._t_label(
                "viz_interaction_3d_title",
                "Complexe 3D et résidus interactifs",
                "PanelTitle",
            )
        )


        panel_layout.addWidget(self.interaction_3d_viewer, 1)
        layout.addWidget(panel, 1)

        scroll = QScrollArea()
        scroll.setObjectName("Interaction3DScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)

        return scroll

    def _refresh_molecule_combo(self):

        molecules = sorted(self.hit_results.keys())

        combo = self.diagram_molecule_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(molecules)
        combo.blockSignals(False)

        combo_3d = self.interaction_3d_molecule_combo
        combo_3d.blockSignals(True)
        combo_3d.clear()
        combo_3d.addItems(molecules)
        combo_3d.blockSignals(False)

        if molecules:
            combo.setCurrentIndex(0)
            self._on_diagram_molecule_changed(molecules[0])
            combo_3d.setCurrentIndex(0)
            self._on_3d_molecule_changed(molecules[0])

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

    def _on_interaction_viewer_loaded(self, ok):
        self._interaction_viewer_loaded = bool(ok)
        if self._interaction_viewer_loaded:
            self._display_interaction_complex()

    def _on_3d_molecule_changed(self, molecule):
        if molecule and molecule in self.hit_results:
            self._display_interaction_complex(molecule)

    def _display_interaction_complex(self, molecule=None):
        if not self._interaction_viewer_loaded:
            return

        molecule = molecule or self.interaction_3d_molecule_combo.currentText()
        data = self.hit_results.get(molecule)
        if not data:
            return

        complex_path = Path(data.get("complex", ""))
        if not complex_path.exists():
            return

        try:
            pdb_text = complex_path.read_text(
                encoding="utf-8", errors="ignore"
            )
            interactions = data.get("interactions", {}).get("summary", [])
            interactions_json = json.dumps(interactions, ensure_ascii=False)
            script = (
                f"loadComplex({json.dumps(pdb_text)}, "
                f"{json.dumps(interactions_json)});"
            )
            self.interaction_3d_viewer.page().runJavaScript(script)
        except (OSError, TypeError, ValueError):
            return

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
            export_dir = viz_bridge.export_visualization_results(
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


class ThemeBackground(QWidget):
    """Paint a cover-scaled theme image behind the existing interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_paths = sorted(
            (Path(__file__).resolve().parents[2] / "image_theme").glob(
                "*.jpg"
            )
        )
        self._theme_index = (
            GLASS_PREFERENCES["theme_index"] % len(self._theme_paths)
            if self._theme_paths
            else 0
        )
        self._pixmap = QPixmap()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._load_theme()

    def _load_theme(self):
        if not self._theme_paths:
            return
        self._pixmap = QPixmap(str(self._theme_paths[self._theme_index]))
        self.update()

    def next_theme(self):
        if not self._theme_paths:
            return ""
        self._theme_index = (self._theme_index + 1) % len(self._theme_paths)
        GLASS_PREFERENCES["theme_index"] = self._theme_index
        _PREFERENCES.setValue("theme/index", self._theme_index)
        _PREFERENCES.sync()
        self._load_theme()
        return self.current_theme_name()

    def current_theme_name(self):
        if not self._theme_paths:
            return ""
        return self._theme_paths[self._theme_index].stem

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#0b1219"))

        if not self._pixmap.isNull() and self.width() and self.height():
            scale = max(
                self.width() / self._pixmap.width(),
                self.height() / self._pixmap.height(),
            )
            scaled_size = self._pixmap.size() * scale
            scaled = self._pixmap.scaled(
                scaled_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        # The veil keeps text, tables, and controls readable over any photo.
        veil = _theme_color("bg_veil_color")
        veil.setAlpha(_pct_alpha(GLASS_PREFERENCES.get("bg_veil_opacity", 70)))
        painter.fillRect(self.rect(), veil)


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
        self.theme_background = None

        self.create_toolbar()

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.status.showMessage(
            "Prêt — aucun calcul en cours"
        )

        self.build_interface()

        for table in self.findChildren(QTableWidget):
            configure_glass_table(table)

        apply_glass_elevation_to_children(
            self, {"ContentPanel", "ToolbarPanel"}
        )

        self.retranslate_ui()

        # Apparence : popups floutés, libellés personnalisés, réglages appliqués.
        install_glass_popup_manager(QApplication.instance())
        apply_runtime_preferences()

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

        if hasattr(self, "primary_tabs"):
            tab_labels = [
                t("side_docking"), t("nav_analysis"), t("nav_visualization"),
                t("nav_phytomolecules"),
            ]
            for btn, lbl in zip(self.primary_tabs, tab_labels):
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
            self.lang_action.setText(self._lang_button_text())
            self.lang_action.setToolTip(t("toolbar_tooltip_lang"))
        if hasattr(self, "theme_action"):
            self.theme_action.setText(t("toolbar_theme"))
            self.theme_action.setToolTip(t("toolbar_tooltip_theme"))
        if hasattr(self, "preferences_action"):
            self.preferences_action.setText(t("toolbar_preferences"))
            self.preferences_action.setToolTip(t("toolbar_tooltip_preferences"))
        if hasattr(self, "load_csv_action"):
            self.load_csv_action.setText(t("toolbar_load_csv"))
            self.load_csv_action.setToolTip(t("toolbar_tooltip_load_csv"))
        if hasattr(self, "about_action"):
            self.about_action.setText(t("toolbar_about"))

        if hasattr(self, "status"):
            self.status.showMessage(t("status_ready"))

    def _lang_button_text(self) -> str:
        """
        Texte du bouton de langue : precede d'un globe, seul symbole
        vraiment reconnu universellement pour "changer de langue" —
        sans ca, ce bouton se confondait visuellement avec les actions
        "Charger une analyse" / "A propos" qui n'ont rien a voir.
        """
        return f"🌐 {self.lang_mgr.native_name()}"

    def _on_toggle_language(self):
        self.lang_mgr.cycle_language()

    def _on_change_theme(self):
        if self.theme_background is None:
            return
        theme_name = self.theme_background.next_theme()
        self.theme_action.setToolTip(self.lang_mgr.t("toolbar_theme_tooltip_applied", name=theme_name))
        self.status.showMessage(self.lang_mgr.t("status_theme_applied", name=theme_name))

    def _open_preferences(self):
        dialog = GlassPreferencesDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status.showMessage(self.lang_mgr.t("status_glass_prefs_saved"))
        else:
            self.status.showMessage(self.lang_mgr.t("status_glass_prefs_unchanged"))

    def closeEvent(self, event):

        try:
            viz_bridge.cleanup_visualization_outputs()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage visualisation : {exc}")

        try:
            if hasattr(self, "credits_page"):
                self.credits_page.shutdown()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage threads Crédits : {exc}")

        try:
            if hasattr(self, "phyto_page"):
                self.phyto_page.shutdown()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage threads Phytomolecules : {exc}")

        try:
            end_session()
        except Exception as exc:
            gui_debug(f"Erreur nettoyage fin de session : {exc}")

        try:
            self.docking_page._session_manager.cleanup_session()
        except Exception as exc:
            gui_debug(
                f"Erreur nettoyage workspace de session : {exc}"
            )

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

        t = self.lang_mgr.t

        quit_action = QAction(t("menu_quit"), self)

        quit_action.triggered.connect(
            self.close
        )

        file_menu.addAction(quit_action)
        self.menu_action_quit = quit_action

        prepare_action = QAction(
            t("menu_prepare_ligands"), self
        )

        prepare_action.triggered.connect(
            lambda: self.primary_navigation.buttons[0].click()
        )

        docking_menu.addAction(prepare_action)
        self.menu_action_prepare = prepare_action

        launch_action = QAction(
            t("menu_launch_docking"), self
        )

        launch_action.triggered.connect(
            lambda: self.primary_navigation.buttons[0].click()
        )

        docking_menu.addAction(launch_action)
        self.menu_action_launch = launch_action

        analysis_action = QAction(
            t("menu_load_analysis_csv"),
            self
        )

        analysis_action.triggered.connect(
            self.load_statistics_analysis
        )

        analysis_menu.addAction(
            analysis_action
        )
        self.menu_action_load_analysis = analysis_action

        results_action = QAction(
            t("menu_view_results"), self
        )

        results_action.triggered.connect(
            lambda: self.primary_navigation.buttons[1].click()
        )

        analysis_menu.addAction(results_action)
        self.menu_action_results = results_action

        visualization_action = QAction(
            t("menu_open_visualization"), self
        )

        visualization_action.triggered.connect(
            lambda: self.primary_navigation.buttons[2].click()
        )

        visualization_menu.addAction(visualization_action)
        self.menu_action_visualization = visualization_action

        preferences_action = QAction(
            t("menu_preferences_soon"), self
        )

        preferences_action.setEnabled(False)

        tools_menu.addAction(preferences_action)
        self.menu_action_preferences_soon = preferences_action

        about_action = QAction(
            t("menu_about_vina"), self
        )

        about_action.triggered.connect(
            self.show_about_dialog
        )

        help_menu.addAction(about_action)
        self.menu_action_about = about_action

    def show_about_dialog(self):
        from PySide6.QtWidgets import QDialog

        t = self.lang_mgr.t

        dialog = QDialog(self)
        dialog.setWindowTitle(t("menu_about_vina"))
        dialog.setMinimumWidth(380)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

        text_label = QLabel(
            f"<b>{t('vina_app_name')}</b><br>"
            f"{t('vina_app_subtitle')}<br><br>"
            f"{t('about_pipeline_desc')}<br><br>"
            f'<a href="credits" style="text-decoration: underline;">{t("about_credits_link")}</a>'
        )
        text_label.setTextFormat(Qt.RichText)
        text_label.setOpenExternalLinks(False)
        text_label.setWordWrap(True)
        text_label.linkActivated.connect(
            lambda _link: self._open_credits_from_about(dialog)
        )
        layout.addWidget(text_label)

        close_button = LiquidGlassButton(t("scan_btn_close"))
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)

        dialog.exec()

    def _open_credits_from_about(self, dialog):
        # Le lien "Credits" de la boite "A propos" bascule vers la page
        # credits_page (switch_primary gere deja le scan paresseux du
        # dossier et le changement de page de travail).
        dialog.accept()
        self.switch_primary(4)

    # ------------------------------------------------------------------
    # TOOLBAR
    # ------------------------------------------------------------------

    def create_toolbar(self):

        toolbar = GlassToolBar(
            "Navigation"
        )
        self.addToolBar(toolbar)

        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        # C'est LA navigation principale depuis le patch13 (plus une
        # simple barre d'outils optionnelle) : un clic droit dessus ne
        # doit plus jamais permettre de la masquer, sous peine de ne
        # plus avoir aucun moyen de la faire revenir depuis l'interface
        # (la barre de menu qui offrait ce recours a ete supprimee).
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)

        # Les 3 destinations qui occupaient auparavant toute la hauteur
        # de la colonne "ESPACE DE TRAVAIL" deviennent des onglets
        # horizontaux ici : plus aucune colonne verticale dediee, tout
        # l'espace qu'elle occupait revient au contenu de chaque page.
        self.primary_tabs = []

        for index, text in enumerate([
            self.lang_mgr.t("side_docking"),
            self.lang_mgr.t("nav_analysis"),
            self.lang_mgr.t("nav_visualization"),
            self.lang_mgr.t("nav_phytomolecules"),
        ]):
            button = LiquidGlassToolButton()
            button.setObjectName("TopTab")
            button.setText(text)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            # Qt ne met pas la main de clic par defaut sur un
            # QToolButton : sans ca, rien ne "sent" cliquable au repos.
            button.setCursor(Qt.PointingHandCursor)

            button.clicked.connect(
                lambda checked=False, i=index: self.switch_primary(i)
            )

            self.primary_tabs.append(button)
            toolbar.addWidget(button)

        self.primary_tabs[0].setChecked(True)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        def _set_pointer_cursor(action):
            # Une QAction n'a pas de curseur propre : il faut recuperer
            # le vrai widget-bouton que la toolbar a cree pour elle.
            widget = toolbar.widgetForAction(action)
            if widget is not None:
                widget.setCursor(Qt.PointingHandCursor)

        self.lang_action = QAction(self._lang_button_text(), self)
        self.lang_action.setToolTip(self.lang_mgr.t("toolbar_tooltip_lang"))
        self.lang_action.triggered.connect(self._on_toggle_language)
        toolbar.addAction(self.lang_action)
        _set_pointer_cursor(self.lang_action)

        self.theme_action = QAction(self.lang_mgr.t("toolbar_theme"), self)
        self.theme_action.setToolTip(self.lang_mgr.t("toolbar_tooltip_theme"))
        self.theme_action.triggered.connect(self._on_change_theme)
        toolbar.addAction(self.theme_action)
        _set_pointer_cursor(self.theme_action)

        self.preferences_action = QAction(self.lang_mgr.t("toolbar_preferences"), self)
        self.preferences_action.setToolTip(self.lang_mgr.t("toolbar_tooltip_preferences"))
        self.preferences_action.triggered.connect(self._open_preferences)
        toolbar.addAction(self.preferences_action)
        _set_pointer_cursor(self.preferences_action)

        toolbar.addSeparator()

        # Rapatriees depuis l'ancien menu "Fichier/Analyse" (supprime) :
        # rien n'est perdu, juste deplace la ou il reste accessible.
        self.load_csv_action = QAction(self.lang_mgr.t("toolbar_load_csv"), self)
        self.load_csv_action.setToolTip(self.lang_mgr.t("toolbar_tooltip_load_csv"))
        self.load_csv_action.triggered.connect(self.load_statistics_analysis)
        toolbar.addAction(self.load_csv_action)
        _set_pointer_cursor(self.load_csv_action)

        self.about_action = QAction(self.lang_mgr.t("toolbar_about"), self)
        self.about_action.triggered.connect(self.show_about_dialog)
        toolbar.addAction(self.about_action)
        _set_pointer_cursor(self.about_action)

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------

    def _refresh_header_target(self):
        # patch-entete : la cible affichee suit la page active
        try:
            page = self.workspace.currentWidget()
            if page is self.analysis_page:
                text = self.analysis_page.campaign_summary()
            else:
                text = self.docking_page.target_combo.currentText()
            self.header_target_label.setText(text)
        except Exception as exc:
            gui_debug("En-tete cible ignore : " + str(exc))

    def build_interface(self):

        central = ThemeBackground()
        self.theme_background = central

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --------------------------------------------------------------
        # HEADER
        # --------------------------------------------------------------

        header = GlassPanel(radius=16, blur_strength=1.1)
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

        # La colonne "ESPACE DE TRAVAIL" (PrimaryNavigation) n'est plus
        # construite ici : ses 3 destinations sont desormais les onglets
        # horizontaux de la toolbar (voir create_toolbar()). Tout
        # l'espace qu'elle occupait revient au contenu de chaque page.
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

        self.workspace.currentChanged.connect(
            lambda _index: self._refresh_header_target()
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

        self.phyto_page = PhytoPage(lang_mgr=self.lang_mgr)

        self.workspace.addWidget(self.phyto_page)

        self.credits_page = CreditsPage()

        self.workspace.addWidget(
            self.credits_page
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

        if index != 4 and hasattr(self, "credits_page"):
            # On quitte (ou on ne va pas vers) l'onglet Credits : coupe
            # toute video en cours pour qu'elle ne continue pas a se
            # lire en arriere-plan une fois la page quittee.
            self.credits_page.stop_playback()

        self.workspace.setCurrentIndex(
            index
        )

        names = [
            self.lang_mgr.t("side_docking"),
            self.lang_mgr.t("nav_analysis"),
            self.lang_mgr.t("nav_visualization"),
            self.lang_mgr.t("nav_phytomolecules"),
        ]

        if 0 <= index < len(names):

            self.status.showMessage(
                self.lang_mgr.t("status_workspace_active", name=names[index])
            )

        if index == 2 and hasattr(self, "visualization_page"):
            self.visualization_page.ensure_batch_started()

        if index == 4 and hasattr(self, "credits_page"):
            # Le scan du dossier credit_du_logiciel (photos + videos)
            # ne demarre qu'a la premiere ouverture de l'onglet, et se
            # fait en arriere-plan : ouvrir "Credits" ne doit jamais
            # geler l'interface, meme avec des centaines de Mo de medias.
            self.credits_page.ensure_loaded()


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

    # Palette explicite : evite toute fuite du theme sombre du systeme
    # d'exploitation sur les sous-elements que le QSS ne couvre pas
    # explicitement (en-tetes verticaux, coins de tableaux, popups...).
    # Sans cela, Fusion retombe sur la palette du bureau (GTK/Yaru
    # sombre ici), d'ou les zones noires residuelles.
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["window"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["panel"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["panel"]))
    palette.setColor(QPalette.ToolTipText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor(COLORS["accent"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.PlaceholderText, QColor(COLORS["text_muted"]))
    palette.setColor(
        QPalette.Disabled, QPalette.WindowText, QColor(COLORS["text_muted"])
    )
    palette.setColor(
        QPalette.Disabled, QPalette.Text, QColor(COLORS["text_muted"])
    )
    palette.setColor(
        QPalette.Disabled, QPalette.ButtonText, QColor(COLORS["text_muted"])
    )

    app.setPalette(palette)

    apply_runtime_preferences()

    font = QFont(
        str(GLASS_PREFERENCES.get("font_family") or "Noto Sans"),
        10,
    )

    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
