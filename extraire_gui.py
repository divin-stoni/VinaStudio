# -*- coding: utf-8 -*-
"""
extraire_gui.py -- lecture seule.
Extrait de src/gui/main_window.py :
  1. le code complet des fonctions de l'analyse et du tableau de resultats ;
  2. la carte des autres fonctions qui parlent de familles / ligands ;
  3. les lignes qui remplissent le menu des cibles.
Ecrit extrait_gui_analyse.txt. Ne modifie aucun fichier du projet.
"""
import ast
import re
from pathlib import Path

SRC = Path("src/gui/main_window.py")
OUT = Path("extrait_gui_analyse.txt")

WANTED = [
    "run_docking_analysis",
    "refresh_docking_results",
    "populate_statistics_results",
    "build_dynamic_statistics_tabs",
    "_campaign_csv_path",
    "_docking_results_headers",
]
FAMILY_RE = re.compile(
    r"ligand_groups|selected_ligands\s*=|famille|family|families|groupe|SANS_GROUPE",
    re.IGNORECASE,
)
COMBO_RE = re.compile(r"pair_targets|target_combo\.addItem|list_pairs\(")
MAX_FULL = 300

if not SRC.exists():
    raise SystemExit("Introuvable : " + str(SRC) + " (lance ce script depuis la racine du projet)")

text = SRC.read_text(encoding="utf-8")
lines = text.splitlines()
tree = ast.parse(text)

funcs = []


def walk(node, cls=None):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            walk(child, child.name)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append((cls, child))


walk(tree)

out = []
out.append("EXTRAIT GUI - " + str(SRC) + " (" + str(len(lines)) + " lignes)")
out.append("")
out.append("=" * 78)
out.append("1. FONCTIONS COMPLETES")
out.append("=" * 78)

found = set()
for cls, fn in funcs:
    if fn.name in WANTED:
        found.add(fn.name)
        start, end = fn.lineno, fn.end_lineno
        out.append("")
        out.append("#" * 78)
        out.append("# %s.%s  (lignes %d-%d)" % (cls, fn.name, start, end))
        out.append("#" * 78)
        body = lines[start - 1:end]
        if len(body) > MAX_FULL:
            out.extend(body[:MAX_FULL])
            out.append("... [tronque : %d lignes en tout]" % len(body))
        else:
            out.extend(body)

for name in WANTED:
    if name not in found:
        out.append("")
        out.append("(non trouve comme fonction : %s)" % name)

out.append("")
out.append("=" * 78)
out.append("2. AUTRES FONCTIONS QUI PARLENT DE FAMILLES / LIGANDS")
out.append("=" * 78)
for cls, fn in funcs:
    if fn.name in WANTED:
        continue
    hits = [
        (n, lines[n - 1].strip())
        for n in range(fn.lineno, fn.end_lineno + 1)
        if FAMILY_RE.search(lines[n - 1])
    ]
    if not hits:
        continue
    out.append("")
    out.append("%s.%s  (lignes %d-%d, %d ligne(s) concernee(s))" % (
        cls, fn.name, fn.lineno, fn.end_lineno, len(hits)))
    for n, content in hits[:6]:
        out.append("    l.%d : %s" % (n, content[:110]))
    if len(hits) > 6:
        out.append("    ... +%d autres" % (len(hits) - 6))

out.append("")
out.append("=" * 78)
out.append("3. REMPLISSAGE DU MENU DES CIBLES")
out.append("=" * 78)
count = 0
for n, content in enumerate(lines, start=1):
    if COMBO_RE.search(content):
        out.append("l.%d : %s" % (n, content.strip()[:120]))
        count += 1
        if count >= 40:
            out.append("... (plafond atteint)")
            break

OUT.write_text("\n".join(out), encoding="utf-8")
print("Termine. %d fonctions lues." % len(funcs))
print("Trouvees : " + ", ".join(sorted(found)))
print("Ecrit dans : " + str(OUT.resolve()))
