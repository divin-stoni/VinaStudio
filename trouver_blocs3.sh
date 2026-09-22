#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"

if [ ! -f "$FILE" ]; then
    echo "Fichier introuvable : $FILE"
    exit 1
fi

dump() {
    local start="$1" end="$2" label="$3"
    echo "############################################################"
    echo "# $label  (lignes $start-$end)"
    echo "############################################################"
    sed -n "${start},${end}p" "$FILE" | nl -ba -v "$start"
    echo
}

dump 3520 3600 "Classe PrimaryNavigation"
dump 10195 10235 "Contexte de tab_labels (ligne 10211)"
dump 10495 10545 "Boucle de creation des boutons d'onglets (ligne 10520)"
dump 10465 10495 "show_about_dialog complet"
