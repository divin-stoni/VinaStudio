import sys, shutil, py_compile, datetime, ast
from pathlib import Path

DEFAULT = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui" / "main_window.py"
MW = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
BACKUP_DIR = MW.parent.parent.parent / "_patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

text = MW.read_text(encoding="utf-8")
if "_dark_tokens" in text:
    print("Deja patche (_dark_tokens present). Rien a faire.")
    sys.exit(0)

REPL = []

# ---------------------------------------------------------------- 1. schema
REPL.append(("groupe Zones sombres",
'_G_POP = "Menus et flou"\n',
'_G_POP = "Menus et flou"\n_G_DARK = "Zones sombres"\n'))

REPL.append(("reglages Zones sombres",
'    _spec("popup_tooltips", "Appliquer aussi aux info-bulles", "bool", True, _G_POP),\n]\n',
'''    _spec("popup_tooltips", "Appliquer aussi aux info-bulles", "bool", True, _G_POP),
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
'''))

REPL.append(("valeurs Auto",
'    "popup_hover_text_color": lambda: _theme_color("text_color"),\n}\n',
'''    "popup_hover_text_color": lambda: _theme_color("text_color"),
    "dialog_color": lambda: _theme_color("panel_tint"),
    "header_color": lambda: _theme_color("button_tint"),
    "header_text_color": lambda: _theme_color("text_color"),
}
'''))

# ----------------------------------------------- 2. jetons suivis en direct
REPL.append(("jetons suivis",
'''_TEXT_TOKENS = (
    "text", "text_secondary", "text_muted",
    "accent_dark", "accent_ink", "success", "warning", "danger",
)
''',
'''_TEXT_TOKENS = (
    "text", "text_secondary", "text_muted",
    "accent_dark", "accent_ink", "success", "warning", "danger",
    "panel", "surface", "surface_alt", "window", "window_gradient",
    "glass", "glass_soft", "glass_strong", "glass_sheen", "viewer", "dialog_bg",
)
'''))

# ------------------------------------ 3. calcul des jetons sombres (pur Python)
REPL.append(("fonction _dark_tokens",
'def _refresh_preference_palette():\n',
'''def _clamp255(value):
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
'''))

REPL.append(("mise a jour de COLORS",
'    COLORS["danger"] = _theme_color("danger_color").name()\n    _remember_tokens()\n',
'''    COLORS["danger"] = _theme_color("danger_color").name()

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
'''))

# ------------------------------------------------ 4. palette Qt de l'application
REPL.append(("palette : etat",
'    state = (COLORS["text"], COLORS["text_muted"])\n',
'''    state = (
        COLORS["text"], COLORS["text_muted"], COLORS["window"],
        COLORS["panel"], COLORS["surface"], COLORS["surface_alt"],
    )
'''))

REPL.append(("palette : couleurs de fond",
'    palette.setColor(QPalette.ToolTipText, text)\n    palette.setColor(QPalette.PlaceholderText, muted)\n    app.setPalette(palette)\n',
'''    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.PlaceholderText, muted)
    palette.setColor(QPalette.Window, QColor(COLORS["window"]))
    palette.setColor(QPalette.Base, QColor(COLORS["panel"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["panel"]))
    app.setPalette(palette)
'''))

# ---------------------------------------- 5. feuille de style dynamique (QSS)
REPL.append(("QSS : calcul des regles sombres",
'    btn_text_hover = _theme_color("button_text_hover_color").name()\n\n    return f"""\n',
'''    btn_text_hover = _theme_color("button_text_hover_color").name()

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
'''))

REPL.append(("QSS : ajout des regles sombres",
'    """ + _tab_text_qss() + _tab_bar_qss() + _popup_qss()\n',
'    """ + dark_qss + _tab_text_qss() + _tab_bar_qss() + _popup_qss()\n'))

# --------------------------- 6. dialogue « Choisir un récepteur » (fond opaque)
REPL.append(("dialogue Choisir un recepteur",
'''        self.setWindowTitle("Choisir un récepteur")
        self.setModal(True)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {COLORS["panel"]};
''',
'''        self.setWindowTitle("Choisir un récepteur")
        self.setModal(True)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {COLORS["dialog_bg"]};
'''))

# ------------------------------------------------------------------ application
backup = BACKUP_DIR / f"main_window.py.backup_darkzones_{STAMP}"
shutil.copy2(MW, backup)
print("Sauvegarde :", backup)

new_text = text
for label, old, new in REPL:
    n = new_text.count(old)
    if n != 1:
        print(f"ECHEC bloc « {label} » : {n} occurrence(s) au lieu de 1. Rien n'a été modifié.")
        sys.exit(1)
    new_text = new_text.replace(old, new)
    print(f"OK  {label}")

MW.write_text(new_text, encoding="utf-8")

try:
    py_compile.compile(str(MW), doraise=True)
    print("py_compile : OK")
except Exception as exc:
    print("py_compile ECHEC :", exc)
    shutil.copy2(backup, MW)
    print("main_window.py restauré depuis la sauvegarde.")
    sys.exit(1)

# ------- Vérification : avec les réglages par défaut, RIEN ne doit changer -------
tree = ast.parse(new_text)
src = "\n".join(
    ast.get_source_segment(new_text, n)
    for n in tree.body
    if isinstance(n, ast.FunctionDef) and n.name in ("_clamp255", "_dark_tokens")
)
ns = {}
exec(src, ns)
got = ns["_dark_tokens"]((15, 28, 42), (15, 23, 33), (17, 28, 38), 160)
expected = {
    "panel": "#0f1c2a",
    "surface": "#101d2b",
    "surface_alt": "#152739",
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
}
bad = [k for k in expected if got.get(k) != expected[k]]
if bad:
    print("ECHEC vérification des valeurs par défaut :", bad)
    shutil.copy2(backup, MW)
    print("main_window.py restauré depuis la sauvegarde.")
    sys.exit(1)
print("Vérification : valeurs par défaut identiques à l'apparence d'origine (10/10).")

print("\nRESUME : nouvel onglet « Zones sombres » dans les paramètres d'apparence.")
