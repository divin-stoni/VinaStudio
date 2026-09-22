#!/usr/bin/env bash
set -uo pipefail

SRC_FILTER='--include=*.py'
EXCLUDES='--exclude-dir=venv --exclude-dir=.git --exclude-dir=_archive_backups --exclude-dir=_a_supprimer --exclude-dir=_patch_backups'

echo "======================================================================"
echo "1) Tous les fichiers qui importent ou referencent les modules de visu"
echo "   (interaction_3d, InteractionVisualizer, PoseManager, visualization_manager)"
echo "======================================================================"
grep -rln -E "interaction_3d|InteractionVisualizer|PoseManager|visualization_manager|VisualizationManager" $SRC_FILTER $EXCLUDES . 2>/dev/null

echo
echo "======================================================================"
echo "2) Contenu complet de visualization_manager.py (couche d'orchestration probable)"
echo "======================================================================"
if [[ -f src/visualization/visualization_manager.py ]]; then
    cat -n src/visualization/visualization_manager.py
else
    echo "!! src/visualization/visualization_manager.py introuvable"
fi

echo
echo "======================================================================"
echo "3) Import de visualization_manager (ou de la classe) dans main_window.py"
echo "======================================================================"
grep -n -E "visualization_manager|VisualizationManager|from.*visualization import|import.*visualization" src/gui/main_window.py

echo
echo "======================================================================"
echo "4) Appels a la couche visu depuis main_window.py (self.viz_*, self.visu_*, etc.)"
echo "======================================================================"
grep -n -E "self\.(viz|visu|visualization|viewer)[a-zA-Z_]*\s*=" src/gui/main_window.py | head -30

echo
echo "======================================================================"
echo "5) Boutons/actions lies a '3D', 'pose', 'interaction' dans main_window.py"
echo "======================================================================"
grep -n -iE "\.clicked\.connect|\.triggered\.connect" src/gui/main_window.py | grep -iE "3d|pose|interaction|chimera|viewer" 

echo
echo "======================================================================"
echo "6) Import de visualization_bridge.py dans main_window.py, et son contenu"
echo "======================================================================"
grep -n "visualization_bridge" src/gui/main_window.py
echo "--- Contenu de src/gui/visualization_bridge.py ---"
if [[ -f src/gui/visualization_bridge.py ]]; then
    cat -n src/gui/visualization_bridge.py
fi

echo
echo "======================================================================"
echo "7) Toutes les references croisees entre fichiers GUI et modules visu"
echo "   (qui appelle qui, sur l'ensemble de src/)"
echo "======================================================================"
for f in src/visualization/interaction_3d.py src/visualization/interaction_visualizer.py src/visualization/pose_manager.py; do
    echo "--- Qui importe $f ailleurs dans le projet ---"
    BASENAME=$(basename "$f" .py)
    grep -rln "$BASENAME" $SRC_FILTER $EXCLUDES . 2>/dev/null | grep -v "^$f$"
    echo
done

echo
echo "======================================================================"
echo "FIN DU DIAGNOSTIC"
echo "======================================================================"
