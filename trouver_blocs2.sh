#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"

if [ ! -f "$FILE" ]; then
    echo "Fichier introuvable : $FILE"
    exit 1
fi

echo "=== Fichier : $FILE ($(wc -l < "$FILE") lignes) ==="
echo

echo "############################################################"
echo "# A) Barre d'onglets primaire (primary_navigation) : creation"
echo "############################################################"
grep -n "primary_navigation\|PrimaryNavigation" "$FILE" || echo "(rien)"

echo
echo "############################################################"
echo "# B) Le mot 'Crédits' comme texte de bouton/onglet"
echo "############################################################"
grep -n "['\"]Crédits['\"]\|['\"]Credits['\"]" "$FILE" || echo "(rien)"

echo
echo "############################################################"
echo "# C) Contexte large (60 lignes avant/apres) autour de 'index == 4'"
echo "############################################################"
grep -n "index == 4" "$FILE" | cut -d: -f1 | while read -r ln; do
    start=$((ln - 60)); [ "$start" -lt 1 ] && start=1
    end=$((ln + 20))
    echo ">>> autour de la ligne $ln :"
    sed -n "${start},${end}p" "$FILE" | nl -ba -v "$start"
    echo "------------------------------------------------------------"
done

echo
echo "############################################################"
echo "# D) setCurrentIndex / setCurrentWidget sur workspace"
echo "############################################################"
grep -n "workspace.setCurrentIndex\|workspace.setCurrentWidget\|self\.workspace\.setCurrent" "$FILE" || echo "(rien)"
