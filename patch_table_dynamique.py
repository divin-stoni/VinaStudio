# -*- coding: utf-8 -*-
"""
patch_table_dynamique.py

Patch reversible sur src/gui/main_window.py :
le tableau "Resultats du docking" affiche une colonne d'affinite par
recepteur de la campagne (AcrB, AcrR, MexB, MexR, ...) au lieu des deux
colonnes fixes MexB / MexR, et lit tous les formats de CSV grace a
src/campaign_table.py.

  - refresh_docking_results : nouvelle version dynamique ; l'ancienne est
    conservee sous le nom _refresh_docking_results_legacy et sert de
    repli automatique si la nouvelle echoue.
  - results_page : le tableau est rempli avec la version dynamique.

Prerequis : src/campaign_table.py (etape 1).

Usage, depuis la racine du projet :
    python3 patch_table_dynamique.py --check
    python3 patch_table_dynamique.py
    python3 patch_table_dynamique.py --revert
"""

import ast
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

TARGET = Path("src/gui/main_window.py")
BACKUP_TAG = ".bak_tabledyn_"

OLD_REFRESH = """def refresh_docking_results(self):"""

NEW_REFRESH = '''def refresh_docking_results(self):
    # patch-table-dynamique : une colonne par recepteur de la campagne
    try:
        self._fill_docking_table_dynamic()
    except Exception as exc:
        gui_debug("TABLEAU DYNAMIQUE ignore : " + str(exc))
        self._refresh_docking_results_legacy()

def _receptor_table_label(self, receptor_id, fallback):
    """Nom court du recepteur (AcrB, MexB...) tire de son profil."""
    try:
        from src.docking.receptor_profile import (
            resolve_target_profile,
            short_label,
        )
        return str(short_label(resolve_target_profile(receptor_id)))
    except Exception:
        return fallback

def _fill_docking_table_dynamic(self, table=None, csv_path=None):
    from src.campaign_table import normalize_docking_csv, campaign_shape

    if table is None:
        table = getattr(self, "docking_results_table", None)
    if table is None:
        return
    if csv_path is None:
        csv_path = getattr(self, "docking_results_csv", None)
    if not csv_path or not Path(csv_path).exists():
        table.setRowCount(0)
        return

    data = normalize_docking_csv(csv_path)
    info = campaign_shape(data)
    receptors = info["receptors"]
    labels = {
        rid: self._receptor_table_label(rid, info["labels"][rid])
        for rid in receptors
    }

    base = self._docking_results_headers()
    headers = (
        list(base[:3])
        + [labels[rid] + " (kcal/mol)" for rid in receptors]
        + [base[-1]]
    )

    # Tout est calcule avant de toucher au tableau.
    rows = []
    for rank, (molecule, sub) in enumerate(
        data.groupby("molecule", sort=False), start=1
    ):
        families = [g for g in sub["groupe"] if g]
        cells = [str(rank), molecule, families[0] if families else ""]
        problems = []
        for rid in receptors:
            rec = sub[sub["receptor_id"] == rid]
            if rec.empty:
                cells.append("")
                problems.append(labels[rid] + " : absent")
                continue
            value = rec["best_affinity"].iloc[0]
            cells.append("" if value != value else "%.3f" % value)
            status = str(rec["status"].iloc[0])
            if status.upper() != "OK":
                problems.append(labels[rid] + " : " + status)
        cells.append("OK" if not problems else " ; ".join(problems))
        rows.append(cells)

    table.setRowCount(0)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    for col in range(len(headers)):
        table.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.Stretch
        )
    for cells in rows:
        row = table.rowCount()
        table.insertRow(row)
        for col, value in enumerate(cells):
            table.setItem(row, col, QTableWidgetItem(str(value)))

def _refresh_docking_results_legacy(self):'''

OLD_PAGE = """layout.addWidget(table, 1)

scroll = QScrollArea()
scroll.setObjectName("ResultsScrollArea")"""

NEW_PAGE = """# patch-table-dynamique : colonnes selon les recepteurs de la campagne
try:
    self._fill_docking_table_dynamic(table, csv_path)
except Exception as exc:
    gui_debug("TABLEAU DYNAMIQUE ignore : " + str(exc))

layout.addWidget(table, 1)

scroll = QScrollArea()
scroll.setObjectName("ResultsScrollArea")"""

EDITS = [
    ("tableau rafraichi apres docking (refresh_docking_results)",
     OLD_REFRESH, NEW_REFRESH, "patch-table-dynamique : une colonne"),
    ("tableau de la page Resultats (results_page)",
     OLD_PAGE, NEW_PAGE, "patch-table-dynamique : colonnes selon"),
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


def precheck_module():
    module = Path("src/campaign_table.py")
    if not module.is_file():
        print("X src/campaign_table.py est introuvable.")
        print("  Cree-le d'abord avec la commande de l'etape 1 (lecture des CSV).")
        return False
    sys.path.insert(0, str(Path.cwd()))
    try:
        from src.campaign_table import normalize_docking_csv, campaign_shape  # noqa
    except Exception as exc:
        print("X src/campaign_table.py ne s'importe pas : %r" % (exc,))
        return False
    print("ok : src/campaign_table.py present et importable")
    return True


def do_check():
    if not TARGET.is_file():
        print("Introuvable : %s (lance depuis la racine du projet)" % TARGET)
        return 1
    ok = precheck_module()
    text = TARGET.read_text(encoding="utf-8")
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
    if not precheck_module():
        print("Aucun fichier n'a ete modifie.")
        return 1

    original = TARGET.read_text(encoding="utf-8")
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
    print("Termine. Pour annuler : python3 patch_table_dynamique.py --revert")
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
    print("Usage : python3 patch_table_dynamique.py [--check | --revert]")
    raise SystemExit(1)
