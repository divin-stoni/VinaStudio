#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"

echo "############################################################"
echo "# A) install_vinastudio_local.sh"
echo "############################################################"
FILE="$ROOT/dev/scripts_maintenance/install_vinastudio_local.sh"
if [ -f "$FILE" ]; then
    nl -ba "$FILE"
else
    echo "(introuvable : $FILE)"
    find "$ROOT" -iname "install_vinastudio_local.sh" 2>/dev/null
fi

echo
echo "############################################################"
echo "# B) phyto_page.py : resolution de chemins (Path(__file__), sys.frozen, dossiers de donnees)"
echo "############################################################"
PHYTO="$ROOT/src/gui/phyto_page.py"
if [ -f "$PHYTO" ]; then
    echo "$PHYTO : $(wc -l < "$PHYTO") lignes"
    grep -n "Path(__file__)\|sys.frozen\|sys.executable\|sys._MEIPASS\|_root\s*=\|def _.*root\|\.is_dir()\|reference_data\|phyto" "$PHYTO" | head -80
else
    echo "(introuvable)"
fi

echo
echo "############################################################"
echo "# C) Autres dossiers de donnees a la racine du projet (hors venv/build/dist/git)"
echo "############################################################"
find "$ROOT" -maxdepth 1 -type d | grep -vE "venv|/\.git$|/build$|/dist$|__pycache__|backups|archive" | sort
