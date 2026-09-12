#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
SRC_DIR="$PROJECT_ROOT/src"
APP_NAME="VinaStudio"
INSTALL_DIR="$HOME/.local/share/${APP_NAME}"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
BIN_DIR="$HOME/.local/bin"

echo "=================================================="
echo "ETAPE 1 : nettoyage de tous les essais AppImage precedents"
echo "=================================================="
rm -f "$PROJECT_ROOT"/*.AppImage
rm -rf "$PROJECT_ROOT/squashfs-root"
rm -rf "$SRC_DIR/appimage_build"
rm -f "$PROJECT_ROOT"/*_log.txt "$PROJECT_ROOT"/*_report.txt
rm -f "$SRC_DIR"/*_log.txt "$SRC_DIR"/*_report.txt
rm -f "$SRC_DIR"/diag_*.sh "$SRC_DIR"/fix_*.sh "$SRC_DIR"/rebuild_*.sh
echo "Nettoyage termine."

echo "=================================================="
echo "ETAPE 2 : verification que le build PyInstaller existe toujours"
echo "=================================================="
if [ ! -d "$PROJECT_ROOT/dist/$APP_NAME" ]; then
    echo "ERREUR : dist/$APP_NAME introuvable. Le build a peut-etre ete efface."
    echo "Relance d'abord : cd $PROJECT_ROOT && pyinstaller --noconfirm src/VinaStudio.spec"
    exit 1
fi
echo "OK, build trouve."

echo "=================================================="
echo "ETAPE 3 : installation dans un dossier PERSONNEL inscriptible (pas de lecture seule)"
echo "=================================================="
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$PROJECT_ROOT/dist/$APP_NAME/"* "$INSTALL_DIR/"
echo "Installe dans : $INSTALL_DIR"

echo "=================================================="
echo "ETAPE 4 : copie de l'icone"
echo "=================================================="
mkdir -p "$ICON_DIR"
cp "$SRC_DIR/vinastudio_icon.png" "$ICON_DIR/vinastudio_icon.png"

echo "=================================================="
echo "ETAPE 5 : creation d'un lanceur (script simple, pas d'AppImage)"
echo "=================================================="
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/vinastudio" << LAUNCHER
#!/bin/bash
exec "$INSTALL_DIR/$APP_NAME" "\$@"
LAUNCHER
chmod +x "$BIN_DIR/vinastudio"

echo "=================================================="
echo "ETAPE 6 : creation de l'entree dans le menu d'applications"
echo "=================================================="
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/vinastudio.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=VINA Studio
Comment=Analyse statistique de docking moleculaire MexAB-OprM/MexR
Exec=$BIN_DIR/vinastudio
Icon=vinastudio_icon
Categories=Science;
Terminal=false
DESKTOP
chmod +x "$DESKTOP_DIR/vinastudio.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "=================================================="
echo "ETAPE 7 : test direct de l'installation finale"
echo "=================================================="
timeout 5 "$BIN_DIR/vinastudio" &
TESTPID=$!
sleep 3
if kill -0 $TESTPID 2>/dev/null; then
    echo "OK : l'application installee tourne correctement"
    kill $TESTPID 2>/dev/null || true
else
    wait $TESTPID
    echo "ATTENTION : echec du test, voir erreur ci-dessus"
fi

echo "=================================================="
echo "TERMINE"
echo "L'application est installee et disponible :"
echo "  - dans ton menu d'applications, sous le nom 'VINA Studio'"
echo "  - ou en tapant simplement : vinastudio"
echo "=================================================="
