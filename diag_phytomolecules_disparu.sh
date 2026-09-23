#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) phyto_page.py a-t-il change recemment (git log) ?"
echo "======================================================================"
git log --oneline -5 -- src/gui/phyto_page.py

echo
echo "======================================================================"
echo "2) main_window.py a-t-il change quelque chose lie a phyto/Phytomolecules ?"
echo "   (diff entre le dernier commit avant nos patchs et maintenant)"
echo "======================================================================"
git log --oneline -10 -- src/gui/main_window.py
echo
echo "--- Diff complet des changements 'phyto' dans main_window.py depuis avant nos patchs ---"
git diff ad9c83d HEAD -- src/gui/main_window.py | grep -i "phyto" -A3 -B3

echo
echo "======================================================================"
echo "3) Comment l'onglet Phytomolecules est-il ajoute dans main_window.py ?"
echo "   (recherche de PhytoPage, phyto_page, Phytomolecules)"
echo "======================================================================"
grep -n -B3 -A8 "PhytoPage\|phyto_page\|Phytomolécules" src/gui/main_window.py | head -80

echo
echo "======================================================================"
echo "4) Y a-t-il un try/except autour de la creation des onglets qui pourrait"
echo "   masquer une erreur silencieusement ?"
echo "======================================================================"
grep -n -B10 "PhytoPage(" src/gui/main_window.py | grep -n "try:\|except"

echo
echo "======================================================================"
echo "5) requests est-il installe dans le venv local (celui utilise pour le .deb) ?"
echo "======================================================================"
python3 -c "import requests; print('requests OK, version', requests.__version__)" 2>&1

echo
echo "======================================================================"
echo "6) Le fichier phyto_page.py est-il syntaxiquement valide actuellement ?"
echo "======================================================================"
python3 -c "import ast; ast.parse(open('src/gui/phyto_page.py', encoding='utf-8').read()); print('OK: syntaxe valide')" 2>&1

echo
echo "======================================================================"
echo "7) Le .deb installe est-il a jour avec le code source actuel ?"
echo "   (date du .deb vs date du dernier commit)"
echo "======================================================================"
ls -la vinastudio_*.deb 2>&1
git log -1 --format="Dernier commit : %h %ci"

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
