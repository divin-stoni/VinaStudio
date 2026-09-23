#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) Recensement : tous les patchs/diagnostics a la racine et dans src/"
echo "======================================================================"
PATTERNS="patch[0-9]*_*.py patch_*.py diag_*.sh diag_*.py diagnose_*.py diagnostic_*.py trouver_*.sh verif_*.sh audit_*.sh audit_*.py fix_*.sh fix_*.py"

FOUND_FILES=""
for pat in $PATTERNS; do
    for f in $pat src/$pat; do
        if [[ -f "$f" ]]; then
            FOUND_FILES="$FOUND_FILES $f"
        fi
    done
done

# Dedoublonnage
FOUND_FILES=$(echo "$FOUND_FILES" | tr ' ' '\n' | sort -u | grep -v '^$')
COUNT=$(echo "$FOUND_FILES" | wc -l)
echo "$COUNT fichiers trouves."
echo "$FOUND_FILES"

echo
echo "======================================================================"
echo "2) Verification : est-ce que l'un de ces fichiers est importe ailleurs"
echo "   dans le code de l'application (src/, docking/, run_gui.py) ?"
echo "======================================================================"
ANY_REFERENCED=0
for f in $FOUND_FILES; do
    MODNAME=$(basename "$f" .py)
    MODNAME=$(basename "$MODNAME" .sh)
    HITS=$(grep -rln "\b$MODNAME\b" src/ docking/ run_gui.py docking_parser.py 2>/dev/null | grep -v "^$f$")
    if [[ -n "$HITS" ]]; then
        echo "!! $f est reference dans : $HITS"
        ANY_REFERENCED=1
    fi
done
if [[ "$ANY_REFERENCED" -eq 0 ]]; then
    echo "Aucun de ces fichiers n'est importe/reference par le code de l'application. Sans risque a deplacer."
else
    echo "!! ATTENTION : au moins un fichier semble reference ailleurs -- NE PAS deplacer avant verification manuelle."
fi

echo
echo "======================================================================"
echo "3) Archivage (git mv, pas rm -- tout reste recuperable via git)"
echo "======================================================================"
if [[ "$ANY_REFERENCED" -eq 1 ]]; then
    echo "Archivage annule par securite (voir section 2). Corrige d'abord le probleme signale."
    exit 1
fi

ARCHIVE_DIR="dev/archive_patchs_diagnostics"
mkdir -p "$ARCHIVE_DIR"

for f in $FOUND_FILES; do
    dest="$ARCHIVE_DIR/$(basename "$f")"
    if [[ -f "$dest" ]]; then
        dest="$ARCHIVE_DIR/$(dirname "$f" | tr '/' '_')_$(basename "$f")"
    fi
    git mv "$f" "$dest" 2>/dev/null || mv "$f" "$dest"
    echo "Archive : $f -> $dest"
done

echo
echo "======================================================================"
echo "4) Etat apres archivage"
echo "======================================================================"
git status --porcelain | head -40

echo
echo "======================================================================"
echo "RIEN N'A ETE COMMIT. Verifie la liste ci-dessus, puis :"
echo "  git add -A"
echo "  git commit -m \"Nettoyage : archive les patchs/diagnostics dans dev/archive_patchs_diagnostics/\""
echo "  git push origin main"
echo "======================================================================"
