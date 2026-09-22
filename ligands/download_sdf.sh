#!/bin/bash
# Usage: ./download_sdf.sh <fichier_noms.txt> <sortie.sdf>
# Télécharge un SDF par molécule depuis PubChem PUG REST et concatène le tout.
# Log les noms introuvables dans <sortie>_manquants.txt pour vérification manuelle.

set -euo pipefail

INPUT="$1"
OUTPUT="$2"
MISSING="${OUTPUT%.sdf}_manquants.txt"

> "$OUTPUT"
> "$MISSING"

TOTAL=$(wc -l < "$INPUT")
COUNT=0

while IFS= read -r name; do
    [ -z "$name" ] && continue
    COUNT=$((COUNT+1))
    # encode les espaces pour l'URL
    encoded=$(echo "$name" | sed 's/ /%20/g')
    echo "[$COUNT/$TOTAL] $name"

    response=$(curl -s -w "\n%{http_code}" "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encoded}/SDF")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ] && [ -n "$body" ]; then
        echo "$body" >> "$OUTPUT"
    else
        echo "$name" >> "$MISSING"
        echo "  -> ÉCHEC (code $http_code)"
    fi

    sleep 0.3   # respecter le rate limit PubChem (5 req/s max recommandé)
done < "$INPUT"

echo ""
echo "Terminé : $OUTPUT"
echo "Molécules manquantes (à vérifier manuellement) : $MISSING"
[ -s "$MISSING" ] && cat "$MISSING"
