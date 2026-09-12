# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/VinaStudio.spec")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

old = "    ['main.py'],"
new = "    ['../run_gui.py'],"

if old not in content:
    raise SystemExit(f"✗ Ligne attendue introuvable : {old!r}. Patch annulé.")

content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ .spec corrigé : entrée = run_gui.py (avec le test --plip-worker) au lieu de main.py")
