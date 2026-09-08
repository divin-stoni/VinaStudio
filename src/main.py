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

from PySide6.QtGui import QFont
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

    app.setFont(
        QFont(
            "Noto Sans",
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
