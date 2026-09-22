#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"

echo "=== Racine analysée : $ROOT ==="
echo

echo "############################################################"
echo "# A) Fichiers .spec (PyInstaller)"
echo "############################################################"
find "$ROOT" -maxdepth 3 -name "*.spec" 2>/dev/null

echo
echo "############################################################"
echo "# B) Dossier debian/ (paquet .deb) s'il existe"
echo "############################################################"
find "$ROOT" -maxdepth 3 -iname "debian" -type d 2>/dev/null
find "$ROOT" -maxdepth 4 -iname "control" 2>/dev/null

echo
echo "############################################################"
echo "# C) Scripts de build / packaging (noms probables)"
echo "############################################################"
find "$ROOT" -maxdepth 2 -iname "*build*.sh" -o -iname "*package*.sh" -o -iname "*deb*.sh" -o -iname "Makefile" -o -iname "setup.py" 2>/dev/null

echo
echo "############################################################"
echo "# D) Racine du projet (listing complet, 1 niveau)"
echo "############################################################"
find "$ROOT" -maxdepth 1 | sort

echo
echo "############################################################"
echo "# E) Contenu de src/build et src/dist (deja vus precedemment)"
echo "############################################################"
find "$ROOT/src/build" -maxdepth 2 2>/dev/null
echo "---"
find "$ROOT/src/dist" -maxdepth 2 2>/dev/null

echo
echo "############################################################"
echo "# F) Fichiers mentionnant 'hiddenimports' ou 'datas' (PyInstaller) ou 'Depends:' (deb)"
echo "############################################################"
grep -rl "hiddenimports\|Depends:\|datas\s*=" "$ROOT" --include="*.spec" --include="*.sh" --include="control" --include="Makefile" 2>/dev/null || echo "(rien)"

echo
echo "############################################################"
echo "# G) README / CHANGELOG a la racine (pour reperer la doc de release existante)"
echo "############################################################"
find "$ROOT" -maxdepth 1 -iname "README*" -o -iname "CHANGELOG*" -o -iname "VERSION*" 2>/dev/null
