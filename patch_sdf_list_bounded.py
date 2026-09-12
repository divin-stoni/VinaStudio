# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/gui/main_window.py")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

old = '''        self.sdf_list.setMinimumHeight(
            150
        )'''

new = '''        self.sdf_list.setMinimumHeight(150)
        self.sdf_list.setMaximumHeight(350)'''

if old not in content:
    raise SystemExit("✗ Bloc introuvable, patch annulé.")
content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ sdf_list borné : 150-350px, avec sa propre barre de défilement au-delà")
