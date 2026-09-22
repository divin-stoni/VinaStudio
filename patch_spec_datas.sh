#!/bin/bash
# Ajoute automatiquement 'image_theme' et 'receptor_profiles' dans le
# bloc datas=[...] du VinaStudio.spec, juste après la ligne assets/fonts.
# Fait un backup avant toute modification et vérifie le résultat.
#
# Usage : ./patch_spec_datas.sh /home/stoni/MexAB_MexR_Analyzer_BETA

set -euo pipefail

PROJECT_ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"
SPEC_FILE="$PROJECT_ROOT/src/VinaStudio.spec"

if [ ! -f "$SPEC_FILE" ]; then
    echo "ERREUR : .spec introuvable à $SPEC_FILE"
    exit 1
fi

# --- 1. Vérifier que les dossiers à ajouter existent bien ---
IMAGE_THEME_DIR="$PROJECT_ROOT/image_theme"
RECEPTOR_PROFILES_DIR="$PROJECT_ROOT/receptor_profiles"

for d in "$IMAGE_THEME_DIR" "$RECEPTOR_PROFILES_DIR"; do
    if [ ! -d "$d" ]; then
        echo "ERREUR : dossier introuvable : $d"
        exit 1
    fi
done

# --- 2. Ne rien faire si déjà présent (script idempotent) ---
if grep -q "'$IMAGE_THEME_DIR'" "$SPEC_FILE" && grep -q "'$RECEPTOR_PROFILES_DIR'" "$SPEC_FILE"; then
    echo "Déjà présent dans le .spec, aucune modification nécessaire."
    exit 0
fi

# --- 3. Backup horodaté avant toute modification ---
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${SPEC_FILE}.bak_before_datas_patch_${TIMESTAMP}"
cp "$SPEC_FILE" "$BACKUP_FILE"
echo "Backup créé : $BACKUP_FILE"

# --- 4. Insertion des deux nouvelles lignes après la ligne assets/fonts ---
ANCHOR="src/assets/fonts', 'assets/fonts'),"

if ! grep -qF "$ANCHOR" "$SPEC_FILE"; then
    echo "ERREUR : ligne d'ancrage (assets/fonts) introuvable, patch annulé."
    echo "Le .spec n'a pas été modifié (backup inutile, restauré)."
    rm -f "$BACKUP_FILE"
    exit 1
fi

python3 - "$SPEC_FILE" "$IMAGE_THEME_DIR" "$RECEPTOR_PROFILES_DIR" <<'PYEOF'
import sys

spec_path, image_theme_dir, receptor_profiles_dir = sys.argv[1:4]

with open(spec_path, "r", encoding="utf-8") as f:
    content = f.read()

anchor = "src/assets/fonts', 'assets/fonts'),"
new_lines = (
    f"\n        ('{image_theme_dir}', 'image_theme'),"
    f"\n        ('{receptor_profiles_dir}', 'receptor_profiles'),"
)

idx = content.find(anchor)
if idx == -1:
    print("ERREUR : ancre introuvable côté Python", file=sys.stderr)
    sys.exit(1)

insert_at = idx + len(anchor)
patched = content[:insert_at] + new_lines + content[insert_at:]

with open(spec_path, "w", encoding="utf-8") as f:
    f.write(patched)

print("Insertion effectuée avec succès.")
PYEOF

# --- 5. Vérification de syntaxe Python basique (le .spec est du Python) ---
if python3 -c "compile(open('$SPEC_FILE').read(), '$SPEC_FILE', 'exec')" 2>/tmp/spec_syntax_error.txt; then
    echo "OK : le .spec reste syntaxiquement valide."
else
    echo "ERREUR DE SYNTAXE détectée après modification :"
    cat /tmp/spec_syntax_error.txt
    echo "Restauration du backup..."
    cp "$BACKUP_FILE" "$SPEC_FILE"
    echo "Le .spec original a été restauré. Aucune casse."
    exit 1
fi

echo
echo "=================================================================="
echo " Extrait du bloc datas=[...] après modification :"
echo "=================================================================="
grep -A 14 "datas=\[" "$SPEC_FILE"
echo "=================================================================="
echo
echo "Si tout te semble correct, tu peux recompiler avec :"
echo "  cd $PROJECT_ROOT/src && rm -rf build dist && pyinstaller VinaStudio.spec"
