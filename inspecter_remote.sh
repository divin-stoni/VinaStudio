#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/MexAB_MexR_Analyzer_BETA"

echo "=== git fetch origin ==="
git fetch origin

echo
echo "=== Commits sur origin/main ==="
git log --oneline origin/main

echo
echo "=== Fichiers presents sur origin/main ==="
git ls-tree -r origin/main --name-only

echo
echo "=== Divergence locale vs distante ==="
git log --oneline --left-right --graph main...origin/main 2>/dev/null || echo "(pas de base commune -- historiques non lies)"
