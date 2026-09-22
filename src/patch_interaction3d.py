#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch minimal : Interaction 3D (onglet Visualisation) qui ne se rafraichit
qu'au mouvement de la souris.

Cause visee : le panneau qui contient le QWebEngineView de l'onglet
« Interaction 3D » recoit l'ombre portee (QGraphicsDropShadowEffect) que le
logiciel ajoute a tous les ContentPanel. Chromium ne se repeint alors que
sur evenement de souris. Le viewer du Docking a deja la protection
(skip_glass_elevation) ; celui-ci l'avait oubliee.

Ce que fait le patch : UNE seule ligne ajoutee dans interaction_3d_page() :

    panel.setProperty("skip_glass_elevation", True)

Rien d'autre. Aucun timer, aucun JavaScript, aucun thread ajoute.

Utilisation (depuis le dossier du projet) :

    python3 patch_interaction3d.py                 # applique le patch
    python3 patch_interaction3d.py --check         # dit seulement s'il est applique
    python3 patch_interaction3d.py --revert        # retire le patch
    python3 patch_interaction3d.py chemin/vers/main_window.py   # chemin explicite

Securites :
  - sauvegarde du fichier d'origine (main_window.py.bak_interaction3d),
    creee une seule fois ;
  - refuse de toucher au fichier si le point d'insertion n'est pas
    trouve de facon certaine (ne devine jamais) ;
  - verifie que le fichier reste du Python valide ; sinon, le fichier
    est laisse INTACT ;
  - relancer le patch ne fait rien s'il est deja applique.
"""

import argparse
import py_compile
import re
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = "patch-interaction3d"
FUNC_DEF = "    def interaction_3d_page(self):"
ANCHOR_RE = re.compile(r'^(\s*)panel\.setObjectName\("ContentPanel"\)\s*$')
INSERT_TEMPLATE = (
    '{indent}panel.setProperty("skip_glass_elevation", True)'
    "  # " + MARKER + " : pas d'ombre portee sur un QWebEngineView\n"
)


def find_target(cli_path):
    if cli_path:
        p = Path(cli_path)
        return p if p.is_file() else None
    for candidate in (
        Path("src/gui/main_window.py"),
        Path("gui/main_window.py"),
        Path("main_window.py"),
        Path(__file__).resolve().parent / "src/gui/main_window.py",
        Path(__file__).resolve().parent / "main_window.py",
    ):
        if candidate.is_file():
            return candidate
    return None


def function_span(lines):
    """(debut, fin) des lignes de interaction_3d_page(), ou None si absente
    ou ambigue."""
    starts = [i for i, l in enumerate(lines) if l.rstrip() == FUNC_DEF]
    if len(starts) != 1:
        return None
    start = starts[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        # prochaine methode de la meme classe (4 espaces, "def ")
        if re.match(r"^    def \w", lines[i]):
            end = i
            break
    return start, end


def analyse(lines):
    span = function_span(lines)
    if span is None:
        return "no_function", None, None
    start, end = span
    anchors = [i for i in range(start, end) if ANCHOR_RE.match(lines[i].rstrip("\r\n"))]
    marked = [i for i in range(start, end) if MARKER in lines[i]]
    if marked:
        return "applied", marked, anchors
    if len(anchors) != 1:
        return "bad_anchor", None, anchors
    return "ready", None, anchors


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("path", nargs="?", help="chemin de main_window.py")
    parser.add_argument("--revert", action="store_true", help="retire le patch")
    parser.add_argument("--check", action="store_true", help="n'ecrit rien")
    args = parser.parse_args()

    target = find_target(args.path)
    if target is None:
        print("ERREUR : main_window.py introuvable. Lance ce script depuis la "
              "racine du projet, ou donne le chemin en argument.")
        return 2

    with open(target, "r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    state, marked, anchors = analyse(lines)

    if state == "no_function":
        print("ERREUR : interaction_3d_page() introuvable (ou en double) dans "
              f"{target}. Rien n'a ete modifie.")
        return 3

    if args.check:
        print({"applied": "Patch DEJA applique.",
               "ready": "Patch NON applique (pret a etre applique).",
               "bad_anchor": "Point d'insertion ambigu : rien ne sera modifie."}[state])
        return 0

    if args.revert:
        if state != "applied":
            print("Rien a retirer : le patch n'est pas applique.")
            return 0
        new_lines = [l for i, l in enumerate(lines) if i not in set(marked)]
        action = "retire"
    else:
        if state == "applied":
            print("Deja applique : rien a faire.")
            return 0
        if state == "bad_anchor":
            print("ERREUR : le point d'insertion "
                  '(panel.setObjectName("ContentPanel") dans '
                  "interaction_3d_page) n'est pas unique/introuvable. "
                  "Rien n'a ete modifie.")
            return 3
        idx = anchors[0]
        indent = ANCHOR_RE.match(lines[idx].rstrip("\r\n")).group(1)
        newline = "\r\n" if lines[idx].endswith("\r\n") else "\n"
        insertion = INSERT_TEMPLATE.format(indent=indent).replace("\n", newline)
        new_lines = lines[: idx + 1] + [insertion] + lines[idx + 1:]
        action = "applique"

    # Verification : le resultat doit rester du Python valide.
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.py"
        probe.write_text("".join(new_lines), encoding="utf-8", newline="")
        try:
            py_compile.compile(str(probe), doraise=True)
        except py_compile.PyCompileError as exc:
            print("ERREUR : le fichier ne serait plus valide apres patch. "
                  "Fichier laisse intact.\n", exc)
            return 4

    backup = target.with_name(target.name + ".bak_interaction3d")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"Sauvegarde creee : {backup}")

    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(new_lines)

    print(f"Patch {action} dans {target}.")
    if action == "applique":
        print("Relance le logiciel, ouvre Visualisation > Interaction 3D et "
              "zoome a la molette SANS bouger la souris.")
        print("Pour annuler : python3 patch_interaction3d.py --revert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
