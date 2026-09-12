# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/VinaStudio.spec")
if not TARGET.exists():
    raise SystemExit(f"Fichier introuvable : {TARGET}")

backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

ROOT = "/home/stoni/MexAB_MexR_Analyzer_BETA"

old_binaries = "binaries=[],"
new_binaries = f"""binaries=[
        ('{ROOT}/docking/bin/vina', 'docking/bin'),
        ('{ROOT}/obabel_runtime/bin/obabel', 'obabel_runtime/bin'),
        ('{ROOT}/runtime_libs/libboost_thread.so.1.88.0', 'runtime_libs'),
        ('{ROOT}/runtime_libs/libboost_filesystem.so.1.88.0', 'runtime_libs'),
        ('{ROOT}/runtime_libs/libboost_program_options.so.1.88.0', 'runtime_libs'),
        ('{ROOT}/runtime_libs/libopenbabel.so.7', 'runtime_libs'),
        ('{ROOT}/runtime_libs/libinchi.so.1.07', 'runtime_libs'),
        ('{ROOT}/runtime_libs/libmaeparser.so.1', 'runtime_libs'),
    ],"""

if old_binaries not in content:
    raise SystemExit("✗ Ligne 'binaries=[],' introuvable, patch annulé.")
content = content.replace(old_binaries, new_binaries, 1)

old_datas = f"datas=[('{ROOT}/reference_data', 'reference_data'), ('{ROOT}/src/i18n', 'i18n')],"
new_datas = f"""datas=[
        ('{ROOT}/reference_data', 'reference_data'),
        ('{ROOT}/src/i18n', 'i18n'),
        ('{ROOT}/docking/receptor', 'docking/receptor'),
        ('{ROOT}/obabel_runtime/lib/openbabel', 'obabel_runtime/lib/openbabel'),
        ('{ROOT}/obabel_runtime/share/openbabel', 'obabel_runtime/share/openbabel'),
    ],"""

if old_datas not in content:
    raise SystemExit("✗ Ligne 'datas=[...]' introuvable telle qu'attendue, patch annulé.")
content = content.replace(old_datas, new_datas, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ VinaStudio.spec patché : binaires + données Linux embarqués")
