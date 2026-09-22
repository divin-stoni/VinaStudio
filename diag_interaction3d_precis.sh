#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) Toutes les lignes de main_window.py mentionnant 'interaction_3d' (+-3 lignes de contexte)"
echo "======================================================================"
grep -n -B3 -A3 "interaction_3d" src/gui/main_window.py

echo
echo "======================================================================"
echo "2) Fonctions/objets importes depuis interaction_3d dans main_window.py"
echo "======================================================================"
grep -n "from.*interaction_3d\|import.*interaction_3d" src/gui/main_window.py

echo
echo "======================================================================"
echo "3) Toutes les fonctions definies dans interaction_3d.py (pour savoir ce qui est appelable)"
echo "======================================================================"
grep -n "^def \|^class " src/visualization/interaction_3d.py

echo
echo "======================================================================"
echo "4) Lesquelles de ces fonctions sont reellement appelees dans main_window.py"
echo "======================================================================"
for fn in $(grep -oP '(?<=^def )\w+' src/visualization/interaction_3d.py); do
    COUNT=$(grep -c "\b$fn\b" src/gui/main_window.py)
    printf "%-40s -> appelee %s fois dans main_window.py\n" "$fn" "$COUNT"
done

echo
echo "======================================================================"
echo "5) Le viewer 3Dmol.js / QWebEngineView est-il un circuit separe ?"
echo "======================================================================"
echo "--- references a 3Dmol / QWebEngineView dans main_window.py ---"
grep -n -c "3Dmol\|QWebEngineView" src/gui/main_window.py
echo "--- references a viewer_template dans main_window.py ---"
grep -n "viewer_template" src/gui/main_window.py

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
