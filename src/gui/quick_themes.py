"""Thèmes rapides pour VINA Studio (version 2, palettes réglées image par image).

Un thème rapide = un jeu de réglages ``glass/*`` (mêmes clés que
image_theme/default_theme.json) + une image de fond.

Principe de conception (évite le « bleu sur bleu ») :
  * les boutons sont du verre neutre (blanc) ; l'accent est réservé aux
    éléments actifs : onglet actif, barre d'état, cases, titres ;
  * panneaux, champs et cartes sont neutres, légèrement teintés vers le fond
    du thème, jamais de la couleur d'accent ;
  * les couleurs de texte sont corrigées automatiquement pour garder un
    contraste lisible (ratio >= 4,5 pour le texte principal).

L'application passe par _set_value puis _apply_now, comme « Réinitialiser ».
"""
from __future__ import annotations

import json
import random
from pathlib import Path

IMAGE_DIR = Path(__file__).resolve().parents[2] / "image_theme"


# ------------------------------------------------------------------ couleurs
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)


def _shade(h, f):
    """f > 0 éclaircit, f < 0 assombrit."""
    r, g, b = _rgb(h)
    if f >= 0:
        return _hex((c + (255 - c) * f for c in (r, g, b)))
    return _hex((c * (1 + f) for c in (r, g, b)))


def _mix(a, b, t):
    """t = part de b."""
    return _hex(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b)))


def _lum(h):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _ensure(fg, bg, minimum):
    """Éclaircit ou assombrit `fg` jusqu'à un contraste suffisant sur `bg`."""
    toward = "#ffffff" if _lum(bg) < 0.4 else "#000000"
    out = fg
    for _ in range(14):
        if _ratio(out, bg) >= minimum:
            break
        out = _mix(out, toward, 0.12)
    return out


# ------------------------------------------------------------------- thèmes
# Chaque image a été regardée ; l'accent et le fond sombre ("deep") viennent
# de ses couleurs. "veil" = opacité du voile posé sur l'image (lisibilité).
DARK = {
    "Graphite":          dict(image="black-background", accent="#c0c6cf", deep="#14161a", veil=35),
    "Aurore boréale":    dict(image="vincent-guth-62V7ntlKgL8-unsplash", accent="#5fe0a0", deep="#0b1713", veil=40),
    "Molécules":         dict(image="pexels-googledeepmind-25626509", accent="#5aa9ff", deep="#0b1626", veil=45),
    "Voie lactée":       dict(image="greg-rakozy-oMpAz-DN-9I-unsplash", accent="#b48cf0", deep="#100e1a", veil=38),
    "Horizon":           dict(image="steve-a-johnson-PyOuwV2_dyA-unsplash", accent="#5fd3c7", deep="#08141a", veil=30),
    "ADN":               dict(image="pexels-nicola-narracci-157460431-35967917", accent="#9fb4ff", deep="#080a16", veil=30),
}
LIGHT = {
    "Verre clair":       dict(image="texture-ciment-fond-beton-espace-vide_53876-129755", accent="#1f4fbf", veil=55),
    "Laboratoire":       dict(image="pexels-mikhail-nilov-8851079", accent="#1f7a4d", veil=62),
}

THEMES = {"Enregistré": {"kind": "saved"},
          "Écran de démarrage": {"kind": "startup"}}
for _n in DARK:
    THEMES[_n] = {"kind": "dark", **DARK[_n]}
for _n in LIGHT:
    THEMES[_n] = {"kind": "light", **LIGHT[_n]}
THEMES["Aléatoire"] = {"kind": "random"}
THEMES["Personnalisé"] = {"kind": "custom"}


def _find_image(stem):
    if not stem or not IMAGE_DIR.is_dir():
        return None
    for p in sorted(IMAGE_DIR.glob(stem + ".*")):
        if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
            return p
    return None


def _load_saved_preset():
    try:
        return json.loads((IMAGE_DIR / "default_theme.json").read_text(encoding="utf-8"))
    except Exception:
        return {"glass": {}, "background": None}


# --------------------------------------------------------------- construction
def _glass_dark(spec):
    acc, deep = spec["accent"], spec["deep"]
    win = _shade(deep, -0.15)
    card = _shade(deep, 0.06)
    status_bg = _shade(acc, -0.5)
    panel = _mix(_shade(deep, 0.24), acc, 0.08)
    # couleur réellement vue sous le texte : panneau (78 %) sur fond sombre
    eff = _mix(_shade(deep, -0.1), panel, 0.78)
    g = {
        "base_color": deep, "window_color": win, "field_color": _shade(deep, 0.03),
        "card_color": card, "viewer_color": _shade(deep, -0.35),
        "bg_veil_color": _shade(deep, -0.45), "bg_veil_opacity": str(spec["veil"]),
        "dialog_color": "",
        "text_color": _ensure("#f1f5f9", eff, 7.0),
        "text_secondary_color": _ensure("#cbd5e1", eff, 5.0),
        "text_muted_color": _ensure("#a3b1c2", eff, 4.0),
        "title_color": _ensure(_shade(acc, 0.35), eff, 5.5),
        "status_text_color": _ensure("#ffffff", status_bg, 4.5),
        "tint": acc,
        "accent_green": status_bg,
        "panel_tint": panel,
        "scrollbar_tint": "#ffffff",
        "button_tint": "#ffffff", "button_border_color": "#ffffff",
        "button_pressed_tint": _shade(acc, 0.3),
        "tab_tint": _shade(deep, 0.30), "tab_hover_tint": _shade(deep, 0.5),
        "tab_active_tint": acc, "tab_border_color": "#ffffff",
        "tab_text_active_color": "#ffffff",
        "popup_tint": _shade(deep, 0.08), "popup_border_color": _shade(acc, 0.4),
        "success_color": "#5fd3a1", "warning_color": "#f4c66b", "danger_color": "#ff8a8a",
        # textes de boutons, onglets, listes : vides = couleur d'origine
        "button_text_color": "", "button_text_hover_color": "",
        "tab_text_color": "", "tab_text_hover_color": "",
        "popup_text_color": "", "popup_hover_text_color": "",
        "header_text_color": "", "header_color": "",
        # opacités
        "opacity": "26", "panel_opacity": "78", "card_opacity": "66",
        "button_opacity": "20", "tab_opacity": "58", "tab_active_opacity": "34",
        "popup_opacity": "82",
    }
    return g


def _glass_light(spec):
    acc = spec["accent"]
    ink, soft, mute = "#1f2933", "#44505c", "#66727f"
    status_bg = acc
    g = {
        "base_color": "#ffffff", "window_color": "#f4f7fb", "field_color": "#ffffff",
        "card_color": "#ffffff", "viewer_color": "#0b1219",
        "bg_veil_color": "#ffffff", "bg_veil_opacity": str(spec["veil"]),
        "dialog_color": "#ffffff",
        "text_color": ink, "text_secondary_color": soft, "text_muted_color": mute,
        "title_color": _ensure(acc, "#f4f7fb", 4.5),
        "status_text_color": _ensure("#ffffff", status_bg, 4.5),
        "tint": acc, "accent_green": status_bg,
        "panel_tint": "#ffffff", "scrollbar_tint": "#8a95a3",
        "button_tint": _mix("#ffffff", acc, 0.12), "button_border_color": "#aeb8c4",
        "button_pressed_tint": _mix("#ffffff", acc, 0.30),
        "tab_tint": "#ffffff", "tab_hover_tint": _mix("#ffffff", acc, 0.15),
        "tab_active_tint": _mix("#ffffff", acc, 0.30), "tab_border_color": "#aeb8c4",
        "tab_text_active_color": _ensure(acc, "#e8eef9", 4.5),
        "popup_tint": "#ffffff", "popup_border_color": "#aeb8c4",
        "success_color": "#15803d", "warning_color": "#b45309", "danger_color": "#b91c1c",
        "button_text_color": ink, "button_text_hover_color": _ensure(acc, "#ffffff", 4.5),
        "tab_text_color": ink, "tab_text_hover_color": _ensure(acc, "#ffffff", 4.5),
        "popup_text_color": ink, "popup_hover_text_color": _ensure(acc, "#ffffff", 4.5),
        "header_text_color": _ensure(acc, "#ffffff", 4.5), "header_color": "#ffffff",
        "opacity": "30", "panel_opacity": "86", "card_opacity": "88",
        "button_opacity": "30", "tab_opacity": "72", "tab_active_opacity": "40",
        "popup_opacity": "94",
    }
    return g


def _glass_startup():
    """Même palette que l'écran de démarrage (startup.py) : fond blanc,
    titres #1f4fbf, textes #1f2933 / #44505c / #6b7785."""
    g = _glass_light(dict(accent="#1f4fbf", veil=100))
    g.update({
        "bg_veil_opacity": "100", "title_size": "22",
        "text_secondary_color": "#44505c", "text_muted_color": "#6b7785",
    })
    return g


def resolve_theme(name, rng=None):
    """-> (glass dict | None, fond, libellé). fond : Path, None (aucune image)
    ou "keep" (ne pas toucher au fond)."""
    rng = rng or random
    spec = THEMES.get(name)
    if spec is None:
        return None, "keep", f"Thème inconnu : {name}"
    kind = spec["kind"]
    if kind == "custom":
        return None, "keep", "Personnalisé : réglez librement les options ci-dessous"
    if kind == "random":
        pick = rng.choice([n for n, s in THEMES.items() if s["kind"] in ("dark", "light")])
        glass, bg, _ = resolve_theme(pick, rng)
        return glass, bg, f"Aléatoire → {pick}"
    if kind == "saved":
        preset = _load_saved_preset()
        bg = "keep"
        nm = preset.get("background")
        if nm and (IMAGE_DIR / nm).is_file():
            bg = IMAGE_DIR / nm
        return dict(preset.get("glass", {})), bg, "Thème enregistré"
    if kind == "startup":
        return _glass_startup(), None, name
    glass = (_glass_dark if kind == "dark" else _glass_light)(spec)
    img = _find_image(spec.get("image"))
    return glass, (img if img else "keep"), name


def _coerce(value, default):
    try:
        if isinstance(default, bool):
            return str(value).strip().lower() in ("1", "true", "yes", "oui")
        if isinstance(default, int):
            return int(float(value))
        if isinstance(default, float):
            return float(value)
    except (TypeError, ValueError):
        return default
    return "" if value is None else str(value)


# ----------------------------------------------------------------- application
def apply_quick_theme(name, dialog, schema, rng=None):
    glass, bg, label = resolve_theme(name, rng)
    if glass is not None:
        specs = {s["key"]: s for s in schema}
        for key, val in glass.items():
            spec = specs.get(key)
            if spec is None:
                continue
            dialog._set_value(key, _coerce(val, spec["default"]))
        if bg != "keep":
            try:
                host = dialog.parent()
                bgw = getattr(host, "theme_background", None)
                if bgw is not None:
                    bgw.set_background(bg)
            except Exception:
                pass
        try:
            dialog._style_timer.stop()
        except Exception:
            pass
        dialog._apply_now()
    return label


def build_quick_theme_bar(dialog, schema):
    from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

    bar = QWidget()
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(QLabel("Thèmes rapides :"))
    combo = QComboBox()
    combo.addItems(list(THEMES))
    lay.addWidget(combo, 1)
    rnd = QPushButton("Aléatoire")
    lay.addWidget(rnd)
    info = QLabel("")
    lay.addWidget(info)

    def run(name):
        info.setText(apply_quick_theme(name, dialog, schema))

    combo.activated.connect(lambda _i: run(combo.currentText()))
    rnd.clicked.connect(lambda: run("Aléatoire"))
    bar.combo = combo
    return bar
