#!/bin/bash
PROJ=/home/stoni/MexAB_MexR_Analyzer_BETA
F="$PROJ/src/visualization/plip_runner.py"

echo "=== Contenu complet de plip_runner.py ==="
cat -n "$F"

echo ""
echo "=== Chemin exact du binaire plip dans le venv ==="
ls -la "$PROJ/venv/bin/plip"

echo ""
echo "=== Contenu de venv/bin/plip (est-ce un script shebang python ?) ==="
head -5 "$PROJ/venv/bin/plip"

echo ""
echo "=== Comment l'app est lancée en ce moment (process actif) ==="
ps aux | grep -iE "vina|mexab|run_gui|python" | grep -v grep
