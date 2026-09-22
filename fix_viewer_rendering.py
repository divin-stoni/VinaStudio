#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_viewer_rendering.py
========================

Corrige le rendu blanc / figé du visualiseur 3D (QWebEngineView + 3Dmol.js)
dans gui/main_window.py.

Cause racine diagnostiquée :
  1. Qt.AA_ShareOpenGLContexts n'est jamais positionne avant la creation de
     QApplication (prerequis documente de QtWebEngine pour le partage de
     contexte OpenGL entre Chromium et Qt).
  2. Aucun flag Chromium n'est configure pour forcer un rendu WebGL
     logiciel, indispensable sous WSL2 ou le sous-processus GPU de
     Chromium echoue souvent a initialiser un contexte materiel correct.

Sans ces deux reglages, le canvas WebGL reste blanc et ne se met a jour
que lorsqu'un evenement externe (ex. deplacement de la barre de
defilement de la QScrollArea parente) force un repaint complet du
widget — d'ou le panneau blanc au demarrage, la mise a jour uniquement
au scroll, et l'absence de reaction aux rotations a la souris.

Usage :
    cd ~/MexAB_MexR_Analyzer_BETA        # racine du projet (contient src/gui/main_window.py)
    python3 fix_viewer_rendering.py

Le script :
  - localise automatiquement src/gui/main_window.py depuis le repertoire courant
  - fait une sauvegarde horodatee avant toute modification
  - applique deux remplacements de blocs de texte exacts
  - verifie la syntaxe du fichier patche avec ast.parse
  - restaure automatiquement la sauvegarde en cas d'echec
  - affiche un rapport clair
"""

from __future__ import annotations

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path


TARGET_RELATIVE = Path("src") / "gui" / "main_window.py"

# ----------------------------------------------------------------------------
# Bloc 1 : flags Chromium (WebGL logiciel), a inserer tout en tete du fichier,
# avant tout import PySide6 (le sous-processus GPU de Chromium lit cette
# variable d'environnement des son initialisation, il faut donc la
# positionner le plus tot possible).
# ----------------------------------------------------------------------------
OLD_BLOCK_1 = '''# -*- coding: utf-8 -*-

from __future__ import annotations
from src.session_runtime import start_new_session, end_session'''

NEW_BLOCK_1 = '''# -*- coding: utf-8 -*-

from __future__ import annotations

# ----------------------------------------------------------------------------
# WORKAROUND WebGL/QtWebEngine (rendu du visualiseur 3D)
# ----------------------------------------------------------------------------
# Sous WSL2 (et plus generalement dans les environnements graphiques
# distants/virtualises : Xvfb, VNC, VMs...), le processus GPU de Chromium
# utilise par QtWebEngine echoue souvent a initialiser un contexte WebGL
# materiel correct. Resultat observe : le panneau du visualiseur reste
# blanc au demarrage, ne s'actualise que lorsqu'un evenement externe force
# un repaint complet du widget (ex. deplacer la barre de defilement de la
# QScrollArea parente), et les rotations a la souris (qui dependent des
# frames WebGL rendues via requestAnimationFrame) restent sans effet car
# le compositeur GPU ne fournit jamais de nouvelle frame.
#
# Cette variable doit etre positionnee AVANT toute creation de widget
# QtWebEngine ; elle force Chromium a utiliser un rendu WebGL logiciel
# (ANGLE/SwiftShader) au lieu du GPU materiel indisponible/instable.
import os

os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--use-gl=angle --use-angle=swiftshader --disable-gpu-compositing "
    "--enable-webgl --ignore-gpu-blocklist",
)

from src.session_runtime import start_new_session, end_session'''


# ----------------------------------------------------------------------------
# Bloc 2 : partage de contexte OpenGL, a positionner juste avant la creation
# de QApplication.
# ----------------------------------------------------------------------------
OLD_BLOCK_2 = '''def main():

    app = QApplication(sys.argv)'''

NEW_BLOCK_2 = '''def main():

    # Doit etre positionne AVANT la creation de QApplication : prerequis
    # documente de QtWebEngine pour le partage de contexte OpenGL entre
    # Chromium et Qt (evite le rendu WebGL fige/blanc du visualiseur 3D).
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)'''


def find_target() -> Path:
    candidates = [
        Path.cwd() / TARGET_RELATIVE,
        Path.cwd() / "main_window.py",
    ]
    for c in candidates:
        if c.is_file() and c.name == "main_window.py":
            return c
    # dernier recours : recherche recursive depuis le repertoire courant
    matches = list(Path.cwd().rglob("main_window.py"))
    matches = [m for m in matches if ".backup_" not in m.name and ".before_" not in m.name]
    if len(matches) == 1:
        return matches[0]
    print("[ERREUR] Impossible de localiser gui/main_window.py automatiquement.")
    print("         Lance ce script depuis la racine du projet")
    print("         (celle qui contient src/gui/main_window.py), ou place-le")
    print("         a cote de main_window.py.")
    if matches:
        print("\nCandidats trouves :")
        for m in matches:
            print(f"  - {m}")
    sys.exit(1)


def apply_block(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count == 0:
        print(f"[ERREUR] Bloc introuvable ({label}). Le fichier a peut-etre deja "
              f"ete modifie, ou sa structure a change depuis le diagnostic.")
        sys.exit(1)
    if count > 1:
        print(f"[ERREUR] Bloc trouve {count} fois ({label}) — remplacement ambigu, abandon.")
        sys.exit(1)
    print(f"[OK] Bloc localise et remplace : {label}")
    return content.replace(old, new, 1)


def main() -> None:
    target = find_target()
    print(f"Fichier cible : {target}")

    original_text = target.read_text(encoding="utf-8")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target.with_name(f"{target.name}.backup_{timestamp}")
    shutil.copy2(target, backup_path)
    print(f"[OK] Sauvegarde creee : {backup_path}")

    patched = original_text
    patched = apply_block(
        patched, OLD_BLOCK_1, NEW_BLOCK_1,
        "flags Chromium WebGL logiciel (en-tete du fichier)",
    )
    patched = apply_block(
        patched, OLD_BLOCK_2, NEW_BLOCK_2,
        "Qt.AA_ShareOpenGLContexts (avant QApplication)",
    )

    try:
        ast.parse(patched)
    except SyntaxError as exc:
        print(f"[ERREUR] Le fichier patche contient une erreur de syntaxe : {exc}")
        print("         Aucune modification ecrite, le fichier original est intact.")
        sys.exit(1)

    target.write_text(patched, encoding="utf-8")

    print("\n" + "=" * 70)
    print("PATCH APPLIQUE AVEC SUCCES")
    print("=" * 70)
    print(f"Fichier modifie      : {target}")
    print(f"Sauvegarde (avant)   : {backup_path}")
    print("Verification syntaxe : OK (ast.parse)")
    print("\nChangements :")
    print("  1. Flags Chromium (rendu WebGL logiciel) ajoutes en tete de fichier,")
    print("     avant les imports PySide6/QtWebEngine.")
    print("  2. QApplication.setAttribute(Qt.AA_ShareOpenGLContexts) ajoute juste")
    print("     avant la creation de QApplication dans main().")
    print("\nRelance VinaStudio pour verifier :")
    print("  - le panneau 3D doit afficher la proteine des le chargement (plus de blanc)")
    print("  - la rotation a la souris doit fonctionner immediatement")
    print("\nEn cas de probleme, restaure la sauvegarde :")
    print(f"  cp {backup_path} {target}")


if __name__ == "__main__":
    main()
