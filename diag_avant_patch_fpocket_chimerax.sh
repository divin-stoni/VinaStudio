#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) Message d'erreur fpocket -- localisation exacte (avec contexte)"
echo "======================================================================"
grep -rn -B5 -A8 "fpocket introuvable\|apt install fpocket\|fpocket.*PATH" src/gui/main_window.py

echo
echo "======================================================================"
echo "2) Reste-t-il d'autres endroits ou fpocket est mentionne dans main_window.py ?"
echo "======================================================================"
grep -n "fpocket" src/gui/main_window.py

echo
echo "======================================================================"
echo "3) Contexte exact des references a 'interaction_3d' hors main_window.py"
echo "   (pour verifier si ce sont de vrais imports ou de simples mentions)"
echo "======================================================================"
echo "--- src/translations.py ---"
grep -n -B2 -A2 "interaction_3d\|chimerax\|ChimeraX" src/translations.py
echo
echo "--- src/patch_interaction3d.py (debut du fichier, but du patch) ---"
head -30 src/patch_interaction3d.py
echo
echo "--- tests/test_viewer_drag_repaint.py (imports uniquement) ---"
grep -n "^import\|^from" tests/test_viewer_drag_repaint.py

echo
echo "======================================================================"
echo "4) Blocs ChimeraX exacts (numeros de ligne) dans les deux registres"
echo "======================================================================"
echo "--- src/tools/tool_manager.py ---"
grep -n "chimerax\|ChimeraX" src/tools/tool_manager.py
echo
echo "--- src/environment/environment_manager.py ---"
grep -n "chimerax\|ChimeraX" src/environment/environment_manager.py

echo
echo "======================================================================"
echo "5) La cle 'chimerax' est-elle lue ailleurs dans le code (settings, UI) ?"
echo "   (au cas ou une page Parametres afficherait cette entree)"
echo "======================================================================"
grep -rn --include="*.py" --exclude-dir=venv --exclude-dir=.git --exclude-dir=_archive_backups --exclude-dir=_a_supprimer --exclude-dir=_patch_backups '"chimerax"' . 2>/dev/null | grep -v "tool_manager.py\|environment_manager.py\|pose_manager.py\|interaction_visualizer.py\|interaction_3d.py"

echo
echo "======================================================================"
echo "6) Ligne exacte du commentaire dans structural_validator.py"
echo "======================================================================"
grep -n -B2 -A2 "ChimeraX" src/analysis/structural_validator.py

echo
echo "======================================================================"
echo "7) Ligne exacte dans diagnose_docking_ui.py"
echo "======================================================================"
grep -n -B2 -A2 "chimerax" src/diagnose_docking_ui.py

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
