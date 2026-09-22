#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"

echo "############################################################"
echo "# A) Contenu de .github (workflows CI existants ?)"
echo "############################################################"
find "$ROOT/.github" -type f 2>/dev/null

echo
echo "############################################################"
echo "# B) VinaStudio.iss (Inno Setup)"
echo "############################################################"
if [ -f "$ROOT/VinaStudio.iss" ]; then
    echo "$(wc -l < "$ROOT/VinaStudio.iss") lignes"
    nl -ba "$ROOT/VinaStudio.iss"
else
    echo "(absent)"
fi

echo
echo "############################################################"
echo "# C) requirements-windows.txt"
echo "############################################################"
if [ -f "$ROOT/requirements-windows.txt" ]; then
    cat "$ROOT/requirements-windows.txt"
else
    echo "(absent)"
fi

echo
echo "############################################################"
echo "# D) Scripts/fichiers mentionnant 'windows' ou '.spec' Windows separe"
echo "############################################################"
find "$ROOT" -maxdepth 2 -iname "*windows*" 2>/dev/null
find "$ROOT" -maxdepth 3 -iname "*.spec" 2>/dev/null

echo
echo "############################################################"
echo "# E) README.md : sections mentionnant Windows"
echo "############################################################"
grep -n -i "windows" "$ROOT/README.md" 2>/dev/null || echo "(rien)"

echo
echo "############################################################"
echo "# F) Remote git configure (pour confirmer le depot GitHub cible)"
echo "############################################################"
cd "$ROOT" && git remote -v 2>/dev/null || echo "(pas de remote / pas un repo git ici)"
