#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch build_and_package_v2.sh : ajoute credit_du_logiciel au build.

Contexte : _credits_root() (credits_page.py) cherche le dossier
credit_du_logiciel A COTE de l'executable (sys.executable.parent),
jamais dans _internal/. Il ne peut donc pas passer par le bloc
datas=[...] du .spec (qui atterrit toujours sous _internal/) : il doit
etre copie explicitement, au bon endroit, par le script de packaging.

Trois insertions :
  1) Juste apres la verification de l'executable fraichement compile :
     copie credit_du_logiciel a cote de lui dans src/dist/VinaStudio/
     (ce qui suffit a lui seul pour l'archive .tar.gz, qui empaquette
     tout ce dossier).
  2) Dans la construction de l'arborescence .deb, apres la copie de
     _internal : copie credit_du_logiciel a cote de l'executable dans
     le paquet (le .deb ne copie PAS tout src/dist/VinaStudio, il
     copie l'executable et _internal explicitement, donc credit_du_logiciel
     doit l'etre aussi).
  3) Un controle fatal supplementaire, dans le meme style que les
     verifications deja presentes dans le script (echec net plutot
     qu'un .deb silencieusement incomplet).

Sauvegarde horodatee avant ecriture, verification de syntaxe bash
(bash -n) apres patch, restauration automatique si ca casse.
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PATH = Path.home() / "MexAB_MexR_Analyzer_BETA" / "build_and_package_v2.sh"

REPLACEMENTS = [
    (
        'echo ""\n'
        'echo "=== 3. VERIFICATION STRICTE : l\'executable existe-t-il APRES build ? ==="\n'
        'SRC_EXE="$PROJ/src/dist/VinaStudio/VinaStudio"\n'
        'if [ ! -f "$SRC_EXE" ]; then\n'
        '    echo "ERREUR FATALE : $SRC_EXE n\'existe pas apres le build. Abandon."\n'
        '    exit 1\n'
        'fi\n'
        'echo "OK : $SRC_EXE present ($(stat -c%s "$SRC_EXE") octets)"\n',
        'echo ""\n'
        'echo "=== 3. VERIFICATION STRICTE : l\'executable existe-t-il APRES build ? ==="\n'
        'SRC_EXE="$PROJ/src/dist/VinaStudio/VinaStudio"\n'
        'if [ ! -f "$SRC_EXE" ]; then\n'
        '    echo "ERREUR FATALE : $SRC_EXE n\'existe pas apres le build. Abandon."\n'
        '    exit 1\n'
        'fi\n'
        'echo "OK : $SRC_EXE present ($(stat -c%s "$SRC_EXE") octets)"\n'
        '\n'
        'echo ""\n'
        'echo "=== 3bis. Copie de credit_du_logiciel (a cote de l\'executable, requis par _credits_root()) ==="\n'
        'CREDITS_SRC="$PROJ/credit_du_logiciel"\n'
        'CREDITS_DEST="$PROJ/src/dist/VinaStudio/credit_du_logiciel"\n'
        'if [ ! -d "$CREDITS_SRC" ]; then\n'
        '    echo "ERREUR FATALE : $CREDITS_SRC introuvable. Abandon."\n'
        '    exit 1\n'
        'fi\n'
        'rm -rf "$CREDITS_DEST"\n'
        'cp -r "$CREDITS_SRC" "$CREDITS_DEST"\n'
        'echo "OK : credit_du_logiciel copie dans $CREDITS_DEST"\n',
    ),
    (
        'echo "Copie de _internal (peut prendre du temps, ~20000 fichiers)..."\n'
        'cp -r "$PROJ/src/dist/VinaStudio/_internal" "$DEB_ROOT/opt/$PKGNAME/_internal"\n',
        'echo "Copie de _internal (peut prendre du temps, ~20000 fichiers)..."\n'
        'cp -r "$PROJ/src/dist/VinaStudio/_internal" "$DEB_ROOT/opt/$PKGNAME/_internal"\n'
        '\n'
        'echo "Copie de credit_du_logiciel (a cote de l\'executable dans le paquet, requis par _credits_root())..."\n'
        'cp -r "$PROJ/src/dist/VinaStudio/credit_du_logiciel" "$DEB_ROOT/opt/$PKGNAME/credit_du_logiciel"\n',
    ),
    (
        'echo ""\n'
        'echo "=== 5. VERIFICATION STRICTE : l\'executable est-il bien dans le paquet ? ==="\n'
        'if [ ! -f "$DEB_ROOT/opt/$PKGNAME/VinaStudio" ]; then\n'
        '    echo "ERREUR FATALE : la copie de l\'executable a echoue silencieusement. Abandon."\n'
        '    exit 1\n'
        'fi\n'
        'echo "OK : present dans $DEB_ROOT/opt/$PKGNAME/VinaStudio"\n',
        'echo ""\n'
        'echo "=== 5. VERIFICATION STRICTE : l\'executable est-il bien dans le paquet ? ==="\n'
        'if [ ! -f "$DEB_ROOT/opt/$PKGNAME/VinaStudio" ]; then\n'
        '    echo "ERREUR FATALE : la copie de l\'executable a echoue silencieusement. Abandon."\n'
        '    exit 1\n'
        'fi\n'
        'echo "OK : present dans $DEB_ROOT/opt/$PKGNAME/VinaStudio"\n'
        '\n'
        'if [ ! -d "$DEB_ROOT/opt/$PKGNAME/credit_du_logiciel" ]; then\n'
        '    echo "ERREUR FATALE : credit_du_logiciel absent du paquet. Abandon."\n'
        '    exit 1\n'
        'fi\n'
        'echo "OK : credit_du_logiciel present dans $DEB_ROOT/opt/$PKGNAME/credit_du_logiciel"\n',
    ),
]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        sys.exit(1)

    original = path.read_text(encoding="utf-8")
    text = original

    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count == 0:
            print(f"ÉCHEC : bloc introuvable (le fichier a peut-être déjà changé) :\n---\n{old[:150]}...\n---")
            sys.exit(1)
        if count > 1:
            print(f"ÉCHEC : bloc trouvé {count} fois (devrait être unique) :\n---\n{old[:150]}...\n---")
            sys.exit(1)
        text = text.replace(old, new)

    if text == original:
        print("Rien à changer (le fichier semble déjà patché).")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup_path)
    print(f"Sauvegarde : {backup_path}")

    path.write_text(text, encoding="utf-8")

    check = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    if check.returncode != 0:
        print("ÉCHEC de vérification syntaxique (bash -n), restauration de la sauvegarde :")
        print(check.stderr)
        shutil.copy2(backup_path, path)
        sys.exit(1)

    print("Patch appliqué avec succès, syntaxe bash vérifiée.")


if __name__ == "__main__":
    main()
