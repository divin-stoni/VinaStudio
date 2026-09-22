#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"

dump() {
    local start="$1" end="$2" label="$3"
    echo "############################################################"
    echo "# $label  (lignes $start-$end)"
    echo "############################################################"
    sed -n "${start},${end}p" "$FILE" | nl -ba -v "$start"
    echo
}

dump 5830 5960 "Resolution du/des recepteur(s) courant(s) a partir du combo (autour de 5858-5949)"
dump 6020 6060 "Usage de current_single_target pour choisir le profil (6039-6050)"
dump 6660 6700 "Construction de pair_targets pour une nouvelle paire importee (6683)"
dump 6830 6930 "current_single_target dans le viewer 3D (6854-6916)"
dump 7190 7230 "pair_members re-utilise plus loin (7214)"
dump 9354 9420 "Debut de la classe VisualizationPage"
