# -*- coding: utf-8 -*-
"""
extraire_session.py -- lecture seule.

Cherche :
  1. quels patchs sont deja appliques ;
  2. les fichiers de resultats qui peuvent etre relus par "Lancer l'analyse" ;
  3. tout ce qui parle de session / nettoyage / derniers resultats memorises ;
  4. le code du bandeau "Cible active" et des fonctions de session.
Ecrit extrait_session.txt. Ne modifie aucun fichier du projet.
"""
import ast
import datetime
import os
import re
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
MAIN = SRC / "gui" / "main_window.py"
OUT = ROOT / "extrait_session.txt"
EXCL = {"dist", "venv", ".venv", "__pycache__", ".git", "node_modules"}

out = []


def w(text=""):
    out.append(text)


def title(text):
    w()
    w("=" * 78)
    w(text)
    w("=" * 78)


def py_files():
    for dirpath, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in EXCL]
        for name in sorted(files):
            if name.endswith(".py"):
                yield Path(dirpath) / name


if not MAIN.is_file():
    raise SystemExit("Introuvable : " + str(MAIN) + " (lance depuis la racine du projet)")

main_text = MAIN.read_text(encoding="utf-8")
main_lines = main_text.splitlines()

# ----------------------------------------------------------------------
title("1. PATCHS APPLIQUES")
markers = [
    ("patch_familles (worker)", "patch-familles : familles choisies"),
    ("patch_table_dynamique", "patch-table-dynamique : une colonne"),
    ("patch_campagne", "patch-campagne"),
    ("patch_libelles (texte du filtre)", "patch-libelles-gui"),
]
for label, marker in markers:
    w("%-34s : %s" % (label, "OUI" if marker in main_text else "non"))
w("%-34s : %s" % ("src/campaign_table.py", "present" if (SRC / "campaign_table.py").is_file() else "ABSENT"))

# ----------------------------------------------------------------------
title("2. FICHIERS DE RESULTATS SUSCEPTIBLES D'ETRE RELUS")
names = re.compile(
    r"^(docking_results.*\.csv|analysis_ready.*\.csv|scores_fusionnes.*\.(csv|json))$"
)
found = []
for dirpath, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in EXCL]
    for name in files:
        if names.match(name):
            p = Path(dirpath) / name
            st = p.stat()
            found.append((st.st_mtime, p, st.st_size))
found.sort(reverse=True)
for mtime, p, size in found[:80]:
    stamp = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    w("%s  %8d o  %s" % (stamp, size, p.relative_to(ROOT)))
if len(found) > 80:
    w("... +%d autres" % (len(found) - 80))

# ----------------------------------------------------------------------
title("3. FICHIERS DONT LE NOM PARLE DE SESSION / NETTOYAGE")
for p in py_files():
    if re.search(r"session|clean|purge|nettoy", p.name, re.IGNORECASE):
        w(str(p.relative_to(ROOT)))

title("4. LIGNES QUI PARLENT DE SESSION / NETTOYAGE / SUPPRESSION")
kw = re.compile(
    r"session|nettoy|cleanup|clean_|purge|rmtree|\.unlink\(|os\.remove|"
    r"Cible active|cible_active|active_target",
    re.IGNORECASE,
)
count = 0
for p in py_files():
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    for n, line in enumerate(lines, start=1):
        if kw.search(line):
            w("%s:%d: %s" % (p.relative_to(ROOT), n, line.strip()[:130]))
            count += 1
            if count >= 200:
                break
    if count >= 200:
        w("... (plafond atteint)")
        break

title("5. RESULTATS MEMORISES ENTRE DEUX LANCEMENTS (QSettings)")
kw2 = re.compile(r"(setValue|\.value)\(", re.IGNORECASE)
kw3 = re.compile(r"csv|result|last|dernier|campaign|campagne|analysis|analyse|docking|session",
                 re.IGNORECASE)
count = 0
for p in py_files():
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    for n, line in enumerate(lines, start=1):
        if kw2.search(line) and kw3.search(line):
            w("%s:%d: %s" % (p.relative_to(ROOT), n, line.strip()[:130]))
            count += 1
            if count >= 80:
                break
    if count >= 80:
        break

# ----------------------------------------------------------------------
title("6. CODE DES FONCTIONS CONCERNEES (main_window.py)")
tree = ast.parse(main_text)
funcs = []


def walk(node, cls=None):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            walk(child, child.name)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append((cls, child))


walk(tree)
name_re = re.compile(
    r"session|clean|nettoy|purge|reset|clear_|_batch_root|_refresh_campaign_combo|"
    r"closeEvent|^main$|target_banner|active_target|set_active|update_header|"
    r"refresh_header|update_target",
    re.IGNORECASE,
)
MAX = 130
shown = 0
for cls, fn in funcs:
    body = main_lines[fn.lineno - 1:fn.end_lineno]
    joined = "\n".join(body)
    if name_re.search(fn.name) or "Cible active" in joined:
        w()
        w("#" * 78)
        w("# %s.%s  (lignes %d-%d)" % (cls, fn.name, fn.lineno, fn.end_lineno))
        w("#" * 78)
        out.extend(body[:MAX])
        if len(body) > MAX:
            w("... [tronque : %d lignes en tout]" % len(body))
        shown += 1
        if shown >= 25:
            w("... (plafond de fonctions atteint)")
            break

OUT.write_text("\n".join(out), encoding="utf-8")
print("Termine. Ecrit dans : " + str(OUT))
