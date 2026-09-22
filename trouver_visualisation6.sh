#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"

echo "############################################################"
echo "# A) Toutes les lignes entre 9354 et 10713 touchant hit_results / current_hits / molecule_combo"
echo "############################################################"
sed -n '9354,10713p' "$FILE" | nl -ba -v 9354 | grep -i "hit_results\|current_hits\|molecule_combo\|molecule_list\|residue.*combo\|residus"

echo
echo "############################################################"
echo "# B) Toutes les definitions de methode (def ...) dans VisualizationPage"
echo "############################################################"
sed -n '9354,10713p' "$FILE" | nl -ba -v 9354 | grep "    def "
