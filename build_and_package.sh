#!/bin/bash
set -e

PROJ="/home/stoni/MexAB_MexR_Analyzer_BETA"
VENV_PYINSTALLER="$PROJ/venv/bin/pyinstaller"
VERSION="1.0.0"          # <-- change ici si tu veux une autre version
PKGNAME="vinastudio"
MAINTAINER="Divin Stoni Mbanimi <divin.stoni@example.com>"   # <-- adapte l'email si besoin

cd "$PROJ"

echo "=== 1. Nettoyage des anciens build/dist (potentiellement perimes) ==="
rm -rf "$PROJ/build" "$PROJ/dist"
rm -rf "$PROJ/src/build" "$PROJ/src/dist"
echo "Nettoyage termine."

echo ""
echo "=== 2. Verification que pyinstaller (venv) existe ==="
if [ ! -x "$VENV_PYINSTALLER" ]; then
    echo "ERREUR : $VENV_PYINSTALLER introuvable. Le venv contient-il pyinstaller ?"
    exit 1
fi
"$VENV_PYINSTALLER" --version

echo ""
echo "=== 3. Rebuild complet avec VinaStudio.spec ==="
cd "$PROJ/src"
"$VENV_PYINSTALLER" --noconfirm VinaStudio.spec

if [ ! -d "$PROJ/src/dist/VinaStudio" ]; then
    echo "ERREUR : le build n'a pas produit src/dist/VinaStudio. Abandon."
    exit 1
fi
echo "Build PyInstaller termine : $PROJ/src/dist/VinaStudio"

echo ""
echo "=== 4. Construction du paquet .deb ==="
DEB_ROOT="/tmp/${PKGNAME}_deb_build"
rm -rf "$DEB_ROOT"
mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/opt/$PKGNAME"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/share/pixmaps"

# Copie du contenu buildé
cp -r "$PROJ/src/dist/VinaStudio/." "$DEB_ROOT/opt/$PKGNAME/"

# Icone (recuperee depuis le spec)
if [ -f "$PROJ/src/vinastudio_icon.png" ]; then
    cp "$PROJ/src/vinastudio_icon.png" "$DEB_ROOT/usr/share/pixmaps/${PKGNAME}.png"
fi

# Calcul de la taille installee (en Ko, requis par dpkg)
INSTALLED_SIZE=$(du -sk "$DEB_ROOT/opt/$PKGNAME" | cut -f1)

# Fichier de controle DEBIAN/control
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

# Raccourci menu (.desktop) pointant vers /opt
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

# Permissions d'execution
chmod +x "$DEB_ROOT/opt/$PKGNAME/VinaStudio"
find "$DEB_ROOT/opt/$PKGNAME" -type d -exec chmod 755 {} \;

DEB_FILE="$PROJ/${PKGNAME}_${VERSION}_amd64.deb"
dpkg-deb --root-owner-group --build "$DEB_ROOT" "$DEB_FILE"

echo "Paquet .deb cree : $DEB_FILE"

echo ""
echo "=== 5. Archive portable compressee (.tar.gz) ==="
cd "$PROJ/src/dist"
TAR_FILE="$PROJ/${PKGNAME}_${VERSION}_linux_portable.tar.gz"
tar -czf "$TAR_FILE" VinaStudio
echo "Archive portable creee : $TAR_FILE"

echo ""
echo "=== RESUME ==="
ls -lh "$DEB_FILE" "$TAR_FILE"
echo ""
echo "Pour tester l'installation du .deb :"
echo "  sudo dpkg -i $DEB_FILE"
echo "Pour la desinstaller ensuite :"
echo "  sudo dpkg -r $PKGNAME"
