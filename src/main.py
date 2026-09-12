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

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow, APP_STYLE


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("VINA Studio")
    app.setOrganizationName("VINA Studio")

    # ----------------------------------------------------------
    # STYLE VINA STUDIO
    # ----------------------------------------------------------

    app.setStyle("Fusion")
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
