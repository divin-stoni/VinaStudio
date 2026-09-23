#!/bin/bash
# recompiler_vinastudio.sh
# Verifie que le patch credit_du_logiciel est bien applique au script de
# build, nettoie les artefacts de compilation precedents, puis relance
# la compilation complete.
#
# A lancer depuis la racine de MexAB_MexR_Analyzer_BETA :
#   bash recompiler_vinastudio.sh

set -uo pipefail

echo "========================================================"
echo " 1. Verification : le patch credit_du_logiciel est-il"
echo "    deja applique a build_and_package_v2.sh ?"
echo "========================================================"
if grep -q "CREDITS_SRC" build_and_package_v2.sh 2>/dev/null; then
    echo "OK : le patch semble deja applique (CREDITS_SRC trouve)."
    PATCH_DEJA_APPLIQUE=1
else
    echo "!! Le patch NE semble PAS applique a build_and_package_v2.sh."
    echo "   Application maintenant via patch_build_credits_data.py..."
    PATCH_DEJA_APPLIQUE=0
    if [ -f patch_build_credits_data.py ]; then
        python3 patch_build_credits_data.py
        echo
        echo "-- Re-verification apres patch --"
        if grep -q "CREDITS_SRC" build_and_package_v2.sh 2>/dev/null; then
            echo "OK : patch applique avec succes."
        else
            echo "!! ECHEC : CREDITS_SRC toujours absent apres patch."
            echo "   Verifiez manuellement patch_build_credits_data.py"
            echo "   et build_and_package_v2.sh avant de continuer."
            exit 1
        fi
    else
        echo "!! patch_build_credits_data.py introuvable. Arret."
        exit 1
    fi
fi
echo

echo "========================================================"
echo " 2. Nettoyage des artefacts de compilation precedents"
echo "    (src/build, src/dist) pour un rebuild propre"
echo "========================================================"
if [ -d src/build ]; then
    echo "Suppression de src/build/ ..."
    rm -rf src/build
fi
if [ -d src/dist ]; then
    echo "Suppression de src/dist/ ..."
    rm -rf src/dist
fi
echo "OK."
echo

echo "========================================================"
echo " 3. Lancement de la compilation complete"
echo "    via build_and_package_v2.sh"
echo "========================================================"
chmod +x build_and_package_v2.sh
bash build_and_package_v2.sh
BUILD_STATUS=$?
echo

echo "========================================================"
echo " 4. Verification post-build : credit_du_logiciel est-il"
echo "    bien present a cote de l'executable ?"
echo "========================================================"
if [ -d "src/dist/VinaStudio/credit_du_logiciel" ]; then
    echo "OK : src/dist/VinaStudio/credit_du_logiciel present."
    du -sh src/dist/VinaStudio/credit_du_logiciel
else
    echo "!! ATTENTION : src/dist/VinaStudio/credit_du_logiciel est ABSENT."
    echo "   L'onglet Credits plantera a l'execution."
fi
echo

echo "========================================================"
echo " 5. Contenu final de src/dist/VinaStudio/ (verification rapide)"
echo "========================================================"
ls -la src/dist/VinaStudio/ 2>/dev/null | head -n 30
echo

if [ "$BUILD_STATUS" -eq 0 ]; then
    echo "========================================================"
    echo " TERMINE : compilation reussie."
    echo "========================================================"
else
    echo "========================================================"
    echo " TERMINE avec ERREUR (code $BUILD_STATUS)."
    echo " Copiez-collez toute la sortie ci-dessus pour qu'on"
    echo " diagnostique l'echec de build."
    echo "========================================================"
fi
