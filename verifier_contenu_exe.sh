#!/usr/bin/env bash
set -uo pipefail

EXE_PATH="${1:-}"

if [[ -z "$EXE_PATH" ]]; then
    echo "Usage: bash verifier_contenu_exe.sh /chemin/vers/VinaStudio.exe"
    echo
    echo "Etapes avant de lancer ce script :"
    echo "  1) Telecharge l'artefact 'VinaStudio-Windows' depuis la page GitHub Actions"
    echo "  2) unzip VinaStudio-Windows.zip -d vinastudio_extrait"
    echo "  3) bash verifier_contenu_exe.sh vinastudio_extrait/VinaStudio.exe"
    exit 1
fi

if [[ ! -f "$EXE_PATH" ]]; then
    echo "!! Fichier introuvable : $EXE_PATH"
    exit 1
fi

if [[ ! -x "venv/bin/pyi-archive_viewer" ]]; then
    echo "!! venv/bin/pyi-archive_viewer introuvable. Lance ce script depuis ~/MexAB_MexR_Analyzer_BETA"
    echo "   ou active ton venv avant (source venv/bin/activate)."
    exit 1
fi

echo "======================================================================"
echo "1) Listing complet de l'archive PyInstaller (recursif)"
echo "======================================================================"
venv/bin/pyi-archive_viewer -l -r "$EXE_PATH" > /tmp/toc_listing.txt 2>&1
LINES=$(wc -l < /tmp/toc_listing.txt)
echo "Listing genere : $LINES lignes (voir /tmp/toc_listing.txt pour le detail complet)"

echo
echo "======================================================================"
echo "2) Presence des plugins de formats openbabel (le risque signale)"
echo "======================================================================"
echo "--- Recherche 'inchi' ---"
grep -i "inchi" /tmp/toc_listing.txt || echo "AUCUNE occurrence -- suspect"
echo "--- Recherche 'pdbqtformat' ---"
grep -i "pdbqtformat" /tmp/toc_listing.txt || echo "AUCUNE occurrence -- suspect"
echo "--- Recherche generale 'openbabel' (nombre d'occurrences) ---"
grep -ci "openbabel" /tmp/toc_listing.txt

echo
echo "======================================================================"
echo "3) Presence des donnees openbabel (share/openbabel)"
echo "======================================================================"
grep -i "share.openbabel\|share/openbabel" /tmp/toc_listing.txt | head -10
COUNT_SHARE=$(grep -ci "share.openbabel\|share/openbabel" /tmp/toc_listing.txt)
echo "Nombre d'entrees share/openbabel : $COUNT_SHARE"

echo
echo "======================================================================"
echo "4) Presence des autres donnees critiques du .spec"
echo "======================================================================"
for pattern in "reference_data" "i18n" "docking.receptor" "assets.fonts" "image_theme" "receptor_profiles" "vina.exe" "vc_redist"; do
    COUNT=$(grep -ci "$pattern" /tmp/toc_listing.txt)
    printf "%-20s -> %s occurrence(s)\n" "$pattern" "$COUNT"
done

echo
echo "======================================================================"
echo "RESUME"
echo "======================================================================"
echo "Si les sections 2 et 3 renvoient des occurrences > 0, les plugins et"
echo "donnees openbabel sont bien embarques -- le risque signale est ecarte"
echo "au niveau du packaging. Cela ne garantit PAS que le code Python les"
echo "trouve au bon endroit a l'execution (chemin _fix_babel_datadir...),"
echo "seul un lancement reel sur Windows le confirmera."
echo "Le listing complet est dans /tmp/toc_listing.txt si besoin de creuser."
