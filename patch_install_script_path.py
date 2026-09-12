# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("install_vinastudio_local.sh")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

old = '''if [ ! -d "$SRC_DIR/dist/$APP_NAME" ]; then
    echo "ERREUR : dist/$APP_NAME introuvable. Le build a peut-etre ete efface."
    echo "Relance d'abord : cd $SRC_DIR && pyinstaller --noconfirm --windowed --name $APP_NAME --paths $PROJECT_ROOT --icon=vinastudio_icon.png --add-data $PROJECT_ROOT/reference_data:reference_data --add-data $SRC_DIR/i18n:i18n main.py"
    exit 1
fi
echo "OK, build trouve."'''

new = '''if [ ! -d "$PROJECT_ROOT/dist/$APP_NAME" ]; then
    echo "ERREUR : dist/$APP_NAME introuvable. Le build a peut-etre ete efface."
    echo "Relance d'abord : cd $PROJECT_ROOT && pyinstaller --noconfirm src/VinaStudio.spec"
    exit 1
fi
echo "OK, build trouve."'''

if old not in content:
    raise SystemExit("✗ Bloc attendu introuvable, patch annulé.")
content = content.replace(old, new, 1)

old_cp = 'cp -r "$SRC_DIR/dist/$APP_NAME/"* "$INSTALL_DIR/"'
new_cp = 'cp -r "$PROJECT_ROOT/dist/$APP_NAME/"* "$INSTALL_DIR/"'

if old_cp not in content:
    raise SystemExit("✗ Ligne de copie introuvable, patch annulé.")
content = content.replace(old_cp, new_cp, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ install_vinastudio_local.sh corrigé : pointe vers dist/VinaStudio à la racine du projet")
