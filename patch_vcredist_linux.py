# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/tools/vcredist_check.py")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

old = '''    if not getattr(sys, "frozen", False):
        return  # dev/Linux : pas concerne

    if _vcredist_present():'''

new = '''    if not getattr(sys, "frozen", False):
        return  # dev : pas concerne

    if not sys.platform.startswith("win"):
        return  # Linux/macOS : le VC++ Redistributable n'existe pas ici

    if _vcredist_present():'''

if old not in content:
    raise SystemExit("✗ Bloc attendu introuvable, patch annulé.")

content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ vcredist_check.py corrigé : ignoré sur Linux/macOS même en mode packagé")
