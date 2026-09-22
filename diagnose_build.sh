#!/bin/bash
# Diagnostic : compare les dossiers du projet avec ce qui est déclaré
# dans datas=[...] du fichier VinaStudio.spec
#
# Usage : ./diagnose_build.sh /home/stoni/MexAB_MexR_Analyzer_BETA

set -uo pipefail

PROJECT_ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"
SPEC_FILE="$PROJECT_ROOT/src/VinaStudio.spec"

if [ ! -f "$SPEC_FILE" ]; then
    echo "ERREUR : .spec introuvable à $SPEC_FILE"
    exit 1
fi

echo "=================================================================="
echo " Racine du projet : $PROJECT_ROOT"
echo " Fichier .spec    : $SPEC_FILE"
echo "=================================================================="
echo

# --- 1. Dossiers/fichiers à ignorer d'office (archives, builds, meta) ---
EXCLUDE_REGEX='(^\.|^dist$|^build$|^__pycache__$|^\.git$|^\.venv$|^venv$|^env$|^node_modules$|_archive_backups|\.bak|backup|old|copie|copy)'

# --- 2. Extraire les chemins sources déjà déclarés dans datas=[...] ---
# On récupère tout ce qui est entre "datas=[" et la ligne "]" qui suit,
# puis on isole le premier élément de chaque tuple ('/chemin/source', 'dest')
DECLARED_PATHS=$(awk '/datas=\[/,/^\s*\]/' "$SPEC_FILE" \
    | grep -oP "'\K[^']*(?='\s*,)" \
    | grep "^/")

echo "--- Chemins DÉJÀ déclarés dans datas=[...] du .spec ---"
if [ -z "$DECLARED_PATHS" ]; then
    echo "  (aucun trouvé — vérifie le format du .spec)"
else
    echo "$DECLARED_PATHS" | sed 's/^/  OK  /'
fi
echo

# --- 3. Lister les dossiers candidats à la racine et dans src/ ---
echo "--- Dossiers de premier niveau détectés (hors exclusions) ---"
echo

check_dir() {
    local dir="$1"
    local base
    base=$(basename "$dir")

    # Ignorer les dossiers d'exclusion
    if [[ "$base" =~ $EXCLUDE_REGEX ]]; then
        return
    fi

    # Un dossier est "déclaré" si son chemin absolu apparaît dans DECLARED_PATHS
    if echo "$DECLARED_PATHS" | grep -qF "$dir"; then
        echo "  [EMBARQUÉ]     $dir"
    else
        # Vérifie s'il contient au moins un fichier (dossier non vide)
        if [ -n "$(find "$dir" -maxdepth 2 -type f 2>/dev/null | head -n 1)" ]; then
            echo "  [MANQUANT !!]  $dir"
        else
            echo "  [vide/ignoré]  $dir"
        fi
    fi
}

for d in "$PROJECT_ROOT"/*/ "$PROJECT_ROOT"/src/*/; do
    [ -d "$d" ] || continue
    check_dir "${d%/}"
done | sort -u

echo
echo "=================================================================="
echo " Résumé : les lignes [MANQUANT !!] sont des dossiers non vides"
echo " qui NE SONT PAS dans datas=[...] du .spec -> à ajouter avant"
echo " la prochaine compilation."
echo "=================================================================="
