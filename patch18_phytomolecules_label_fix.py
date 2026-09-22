#!/usr/bin/env python3
"""
patch18_phytomolecules_label_fix.py

Corrige retranslate_ui() : tab_labels n'avait que 4 entrees pour 5
boutons (Docking/Analyse/Visualisation/Phytomolecules/Credits) -> zip()
tronquait et le 4e bouton affichait "Credits" au lieu de
"Phytomolecules". Ajoute "Phytomolécules" a la bonne position.

Usage :
    python3 patch18_phytomolecules_label_fix.py [chemin_racine_projet]
"""

import datetime
import py_compile
import shutil
import sys
from pathlib import Path

DEFAULT_CANDIDATES = [Path.home() / "MexAB_MexR_Analyzer_BETA", Path.cwd()]

OLD = 'tab_labels = [t("side_docking"), t("nav_analysis"), t("nav_visualization"), "Crédits"]'
NEW = 'tab_labels = [t("side_docking"), t("nav_analysis"), t("nav_visualization"), "Phytomolécules", "Crédits"]'


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
    backup_path = root / "_archive_backups" / ts / "pre_patch18_main_window.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_window_path, backup_path)
    print("[OK] Sauvegarde : " + str(backup_path))

    text = main_window_path.read_text(encoding="utf-8")

    if NEW in text:
        print("[SKIP] Deja corrige, rien a faire.")
        return

    count = text.count(OLD)
    if count == 0:
        print("[ECHEC] Ancre non trouvee telle quelle -> NON applique. "
              "Verifie que le fichier n'a pas change depuis le dernier rapport.")
        sys.exit(1)
    if count > 1:
        print("[ECHEC] Ancre trouvee " + str(count) + " fois (pas unique) -> NON applique par prudence.")
        sys.exit(1)

    text = text.replace(OLD, NEW, 1)
    main_window_path.write_text(text, encoding="utf-8")
    print("[OK] tab_labels corrige : 'Phytomolécules' ajoute avant 'Crédits'.")

    try:
        py_compile.compile(str(main_window_path), doraise=True)
        print("[OK] Compile : src/gui/main_window.py")
    except py_compile.PyCompileError as exc:
        print("[ERREUR] Echec de compilation : " + str(exc))
        shutil.copy2(backup_path, main_window_path)
        print("[RESTAURE] main_window.py remis dans son etat d'avant patch18.")
        sys.exit(1)

    print("\nProchaine etape reelle : relance 'python3 main.py' depuis src/ et verifie "
          "que le 4e bouton affiche bien 'Phytomolécules'.")


if __name__ == "__main__":
    main()
