#!/bin/bash
# diag_ressources_reelles.sh
# Cherche, dans le code source, les references reelles a des dossiers
# de ressources (credit_du_logiciel, ligands, docs, scientific_analysis)
# et detecte le mecanisme utilise pour resoudre les chemins sous PyInstaller
# (sys._MEIPASS / resource_path), ainsi que d'eventuels imports dynamiques
# qui necessiteraient un ajout a hiddenimports.
#
# A lancer depuis la racine de MexAB_MexR_Analyzer_BETA :
#   bash diag_ressources_reelles.sh > diag_ressources_output.txt 2>&1
#   cat diag_ressources_output.txt

set -uo pipefail

SRC_DIRS="src patch16_phytomolecules_tab.py patch17_phytomolecules_finish.py patch18_phytomolecules_label_fix.py patch19_switch_primary_fix.py patch20_phyto_search_fixes.py patch21_phyto_fixes.py patch22_phyto_ui_image_sdf.py patch_credits_about.py patch_credits_stop_video.py patch_build_credits_data.py patch_campagne.py"

echo "========================================================"
echo " 1. Comment les chemins de ressources sont resolus"
echo "    (recherche de sys._MEIPASS / resource_path / getattr)"
echo "========================================================"
grep -rn "_MEIPASS\|resource_path\|resource_dir\|get_resource" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 2. Références au dossier 'credit_du_logiciel' dans le code"
echo "========================================================"
grep -rn "credit_du_logiciel" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 3. Références au dossier 'ligands' dans le code"
echo "     (hors scripts de conversion ponctuels)"
echo "========================================================"
grep -rn "['\"]ligands" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 4. Références à 'phytomolecules' (sdf/individuels) dans le code"
echo "========================================================"
grep -rn "phytomolecule" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 5. Références au dossier 'docs' (technical_notes, pdf) dans le code"
echo "========================================================"
grep -rn "['\"]docs\|technical_notes\|chemrxiv" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 6. Références au dossier 'scientific_analysis' dans le code"
echo "========================================================"
grep -rn "scientific_analysis" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 7. Imports dynamiques potentiels (importlib, __import__)"
echo "     -> nécessiteraient un ajout à hiddenimports"
echo "========================================================"
grep -rn "importlib\|__import__(" $SRC_DIRS 2>/dev/null
echo

echo "========================================================"
echo " 8. Contenu de campaign_table.py / patch_campagne.py"
echo "     (référence-t-il des fichiers externes au dossier docking/) ?"
echo "========================================================"
grep -n "open(\|Path(\|os.path.join\|\.read_csv\|\.read_json" src/campaign_table.py patch_campagne.py 2>/dev/null
echo

echo "========================================================"
echo " 9. Taille réelle des dossiers de ressources en question"
echo "========================================================"
for d in credit_du_logiciel ligands docs scientific_analysis image_theme receptor_profiles; do
    if [ -d "$d" ]; then
        taille=$(du -sh "$d" 2>/dev/null | cut -f1)
        echo "$d : $taille"
    fi
done
echo

echo "========================================================"
echo " 10. Contenu de gui/credits_page.py : quels fichiers exacts"
echo "     sont ouverts / affichés (photos, captions.json, vidéos) ?"
echo "========================================================"
if [ -f src/gui/credits_page.py ]; then
    grep -n "open(\|Path(\|os.path.join\|QUrl\|\.mp4\|\.jpg\|captions" src/gui/credits_page.py
fi
echo

echo "========================================================"
echo " TERMINÉ."
echo "========================================================"
