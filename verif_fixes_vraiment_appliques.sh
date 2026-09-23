#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) 'requests' est-il dans requirements-windows.txt / requirements.txt ?"
echo "======================================================================"
echo "--- requirements-windows.txt ---"
grep -i "requests" requirements-windows.txt || echo "ABSENT"
echo "--- requirements.txt ---"
grep -i "requests" requirements.txt || echo "ABSENT"

echo
echo "======================================================================"
echo "2) ChimeraX est-il encore dans le code (tool_manager.py, environment_manager.py) ?"
echo "======================================================================"
grep -ci "chimerax" src/tools/tool_manager.py src/environment/environment_manager.py

echo
echo "======================================================================"
echo "3) Les 3 fichiers orphelins ont-ils ete supprimes ?"
echo "======================================================================"
for f in src/visualization/interaction_3d.py src/visualization/pose_manager.py src/visualization/interaction_visualizer.py; do
    if [[ -f "$f" ]]; then
        echo "TOUJOURS PRESENT : $f"
    else
        echo "supprime : $f"
    fi
done

echo
echo "======================================================================"
echo "4) Ces changements sont-ils dans l'historique git (commits recents) ?"
echo "======================================================================"
git log --oneline -8

echo
echo "======================================================================"
echo "5) Y a-t-il des modifications non commitees en ce moment ?"
echo "======================================================================"
git status --porcelain | head -30

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
