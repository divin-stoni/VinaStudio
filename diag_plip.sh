#!/bin/bash
echo "=== 1. Recherche du dossier projet ==="
PROJ=$(find ~ -maxdepth 2 -iname "MexAB_MexR_Analyzer_BETA*" -type d 2>/dev/null | head -1)
echo "Projet détecté : $PROJ"

echo ""
echo "=== 2. La commande 'plip' est-elle sur le PATH global (hors venv) ? ==="
which plip 2>/dev/null || echo "-> 'plip' INTROUVABLE dans le PATH système"

echo ""
echo "=== 3. Le venv du projet contient-il plip ? ==="
if [ -d "$PROJ/venv" ]; then
    ls "$PROJ/venv/bin" | grep -i plip || echo "-> pas de binaire 'plip' dans venv/bin"
    "$PROJ/venv/bin/python" -c "import plip; print('module plip importable, version:', getattr(plip,'__version__','?'))" 2>&1
else
    echo "-> pas de dossier venv trouvé à $PROJ/venv"
fi

echo ""
echo "=== 4. Comment plip_runner.py appelle-t-il PLIP ? ==="
find "$PROJ" -iname "plip_runner.py" ! -iname "*.bak*" ! -iname "*.backup*" ! -iname "*.broken*" 2>/dev/null | while read f; do
    echo "--- $f ---"
    grep -n -i "plip" "$f" | grep -iE "subprocess|run\(|Popen|\[.?plip.?\]|cmd"
done

echo ""
echo "=== 5. Est-ce que tu lances l'exécutable packagé (PyInstaller) ou le venv directement ? ==="
ps aux | grep -i "VinaStudio\|MexAB_MexR_Analyzer\|run_gui" | grep -v grep

echo ""
echo "=== FIN DU DIAGNOSTIC ==="
