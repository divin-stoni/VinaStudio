from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)


class ThemeManager:
    """Persistent glass theme state and the stylesheet it produces."""

    defaults = {
        "text_color": "#f4f1e8",
        "button_color": "#c99b63",
        "tab_color": "#ad8060",
        "scrollbar_color": "#c8a477",
        "status_color": "#8c735d",
        "button_alpha": 34,
        "tab_alpha": 26,
        "global_alpha": 28,
        "ambient_alpha": 22,
        "reflection_alpha": 42,
        "pastel_strength": 62,
        "glow_strength": 34,
        "popup_alpha": 78,
        "popup_blur": 8,
        "radius": 12,
        "refractive_index": 1.45,
        "background_index": 0,
    }

    def __init__(self, parent=None):
        self.settings = QSettings("VINA Studio", "VINA Studio")
        self.parent = parent
        self.state = {
            key: self.settings.value(f"theme/{key}", value)
            for key, value in self.defaults.items()
        }
        legacy_values = {
            "text_color": "#edf5ff",
            "button_color": "#78aee8",
            "tab_color": "#5f91c7",
            "scrollbar_color": "#8bb7e5",
            "status_color": "#7eb3df",
        }
        for key, legacy_value in legacy_values.items():
            if self.state[key] == legacy_value:
                self.state[key] = self.defaults[key]
                self.settings.setValue(f"theme/{key}", self.state[key])
        for key in ("button_color", "tab_color", "scrollbar_color", "status_color"):
            color = QColor(self.state[key])
            hue = color.hue()
            is_blue = hue >= 165 and hue <= 265 and color.saturation() >= 55
            is_black_status = key == "status_color" and color.lightness() < 24
            if is_blue or is_black_status:
                self.state[key] = self.defaults[key]
                self.settings.setValue(f"theme/{key}", self.state[key])
        if self.state["global_alpha"] == 100:
            self.state["global_alpha"] = self.defaults["global_alpha"]
            self.settings.setValue("theme/global_alpha", self.state["global_alpha"])
        if self.state["button_alpha"] == 72:
            self.state["button_alpha"] = self.defaults["button_alpha"]
            self.settings.setValue("theme/button_alpha", self.state["button_alpha"])
        if self.state["tab_alpha"] == 64:
            self.state["tab_alpha"] = self.defaults["tab_alpha"]
            self.settings.setValue("theme/tab_alpha", self.state["tab_alpha"])
        for key in (
            "button_alpha", "tab_alpha", "global_alpha", "ambient_alpha",
            "reflection_alpha", "pastel_strength", "glow_strength",
            "popup_alpha", "popup_blur", "radius", "background_index",
        ):
            self.state[key] = int(self.state[key])
        self.state["refractive_index"] = float(self.state["refractive_index"])

    @property
    def background_paths(self) -> list[Path]:
        root = Path(__file__).resolve().parents[2] / "image_theme"
        return sorted(root.glob("*.jpg")) + sorted(root.glob("*.jpeg")) + sorted(root.glob("*.png"))

    @property
    def background_path(self) -> Path | None:
        paths = self.background_paths
        if not paths:
            return None
        return paths[self.state["background_index"] % len(paths)]

    def set_value(self, key, value):
        if key not in self.defaults:
            raise KeyError(key)
        self.state[key] = value
        self.settings.setValue(f"theme/{key}", value)

    def next_background(self) -> Path | None:
        paths = self.background_paths
        if not paths:
            return None
        self.set_value("background_index", (self.state["background_index"] + 1) % len(paths))
        return self.background_path

    @staticmethod
    def _rgba(hex_color: str, alpha_percent: int) -> str:
        color = QColor(hex_color)
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {round(alpha_percent * 2.55)})"

    @staticmethod
    def _mix(first: str, second: str, amount: int) -> str:
        """Mix two colors; used to make the pastel and highlight layers real."""
        left, right = QColor(first), QColor(second)
        ratio = max(0.0, min(1.0, amount / 100.0))
        return QColor(
            round(left.red() * (1 - ratio) + right.red() * ratio),
            round(left.green() * (1 - ratio) + right.green() * ratio),
            round(left.blue() * (1 - ratio) + right.blue() * ratio),
        ).name()

    @staticmethod
    def fresnel_reflectance(index: float) -> float:
        """Normal-incidence Fresnel reflectance for glass against air."""
        return ((index - 1.0) / (index + 1.0)) ** 2

    def stylesheet(self) -> str:
        state = self.state
        button = self._rgba(state["button_color"], state["button_alpha"])
        tab = self._rgba(state["tab_color"], state["tab_alpha"])
        global_tint = self._rgba(state["tab_color"], state["global_alpha"])
        scrollbar = self._rgba(state["scrollbar_color"], 88)
        status = self._rgba(state["status_color"], 42)
        panel = self._rgba(state["tab_color"], min(46, max(22, state["global_alpha"] + 18)))
        panel_edge = self._rgba(state["text_color"], 40)
        pastel_button = self._mix(state["button_color"], "#fff7e8", state["pastel_strength"])
        pastel_tab = self._mix(state["tab_color"], "#fff7e8", state["pastel_strength"])
        reflection = self._rgba(state["text_color"], state["reflection_alpha"])
        ambient = self._rgba(state["tab_color"], state["ambient_alpha"])
        popup = self._rgba(pastel_tab, state["popup_alpha"])
        popup_edge = self._rgba(pastel_button, min(100, state["glow_strength"] + 42))
        popup_solid = QColor(pastel_tab).name()
        radius = state["radius"]
        return f"""
QMainWindow, QWidget#ThemeSurface {{
    color: {state['text_color']};
    background: transparent;
}}
QWidget, QLabel, QAbstractButton, QLineEdit, QTextEdit, QPlainTextEdit,
QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QRadioButton,
QTableWidget, QTableView, QTreeView, QListWidget, QHeaderView,
QStatusBar, QMenu, QDialog, QGroupBox, QTabBar::tab {{
    color: {state['text_color']};
}}
QMainWindow, QToolBar, QFrame, QStackedWidget, QScrollArea,
QAbstractScrollArea, QTableWidget, QTableView, QHeaderView, QTreeView,
QListWidget, QComboBox {{
    background: transparent;
    background-color: transparent;
}}
QToolButton, QPushButton {{
    color: {state['text_color']};
    background: {button};
    background-color: {button};
    border: 1px solid {self._rgba(state['button_color'], min(100, state['button_alpha'] + 28))};
    border-radius: {radius}px;
    outline: none;
}}
QToolButton:hover, QPushButton:hover {{
    background: {self._rgba(state['button_color'], min(100, state['button_alpha'] + 16))};
    background-color: {self._rgba(state['button_color'], min(100, state['button_alpha'] + 16))};
}}
QToolButton#TopTab, QToolButton#PrimaryNavigation, QToolButton#SecondaryTab {{
    color: {state['text_color']};
    background: {tab};
    background-color: {tab};
    border-radius: {radius}px;
}}
QToolButton#TopTab:checked, QToolButton#PrimaryNavigation:checked, QToolButton#SecondaryTab:checked {{
    background: {global_tint};
    background-color: {global_tint};
    border-color: {state['text_color']};
    border-width: 2px;
}}
QFrame#ContentPanel, QFrame#ToolbarPanel, QFrame#TopHeader, QFrame#NavigationHeader {{
    background: {global_tint};
    border-radius: {radius}px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {scrollbar};
    border-radius: {max(4, radius // 2)}px;
}}
QStatusBar {{
    color: {state['text_color']};
    background: {status};
    border-radius: {radius}px;
}}
QMenu, QComboBox, QMessageBox, QDialog {{
    color: {state['text_color']};
    background: {popup};
    background-color: {popup};
    border: 1px solid {popup_edge};
    border-radius: {radius}px;
}}
QMenu {{
    /* Wayland cannot reliably composite translucent native menus. */
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {self._mix(popup_solid, '#ffffff', 16)},
        stop:0.16 {popup_solid},
        stop:1 {self._mix(popup_solid, '#000000', 8)});
    background-color: {popup_solid};
    color: {state['text_color']};
    border: 1px solid {popup_edge};
    border-radius: {radius}px;
    selection-background-color: {self._rgba(pastel_button, 58)};
    outline: none;
    padding: 6px;
}}
QMenu::item {{
    color: {state['text_color']};
    background: transparent;
    border-radius: {max(6, radius - 4)}px;
    padding: 8px 12px;
}}
QMenu::item:selected {{
    color: {state['text_color']};
    background: {self._rgba(pastel_button, 58)};
    border: 1px solid {self._rgba(pastel_button, state['glow_strength'] + 28)};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {self._rgba(pastel_tab, max(20, state['global_alpha'] + 12))};
    border: 1px solid {self._rgba(pastel_button, state['glow_strength'] + 30)};
}}
QFrame#TopHeader, QFrame#ContentPanel, QFrame#ToolbarPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {reflection}, stop:0.18 {ambient}, stop:0.62 {panel}, stop:1 transparent);
}}
QFrame#ContentPanel, QFrame#ToolbarPanel, QFrame#TopHeader, QFrame#NavigationHeader {{
    background: {panel};
    background-color: {panel};
    border: 1px solid {panel_edge};
    border-top: 1px solid {self._rgba(state['text_color'], 34)};
    border-left: 1px solid {self._rgba(state['text_color'], 22)};
    border-bottom: 1px solid {self._rgba(state['button_color'], 48)};
    border-right: 1px solid {self._rgba(state['button_color'], 34)};
}}
QTableWidget::item, QTableView::item, QTreeView::item, QListWidget::item {{
    background: transparent;
}}
"""

    def popup_view_stylesheet(self) -> str:
        state = self.state
        pastel = self._mix(state["tab_color"], "#fff7e8", state["pastel_strength"])
        highlight = self._mix(state["button_color"], "#fff7e8", state["pastel_strength"])
        return f"""
QAbstractItemView {{
    color: {state['text_color']};
    background-color: {pastel};
    border: 1px solid {self._rgba(highlight, min(100, state['glow_strength'] + 42))};
    border-radius: {state['radius']}px;
    padding: 6px;
    outline: none;
    selection-background-color: {self._rgba(highlight, 70)};
    selection-color: {state['text_color']};
}}
QAbstractItemView::item {{
    color: {state['text_color']};
    background: transparent;
    border-radius: {max(6, state['radius'] - 4)}px;
    padding: 8px 12px;
}}
QAbstractItemView::item:selected, QAbstractItemView::item:hover {{
    color: {state['text_color']};
    background-color: {self._rgba(highlight, 70)};
}}
"""


class PreferencesDialog(QDialog):
    applied = Signal()

    def __init__(self, theme: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Préférences d'apparence")
        self.setMinimumWidth(460)
        # Les fenetres Qt translucides rendent parfois les QGroupBox noirs
        # sur Linux; le dialogue garde donc un fond verre controle.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        panel = theme._rgba(theme.state["tab_color"], 88)
        edge = theme._rgba(theme.state["button_color"], 70)
        pastel_button = theme._mix(theme.state["button_color"], "#fff7e8", theme.state["pastel_strength"])
        pastel_tab = theme._mix(theme.state["tab_color"], "#fff7e8", theme.state["pastel_strength"])
        self.setStyleSheet(f"""
            QDialog {{
                color: {theme.state['text_color']};
                background: {panel};
                background-color: {theme._rgba(pastel_tab, 92)};
                border: 1px solid {edge};
                border-radius: {theme.state['radius']}px;
            }}
            QDialog > QWidget {{ background: transparent; }}
            QLabel {{ color: {theme.state['text_color']}; background: transparent; }}
            QGroupBox {{
                color: {theme.state['text_color']};
                background: {theme._rgba(theme.state['tab_color'], 38)};
                background-color: {theme._rgba(pastel_tab, 64)};
                border: 1px solid {edge};
                border-radius: {theme.state['radius']}px;
                margin-top: 10px;
                padding: 12px 8px 8px 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                height: 5px;
                background: {theme._rgba(theme.state['text_color'], 24)};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                margin: -6px 0;
                background: {pastel_button};
                border: 1px solid {theme.state['text_color']};
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {theme._rgba(theme.state['button_color'], 72)};
                border-radius: 3px;
            }}
            QDialogButtonBox QPushButton {{
                color: {theme.state['text_color']};
                background: {theme._rgba(pastel_button, 42)};
                background-color: {theme._rgba(pastel_button, 68)};
                border: 1px solid {edge};
                border-radius: {theme.state['radius']}px;
                padding: 7px 18px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background: {theme._rgba(theme.state['button_color'], 70)};
                background-color: {theme._rgba(pastel_button, 88)};
            }}
        """)
        self._base_style = self.styleSheet()
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.addWidget(QLabel("Apparence liquide et transparence"))

        colors = QGroupBox("Couleurs")
        color_form = QFormLayout(colors)
        self.color_buttons = {}
        labels = {
            "text_color": "Texte",
            "button_color": "Boutons",
            "tab_color": "Onglets",
            "scrollbar_color": "Défilements",
            "status_color": "Barre d'état",
        }
        for key, label in labels.items():
            button = QPushButton()
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, k=key: self._choose_color(k))
            self.color_buttons[key] = button
            color_form.addRow(label, button)
        root.addWidget(colors)

        geometry = QGroupBox("Formes et transparence")
        form = QFormLayout(geometry)
        self.sliders = {}
        for key, label, minimum, maximum in (
            ("radius", "Rayon des formes", 0, 32),
            ("button_alpha", "Transparence des boutons", 10, 100),
            ("tab_alpha", "Transparence des onglets", 10, 100),
            ("global_alpha", "Transparence générale", 10, 100),
        ):
            slider = QSlider()
            slider.setOrientation(Qt.Horizontal)
            slider.setRange(minimum, maximum)
            slider.setValue(int(theme.state[key]))
            slider.valueChanged.connect(lambda value, k=key: self._set(k, value))
            self.sliders[key] = slider
            form.addRow(label, slider)
        root.addWidget(geometry)

        optical = QGroupBox("Optique du verre")
        optical_form = QFormLayout(optical)
        self.index_slider = QSlider()
        self.index_slider.setOrientation(Qt.Horizontal)
        self.index_slider.setRange(100, 250)
        self.index_slider.setValue(round(theme.state["refractive_index"] * 100))
        self.index_slider.valueChanged.connect(lambda value: self._set("refractive_index", value / 100))
        self.reflectance_label = QLabel()
        optical_form.addRow("Indice de réfraction", self.index_slider)
        optical_form.addRow("Réflexion Fresnel à 0°", self.reflectance_label)
        root.addWidget(optical)

        dynamics = QGroupBox("Vie du verre")
        dynamics_form = QFormLayout(dynamics)
        self.dynamic_sliders = {}
        for key, label, minimum, maximum in (
            ("pastel_strength", "Douceur pastel", 0, 100),
            ("ambient_alpha", "Lumière ambiante", 0, 60),
            ("reflection_alpha", "Éclat / réflexion", 0, 100),
            ("glow_strength", "Halo des boutons et onglets", 0, 80),
            ("popup_alpha", "Transparence menus déroulants", 20, 100),
            ("popup_blur", "Intensité givrée des menus", 0, 24),
        ):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(minimum, maximum)
            slider.setValue(int(theme.state[key]))
            slider.valueChanged.connect(lambda value, k=key: self._set(k, value))
            self.dynamic_sliders[key] = slider
            dynamics_form.addRow(label, slider)
        root.addWidget(dynamics)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._refresh()

    def _set(self, key, value):
        self.theme.set_value(key, value)
        self._refresh()
        self._refresh_dialog_style()
        self.applied.emit()

    def _choose_color(self, key):
        color = QColorDialog.getColor(QColor(self.theme.state[key]), self)
        if color.isValid():
            self.theme.set_value(key, color.name())
            self._refresh()
            self._refresh_dialog_style()
            self.applied.emit()

    def _refresh(self):
        for key, button in self.color_buttons.items():
            color = QColor(self.theme.state[key])
            button.setText(color.name().upper())
            button.setStyleSheet(f"background: {color.name()}; color: {'#111' if color.lightness() > 150 else '#fff'};")
        reflection = self.theme.fresnel_reflectance(float(self.theme.state["refractive_index"]))
        self.reflectance_label.setText(f"{reflection * 100:.2f} %")

    def _refresh_dialog_style(self):
        pastel_tab = self.theme._mix(
            self.theme.state["tab_color"],
            "#fff7e8",
            self.theme.state["pastel_strength"],
        )
        pastel_button = self.theme._mix(
            self.theme.state["button_color"],
            "#fff7e8",
            self.theme.state["pastel_strength"],
        )
        self.setStyleSheet(self._base_style + f"""
            QDialog {{
                color: {self.theme.state['text_color']};
                background-color: {self.theme._rgba(pastel_tab, 92)};
            }}
            QLabel, QGroupBox {{ color: {self.theme.state['text_color']}; }}
            QGroupBox {{
                background-color: {self.theme._rgba(pastel_tab, 64)};
                border-color: {self.theme._rgba(pastel_button, 70)};
            }}
            QSlider::handle:horizontal {{
                background: {pastel_button};
                border-color: {self.theme.state['text_color']};
            }}
            QSlider::sub-page:horizontal {{
                background: {self.theme._rgba(pastel_button, 72)};
            }}
            QDialogButtonBox QPushButton {{
                color: {self.theme.state['text_color']};
                background-color: {self.theme._rgba(pastel_button, 68)};
            }}
        """)

    def _accept(self):
        self.applied.emit()
        self.accept()
