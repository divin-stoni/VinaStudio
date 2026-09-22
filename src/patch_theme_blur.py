#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch VinaStudio — apparence 100 % paramétrable + popups floutés + libellés éditables.

  * Menus contextuels, listes déroulantes, info-bulles : thème commun translucide
    avec un VRAI flou de l'arrière-plan (rayon réglable) ;
  * couleurs des onglets (repos / survol / actif), boutons, texte, polices,
    tailles, messages d'état : tout est réglable depuis « Paramètres » ;
  * tous les libellés de l'interface sont remplaçables (onglet « Libellés ») ;
  * corrige la feuille de style des onglets de résultats (un « ); » en trop
    la rendait invalide) et ré-applique les préférences après construction.

Usage :  python3 patch_theme_blur.py [chemin/vers/main_window.py]
Sauvegarde horodatée automatique, remplacement de blocs exacts (tout ou rien),
vérification ast.parse, restauration automatique en cas d'erreur.
"""
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui" / "main_window.py"
TARGET = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT


BLOCK_SCHEMA = r'''

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

'''

BLOCK_ENGINE = r'''# ============================================================================
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
    """ + _tab_text_qss() + _tab_bar_qss() + _popup_qss()


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
    state = (COLORS["text"], COLORS["text_muted"])
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
        app.installEventFilter(self)

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


def install_glass_popup_manager(app=None):
    """Installe (une seule fois) le gestionnaire de popups floutés."""
    app = app or QApplication.instance()
    if app is None:
        return None
    manager = getattr(app, "_glass_popup_manager", None)
    if manager is None:
        manager = GlassPopupManager(app)
        app._glass_popup_manager = manager
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


'''

BLOCK_GLASS = r'''_GLASS_KINDS = {
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


'''

BLOCK_DIALOG = r'''from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QAbstractItemView as _QAIV


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


'''


class PatchError(Exception):
    pass


def replace_once(text, old, new, name):
    n = text.count(old)
    if n != 1:
        raise PatchError(f"{name} : ancre trouvée {n} fois (attendu : 1)")
    return text.replace(old, new)


def replace_between(text, start, end, new, name):
    i = text.count(start)
    if i != 1:
        raise PatchError(f"{name} : marqueur de début trouvé {i} fois (attendu : 1)")
    a = text.index(start)
    b = text.find(end, a + len(start))
    if b < 0:
        raise PatchError(f"{name} : marqueur de fin introuvable")
    return text[:a] + new + text[b:]


def build(src):
    report = []

    def step(name, fn):
        nonlocal src
        src = fn(src)
        report.append(name)

    # 1. Schéma des réglages, juste après le dictionnaire GLASS_PREFERENCES
    step("Schéma des réglages (≈ 60 paramètres)", lambda s: replace_once(
        s,
        '    "theme_index": int(_PREFERENCES.value("theme/index", 0)),\n}\n',
        '    "theme_index": int(_PREFERENCES.value("theme/index", 0)),\n}\n' + BLOCK_SCHEMA,
        "schéma"))

    # 2. Moteur : palette, feuilles de style, popups floutés, libellés
    step("Moteur d'apparence (palette, QSS, flou des popups, libellés)", lambda s: replace_between(
        s,
        'def _refresh_preference_palette():\n    """Refresh shared accent colors before APP_STYLE is formatted."""',
        'COLORS = {\n    "window": "#0f1721",',
        BLOCK_ENGINE + "\n",
        "moteur"))

    # 3. APP_STYLE devient reconstructible (polices pilotées par les réglages)
    step("Style de base reconstructible (police / taille)", lambda s: replace_once(
        s,
        'APP_STYLE = f"""\nQMainWindow {{\n    background: {COLORS["window_gradient"]};\n}}\n\n'
        'QWidget {{\n    font-family: "Noto Sans", "Segoe UI", sans-serif;\n    font-size: 13px;\n'
        '    color: {COLORS["text"]};\n}}\n',
        'def _build_app_style():\n    """Feuille de style de base, reconstruite à chaque changement de réglage."""\n'
        '    return f"""\nQMainWindow {{\n    background: {COLORS["window_gradient"]};\n}}\n\n'
        'QWidget {{\n    font-family: "{GLASS_PREFERENCES["font_family"]}", "Noto Sans", "Segoe UI", sans-serif;\n'
        '    font-size: {int(GLASS_PREFERENCES["font_size"])}px;\n    color: {COLORS["text"]};\n}}\n',
        "APP_STYLE (début)"))
    step("Style de base : constante APP_STYLE conservée", lambda s: replace_once(
        s,
        'QMessageBox QPushButton {{\n    min-width: 76px;\n}}\n"""\n',
        'QMessageBox QPushButton {{\n    min-width: 76px;\n}}\n"""\n\n\nAPP_STYLE = _build_app_style()\n',
        "APP_STYLE (fin)"))

    # 4. Verre : boutons et onglets pilotés par les réglages
    step("Boutons et onglets de verre (couleurs, survol, rayon, reflet)", lambda s: replace_between(
        s,
        'def _glass_tint(alpha, factor=1.0, kind="button"):',
        'class GlassPanel(QFrame):',
        BLOCK_GLASS,
        "verre"))

    # 5. Dialogue de paramètres généré depuis le schéma
    step("Dialogue Paramètres (généré + onglet Libellés)", lambda s: replace_between(
        s,
        'class GlassPreferencesDialog(QDialog):',
        'def create_button(text, primary=False):',
        BLOCK_DIALOG,
        "dialogue"))

    # 6. Onglets de résultats : feuille invalide supprimée (le style est global)
    step("Onglets de résultats : ancien style invalide retiré", lambda s: replace_between(
        s,
        '        panel = _preference_color("panel_tint")\n        self.results_tabs.setStyleSheet(\n',
        '        # Les coins du QTabWidget::pane sont arrondis en QSS mais le',
        '        # Style des onglets : entièrement piloté par les réglages (Paramètres > Onglets).\n\n',
        "onglets de résultats"))

    # 7. Voile du fond réglable
    step("Voile du fond réglable", lambda s: replace_once(
        s,
        '        painter.fillRect(self.rect(), QColor(7, 15, 24, 178))\n',
        '        veil = _theme_color("bg_veil_color")\n'
        '        veil.setAlpha(_pct_alpha(GLASS_PREFERENCES.get("bg_veil_opacity", 70)))\n'
        '        painter.fillRect(self.rect(), veil)\n',
        "voile"))

    # 8. Installation à la fin de MainWindow.__init__ et police par défaut
    step("Installation au démarrage de la fenêtre", lambda s: replace_once(
        s,
        '        self.retranslate_ui()\n\n    def retranslate_ui(self, _code=None):',
        '        self.retranslate_ui()\n\n'
        '        # Apparence : popups floutés, libellés personnalisés, réglages appliqués.\n'
        '        install_glass_popup_manager(QApplication.instance())\n'
        '        apply_runtime_preferences()\n\n'
        '    def retranslate_ui(self, _code=None):',
        "installation"))
    step("Police par défaut lue dans les réglages", lambda s: replace_once(
        s,
        '    font = QFont(\n        "Noto Sans",\n        10,\n    )\n',
        '    font = QFont(\n        str(GLASS_PREFERENCES.get("font_family") or "Noto Sans"),\n        10,\n    )\n',
        "police"))
    return src, report


def main():
    print(f"Cible : {TARGET}")
    if not TARGET.is_file():
        print("ERREUR : fichier introuvable. Passe le chemin en argument :")
        print("  python3 patch_theme_blur.py /chemin/vers/main_window.py")
        return 1
    original = TARGET.read_text(encoding="utf-8")
    if "_THEME_SCHEMA" in original:
        print("Patch déjà appliqué (schéma présent) : rien à faire.")
        return 0
    try:
        patched, report = build(original)
    except PatchError as exc:
        print(f"ERREUR : {exc}")
        print("Aucun fichier modifié (le fichier a probablement changé depuis la version attendue).")
        return 2
    try:
        ast.parse(patched)
        compile(patched, str(TARGET), "exec")
    except SyntaxError as exc:
        print(f"ERREUR de syntaxe dans le résultat : {exc}")
        print("Aucun fichier modifié.")
        return 3

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.name}.backup_{stamp}")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(patched, encoding="utf-8")
    try:
        ast.parse(TARGET.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        shutil.copy2(backup, TARGET)
        print(f"ERREUR après écriture : {exc} — fichier restauré depuis la sauvegarde.")
        return 4

    print(f"Sauvegarde : {backup}")
    for line in report:
        print(f"  [OK] {line}")
    print(f"Lignes : {len(original.splitlines())} -> {len(patched.splitlines())}")
    print("Syntaxe vérifiée (ast.parse). Relance VinaStudio, puis ouvre Paramètres.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
