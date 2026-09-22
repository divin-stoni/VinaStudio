#!/bin/bash
PROJ="/home/stoni/MexAB_MexR_Analyzer_BETA"

echo "=== 1. Contenu de dist/VinaStudio (racine, pas recursif) ==="
ls -la "$PROJ/src/dist/VinaStudio/"

echo ""
echo "=== 2. L'executable existe-t-il precisement ? ==="
if [ -f "$PROJ/src/dist/VinaStudio/VinaStudio" ]; then
    echo "-> PRESENT"
    file "$PROJ/src/dist/VinaStudio/VinaStudio"
    ls -la "$PROJ/src/dist/VinaStudio/VinaStudio"
else
    echo "-> ABSENT : le build PyInstaller n'a pas produit l'executable"
fi

echo ""
echo "=== 3. Test de lancement direct depuis dist/ (avant tout packaging) ==="
if [ -f "$PROJ/src/dist/VinaStudio/VinaStudio" ]; then
    "$PROJ/src/dist/VinaStudio/VinaStudio" &
    PID=$!
    sleep 3
    if kill -0 $PID 2>/dev/null; then
        echo "-> L'app tourne (PID $PID), je la ferme pour le test."
        kill $PID
    else
        wait $PID
        echo "-> L'app s'est fermee immediatement (code de sortie : $?)"
    fi
fi
