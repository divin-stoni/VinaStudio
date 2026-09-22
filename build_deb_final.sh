#!/bin/bash
# Chaîne complète : synchronise le build PyInstaller (src/dist -> dist),
# réinstalle localement, puis génère le .deb final.
# S'arrête immédiatement à la moindre erreur.

set -euo pipefail

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
SRC_BUILD="$PROJECT_ROOT/src/dist/VinaStudio"
ROOT_BUILD="$PROJECT_ROOT/dist/VinaStudio"

echo "=================================================="
echo "ETAPE 0 : vérification du build source (src/dist)"
echo "=================================================="
if [ ! -d "$SRC_BUILD" ]; then
    echo "ERREUR : $SRC_BUILD introuvable."
    echo "Relance d'abord : cd $PROJECT_ROOT/src && pyinstaller VinaStudio.spec"
    exit 1
fi

if [ ! -d "$SRC_BUILD/_internal/image_theme" ]; then
    echo "ERREUR : image_theme absent du build source ($SRC_BUILD)."
    echo "Le .spec n'a peut-être pas été patché ou le build est ancien."
    exit 1
fi

if [ ! -d "$SRC_BUILD/_internal/receptor_profiles" ]; then
    echo "ERREUR : receptor_profiles absent du build source ($SRC_BUILD)."
    exit 1
fi

echo "OK : build source trouvé avec image_theme et receptor_profiles."
echo

echo "=================================================="
echo "ETAPE 1 : synchronisation vers $ROOT_BUILD"
echo "  (c'est ici que install_vinastudio_local.sh va chercher)"
echo "=================================================="
rm -rf "$ROOT_BUILD"
mkdir -p "$PROJECT_ROOT/dist"
cp -r "$SRC_BUILD" "$ROOT_BUILD"
echo "OK : copié dans $ROOT_BUILD"
echo

echo "=================================================="
echo "ETAPE 2 : réinstallation locale (install_vinastudio_local.sh)"
echo "=================================================="
bash "$PROJECT_ROOT/dev/scripts_maintenance/install_vinastudio_local.sh"
echo

echo "=================================================="
echo "ETAPE 3 : vérification post-installation locale"
echo "=================================================="
LOCAL_INSTALL="$HOME/.local/share/VinaStudio"
if [ ! -d "$LOCAL_INSTALL/_internal/image_theme" ] || [ ! -d "$LOCAL_INSTALL/_internal/receptor_profiles" ]; then
    echo "ERREUR : l'installation locale ne contient toujours pas les dossiers attendus."
    echo "Vérifie install_vinastudio_local.sh."
    exit 1
fi
echo "OK : installation locale à jour, dossiers présents."
echo

echo "=================================================="
echo "ETAPE 4 : construction du .deb (build_deb_package.sh)"
echo "=================================================="
bash "$PROJECT_ROOT/build_deb_package.sh"
echo

echo "=================================================="
echo "ETAPE 5 : vérification du contenu du .deb généré"
echo "=================================================="
DEB_FILE=$(ls -t "$HOME"/Desktop/vinastudio_*_amd64.deb 2>/dev/null | head -n1)
if [ -z "$DEB_FILE" ]; then
    echo "ERREUR : aucun .deb trouvé dans ~/Desktop"
    exit 1
fi

echo "Fichier : $DEB_FILE"
echo
echo "Contenu vérifié (doit inclure image_theme et receptor_profiles) :"
dpkg-deb -c "$DEB_FILE" | grep -c "image_theme/" | xargs echo "  fichiers image_theme :"
dpkg-deb -c "$DEB_FILE" | grep -c "receptor_profiles/" | xargs echo "  fichiers receptor_profiles :"

echo
echo "=================================================="
echo "TERMINÉ : $DEB_FILE"
echo "=================================================="
