#!/usr/bin/env bash
# Audit complet du pipeline de build Windows : croise le workflow GitHub Actions,
# le(s) fichier(s) .spec PyInstaller, et l'arborescence réelle du dépôt.
# A executer depuis la racine du repo (~/MexAB_MexR_Analyzer_BETA).

set -uo pipefail

WORKFLOW=".github/workflows/build-windows.yml"

echo "======================================================================"
echo "1) CONTENU COMPLET DU WORKFLOW WINDOWS"
echo "======================================================================"
if [[ -f "$WORKFLOW" ]]; then
    cat -n "$WORKFLOW"
else
    echo "!! Fichier introuvable: $WORKFLOW"
fi

echo
echo "======================================================================"
echo "2) TOUS LES FICHIERS .spec DU DEPOT"
echo "======================================================================"
SPEC_FILES=$(find . -maxdepth 3 -iname "*.spec" -not -path "*/build/*" -not -path "*/dist/*")
if [[ -z "$SPEC_FILES" ]]; then
    echo "Aucun fichier .spec trouve."
else
    for f in $SPEC_FILES; do
        echo "--- $f ---"
        cat -n "$f"
        echo
    done
fi

echo
echo "======================================================================"
echo "3) EXTRACTION DES --add-data / --add-binary (workflow Windows)"
echo "======================================================================"
if [[ -f "$WORKFLOW" ]]; then
    grep -oE -- '--add-(data|binary)[= ]"[^"]+"' "$WORKFLOW" | sed 's/--add-[a-z]*[= ]//' > /tmp/wf_add_paths.txt
    grep -oE -- "--add-(data|binary)[= ]'[^']+'" "$WORKFLOW" | sed "s/--add-[a-z]*[= ]//" >> /tmp/wf_add_paths.txt
    if [[ ! -s /tmp/wf_add_paths.txt ]]; then
        echo "Aucune entree --add-data/--add-binary trouvee (verifier le format utilise dans le YAML)."
    else
        cat /tmp/wf_add_paths.txt
    fi
else
    : > /tmp/wf_add_paths.txt
fi

echo
echo "======================================================================"
echo "4) VERIFICATION D'EXISTENCE DE CHAQUE CHEMIN SOURCE (cote Windows)"
echo "======================================================================"
echo "Note: Windows utilise ';' comme separateur src;dest, mais on split sur les deux"
echo "      au cas ou pour attraper une entree mal formee."
echo
if [[ -s /tmp/wf_add_paths.txt ]]; then
    while IFS= read -r entry; do
        [[ -z "$entry" ]] && continue
        src="${entry%%[;:]*}"
        printf "%-55s -> " "$src"
        if [[ -e "$src" ]]; then
            echo "OK"
        else
            echo "MANQUANT"
        fi
    done < /tmp/wf_add_paths.txt
else
    echo "(rien a verifier)"
fi

echo
echo "======================================================================"
echo "5) MEME EXTRACTION POUR LE(S) .spec (reference de verite probable)"
echo "======================================================================"
for f in $SPEC_FILES; do
    echo "--- Chemins declares dans $f ---"
    grep -oE "\('[^']+',\s*'[^']+'\)" "$f" | while read -r pair; do
        src=$(echo "$pair" | sed -E "s/\('([^']+)'.*/\1/")
        printf "%-55s -> " "$src"
        if [[ -e "$src" ]]; then
            echo "OK"
        else
            echo "MANQUANT (relatif au repertoire d'execution)"
        fi
    done
    echo
done

echo
echo "======================================================================"
echo "6) ARBORESCENCE REELLE (src/ + racine, profondeur 3) POUR COMPARAISON VISUELLE"
echo "======================================================================"
find . -maxdepth 3 -not -path "*/.git*" -not -path "*/build/*" -not -path "*/dist/*" -not -path "*/__pycache__*" | sort

echo
echo "======================================================================"
echo "7) HIDDEN IMPORTS / DATAS PYINSTALLER DANS LE WORKFLOW (grep large)"
echo "======================================================================"
if [[ -f "$WORKFLOW" ]]; then
    grep -nE "hidden-import|hiddenimports|collect-data|collect-submodules|pyinstaller" "$WORKFLOW" -i
fi

echo
echo "======================================================================"
echo "8) DIFF RAPIDE: chemins .spec (Linux, verite) vs chemins workflow (Windows)"
echo "======================================================================"
for f in $SPEC_FILES; do
    grep -oE "\('[^']+',\s*'[^']+'\)" "$f" | sed -E "s/\('([^']+)'.*/\1/" | sort -u > /tmp/spec_paths.txt
done
if [[ -s /tmp/wf_add_paths.txt ]]; then
    sed -E 's/[;:].*$//' /tmp/wf_add_paths.txt | sort -u > /tmp/wf_paths_only.txt
else
    : > /tmp/wf_paths_only.txt
fi
echo "Chemins presents dans .spec mais ABSENTS du workflow Windows:"
comm -23 /tmp/spec_paths.txt /tmp/wf_paths_only.txt 2>/dev/null || echo "(comparaison impossible, verifier extraction ci-dessus)"
echo
echo "Chemins presents dans le workflow Windows mais ABSENTS du .spec:"
comm -13 /tmp/spec_paths.txt /tmp/wf_paths_only.txt 2>/dev/null || echo "(comparaison impossible, verifier extraction ci-dessus)"

echo
echo "======================================================================"
echo "FIN DE L'AUDIT"
echo "======================================================================"
