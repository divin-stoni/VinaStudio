# -*- coding: utf-8 -*-
"""
patch_entetes.py

Patch reversible sur src/gui/main_window.py, apres patch_table_dynamique.py :

  Le tableau "Resultats du docking" n'affiche plus les en-tetes
  "MexB (kcal/mol)" / "MexR (kcal/mol)" quand aucune campagne n'est
  chargee : il affiche "Recepteur 1 (kcal/mol)" / "Recepteur 2 (kcal/mol)".
  Des qu'une campagne est chargee, les vrais noms des recepteurs
  (AcrB, AcrR, MexB...) remplacent ces en-tetes, comme avant.

Ne charge aucun ancien resultat et ne change pas le menu Campagne.

Usage, depuis la racine du projet :
    python3 patch_entetes.py --check
    python3 patch_entetes.py
    python3 patch_entetes.py --revert
"""

import ast
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

TARGET = Path("src/gui/main_window.py")
BACKUP_TAG = ".bak_entetes_"
PREREQUIS = "patch-table-dynamique : une colonne"

# 1. la methode qui pose les en-tetes neutres
OLD_METHOD = '''def refresh_docking_results(self):'''

NEW_METHOD = '''def _set_neutral_table_headers(self, table):
    # patch-entetes : en-tetes neutres tant qu'aucune campagne n'est chargee
    headers = list(self._docking_results_headers())
    if len(headers) >= 6:
        headers[3] = "Récepteur 1 (kcal/mol)"
        headers[4] = "Récepteur 2 (kcal/mol)"
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    for col in range(len(headers)):
        table.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.Stretch
        )

def refresh_docking_results(self):'''

# 2. page Resultats sans docking : en-tetes neutres
OLD_PAGE = '''import csv

csv_path = getattr(
    self,
    "docking_results_csv",
    None
)

if not csv_path:

    table.insertRow(0)'''

NEW_PAGE = '''import csv

csv_path = getattr(
    self,
    "docking_results_csv",
    None
)

if not csv_path:

    self._set_neutral_table_headers(table)  # patch-entetes

    table.insertRow(0)'''

# 3. tableau vide apres un rafraichissement sans resultat
OLD_EMPTY = '''if not csv_path or not Path(csv_path).exists():
        table.setRowCount(0)
        return'''

NEW_EMPTY = '''if not csv_path or not Path(csv_path).exists():
    table.setRowCount(0)
    self._set_neutral_table_headers(table)  # patch-entetes
    return'''

EDITS = [
    ("methode des en-tetes neutres",
     OLD_METHOD, NEW_METHOD, "def _set_neutral_table_headers(self, table):"),
    ("page Resultats sans docking : en-tetes neutres",
     OLD_PAGE, NEW_PAGE, "self._set_neutral_table_headers(table)  # patch-entetes\n\n    table.insertRow(0)"),
    ("tableau rafraichi sans resultat : en-tetes neutres",
     OLD_EMPTY, NEW_EMPTY, "table.setRowCount(0) self._set_neutral_table_headers(table)  # patch-entetes return"),
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
    text = TARGET.read_text(encoding="utf-8")
    if not prerequis_ok(text):
        print("Aucun fichier n'a ete modifie.")
        return 1

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
    print("Termine. Pour annuler : python3 patch_entetes.py --revert")
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
    print("Usage : python3 patch_entetes.py [--check | --revert]")
    raise SystemExit(1)
