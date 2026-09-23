#!/usr/bin/env bash
set -euo pipefail

TS=$(date +%Y%m%d_%H%M%S)

for f in requirements.txt requirements-windows.txt; do
    if [[ ! -f "$f" ]]; then
        echo "!! $f introuvable, ignore."
        continue
    fi
    if grep -qi "^requests" "$f"; then
        echo "$f contient deja 'requests', rien a faire."
        continue
    fi
    cp "$f" "${f}.bak_${TS}"
    echo "requests>=2.31" >> "$f"
    echo "Ajoute a $f (backup : ${f}.bak_${TS})"
done

echo
echo "--- Contenu final de requirements.txt (fin de fichier) ---"
tail -5 requirements.txt
echo
echo "--- Contenu final de requirements-windows.txt (fin de fichier) ---"
tail -5 requirements-windows.txt
