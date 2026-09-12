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

# 1. Ajout de l'import des helpers PyInstaller, en tout début de fichier
old_header = "# -*- mode: python ; coding: utf-8 -*-"
new_header = """# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Collecte complete du module Python openbabel (wheel autonome utilise
# par PLIP via "from openbabel import pybel") : plugins de formats
# (lib/openbabel/<version>/*.so) et donnees (share/openbabel/*), qui
# ne sont PAS suivis automatiquement par PyInstaller car charges
# dynamiquement a l'execution, pas via une dependance liee (ldd).
_openbabel_datas = collect_data_files('openbabel')
_openbabel_binaries = collect_dynamic_libs('openbabel')"""

if old_header not in content:
    raise SystemExit("✗ En-tête attendu introuvable, patch annulé.")
content = content.replace(old_header, new_header, 1)

# 2. Injection dans binaries=[...] et datas=[...] existants (deja patches pour Linux)
old_binaries_tail = "        ('/home/stoni/MexAB_MexR_Analyzer_BETA/runtime_libs/libmaeparser.so.1', 'runtime_libs'),\n    ],"
new_binaries_tail = "        ('/home/stoni/MexAB_MexR_Analyzer_BETA/runtime_libs/libmaeparser.so.1', 'runtime_libs'),\n    ] + _openbabel_binaries,"

if old_binaries_tail not in content:
    raise SystemExit("✗ Fin de bloc 'binaries' introuvable telle qu'attendue, patch annulé.")
content = content.replace(old_binaries_tail, new_binaries_tail, 1)

old_datas_tail = "        ('/home/stoni/MexAB_MexR_Analyzer_BETA/obabel_runtime/share/openbabel', 'obabel_runtime/share/openbabel'),\n    ],"
new_datas_tail = "        ('/home/stoni/MexAB_MexR_Analyzer_BETA/obabel_runtime/share/openbabel', 'obabel_runtime/share/openbabel'),\n    ] + _openbabel_datas,"

if old_datas_tail not in content:
    raise SystemExit("✗ Fin de bloc 'datas' introuvable telle qu'attendue, patch annulé.")
content = content.replace(old_datas_tail, new_datas_tail, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ VinaStudio.spec patché : module Python openbabel entièrement collecté (plugins + données)")
