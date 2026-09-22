#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"
SRC="$ROOT/src"

if [ ! -d "$SRC" ]; then
    echo "Dossier introuvable : $SRC"
    exit 1
fi

echo "=== Racine analysée : $SRC ==="
echo

echo "############################################################"
echo "# A) Fichiers du projet mentionnant VisualizationPage"
echo "############################################################"
grep -rln "class VisualizationPage\|VisualizationPage(" "$SRC" || echo "(rien)"

echo
echo "############################################################"
echo "# B) Fichiers mentionnant MexR / MexB / derepresseur (en dur ?)"
echo "############################################################"
grep -rn "MexR\|MexB\|dérépresseur\|derepresseur" "$SRC" --include="*.py" -l || echo "(rien)"

echo
echo "############################################################"
echo "# C) Ou sont generes les fichiers PDB apres docking"
echo "############################################################"
grep -rln "\.pdb\b" "$SRC" --include="*.py" || echo "(rien)"

echo
echo "############################################################"
echo "# D) Structure du dossier src/gui et src/docking"
echo "############################################################"
find "$SRC/gui" -maxdepth 1 -name "*.py" 2>/dev/null | sort
echo "---"
find "$SRC/docking" -maxdepth 1 -name "*.py" 2>/dev/null | sort
echo "---"
find "$SRC" -maxdepth 2 -type d | sort

echo
echo "############################################################"
echo "# E) Dans VisualizationPage (si trouve) : mots-cles receptor/target"
echo "############################################################"
VP_FILE=$(grep -rln "class VisualizationPage" "$SRC" --include="*.py" | head -n1 || true)
if [ -n "${VP_FILE:-}" ]; then
    echo "Fichier : $VP_FILE ($(wc -l < "$VP_FILE") lignes)"
    grep -n -i "receptor\|target\|pdb_path\|pdb_file\|self\.receptor\|self\.target" "$VP_FILE" | head -n 60
else
    echo "(classe VisualizationPage non trouvee automatiquement)"
fi
