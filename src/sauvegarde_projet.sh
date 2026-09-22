#!/usr/bin/env bash
# Usage : ./sauvegarde_projet.sh                  (sans docking/results)
#         ./sauvegarde_projet.sh --avec-resultats (avec docking/results)

PROJET="MexAB_MexR_Analyzer_BETA"
DEST="$HOME/${PROJET}_SAUVEGARDES"
GARDER=10
STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="$DEST/${PROJET}_$STAMP.tar.gz"

if [ ! -d "$HOME/$PROJET" ]; then
  echo "ERREUR : dossier $HOME/$PROJET introuvable."
  exit 1
fi
mkdir -p "$DEST" || exit 1

EXCLUDES=(
  --exclude='venv'
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='*.backup*'
  --exclude='*.bak*'
  --exclude='*.broken_backup*'
  --exclude='_patch_backups'
  --exclude='pkgbuild'
  --exclude='dist'
  --exclude='build'
  --exclude='diag_*.log'
)
if [ "$1" != "--avec-resultats" ]; then
  EXCLUDES+=(--exclude="$PROJET/docking/results")
  echo "(docking/results exclu ; utilise --avec-resultats pour l'inclure)"
fi

# Le projet + les réglages d'apparence (couleurs, transparences...)
CIBLES=("$PROJET")
if [ -d "$HOME/.config/VINA Studio" ]; then
  CIBLES+=(".config/VINA Studio")
fi

echo "Création de l'archive..."
tar -czf "$ARCHIVE" "${EXCLUDES[@]}" -C "$HOME" "${CIBLES[@]}"
if [ $? -ne 0 ]; then
  echo "ERREUR pendant la création de l'archive."
  rm -f "$ARCHIVE"
  exit 1
fi

echo "Vérification de l'archive..."
if ! tar -tzf "$ARCHIVE" > /dev/null 2>&1; then
  echo "ERREUR : archive illisible, supprimée."
  rm -f "$ARCHIVE"
  exit 1
fi

( cd "$DEST" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256" )

# Rotation : on ne garde que les $GARDER dernières archives
ls -1t "$DEST"/${PROJET}_*.tar.gz 2>/dev/null | tail -n +$((GARDER + 1)) | while read -r vieux; do
  rm -f -- "$vieux" "$vieux.sha256"
  echo "Ancienne sauvegarde supprimée : $(basename "$vieux")"
done

echo
echo "=============== SAUVEGARDE TERMINEE ==============="
echo "Archive   : $ARCHIVE"
echo "Taille    : $(du -h "$ARCHIVE" | cut -f1)"
echo "Fichiers  : $(tar -tzf "$ARCHIVE" | wc -l)"
echo "Sauvegardes conservées : $(ls -1 "$DEST"/${PROJET}_*.tar.gz | wc -l) (max $GARDER)"
echo
echo "Pour restaurer dans un dossier de test (sans rien écraser) :"
echo "  mkdir -p ~/restauration_test && tar -xzf \"$ARCHIVE\" -C ~/restauration_test"
