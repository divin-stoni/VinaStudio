import os

# Empeche toute integration de theme de bureau (GTK / qt6ct / qt5ct /
# xdg-desktop-portal "Settings") de repousser sa propre palette (avec
# son bleu d'accent a lui) par-dessus notre theme "verre liquide"
# explicite — meme APRES app.setPalette(...). Cause frequente de
# boutons qui restent bleu vif malgre un QSS qui dit le contraire.
# DOIT rester avant tout import de Qt : le plugin de theme est choisi
# a la creation de QApplication, pas modifiable apres coup.
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "")

import sys
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

from PySide6.QtGui import QFont, QFontDatabase, QPalette, QColor
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow, APP_STYLE, COLORS


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("VINA Studio")
    app.setOrganizationName("VINA Studio")

    # ----------------------------------------------------------
    # STYLE VINA STUDIO
    # ----------------------------------------------------------

    app.setStyle("Fusion")

    # Palette explicite : evite toute fuite du theme sombre du systeme
    # d'exploitation sur les sous-elements que le QSS ne couvre pas
    # explicitement (en-tetes verticaux, coins de tableaux, popups...).
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["window"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["panel"]))
    palette.setColor(QPalette.AlternateBase, QColor("#f6f8fd"))
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

    app.setStyleSheet(APP_STYLE)

    # Police embarquee (au lieu de "Noto Sans", non garantie presente
    # sur toutes les machines Windows) : chargement explicite depuis
    # un fichier .ttf inclus dans l'application, pour un rendu et des
    # dimensions de texte identiques sur toutes les plateformes.
    _font_path = _PROJECT_ROOT / "src" / "assets" / "fonts" / "DejaVuSans.ttf"
    if getattr(sys, "frozen", False):
        _font_path = Path(sys._MEIPASS) / "assets" / "fonts" / "DejaVuSans.ttf"

    _font_family = "Sans Serif"
    if _font_path.exists():
        _font_id = QFontDatabase.addApplicationFont(str(_font_path))
        _families = QFontDatabase.applicationFontFamilies(_font_id)
        if _families:
            _font_family = _families[0]

    app.setFont(
        QFont(
            _font_family,
            10,
        )
    )

    # ----------------------------------------------------------
    # FENÊTRE PRINCIPALE
    # ----------------------------------------------------------

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
