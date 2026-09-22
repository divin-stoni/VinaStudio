#!/usr/bin/env python3
"""
patch17_phytomolecules_finish.py

Termine l'integration de l'onglet Phytomolecules :
  1. Sauvegarde main_window.py avant modification
  2. Ajoute le nettoyage a la fermeture (shutdown) pour phyto_page, juste
     apres celui de credits_page (meme structure try/except, isolee pour
     ne jamais empecher le nettoyage de Credits si phyto_page echoue)
  3. Insere "Phytomolécules" dans la liste des onglets horizontaux
     (TopTab), juste avant "Crédits"
  4. Compile-check + restauration automatique en cas d'echec

Usage :
    python3 patch17_phytomolecules_finish.py [chemin_racine_projet]
"""

import datetime
import py_compile
import shutil
import sys
from pathlib import Path

DEFAULT_CANDIDATES = [Path.home() / "MexAB_MexR_Analyzer_BETA", Path.cwd()]

SHUTDOWN_ANCHOR = (
    '        try:\n'
    '            if hasattr(self, "credits_page"):\n'
    '                self.credits_page.shutdown()\n'
    '        except Exception as exc:\n'
    '            gui_debug(f"Erreur nettoyage threads Crédits : {exc}")'
)

SHUTDOWN_INSERT = (
    '\n\n        try:\n'
    '            if hasattr(self, "phyto_page"):\n'
    '                self.phyto_page.shutdown()\n'
    '        except Exception as exc:\n'
    '            gui_debug(f"Erreur nettoyage threads Phytomolecules : {exc}")'
)

LIST_ANCHOR = '["Docking", "Analyse", "Visualisation", "Crédits"]'
LIST_REPLACEMENT = '["Docking", "Analyse", "Visualisation", "Phytomolécules", "Crédits"]'


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
    backup_path = root / "_archive_backups" / ts / "pre_patch17_main_window.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_window_path, backup_path)
    print("[OK] Sauvegarde : " + str(backup_path))

    text = main_window_path.read_text(encoding="utf-8")
    report = []

    if "phyto_page.shutdown()" in text:
        report.append("Shutdown phyto_page deja present -> rien refait.")
    elif SHUTDOWN_ANCHOR in text:
        text = text.replace(SHUTDOWN_ANCHOR, SHUTDOWN_ANCHOR + SHUTDOWN_INSERT, 1)
        report.append("Shutdown phyto_page ajoute juste apres celui de credits_page.")
    else:
        report.append("ECHEC : ancre shutdown non retrouvee telle quelle -> NON applique.")

    if "Phytomolécules" in text and LIST_ANCHOR not in text:
        report.append("Onglet Phytomolécules deja present dans la liste TopTab -> rien refait.")
    elif LIST_ANCHOR in text:
        count = text.count(LIST_ANCHOR)
        if count == 1:
            text = text.replace(LIST_ANCHOR, LIST_REPLACEMENT, 1)
            report.append("Onglet 'Phytomolécules' insere dans la liste TopTab, juste avant 'Crédits'.")
        else:
            report.append(
                "ECHEC : la liste des onglets apparait " + str(count) + " fois (pas unique) -> NON applique par prudence."
            )
    else:
        report.append("ECHEC : liste des onglets TopTab non retrouvee telle quelle -> NON applique.")

    main_window_path.write_text(text, encoding="utf-8")

    try:
        py_compile.compile(str(main_window_path), doraise=True)
        print("[OK] Compile : src/gui/main_window.py")
    except py_compile.PyCompileError as exc:
        print("[ERREUR] Echec de compilation : " + str(exc))
        shutil.copy2(backup_path, main_window_path)
        print("[RESTAURE] main_window.py remis dans son etat d'avant patch17.")
        sys.exit(1)

    print("")
    print("=" * 78)
    print("RAPPORT PATCH17 - Finalisation onglet Phytomolecules")
    print("=" * 78)
    for line in report:
        print("- " + line)
    print("=" * 78)
    print("Prochaine etape reelle : lancer 'python3 main.py' depuis src/ et verifier")
    print("que l'onglet Phytomolecules apparait et fonctionne dans la barre du haut.")


if __name__ == "__main__":
    main()
