#!/usr/bin/env bash
# Localise dans main_window.py :
#   1) le bloc qui ajoute l'onglet Crédits (CreditsPage) à la barre d'onglets
#   2) le bloc qui construit la boîte / page "À propos"
# Affiche chaque zone trouvée avec 15 lignes de contexte avant/après et
# les numéros de ligne, pour pouvoir coller le bon extrait ensuite.

set -euo pipefail

FILE="$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py"

if [ ! -f "$FILE" ]; then
    echo "Fichier introuvable : $FILE"
    echo "Donne le bon chemin en argument : $0 /chemin/vers/main_window.py"
    if [ "${1:-}" != "" ]; then
        FILE="$1"
    else
        exit 1
    fi
fi

echo "=== Fichier : $FILE ($(wc -l < "$FILE") lignes) ==="
echo

echo "############################################################"
echo "# 1) Onglet CREDITS (CreditsPage / addTab / 'Crédits')"
echo "############################################################"
grep -n -i "creditspage\|credits_page\|['\"]Crédits['\"]\|addTab" "$FILE" | grep -i "credit" || echo "(rien trouvé avec 'credit')"
echo
echo "--- Contexte autour de chaque occurrence 'CreditsPage' ---"
grep -n -i "creditspage" "$FILE" | cut -d: -f1 | while read -r ln; do
    start=$((ln - 15)); [ "$start" -lt 1 ] && start=1
    end=$((ln + 15))
    echo ">>> autour de la ligne $ln :"
    sed -n "${start},${end}p" "$FILE" | nl -ba -v "$start"
    echo "------------------------------------------------------------"
done

echo
echo "############################################################"
echo "# 2) Boîte / page 'À propos'"
echo "############################################################"
grep -n -i "à propos\|a propos\|about" "$FILE" || echo "(rien trouvé avec 'à propos' / 'about')"
echo
echo "--- Contexte autour de chaque occurrence 'about' (insensible casse) ---"
grep -n -i "about" "$FILE" | cut -d: -f1 | while read -r ln; do
    start=$((ln - 15)); [ "$start" -lt 1 ] && start=1
    end=$((ln + 15))
    echo ">>> autour de la ligne $ln :"
    sed -n "${start},${end}p" "$FILE" | nl -ba -v "$start"
    echo "------------------------------------------------------------"
done
