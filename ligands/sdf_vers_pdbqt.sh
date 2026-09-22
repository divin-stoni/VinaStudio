#!/usr/bin/env bash
#
# Convertit tous les fichiers .sdf individuels en .pdbqt pour docking AutoDock Vina.
# Utilise Open Babel : ajoute les hydrogènes, calcule les charges Gasteiger,
# fusionne les hydrogènes non-polaires, détecte les liaisons rotatables.
#
# Usage :
#   ./sdf_vers_pdbqt.sh <dossier_source_sdf> [dossier_sortie_pdbqt] [nb_jobs_paralleles]
#
# Exemple :
#   ./sdf_vers_pdbqt.sh antipsychotiques_individuels antipsychotiques_pdbqt 4
#
# Si dossier_sortie n'est pas donné -> <dossier_source>_pdbqt
# Si nb_jobs n'est pas donné -> 4 (adapté à ton i5-8350U, 4 coeurs logiques)

set -euo pipefail

DOSSIER_SRC="${1:?Usage: $0 <dossier_source_sdf> [dossier_sortie] [nb_jobs]}"
DOSSIER_OUT="${2:-${DOSSIER_SRC%/}_pdbqt}"
NB_JOBS="${3:-4}"

if [ ! -d "$DOSSIER_SRC" ]; then
    echo "❌ Dossier source introuvable : $DOSSIER_SRC"
    exit 1
fi

mkdir -p "$DOSSIER_OUT"

LOG_ECHECS="$DOSSIER_OUT/echecs_conversion.log"
> "$LOG_ECHECS"

N_TOTAL=$(find "$DOSSIER_SRC" -maxdepth 1 -name "*.sdf" | wc -l)
if [ "$N_TOTAL" -eq 0 ]; then
    echo "❌ Aucun fichier .sdf trouvé dans $DOSSIER_SRC"
    exit 1
fi

echo "🔄 Conversion de $N_TOTAL fichiers SDF → PDBQT"
echo "   Source : $DOSSIER_SRC"
echo "   Sortie : $DOSSIER_OUT"
echo "   Parallélisme : $NB_JOBS jobs"
echo ""

convertir_un_fichier() {
    local fichier_sdf="$1"
    local dossier_out="$2"
    local nom_base
    nom_base=$(basename "$fichier_sdf" .sdf)
    local fichier_pdbqt="$dossier_out/${nom_base}.pdbqt"

    if obabel "$fichier_sdf" -O "$fichier_pdbqt" \
        --gen3d \
        -h \
        --partialcharge gasteiger \
        -p 7.4 \
        2>"$dossier_out/.err_${nom_base}.tmp"; then
        rm -f "$dossier_out/.err_${nom_base}.tmp"
        echo "✅ $nom_base.pdbqt"
    else
        echo "❌ ÉCHEC : $nom_base"
        cat "$dossier_out/.err_${nom_base}.tmp" >> "$dossier_out/echecs_conversion.log"
        echo "---" >> "$dossier_out/echecs_conversion.log"
        rm -f "$dossier_out/.err_${nom_base}.tmp"
    fi
}
export -f convertir_un_fichier

find "$DOSSIER_SRC" -maxdepth 1 -name "*.sdf" | \
    xargs -P "$NB_JOBS" -I {} bash -c 'convertir_un_fichier "$@"' _ {} "$DOSSIER_OUT"

echo ""
N_OK=$(find "$DOSSIER_OUT" -maxdepth 1 -name "*.pdbqt" | wc -l)
N_ECHEC=$((N_TOTAL - N_OK))

echo "Terminé : $N_OK/$N_TOTAL convertis avec succès."
if [ "$N_ECHEC" -gt 0 ]; then
    echo "⚠️  $N_ECHEC échec(s) — détails dans $LOG_ECHECS"
fi
