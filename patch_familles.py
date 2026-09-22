# -*- coding: utf-8 -*-
"""
patch_familles.py

Patch reversible sur 3 fichiers :

  1. src/gui/main_window.py, launch_docking :
     les familles choisies dans l'interface sont transmises au
     DockingWorker (colonne "groupe" du CSV de docking).
  2. src/gui/main_window.py, on_docking_finished :
     l'analyse automatique lit scores_fusionnes.csv (avec groupe)
     au lieu de scores_fusionnes_global.csv (sans groupe).
  3. src/stats_engine.py :
     "SANS_GROUPE" / "Sans famille" ne comptent plus comme une famille ;
     en mode GLOBAL, plus de ligne SANS_GROUPE en double dans le
     bootstrap et le leave-one-out.
  4. src/analysis/statistics_pipeline.py :
     le leave-one-out est aussi calcule pour une campagne sans famille
     (il l'etait deja via le faux groupe SANS_GROUPE).

Usage, depuis la racine du projet :
    python3 patch_familles.py --check
    python3 patch_familles.py
    python3 patch_familles.py --revert
"""

import ast
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

FILES = {
    "main_window": Path("src/gui/main_window.py"),
    "stats_engine": Path("src/stats_engine.py"),
    "pipeline": Path("src/analysis/statistics_pipeline.py"),
}

BACKUP_TAG = ".bak_familles_"

# ----------------------------------------------------------------------
# Les modifications : (fichier, description, ancien, nouveau, marqueur)
# "ancien" est cherche sans tenir compte des espaces / retours a la ligne
# et doit correspondre EXACTEMENT UNE fois, sinon rien n'est ecrit.
# ----------------------------------------------------------------------

OLD_WORKER = """self.worker = DockingWorker(
    engines=engines,
    ligands=ligands,
    results_root=self.project_root,
    pair_roles=pair_roles,
)"""

NEW_WORKER = """# patch-familles : familles choisies dans l'interface -> colonne "groupe"
from pathlib import Path as _FamPath
ligand_groups = {}
for _lig_path, _lig_family in getattr(self, "pdbqt_families", {}).items():
    _family = str(_lig_family or "").strip()
    if _family and _family.lower() != "sans famille":
        ligand_groups[str(_FamPath(_lig_path).resolve())] = _family

self.worker = DockingWorker(
    engines=engines,
    ligands=ligands,
    results_root=self.project_root,
    ligand_groups=ligand_groups,
    pair_roles=pair_roles,
)"""

OLD_STATS = """run_statistics_pipeline(
    str(global_csv)
)"""

NEW_STATS = """run_statistics_pipeline(
    str(grouped)  # patch-familles : le CSV global n'a pas de colonne groupe
)"""

OLD_MODE = """["", "nan", "none", "null"]"""

NEW_MODE = """["", "nan", "none", "null", "sans_groupe", "sans famille", "global"]"""

OLD_BOOT = """rows = []
groups = list(work[group_col].dropna().unique())"""

NEW_BOOT = """rows = []
groups = [] if mode == "GLOBAL" else list(work[group_col].dropna().unique())  # patch-familles"""

OLD_LOO = """results = []
groups = list(work[group_col].dropna().unique())"""

NEW_LOO = """results = []
groups = [] if mode == "GLOBAL" else list(work[group_col].dropna().unique())  # patch-familles"""

OLD_LOO_PIPE = """result["leave_one_out"] = None"""

NEW_LOO_PIPE = """result["leave_one_out"] = leave_one_out(df, x_col=x_col, y_col=y_col)  # patch-familles : LOO aussi en mode global"""

EDITS = [
    ("main_window", "transmission des familles au worker (launch_docking)",
     OLD_WORKER, NEW_WORKER, "patch-familles : familles choisies"),
    ("main_window", "analyse automatique sur le CSV avec groupe (on_docking_finished)",
     OLD_STATS, NEW_STATS, "patch-familles : le CSV global"),
    ("stats_engine", "SANS_GROUPE / Sans famille = pas de famille (detect_analysis_mode)",
     OLD_MODE, NEW_MODE, '"sans_groupe", "sans famille"'),
    ("stats_engine", "bootstrap : pas de groupe factice en mode GLOBAL",
     OLD_BOOT, NEW_BOOT, "rows = [] groups = [] if mode"),
    ("stats_engine", "leave-one-out : pas de groupe factice en mode GLOBAL",
     OLD_LOO, NEW_LOO, "results = [] groups = [] if mode"),
    ("pipeline", "leave-one-out calcule aussi sans famille (statistics_pipeline)",
     OLD_LOO_PIPE, NEW_LOO_PIPE, "patch-familles : LOO aussi"),
]


# ----------------------------------------------------------------------
# Outils
# ----------------------------------------------------------------------

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
    normalized = re.sub(r"\s+", " ", marker)
    return normalized in re.sub(r"\s+", " ", text)


def read(path):
    return path.read_text(encoding="utf-8")


def check_files_exist():
    missing = [str(p) for p in FILES.values() if not p.is_file()]
    if missing:
        print("Fichier(s) introuvable(s) : " + ", ".join(missing))
        print("Lance ce script depuis la racine du projet (~/MexAB_MexR_Analyzer_BETA).")
        raise SystemExit(1)


# ----------------------------------------------------------------------
# Modes
# ----------------------------------------------------------------------

def do_check():
    check_files_exist()
    texts = {k: read(p) for k, p in FILES.items()}
    ok = True
    for key, label, old, new, marker in EDITS:
        text = texts[key]
        if already_applied(text, marker):
            state = "deja applique"
        else:
            n = len(find_matches(text, old))
            if n == 1:
                state = "applicable"
            else:
                state = "BLOQUE (%d correspondance(s), 1 attendue)" % n
                ok = False
        print("[%s] %s : %s" % (FILES[key].name, label, state))
    return 0 if ok else 1


def do_apply():
    check_files_exist()
    texts = {k: read(p) for k, p in FILES.items()}
    new_texts = dict(texts)
    todo = []

    for key, label, old, new, marker in EDITS:
        text = new_texts[key]
        if already_applied(text, marker):
            print("= deja applique : " + label)
            continue
        matches = find_matches(text, old)
        if len(matches) != 1:
            print("X BLOQUE : %s (%d correspondance(s), 1 attendue)" % (label, len(matches)))
            print("Aucun fichier n'a ete modifie.")
            return 1
        new_texts[key] = replace_once(text, matches[0], new)
        todo.append(label)

    if not todo:
        print("Rien a faire : tout est deja applique.")
        return 0

    for key, text in new_texts.items():
        try:
            ast.parse(text)
        except SyntaxError as exc:
            print("X Le resultat pour %s ne compile pas (%s)." % (FILES[key].name, exc))
            print("Aucun fichier n'a ete modifie.")
            return 1

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for key, path in FILES.items():
        if new_texts[key] != texts[key]:
            backup = Path(str(path) + BACKUP_TAG + stamp)
            shutil.copy2(path, backup)
            path.write_text(new_texts[key], encoding="utf-8")
            ast.parse(read(path))
            print("+ %s modifie (sauvegarde : %s)" % (path, backup.name))

    for label in todo:
        print("  ok : " + label)
    print("Termine. Pour annuler : python3 patch_familles.py --revert")
    return 0


def do_revert():
    restored = 0
    for key, path in FILES.items():
        backups = sorted(glob.glob(str(path) + BACKUP_TAG + "*"))
        if not backups:
            print("- %s : aucune sauvegarde, rien a restaurer." % path.name)
            continue
        oldest = backups[0]
        shutil.copy2(oldest, path)
        ast.parse(read(path))
        print("+ %s restaure depuis %s" % (path.name, Path(oldest).name))
        restored += 1
    if restored == 0:
        print("Rien n'a ete restaure.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--check"]:
        raise SystemExit(do_check())
    if args == ["--revert"]:
        raise SystemExit(do_revert())
    if args == []:
        raise SystemExit(do_apply())
    print("Usage : python3 patch_familles.py [--check | --revert]")
    raise SystemExit(1)
