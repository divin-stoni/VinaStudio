#!/bin/bash
set -e

APP_NAME="VinaStudio"
INSTALL_DIR="$HOME/.local/share/${APP_NAME}"
STAGING_DIR="$HOME/${APP_NAME}-Linux-x86_64"
ARCHIVE_NAME="${APP_NAME}-Linux-x86_64.tar.gz"
OUTPUT_PATH="$HOME/Desktop/$ARCHIVE_NAME"

echo "=================================================="
echo "ETAPE 1 : verification que l'installation fonctionnelle existe"
echo "=================================================="
if [ ! -d "$INSTALL_DIR" ]; then
    echo "ERREUR : $INSTALL_DIR introuvable. Relance d'abord install_vinastudio_local.sh"
    exit 1
fi
echo "OK, trouve : $INSTALL_DIR"

echo "=================================================="
echo "ETAPE 2 : preparation d'un dossier propre a distribuer"
echo "=================================================="
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
cp -r "$INSTALL_DIR/"* "$STAGING_DIR/"

echo "=================================================="
echo "ETAPE 3 : creation du lanceur (script simple, double-clic ou terminal)"
echo "=================================================="
cat > "$STAGING_DIR/Lancer_VinaStudio.sh" << 'LAUNCHER'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
cd "$HERE"
./VinaStudio
LAUNCHER
chmod +x "$STAGING_DIR/Lancer_VinaStudio.sh"
chmod +x "$STAGING_DIR/VinaStudio"

echo "=================================================="
echo "ETAPE 4 : fichier README pour les destinataires (auditeur/journal/GitHub)"
echo "=================================================="
cat > "$STAGING_DIR/LISEZMOI.txt" << 'README'
VINA Studio - Application d'analyse statistique de docking moleculaire
========================================================================

INSTALLATION : aucune. C'est une application portable.

UTILISATION :
1. Decompressez cette archive n'importe ou sur votre machine
   (Bureau, Documents, cle USB...) - PAS dans un dossier en lecture
   seule comme /usr ou un point de montage AppImage.
2. Ouvrez un terminal dans le dossier decompresse et lancez :
       ./Lancer_VinaStudio.sh
   ou directement :
       ./VinaStudio

PREREQUIS SYSTEME : Linux x86_64 (teste sur Ubuntu). Aucune
installation de Python, Qt ou autre dependance n'est necessaire :
tout est inclus dans l'archive.

Si le lancement echoue avec un message de type "Permission denied" :
       chmod +x VinaStudio Lancer_VinaStudio.sh
README

echo "=================================================="
echo "ETAPE 5 : test final avant compression"
echo "=================================================="
cd "$STAGING_DIR"
timeout 5 ./VinaStudio &
TESTPID=$!
sleep 3
if kill -0 $TESTPID 2>/dev/null; then
    echo "OK : le dossier a distribuer fonctionne correctement"
    kill $TESTPID 2>/dev/null || true
else
    wait $TESTPID
    echo "ATTENTION : echec du test, voir erreur ci-dessus -- ne pas distribuer tel quel"
    exit 1
fi

echo "=================================================="
echo "ETAPE 6 : compression en une seule archive .tar.gz"
echo "=================================================="
cd "$HOME"
mkdir -p "$HOME/Desktop"
tar -czf "$OUTPUT_PATH" "${APP_NAME}-Linux-x86_64"

echo "=================================================="
echo "TERMINE"
echo "Fichier pret a distribuer : $OUTPUT_PATH"
echo "Taille :"
du -h "$OUTPUT_PATH"
echo ""
echo "C'est CE fichier .tar.gz qu'il faut envoyer / deposer sur GitHub / mettre sur cle USB."
echo "=================================================="
