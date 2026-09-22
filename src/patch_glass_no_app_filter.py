import sys, shutil, py_compile, datetime
from pathlib import Path

SRC = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src"
MW = SRC / "gui" / "main_window.py"
MAIN = SRC / "main.py"
BACKUP_DIR = SRC.parent / "_patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def backup(p):
    dest = BACKUP_DIR / f"{p.name}.backup_{STAMP}"
    shutil.copy2(p, dest)
    return dest

def restore(p, b):
    shutil.copy2(b, p)

mw_text = MW.read_text(encoding="utf-8")
if "_GlassProxyStyle" in mw_text:
    print("Deja patche (_GlassProxyStyle present). Rien a faire.")
    sys.exit(0)

# ---------------------------------------------------------------
OLD1 = "        super().__init__(app)\n        app.installEventFilter(self)\n"
NEW1 = (
    "        super().__init__(app)\n"
    "        # PAS de app.installEventFilter(self) : un filtre global plante\n"
    "        # PySide6 6.11 + QtWebEngine (segfault). Le role est tenu par\n"
    "        # _GlassProxyStyle.polish() (widgets uniquement, thread principal).\n"
)

OLD2 = "def install_glass_popup_manager(app=None):"

NEW_CODE = '''from PySide6.QtWidgets import QProxyStyle as _QProxyStyle

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


'''

OLD3 = "        manager = GlassPopupManager(app)\n        app._glass_popup_manager = manager\n"
NEW3 = OLD3 + "        install_glass_proxy_style(app)\n"

# ---------------------------------------------------------------
b_mw = backup(MW)
print("Sauvegarde :", b_mw)

new_text = mw_text
for label, old, new in (
    ("1 (retrait installEventFilter)", OLD1, NEW1),
    ("2 (ajout _GlassProxyStyle)", OLD2, NEW_CODE + OLD2),
    ("3 (appel install_glass_proxy_style)", OLD3, NEW3),
):
    n = new_text.count(old)
    if n != 1:
        print(f"ECHEC bloc {label} : {n} occurrence(s) au lieu de 1. Rien modifie.")
        sys.exit(1)
    new_text = new_text.replace(old, new)
    print(f"OK bloc {label}")

MW.write_text(new_text, encoding="utf-8")
try:
    py_compile.compile(str(MW), doraise=True)
    print("py_compile main_window.py : OK")
except Exception as exc:
    print("py_compile ECHEC :", exc)
    restore(MW, b_mw)
    print("main_window.py restaure depuis la sauvegarde.")
    sys.exit(1)

# ---------------------------------------------------------------
# main.py : installer le style des le depart (optionnel, non bloquant)
if MAIN.exists():
    mt = MAIN.read_text(encoding="utf-8")
    IMP_OLD = "from src.gui.main_window import MainWindow, APP_STYLE, COLORS"
    IMP_NEW = "from src.gui.main_window import MainWindow, APP_STYLE, COLORS, install_glass_proxy_style"
    ST_OLD = 'app.setStyle("Fusion")'
    ST_NEW = "install_glass_proxy_style(app)"
    if mt.count(IMP_OLD) == 1 and mt.count(ST_OLD) == 1:
        b_main = backup(MAIN)
        MAIN.write_text(mt.replace(IMP_OLD, IMP_NEW).replace(ST_OLD, ST_NEW), encoding="utf-8")
        try:
            py_compile.compile(str(MAIN), doraise=True)
            print("OK main.py patche + py_compile OK")
        except Exception as exc:
            print("py_compile main.py ECHEC :", exc)
            restore(MAIN, b_main)
            print("main.py restaure (main_window.py reste patche, le style sera installe au demarrage du manager).")
    else:
        print("main.py : blocs attendus non trouves, non modifie (pas grave : install_glass_popup_manager installe le style).")

print("\nRESUME : filtre global supprime, remplace par _GlassProxyStyle.polish().")
