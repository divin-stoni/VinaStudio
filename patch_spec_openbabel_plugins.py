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

old = "_openbabel_binaries = collect_dynamic_libs('openbabel')"
new = """_openbabel_binaries = collect_dynamic_libs('openbabel')

# Plugins du module Python openbabel (chargement dynamique via
# BABEL_LIBDIR, invisibles pour l'analyse automatique de PyInstaller
# car non lies directement). Copies manuellement dans
# openbabel_python_plugins/ puis places explicitement sous
# openbabel/lib/openbabel/3.2.1 dans le build, la ou
# plip_worker._fix_babel_datadir_for_python_bindings() les attend.
_openbabel_plugin_dir = '/home/stoni/MexAB_MexR_Analyzer_BETA/openbabel_python_plugins'
_openbabel_plugin_datas = [
    (_openbabel_plugin_dir, 'openbabel/lib/openbabel/3.2.1')
]"""

if old not in content:
    raise SystemExit("✗ Ligne '_openbabel_binaries = ...' introuvable, patch annulé.")
content = content.replace(old, new, 1)

old_datas_tail = "    ] + _openbabel_datas,"
new_datas_tail = "    ] + _openbabel_datas + _openbabel_plugin_datas,"

if old_datas_tail not in content:
    raise SystemExit("✗ Fin de bloc 'datas' introuvable telle qu'attendue, patch annulé.")
content = content.replace(old_datas_tail, new_datas_tail, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ VinaStudio.spec patché : plugins openbabel_python_plugins embarqués sous openbabel/lib/openbabel/3.2.1")
