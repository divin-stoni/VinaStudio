#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch build-windows.yml : reference_data a ete deplace sous src/reference_data
(le .spec Linux le confirme deja), mais le workflow Windows pointait encore
vers l'ancien chemin racine "reference_data", inexistant -> PyInstaller
echouait avec "Unable to find ... reference_data".

Sauvegarde horodatee avant ecriture, verification basique apres patch,
restauration automatique si ca casse.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

WORKFLOW_PATH = Path.home() / "MexAB_MexR_Analyzer_BETA" / ".github" / "workflows" / "build-windows.yml"

OLD = '            --add-data "reference_data;reference_data" \\\n'
NEW = '            --add-data "src/reference_data;reference_data" \\\n'


def main():
    path = WORKFLOW_PATH
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        sys.exit(1)

    original = path.read_text(encoding="utf-8")

    count = original.count(OLD)
    if count == 0:
        print("ÉCHEC : ligne introuvable (déjà patché, ou le fichier a changé).")
        sys.exit(1)
    if count > 1:
        print(f"ÉCHEC : ligne trouvée {count} fois (devrait être unique).")
        sys.exit(1)

    text = original.replace(OLD, NEW)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup_path)
    print(f"Sauvegarde : {backup_path}")

    path.write_text(text, encoding="utf-8")

    try:
        import yaml  # type: ignore
        yaml.safe_load(text)
    except ImportError:
        print("(module 'yaml' absent, vérification syntaxique sautée)")
    except Exception as exc:  # noqa: BLE001
        print("ÉCHEC de vérification YAML, restauration de la sauvegarde :")
        print(exc)
        shutil.copy2(backup_path, path)
        sys.exit(1)

    print("Patch appliqué avec succès.")


if __name__ == "__main__":
    main()
