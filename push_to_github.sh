#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
cd "$PROJECT_ROOT"

REPO_URL="https://github.com/divin-stoni/VinaStudio.git"

echo "=================================================="
echo "ETAPE 1 : renommer la branche en 'main' (standard GitHub)"
echo "=================================================="
git branch -m master main

echo "=================================================="
echo "ETAPE 2 : lier le depot distant"
echo "=================================================="
if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REPO_URL"
else
    git remote add origin "$REPO_URL"
fi
git remote -v

echo "=================================================="
echo "ETAPE 3 : push (GitHub va demander tes identifiants)"
echo "=================================================="
echo "IMPORTANT : GitHub ne demande plus ton mot de passe pour ce type"
echo "d'operation. A la place, il faut un 'Personal Access Token' (PAT)."
echo "Si ce n'est pas deja fait :"
echo "  1. https://github.com/settings/tokens -> Generate new token (classic)"
echo "  2. Coche la case 'repo'"
echo "  3. Genere, copie le token (tu ne le reverras plus)"
echo "  4. Quand Git demande 'Password', colle CE TOKEN (pas ton mot de passe GitHub)"
echo ""

git push -u origin main

echo "=================================================="
echo "TERMINE : code pousse sur https://github.com/divin-stoni/VinaStudio"
echo "=================================================="
