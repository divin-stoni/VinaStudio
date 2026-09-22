#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch main_window.py : coupe la video en cours de credits_page des qu'on
quitte l'onglet Credits (changement d'onglet vers un autre index).

A appliquer APRES patch_credits_about.py (suppose que le bloc names[] de
switch_primary a deja ete raccourci par ce premier patch).

Sauvegarde horodatee automatique avant ecriture, verification syntaxique
(py_compile) apres patch ; restauration automatique si la compilation echoue.
"""

import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PATH = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui" / "main_window.py"


OLD_BLOCK = (
    '    def switch_primary(self, index):\n'
    '\n'
    '        self.workspace.setCurrentIndex(\n'
    '            index\n'
    '        )\n'
)

NEW_BLOCK = (
    '    def switch_primary(self, index):\n'
    '\n'
    '        if index != 4 and hasattr(self, "credits_page"):\n'
    '            # On quitte (ou on ne va pas vers) l\'onglet Credits : coupe\n'
    '            # toute video en cours pour qu\'elle ne continue pas a se\n'
    '            # lire en arriere-plan une fois la page quittee.\n'
    '            self.credits_page.stop_playback()\n'
    '\n'
    '        self.workspace.setCurrentIndex(\n'
    '            index\n'
    '        )\n'
)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        sys.exit(1)

    original = path.read_text(encoding="utf-8")

    count = original.count(OLD_BLOCK)
    if count == 0:
        print("ÉCHEC : bloc switch_primary introuvable (fichier déjà modifié différemment ?).")
        sys.exit(1)
    if count > 1:
        print(f"ÉCHEC : bloc trouvé {count} fois (devrait être unique).")
        sys.exit(1)

    text = original.replace(OLD_BLOCK, NEW_BLOCK)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup_path)
    print(f"Sauvegarde : {backup_path}")

    path.write_text(text, encoding="utf-8")

    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        print("ÉCHEC de compilation après patch, restauration de la sauvegarde :")
        print(exc)
        shutil.copy2(backup_path, path)
        sys.exit(1)

    print("Patch appliqué avec succès, syntaxe vérifiée.")
    print("N'oublie pas de remplacer aussi credits_page.py par la version fournie (ajout de stop_playback()).")


if __name__ == "__main__":
    main()
