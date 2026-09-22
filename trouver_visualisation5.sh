#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"
BRIDGE="${2:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/visualization_bridge.py}"

dump() {
    local start="$1" end="$2" label="$3"
    echo "############################################################"
    echo "# $label  (lignes $start-$end)"
    echo "############################################################"
    sed -n "${start},${end}p" "$FILE" | nl -ba -v "$start"
    echo
}

dump 9440 9500 "Boucle sur known_target_labels (autour de 9464-9473)"
dump 9890 9990 "Chargement du PDB courant et choix du target (autour de 9921-9972)"

echo "############################################################"
echo "# visualization_bridge.py (fichier complet, $(wc -l < "$BRIDGE") lignes)"
echo "############################################################"
nl -ba "$BRIDGE"
