#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"
SRC="$ROOT/src"

echo "############################################################"
echo "# A) Definition exacte de 'class VisualizationPage'"
echo "############################################################"
grep -rn "^class VisualizationPage" "$SRC" --include="*.py" || echo "(non trouve avec ce pattern exact)"
grep -rn "class VisualizationPage" "$SRC" --include="*.py" || true

echo
echo "############################################################"
echo "# B) Taille des fichiers cles"
echo "############################################################"
for f in \
    "$SRC/visualization/visualization_manager.py" \
    "$SRC/gui/visualization_bridge.py" \
    "$SRC/docking/vina_worker.py" \
    "$SRC/docking/vina_engine.py" \
    "$SRC/docking/receptor_viewer_pdb_prep.py"
do
    if [ -f "$f" ]; then
        echo "$f : $(wc -l < "$f") lignes"
    else
        echo "$f : ABSENT"
    fi
done

echo
echo "############################################################"
echo "# C) visualization_manager.py : mots-cles receptor/pdb/pair/target"
echo "############################################################"
if [ -f "$SRC/visualization/visualization_manager.py" ]; then
    grep -n -i "receptor\|pdb\|pair\|target\|repressor\|derepresseur\|pump" "$SRC/visualization/visualization_manager.py" | head -n 100
fi

echo
echo "############################################################"
echo "# D) pair_targets et current_single_target dans main_window.py"
echo "############################################################"
grep -n "pair_targets\|current_single_target\|current_pair_target" "$SRC/gui/main_window.py"

echo
echo "############################################################"
echo "# E) receptor_viewer_pdb_prep.py : mots-cles generation PDB"
echo "############################################################"
if [ -f "$SRC/docking/receptor_viewer_pdb_prep.py" ]; then
    grep -n -i "def \|receptor\|pair\|target" "$SRC/docking/receptor_viewer_pdb_prep.py" | head -n 60
fi
