#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"

echo "############################################################"
echo "# A) Mots-cles pertinents entre les lignes 9354 et 10713"
echo "############################################################"
sed -n '9354,10713p' "$FILE" | nl -ba -v 9354 | grep -i "target\|receptor\|mexr\|mexb\|pdb\|repressor\|pump\|derepresseur"
