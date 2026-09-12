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

old = "        ('/home/stoni/MexAB_MexR_Analyzer_BETA/obabel_runtime/share/openbabel', 'obabel_runtime/share/openbabel'),\n    ] + _openbabel_datas + _openbabel_plugin_datas,"
new = "        ('/home/stoni/MexAB_MexR_Analyzer_BETA/obabel_runtime/share/openbabel', 'obabel_runtime/share/openbabel'),\n        ('/home/stoni/MexAB_MexR_Analyzer_BETA/src/assets/fonts', 'assets/fonts'),\n    ] + _openbabel_datas + _openbabel_plugin_datas,"

if old not in content:
    raise SystemExit("✗ Fin de bloc 'datas' introuvable telle qu'attendue, patch annulé.")
content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ VinaStudio.spec patché : police DejaVu Sans embarquée")
