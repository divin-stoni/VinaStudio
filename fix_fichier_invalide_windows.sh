#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/MexAB_MexR_Analyzer_BETA"

echo "=================================================="
echo "ETAPE 1 : suppression du/des fichier(s) au nom invalide"
echo "=================================================="
FOUND=0
while IFS= read -r -d '' f; do
    if [[ "$f" =~ [:\*\?\"\<\>\|\\] ]]; then
        echo "Suppression : $f"
        git rm -- "$f"
        FOUND=1
    fi
done < <(git ls-files -z)

if [ "$FOUND" -eq 0 ]; then
    echo "Rien a supprimer (deja fait ou fichier absent)."
    exit 0
fi

echo "=================================================="
echo "ETAPE 2 : commit"
echo "=================================================="
git commit -m "Retire un fichier au nom invalide sous Windows (contenait ':'), bloquait le checkout CI"

echo "=================================================="
echo "ETAPE 3 : push"
echo "=================================================="
git push origin main

echo "=================================================="
echo "TERMINE -- le build Windows va se redeclencher automatiquement."
echo "  https://github.com/divin-stoni/VinaStudio/actions"
echo "=================================================="
