# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/main.py")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

old_import = "from PySide6.QtGui import QFont\nfrom PySide6.QtWidgets import QApplication"
new_import = "from PySide6.QtGui import QFont, QFontDatabase\nfrom PySide6.QtWidgets import QApplication"
if old_import not in content:
    raise SystemExit("✗ Bloc d'imports introuvable, patch annulé.")
content = content.replace(old_import, new_import, 1)

old_font_block = '''    app.setFont(
        QFont(
            "Noto Sans",
            10,
        )
    )'''

new_font_block = '''    # Police embarquee (au lieu de "Noto Sans", non garantie presente
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
    )'''

if old_font_block not in content:
    raise SystemExit("✗ Bloc de police introuvable, patch annulé.")
content = content.replace(old_font_block, new_font_block, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ main.py patché : police DejaVu Sans embarquée, chargée explicitement")
