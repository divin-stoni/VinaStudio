# -*- coding: utf-8 -*-
"""
patch_session_entete.py

Patch reversible sur src/gui/main_window.py :

  1. "Lancer l'analyse" ne se rabat plus sur d'anciens resultats du disque
     (menu Campagne / "Dernier couple"). Sans docking dans la session,
     il affiche "Aucun resultat de docking disponible".
  2. Le bandeau "Cible active" suit la page :
       - page Docking : la cible choisie pour le docking (comme avant) ;
       - page Analyse : les recepteurs de la campagne analysee
         (ex. AcrB + AcrR), ou "Aucune campagne".
     Il se met a jour au changement de page et apres l'analyse.

Usage, depuis la racine du projet :
    python3 patch_session_entete.py --check
    python3 patch_session_entete.py
    python3 patch_session_entete.py --revert
"""

import ast
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

TARGET = Path("src/gui/main_window.py")
BACKUP_TAG = ".bak_sessionentete_"
MAX_MULTI = 3  # nombre maximal d'emplacements acceptes pour un edit multiple

# ----------------------------------------------------------------------
# 1. plus de repli sur d'anciens resultats
# ----------------------------------------------------------------------

OLD_FALLBACK = '''# Repli : aucune campagne lancee dans cette session — on utilise
# celle selectionnee dans le menu « Campagne », si ses resultats
# existent sur le disque.
if not csv_path:
    csv_path = self._campaign_csv_path(
        self.analysis_campaign_combo.currentText()
        if getattr(self, "analysis_campaign_combo", None)
        else ""
    )'''

NEW_FALLBACK = '''# patch-session : plus aucun repli sur d'anciens resultats du disque.
# L'analyse ne porte que sur le docking de cette session (ou sur une
# analyse chargee explicitement), jamais sur un fichier reste de la veille.'''

# ----------------------------------------------------------------------
# 2. resume de la campagne (AnalysisPage)
# ----------------------------------------------------------------------

OLD_RUN_DEF = '''def run_docking_analysis(self):'''

NEW_RUN_DEF = '''def campaign_summary(self):
    # patch-entete : recepteurs de la campagne analysee
    result = getattr(self, "statistics_result", None)
    if result:
        labels = result.get("labels") or {}
        names = [n for n in (labels.get("x"), labels.get("y")) if n]
        if names:
            return " + ".join(names)
    csv_path = getattr(self, "docking_results_csv", None)
    if csv_path:
        try:
            from src.campaign_table import normalize_docking_csv, campaign_shape
            info = campaign_shape(normalize_docking_csv(csv_path))
            return " + ".join(
                self._receptor_table_label(rid, info["labels"][rid])
                for rid in info["receptors"]
            )
        except Exception:
            pass
    return "Aucune campagne"

def run_docking_analysis(self):'''

# ----------------------------------------------------------------------
# 3. mise a jour du bandeau apres l'analyse
# ----------------------------------------------------------------------

OLD_POPULATE = '''self.populate_statistics_results()

self.stack.setCurrentIndex(
    2
)'''

NEW_POPULATE = '''self.populate_statistics_results()

# patch-entete : recharge le bandeau avec les recepteurs analyses
try:
    self.window()._refresh_header_target()
except Exception:
    pass

self.stack.setCurrentIndex(
    2
)'''

# ----------------------------------------------------------------------
# 4. le bandeau suit la page active (MainWindow)
# ----------------------------------------------------------------------

OLD_BUILD_DEF = '''def build_interface(self):'''

NEW_BUILD_DEF = '''def _refresh_header_target(self):
    # patch-entete : la cible affichee suit la page active
    try:
        page = self.workspace.currentWidget()
        if page is self.analysis_page:
            text = self.analysis_page.campaign_summary()
        else:
            text = self.docking_page.target_combo.currentText()
        self.header_target_label.setText(text)
    except Exception as exc:
        gui_debug("En-tete cible ignore : " + str(exc))

def build_interface(self):'''

OLD_SIGNAL = '''self.header_target_label.setText(
    self.docking_page.target_combo.currentText()
)'''

NEW_SIGNAL = '''self.header_target_label.setText(
    self.docking_page.target_combo.currentText()
)

self.workspace.currentChanged.connect(
    lambda _index: self._refresh_header_target()
)'''

# (description, ancien, nouveau, marqueur, plusieurs emplacements acceptes)
EDITS = [
    ("plus de repli sur d'anciens resultats (run_docking_analysis)",
     OLD_FALLBACK, NEW_FALLBACK, "patch-session : plus aucun repli", False),
    ("resume de la campagne analysee (campaign_summary)",
     OLD_RUN_DEF, NEW_RUN_DEF, "def campaign_summary(self):", False),
    ("bandeau recharge apres l'analyse (tous les emplacements)",
     OLD_POPULATE, NEW_POPULATE, "patch-entete : recharge le bandeau", True),
    ("bandeau qui suit la page (_refresh_header_target)",
     OLD_BUILD_DEF, NEW_BUILD_DEF, "def _refresh_header_target(self):", False),
    ("bandeau relie au changement de page",
     OLD_SIGNAL, NEW_SIGNAL, "lambda _index: self._refresh_header_target()", False),
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


def line_numbers(text, matches):
    return ", ".join(str(text.count("\n", 0, m.start()) + 1) for m in matches)


def already_applied(text, marker):
    return re.sub(r"\s+", " ", marker) in re.sub(r"\s+", " ", text)


def do_check():
    if not TARGET.is_file():
        print("Introuvable : %s (lance depuis la racine du projet)" % TARGET)
        return 1
    text = TARGET.read_text(encoding="utf-8")
    ok = True
    for label, old, new, marker, multi in EDITS:
        if already_applied(text, marker):
            state = "deja applique"
        else:
            found = find_matches(text, old)
            n = len(found)
            good = (1 <= n <= MAX_MULTI) if multi else (n == 1)
            if good and n == 1:
                state = "applicable"
            elif good:
                state = "applicable (%d emplacements, lignes %s)" % (n, line_numbers(text, found))
            else:
                state = "BLOQUE (%d correspondance(s))" % n
                ok = False
        print("[%s] %s : %s" % (TARGET.name, label, state))
    return 0 if ok else 1


def do_apply():
    if not TARGET.is_file():
        print("Introuvable : %s (lance depuis la racine du projet)" % TARGET)
        return 1
    text = TARGET.read_text(encoding="utf-8")
    todo = []
    for label, old, new, marker, multi in EDITS:
        if already_applied(text, marker):
            print("= deja applique : " + label)
            continue
        matches = find_matches(text, old)
        n = len(matches)
        good = (1 <= n <= MAX_MULTI) if multi else (n == 1)
        if not good:
            print("X BLOQUE : %s (%d correspondance(s))" % (label, n))
            print("Aucun fichier n'a ete modifie.")
            return 1
        if n > 1:
            print("  %s : %d emplacements, lignes %s" % (label, n, line_numbers(text, matches)))
        for match in reversed(matches):
            text = replace_once(text, match, new)
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
    print("Termine. Pour annuler : python3 patch_session_entete.py --revert")
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
    print("Usage : python3 patch_session_entete.py [--check | --revert]")
    raise SystemExit(1)
