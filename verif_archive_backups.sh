#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"
cd "$ROOT"

echo "############################################################"
echo "# A) Taille de _archive_backups (non exclu actuellement)"
echo "############################################################"
du -sh _archive_backups 2>/dev/null || echo "(absent)"

echo
echo "############################################################"
echo "# B) Plus gros fichiers dans _archive_backups (verifier >100 Mo)"
echo "############################################################"
find _archive_backups -type f -size +50M -exec ls -lh {} \; 2>/dev/null | awk '{print $5, $NF}'

echo
echo "############################################################"
echo "# C) Tailles des dossiers deja exclus par .gitignore (pour info)"
echo "############################################################"
for d in venv src/dist src/build build dist _a_supprimer .session; do
    if [ -e "$d" ]; then
        du -sh "$d" 2>/dev/null
    fi
done

echo
echo "############################################################"
echo "# D) Autres fichiers >90 Mo hors _archive_backups/venv/dist/build (deja repere : tar.gz, deb)"
echo "############################################################"
find . \
    -path ./venv -prune -o \
    -path ./_archive_backups -prune -o \
    -path ./build -prune -o \
    -path ./dist -prune -o \
    -path ./src/build -prune -o \
    -path ./src/dist -prune -o \
    -type f -size +90M -print 2>/dev/null
