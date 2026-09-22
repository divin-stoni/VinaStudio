#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) tool_manager.py -- dict des definitions (lignes 1 a 95, numerotees)"
echo "======================================================================"
sed -n '1,95p' src/tools/tool_manager.py | nl -ba -v1

echo
echo "======================================================================"
echo "2) tool_manager.py -- methode check_chimerax complete + son appel"
echo "   (lignes 330 a 410, numerotees a partir de 330)"
echo "======================================================================"
sed -n '330,410p' src/tools/tool_manager.py | nl -ba -v330

echo
echo "======================================================================"
echo "3) environment_manager.py -- liste des Dependency() (lignes 1 a 70)"
echo "======================================================================"
sed -n '1,70p' src/environment/environment_manager.py | nl -ba -v1

echo
echo "======================================================================"
echo "4) environment_manager.py -- detect_chimerax + dispatch (lignes 400 a 495)"
echo "======================================================================"
sed -n '400,495p' src/environment/environment_manager.py | nl -ba -v400

echo
echo "======================================================================"
echo "5) Taille des 3 fichiers a supprimer entierement (confirmation orphelins)"
echo "======================================================================"
wc -l src/visualization/interaction_3d.py src/visualization/pose_manager.py src/visualization/interaction_visualizer.py

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
