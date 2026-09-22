#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Patch build Windows :
  1) .github/workflows/build-windows.yml
     - ajoute "src/i18n;i18n" a --add-data (present cote Linux, absent ici)
     - copie credit_du_logiciel a cote de dist\VinaStudio.exe apres le
       build PyInstaller (--onefile => --add-data ne convient pas, meme
       raison que sur Linux : _credits_root() cherche a cote de l'exe
       reel, pas dans un dossier temporaire d'extraction)
     - inclut credit_du_logiciel dans l'artifact "VinaStudio-Windows"
       (le .exe brut, en plus de l'installeur)
  2) VinaStudio.iss (Inno Setup)
     - ajoute credit_du_logiciel a [Files], copie a cote de l'exe
       installe ({app}\credit_du_logiciel)

Sauvegarde horodatee avant ecriture, verification de syntaxe (YAML
via python, .iss juste par relecture) apres patch, restauration
automatique si un fichier casse.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "MexAB_MexR_Analyzer_BETA"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "build-windows.yml"
ISS_PATH = ROOT / "VinaStudio.iss"


WORKFLOW_REPLACEMENTS = [
    (
        '          pyinstaller --noconfirm --onefile --windowed \\\n'
        '            --name VinaStudio \\\n'
        '            --paths src \\\n'
        '            --add-data "reference_data;reference_data" \\\n'
        '            --add-data "docking/receptor;docking/receptor" \\\n',
        '          pyinstaller --noconfirm --onefile --windowed \\\n'
        '            --name VinaStudio \\\n'
        '            --paths src \\\n'
        '            --add-data "reference_data;reference_data" \\\n'
        '            --add-data "src/i18n;i18n" \\\n'
        '            --add-data "docking/receptor;docking/receptor" \\\n',
    ),
    (
        '      - name: Build installer with Inno Setup\n'
        '        shell: pwsh\n'
        '        run: |\n'
        '          & "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" "VinaStudio.iss"\n',
        '      - name: Copy credit_du_logiciel next to the exe (required by _credits_root())\n'
        '        shell: pwsh\n'
        '        run: |\n'
        '          Copy-Item -Path "credit_du_logiciel" -Destination "dist\\credit_du_logiciel" -Recurse -Force\n'
        '          if (-not (Test-Path "dist\\credit_du_logiciel")) {\n'
        '            Write-Error "credit_du_logiciel absent apres copie -- abandon."\n'
        '            exit 1\n'
        '          }\n'
        '          Write-Host "OK : credit_du_logiciel copie dans dist\\credit_du_logiciel"\n'
        '\n'
        '      - name: Build installer with Inno Setup\n'
        '        shell: pwsh\n'
        '        run: |\n'
        '          & "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" "VinaStudio.iss"\n',
    ),
    (
        '      - name: Upload .exe as artifact\n'
        '        uses: actions/upload-artifact@v4\n'
        '        with:\n'
        '          name: VinaStudio-Windows\n'
        '          path: dist/VinaStudio.exe\n',
        '      - name: Upload .exe as artifact\n'
        '        uses: actions/upload-artifact@v4\n'
        '        with:\n'
        '          name: VinaStudio-Windows\n'
        '          path: |\n'
        '            dist/VinaStudio.exe\n'
        '            dist/credit_du_logiciel/**\n',
    ),
]

ISS_REPLACEMENTS = [
    (
        '[Files]\n'
        'Source: "dist\\VinaStudio.exe"; DestDir: "{app}"; Flags: ignoreversion\n',
        '[Files]\n'
        'Source: "dist\\VinaStudio.exe"; DestDir: "{app}"; Flags: ignoreversion\n'
        'Source: "dist\\credit_du_logiciel\\*"; DestDir: "{app}\\credit_du_logiciel"; '
        'Flags: ignoreversion recursesubdirs createallsubdirs\n',
    ),
]


def apply_replacements(path: Path, replacements, syntax_check=None):
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        return False

    original = path.read_text(encoding="utf-8")
    text = original

    for old, new in replacements:
        count = text.count(old)
        if count == 0:
            print(f"ÉCHEC sur {path.name} : bloc introuvable :\n---\n{old[:150]}...\n---")
            return False
        if count > 1:
            print(f"ÉCHEC sur {path.name} : bloc trouvé {count} fois (devrait être unique).")
            return False
        text = text.replace(old, new)

    if text == original:
        print(f"{path.name} : rien à changer (déjà patché ?).")
        return True

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup_path)
    print(f"Sauvegarde : {backup_path}")

    path.write_text(text, encoding="utf-8")

    if syntax_check is not None:
        ok, message = syntax_check(text)
        if not ok:
            print(f"ÉCHEC de vérification sur {path.name}, restauration de la sauvegarde :")
            print(message)
            shutil.copy2(backup_path, path)
            return False

    print(f"{path.name} : patch appliqué avec succès.")
    return True


def check_yaml(text: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        return True, "(module 'yaml' absent, vérification syntaxique sautée)"
    try:
        yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return True, ""


def main():
    ok_workflow = apply_replacements(WORKFLOW_PATH, WORKFLOW_REPLACEMENTS, syntax_check=check_yaml)
    ok_iss = apply_replacements(ISS_PATH, ISS_REPLACEMENTS)

    if not (ok_workflow and ok_iss):
        sys.exit(1)


if __name__ == "__main__":
    main()
