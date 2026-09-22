#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"

echo "############################################################"
echo "# A) .github/workflows/build-windows.yml (version actuelle)"
echo "############################################################"
FILE="$ROOT/.github/workflows/build-windows.yml"
if [ -f "$FILE" ]; then
    echo "$(wc -l < "$FILE") lignes"
    nl -ba "$FILE"
else
    echo "(absent)"
fi

echo
echo "############################################################"
echo "# B) Etat git du depot (branche, remote, statut, derniers commits)"
echo "############################################################"
cd "$ROOT"
echo "--- git status ---"
git status 2>&1 | head -30 || echo "(pas un repo git ou erreur)"
echo "--- git remote -v ---"
git remote -v 2>&1 || true
echo "--- git branch ---"
git branch -a 2>&1 || true
echo "--- git log (5 derniers) ---"
git log --oneline -5 2>&1 || true
echo "--- git tag ---"
git tag 2>&1 || true
