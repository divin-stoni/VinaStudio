#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/MexAB_MexR_Analyzer_BETA"

echo "############################################################"
echo "# A) Caracteres interdits sous Windows : : * ? \" < > | et backslash"
echo "############################################################"
git ls-files -z | while IFS= read -r -d '' f; do
    if [[ "$f" =~ [:\*\?\"\<\>\|\\] ]]; then
        echo "INVALIDE : $f"
    fi
done

echo
echo "############################################################"
echo "# B) Composants se terminant par un espace ou un point (invalide sous Windows)"
echo "############################################################"
git ls-files -z | while IFS= read -r -d '' f; do
    IFS='/' read -ra parts <<< "$f"
    for p in "${parts[@]}"; do
        if [[ "$p" =~ [\ \.]$ ]]; then
            echo "COMPOSANT INVALIDE ('$p') dans : $f"
        fi
    done
done

echo
echo "############################################################"
echo "# C) Noms reserves Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9), sans extension ou avec"
echo "############################################################"
git ls-files -z | while IFS= read -r -d '' f; do
    base=$(basename "$f")
    name="${base%%.*}"
    if [[ "${name^^}" =~ ^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$ ]]; then
        echo "NOM RESERVE : $f"
    fi
done

echo
echo "############################################################"
echo "# D) Collisions de casse (deux chemins distincts sous Linux, identiques sous Windows)"
echo "############################################################"
git ls-files | tr 'A-Z' 'a-z' | sort | uniq -d

echo
echo "############################################################"
echo "# E) Chemins de plus de 200 caracteres (marge sous la limite Windows de 260)"
echo "############################################################"
git ls-files | awk '{ if (length($0) > 200) print length($0), $0 }'

echo
echo "############################################################"
echo "# F) Le fichier deja identifie comme fautif (verification directe)"
echo "############################################################"
git ls-files | grep -F "es en attendant" || echo "(non trouve par ce filtre -- verifier ci-dessus)"
