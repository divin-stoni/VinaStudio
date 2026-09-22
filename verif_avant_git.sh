#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"
cd "$ROOT"

echo "############################################################"
echo "# A) Contenu actuel de .gitignore"
echo "############################################################"
if [ -f .gitignore ]; then
    nl -ba .gitignore
else
    echo "(absent)"
fi

echo
echo "############################################################"
echo "# B) Taille des elements a la racine, tries du plus gros au plus petit"
echo "############################################################"
du -sh --exclude=.git ./* ./.[!.]* 2>/dev/null | sort -rh | head -40

echo
echo "############################################################"
echo "# C) Fichiers individuels de plus de 90 Mo (limite dure GitHub : 100 Mo/fichier)"
echo "############################################################"
find . -path ./venv -prune -o -type f -size +90M -print 2>/dev/null

echo
echo "############################################################"
echo "# D) Taille totale du dossier (hors .git, qui n'existe pas encore)"
echo "############################################################"
du -sh . 2>/dev/null
