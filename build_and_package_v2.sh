#!/bin/bash
set -e
set -u

PROJ="/home/stoni/MexAB_MexR_Analyzer_BETA"
VERSION="1.0.1"
PKGNAME="vinastudio"
MAINTAINER="Divin Stoni Mbanimi <divin.stoni@example.com>"

cd "$PROJ"

echo "=== 1. Nettoyage COMPLET (dist/build racine + src/) ==="
rm -rf "$PROJ/build" "$PROJ/dist"
rm -rf "$PROJ/src/build" "$PROJ/src/dist"
rm -rf "/tmp/${PKGNAME}_deb_build"
echo "OK."

echo ""
echo "=== 2. Rebuild PyInstaller ==="
cd "$PROJ/src"
"$PROJ/venv/bin/pyinstaller" --noconfirm VinaStudio.spec

echo ""
echo "=== 3. VERIFICATION STRICTE : l'executable existe-t-il APRES build ? ==="
SRC_EXE="$PROJ/src/dist/VinaStudio/VinaStudio"
if [ ! -f "$SRC_EXE" ]; then
    echo "ERREUR FATALE : $SRC_EXE n'existe pas apres le build. Abandon."
    exit 1
fi
echo "OK : $SRC_EXE present ($(stat -c%s "$SRC_EXE") octets)"

echo ""
echo "=== 3bis. Copie de credit_du_logiciel (a cote de l'executable, requis par _credits_root()) ==="
CREDITS_SRC="$PROJ/credit_du_logiciel"
CREDITS_DEST="$PROJ/src/dist/VinaStudio/credit_du_logiciel"
if [ ! -d "$CREDITS_SRC" ]; then
    echo "ERREUR FATALE : $CREDITS_SRC introuvable. Abandon."
    exit 1
fi
rm -rf "$CREDITS_DEST"
cp -r "$CREDITS_SRC" "$CREDITS_DEST"
echo "OK : credit_du_logiciel copie dans $CREDITS_DEST"

echo ""
echo "=== 4. Construction de l'arborescence .deb ==="
DEB_ROOT="/tmp/${PKGNAME}_deb_build"
rm -rf "$DEB_ROOT"
mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/opt/$PKGNAME"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/share/pixmaps"

# Copie explicite : d'abord l'executable seul, puis _internal separement,
# pour etre certain qu'aucun des deux n'est silencieusement saute.
echo "Copie de l'executable..."
cp -v "$SRC_EXE" "$DEB_ROOT/opt/$PKGNAME/VinaStudio"

echo "Copie de _internal (peut prendre du temps, ~20000 fichiers)..."
cp -r "$PROJ/src/dist/VinaStudio/_internal" "$DEB_ROOT/opt/$PKGNAME/_internal"

echo "Copie de credit_du_logiciel (a cote de l'executable dans le paquet, requis par _credits_root())..."
cp -r "$PROJ/src/dist/VinaStudio/credit_du_logiciel" "$DEB_ROOT/opt/$PKGNAME/credit_du_logiciel"

echo ""
echo "=== 5. VERIFICATION STRICTE : l'executable est-il bien dans le paquet ? ==="
if [ ! -f "$DEB_ROOT/opt/$PKGNAME/VinaStudio" ]; then
    echo "ERREUR FATALE : la copie de l'executable a echoue silencieusement. Abandon."
    exit 1
fi
echo "OK : present dans $DEB_ROOT/opt/$PKGNAME/VinaStudio"

if [ ! -d "$DEB_ROOT/opt/$PKGNAME/credit_du_logiciel" ]; then
    echo "ERREUR FATALE : credit_du_logiciel absent du paquet. Abandon."
    exit 1
fi
echo "OK : credit_du_logiciel present dans $DEB_ROOT/opt/$PKGNAME/credit_du_logiciel"

chmod +x "$DEB_ROOT/opt/$PKGNAME/VinaStudio"

# Icone
if [ -f "$PROJ/src/vinastudio_icon.png" ]; then
    cp "$PROJ/src/vinastudio_icon.png" "$DEB_ROOT/usr/share/pixmaps/${PKGNAME}.png"
fi

INSTALLED_SIZE=$(du -sk "$DEB_ROOT/opt/$PKGNAME" | cut -f1)

cat > "$DEB_ROOT/DEBIAN/control" << CONTROL
Package: $PKGNAME
Version: $VERSION
Section: science
Priority: optional
Architecture: amd64
Installed-Size: $INSTALLED_SIZE
Maintainer: $MAINTAINER
Description: VINA Studio - Docking moleculaire et analyse des interactions
 Application de bureau pour le repositionnement de medicaments,
 le docking moleculaire (AutoDock Vina) et l'analyse d'interactions
 proteine-ligand (PLIP), avec pipeline statistique integre.
CONTROL

cat > "$DEB_ROOT/usr/share/applications/${PKGNAME}.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=VINA Studio
Comment=Docking moleculaire et analyse des interactions
Exec=/opt/$PKGNAME/VinaStudio
Icon=/usr/share/pixmaps/${PKGNAME}.png
Terminal=false
Categories=Science;Education;
DESKTOP

find "$DEB_ROOT/opt/$PKGNAME" -type d -exec chmod 755 {} \;

echo ""
echo "=== 6. VERIFICATION FINALE avant construction du .deb ==="
echo "Contenu de \$DEB_ROOT/opt/$PKGNAME (racine) :"
ls -la "$DEB_ROOT/opt/$PKGNAME/"
if [ ! -x "$DEB_ROOT/opt/$PKGNAME/VinaStudio" ]; then
    echo "ERREUR FATALE : VinaStudio absent ou non executable juste avant dpkg-deb. Abandon."
    exit 1
fi

DEB_FILE="$PROJ/${PKGNAME}_${VERSION}_amd64.deb"
rm -f "$PROJ"/${PKGNAME}_*_amd64.deb
dpkg-deb --root-owner-group --build "$DEB_ROOT" "$DEB_FILE"

echo ""
echo "=== 7. VERIFICATION POST-BUILD : le .deb contient-il bien l'executable ? ==="
if dpkg-deb --contents "$DEB_FILE" | grep -q "opt/$PKGNAME/VinaStudio\b"; then
    echo "OK : VinaStudio confirme present dans le .deb final."
else
    echo "ERREUR FATALE : l'executable est absent du .deb genere malgre les verifications precedentes."
    exit 1
fi

echo ""
echo "=== 8. Archive portable ==="
cd "$PROJ/src/dist"
TAR_FILE="$PROJ/${PKGNAME}_${VERSION}_linux_portable.tar.gz"
rm -f "$PROJ"/${PKGNAME}_*_linux_portable.tar.gz
tar -czf "$TAR_FILE" VinaStudio

echo ""
echo "=== RESUME ==="
ls -lh "$DEB_FILE" "$TAR_FILE"
echo ""
echo "Installation :"
echo "  sudo dpkg -i $DEB_FILE"
