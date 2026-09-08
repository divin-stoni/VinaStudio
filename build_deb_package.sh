#!/bin/bash
set -e

APP_NAME="vinastudio"
APP_DISPLAY_NAME="VINA Studio"
VERSION="1.0.0"
ARCH="amd64"
PKG_DIR="$HOME/${APP_NAME}_${VERSION}_${ARCH}"
INSTALL_DIR_SRC="$HOME/.local/share/VinaStudio"
OUTPUT_DEB="$HOME/Desktop/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "=================================================="
echo "ETAPE 1 : verification que l'installation fonctionnelle existe"
echo "=================================================="
if [ ! -d "$INSTALL_DIR_SRC" ]; then
    echo "ERREUR : $INSTALL_DIR_SRC introuvable. Relance d'abord install_vinastudio_local.sh"
    exit 1
fi
echo "OK, trouve."

echo "=================================================="
echo "ETAPE 2 : creation de la structure du paquet .deb"
echo "=================================================="
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/opt/$APP_NAME"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PKG_DIR/usr/bin"

echo "=================================================="
echo "ETAPE 3 : copie du programme"
echo "=================================================="
cp -r "$INSTALL_DIR_SRC/"* "$PKG_DIR/opt/$APP_NAME/"

echo "=================================================="
echo "ETAPE 4 : icone et raccourci menu (.desktop)"
echo "=================================================="
cp "$HOME/MexAB_MexR_Analyzer_BETA/src/vinastudio_icon.png" \
   "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/vinastudio_icon.png"

cat > "$PKG_DIR/usr/share/applications/vinastudio.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_DISPLAY_NAME
Comment=Analyse statistique de docking moleculaire MexAB-OprM/MexR
Exec=/opt/$APP_NAME/$APP_NAME.sh
Icon=vinastudio_icon
Categories=Science;
Terminal=false
DESKTOP

echo "=================================================="
echo "ETAPE 5 : lanceur et commande terminal 'vinastudio'"
echo "=================================================="
cat > "$PKG_DIR/opt/$APP_NAME/$APP_NAME.sh" << LAUNCHER
#!/bin/bash
cd /opt/$APP_NAME
exec ./VinaStudio "\$@"
LAUNCHER
chmod +x "$PKG_DIR/opt/$APP_NAME/$APP_NAME.sh"
ln -s "/opt/$APP_NAME/$APP_NAME.sh" "$PKG_DIR/usr/bin/vinastudio"

echo "=================================================="
echo "ETAPE 6 : fichier de controle du paquet"
echo "=================================================="
TAILLE_KO=$(du -sk "$PKG_DIR/opt" | cut -f1)
cat > "$PKG_DIR/DEBIAN/control" << CONTROL
Package: $APP_NAME
Version: $VERSION
Section: science
Priority: optional
Architecture: $ARCH
Installed-Size: $TAILLE_KO
Maintainer: MexAB-OprM Analyzer Project <noreply@example.com>
Description: VINA Studio - Analyse statistique de docking moleculaire
 Application de bureau pour l'analyse statistique de resultats de
 docking moleculaire (MexAB-OprM / MexR, Pseudomonas aeruginosa).
 Comprend correlation dG(MexB)/dG(MexR), indice de selectivite,
 bootstrap, et mode predictif.
CONTROL

echo "=================================================="
echo "ETAPE 7 : script post-installation (rend le dossier inscriptible)"
echo "=================================================="
cat > "$PKG_DIR/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e
chmod -R a+rwX /opt/vinastudio
update-desktop-database /usr/share/applications 2>/dev/null || true
exit 0
POSTINST
chmod +x "$PKG_DIR/DEBIAN/postinst"

cat > "$PKG_DIR/DEBIAN/postrm" << 'POSTRM'
#!/bin/bash
set -e
update-desktop-database /usr/share/applications 2>/dev/null || true
exit 0
POSTRM
chmod +x "$PKG_DIR/DEBIAN/postrm"

echo "=================================================="
echo "ETAPE 8 : construction du fichier .deb"
echo "=================================================="
mkdir -p "$HOME/Desktop"
dpkg-deb --build --root-owner-group "$PKG_DIR" "$OUTPUT_DEB"

echo "=================================================="
echo "TERMINE"
echo "Paquet genere : $OUTPUT_DEB"
du -h "$OUTPUT_DEB"
echo ""
echo "INSTALLATION (chez toi ou chez n'importe qui) :"
echo "  sudo apt install $OUTPUT_DEB"
echo "ou double-clic sur le fichier .deb dans le gestionnaire de fichiers."
echo "L'application apparaitra dans le menu, sous 'VINA Studio'."
echo "=================================================="
