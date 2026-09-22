# -*- coding: utf-8 -*-
"""
patch_campagne.py

Patch reversible sur src/gui/main_window.py, apres patch_table_dynamique.py :

  1. Tableau vide : plus d'en-tetes MexB / MexR ecrits en dur ; on affiche
     des en-tetes neutres (Rang, Molecule, Groupe, DG, Statut).
  2. A l'ouverture de la page Resultats, le tableau montre la campagne
     choisie dans le menu "Campagne" (par defaut la derniere) au lieu
     de "Aucun resultat" quand aucun docking n'a eu lieu dans la session.
  3. Changer de campagne dans le menu met a jour le tableau, et
     "Lancer l'analyse" travaille sur cette campagne.

Usage, depuis la racine du projet :
    python3 patch_campagne.py --check
    python3 patch_campagne.py
    python3 patch_campagne.py --revert
"""

import ast
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

TARGET = Path("src/gui/main_window.py")
BACKUP_TAG = ".bak_campagne_"
PREREQUIS = "patch-table-dynamique : une colonne"

# 1a. nouvelles methodes (inserees avant _receptor_table_label)
OLD_METHODS = '''def _receptor_table_label(self, receptor_id, fallback):'''

NEW_METHODS = '''def _set_neutral_table_headers(self, table):
    # patch-campagne : en-tetes neutres tant qu'aucune campagne n'est chargee
    base = self._docking_results_headers()
    headers = list(base[:3]) + ["ΔG (kcal/mol)"] + [base[-1]]
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    for col in range(len(headers)):
        table.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.Stretch
        )

def _on_campaign_combo_changed_dyn(self, label):
    # patch-campagne : le menu Campagne pilote le tableau et l'analyse
    path = self._campaign_csv_path(label)
    self.docking_results_csv = path
    try:
        self._fill_docking_table_dynamic(csv_path=path or "")
    except Exception as exc:
        gui_debug("TABLEAU DYNAMIQUE ignore : " + str(exc))

def _receptor_table_label(self, receptor_id, fallback):'''

# 1b. tableau sans resultat : en-tetes neutres
OLD_EMPTY = '''if not csv_path or not Path(csv_path).exists():
        table.setRowCount(0)
        return'''

NEW_EMPTY = '''if not csv_path or not Path(csv_path).exists():
    table.setRowCount(0)
    self._set_neutral_table_headers(table)  # patch-campagne
    return'''

# 2. results_page : campagne du menu quand il n'y a pas de docking de session
OLD_PAGE_CSV = '''import csv

csv_path = getattr(
    self,
    "docking_results_csv",
    None
)

if not csv_path:

    table.insertRow(0)'''

NEW_PAGE_CSV = '''import csv

csv_path = getattr(
    self,
    "docking_results_csv",
    None
)

# patch-campagne : sans docking dans cette session, on affiche la campagne
# choisie dans le menu (par defaut la derniere), pas un tableau vide
if not csv_path:
    try:
        csv_path = self._campaign_csv_path(combo.currentText())
    except Exception:
        csv_path = None

if not csv_path:

    self._set_neutral_table_headers(table)

    table.insertRow(0)'''

# 3. changer de campagne met a jour le tableau
OLD_COMBO = '''self._refresh_campaign_combo()

row.addWidget(combo)'''

NEW_COMBO = '''self._refresh_campaign_combo()
combo.currentTextChanged.connect(self._on_campaign_combo_changed_dyn)  # patch-campagne

row.addWidget(combo)'''

EDITS = [
    ("nouvelles methodes (en-tetes neutres, menu Campagne)",
     OLD_METHODS, NEW_METHODS, "def _set_neutral_table_headers(self, table):"),
    ("tableau sans resultat : en-tetes neutres",
     OLD_EMPTY, NEW_EMPTY, "self._set_neutral_table_headers(table)  # patch-campagne"),
    ("page Resultats : campagne du menu a l'ouverture",
     OLD_PAGE_CSV, NEW_PAGE_CSV, "patch-campagne : sans docking dans cette session"),
    ("menu Campagne connecte au tableau",
     OLD_COMBO, NEW_COMBO, "combo.currentTextChanged.connect(self._on_campaign_combo_changed_dyn)"),
]


def build_pattern(old):
    tokens = old.split()
    return re.compile(r"\s*".join(re.escape(t) for t in tokens))


def find_matches(text, old):
    return list(build_pattern(old).finditer(text))


def replace_once(text, match, new):
    line_start = text.rfind("\n", 0, match.start()) + 1
    prefix = text[line_start:match.start()]
    indent = re.match(r"[ \t]*", prefix).group(0)
    lines = new.split("\n")
    out = lines[0] + "".join(
        "\n" + (indent + line if line.strip() else line) for line in lines[1:]
    )
    return text[:match.start()] + out + text[match.end():]


def already_applied(text, marker):
    return re.sub(r"\s+", " ", marker) in re.sub(r"\s+", " ", text)


def prerequis_ok(text):
    if already_applied(text, PREREQUIS):
        return True
    print("X patch_table_dynamique.py n'est pas applique.")
    print("  Applique-le d'abord : python3 patch_table_dynamique.py")
    return False


def do_check():
    if not TARGET.is_file():
        print("Introuvable : %s (lance depuis la racine du projet)" % TARGET)
        return 1
    text = TARGET.read_text(encoding="utf-8")
    ok = prerequis_ok(text)
    for label, old, new, marker in EDITS:
        if already_applied(text, marker):
            state = "deja applique"
        else:
            n = len(find_matches(text, old))
            state = "applicable" if n == 1 else "BLOQUE (%d correspondance(s), 1 attendue)" % n
            ok = ok and n == 1
        print("[%s] %s : %s" % (TARGET.name, label, state))
    return 0 if ok else 1


def do_apply():
    if not TARGET.is_file():
        print("Introuvable : %s (lance depuis la racine du projet)" % TARGET)
        return 1
    original = TARGET.read_text(encoding="utf-8")
    if not prerequis_ok(original):
        print("Aucun fichier n'a ete modifie.")
        return 1

    text = original
    todo = []
    for label, old, new, marker in EDITS:
        if already_applied(text, marker):
            print("= deja applique : " + label)
            continue
        matches = find_matches(text, old)
        if len(matches) != 1:
            print("X BLOQUE : %s (%d correspondance(s), 1 attendue)" % (label, len(matches)))
            print("Aucun fichier n'a ete modifie.")
            return 1
        text = replace_once(text, matches[0], new)
        todo.append(label)

    if not todo:
        print("Rien a faire : tout est deja applique.")
        return 0

    try:
        ast.parse(text)
    except SyntaxError as exc:
        print("X Le resultat ne compile pas (%s)." % (exc,))
        print("Aucun fichier n'a ete modifie.")
        return 1

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(str(TARGET) + BACKUP_TAG + stamp)
    shutil.copy2(TARGET, backup)
    TARGET.write_text(text, encoding="utf-8")
    ast.parse(TARGET.read_text(encoding="utf-8"))
    print("+ %s modifie (sauvegarde : %s)" % (TARGET, backup.name))
    for label in todo:
        print("  ok : " + label)
    print("Termine. Pour annuler : python3 patch_campagne.py --revert")
    return 0


def do_revert():
    backups = sorted(glob.glob(str(TARGET) + BACKUP_TAG + "*"))
    if not backups:
        print("Aucune sauvegarde : rien a restaurer.")
        return 0
    shutil.copy2(backups[0], TARGET)
    ast.parse(TARGET.read_text(encoding="utf-8"))
    print("+ %s restaure depuis %s" % (TARGET.name, Path(backups[0]).name))
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--check"]:
        raise SystemExit(do_check())
    if args == ["--revert"]:
        raise SystemExit(do_revert())
    if args == []:
        raise SystemExit(do_apply())
    print("Usage : python3 patch_campagne.py [--check | --revert]")
    raise SystemExit(1)
