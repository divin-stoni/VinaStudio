#!/usr/bin/env python3
"""
patch19_switch_primary_fix.py

switch_primary() avait "if index == 3: self.credits_page.ensure_loaded()"
code en dur. Depuis l'insertion de Phytomolecules avant Credits dans la
liste des TopTab, Phytomolecules occupe desormais l'index 3 et Credits
l'index 4 -> cliquer sur Phytomolecules declenchait a tort le chargement
(et la lecture audio) de la video Credits en arriere-plan.

Corrige :
  - la liste "names" (utilisee pour le message de statut) : ajoute
    "Phytomolécules" avant "Crédits"
  - la condition "index == 3" -> "index == 4" pour credits_page.ensure_loaded()

Usage :
    python3 patch19_switch_primary_fix.py [chemin_racine_projet]
"""

import datetime
import py_compile
import shutil
import sys
from pathlib import Path

DEFAULT_CANDIDATES = [Path.home() / "MexAB_MexR_Analyzer_BETA", Path.cwd()]

NAMES_OLD = '''        names = [
            "Docking",
            "Analyse",
            "Visualisation",
            "Crédits",
        ]'''

NAMES_NEW = '''        names = [
            "Docking",
            "Analyse",
            "Visualisation",
            "Phytomolécules",
            "Crédits",
        ]'''

CREDIT_INDEX_OLD = '        if index == 3 and hasattr(self, "credits_page"):'
CREDIT_INDEX_NEW = '        if index == 4 and hasattr(self, "credits_page"):'


def find_project_root(arg):
    if arg:
        p = Path(arg).expanduser()
        if p.exists():
            return p
        print("[!] Chemin fourni introuvable : " + str(p), file=sys.stderr)
        sys.exit(1)
    for cand in DEFAULT_CANDIDATES:
        if (cand / "src").exists():
            return cand
    print("[!] Projet introuvable automatiquement, donne le chemin en argument.", file=sys.stderr)
    sys.exit(1)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    root = find_project_root(arg)
    main_window_path = root / "src" / "gui" / "main_window.py"

    if not main_window_path.exists():
        print("[!] Introuvable : " + str(main_window_path), file=sys.stderr)
        sys.exit(1)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = root / "_archive_backups" / ts / "pre_patch19_main_window.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_window_path, backup_path)
    print("[OK] Sauvegarde : " + str(backup_path))

    text = main_window_path.read_text(encoding="utf-8")
    report = []

    if NAMES_NEW in text:
        report.append("Liste 'names' deja corrigee -> rien refait.")
    else:
        count = text.count(NAMES_OLD)
        if count == 1:
            text = text.replace(NAMES_OLD, NAMES_NEW, 1)
            report.append("Liste 'names' corrigee : 'Phytomolécules' ajoute avant 'Crédits'.")
        elif count == 0:
            report.append("ECHEC : ancre 'names' non trouvee telle quelle -> NON applique.")
        else:
            report.append("ECHEC : ancre 'names' trouvee " + str(count) + " fois (pas unique) -> NON applique.")

    if CREDIT_INDEX_NEW in text:
        report.append("Condition index credits_page deja corrigee -> rien refait.")
    else:
        count = text.count(CREDIT_INDEX_OLD)
        if count == 1:
            text = text.replace(CREDIT_INDEX_OLD, CREDIT_INDEX_NEW, 1)
            report.append("Condition corrigee : credits_page.ensure_loaded() se declenche desormais sur index == 4.")
        elif count == 0:
            report.append("ECHEC : ancre 'index == 3' non trouvee telle quelle -> NON applique.")
        else:
            report.append("ECHEC : ancre 'index == 3' trouvee " + str(count) + " fois (pas unique) -> NON applique.")

    main_window_path.write_text(text, encoding="utf-8")

    try:
        py_compile.compile(str(main_window_path), doraise=True)
        print("[OK] Compile : src/gui/main_window.py")
    except py_compile.PyCompileError as exc:
        print("[ERREUR] Echec de compilation : " + str(exc))
        shutil.copy2(backup_path, main_window_path)
        print("[RESTAURE] main_window.py remis dans son etat d'avant patch19.")
        sys.exit(1)

    print("")
    print("=" * 78)
    print("RAPPORT PATCH19")
    print("=" * 78)
    for line in report:
        print("- " + line)
    print("=" * 78)
    print("Prochaine etape reelle : relance 'python3 main.py' depuis src/, clique sur")
    print("Phytomolécules (plus de son/video Crédits), puis clique sur Crédits pour")
    print("verifier que la video s'y lance toujours bien.")


if __name__ == "__main__":
    main()
