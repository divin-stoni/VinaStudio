#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
SRC_DIR="$PROJECT_ROOT/src"
APP_NAME="VinaStudio"
BUILD_DIR="$SRC_DIR/appimage_build"

echo "=================================================="
echo "ETAPE 1/6 : Installation de PyInstaller"
echo "=================================================="
pip install pyinstaller

echo "=================================================="
echo "ETAPE 2/6 : Nettoyage build precedent"
echo "=================================================="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$SRC_DIR"

echo "=================================================="
echo "ETAPE 3/6 : Generation d'une icone placeholder (256x256)"
echo "=================================================="
python3 << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGBA", (256, 256), (30, 60, 114, 255))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
except Exception:
    font = ImageFont.load_default()
text = "VS"
bbox = draw.textbbox((0, 0), text, font=font)
w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
draw.text(((256-w)/2 - bbox[0], (256-h)/2 - bbox[1]), text, fill="white", font=font)
img.save("vinastudio_icon.png")
print("Icone generee : vinastudio_icon.png")
PYEOF

echo "=================================================="
echo "ETAPE 4/6 : Compilation avec PyInstaller (onedir)"
echo "=================================================="
pyinstaller --noconfirm --windowed --name "$APP_NAME" \
    --icon="$SRC_DIR/vinastudio_icon.png" \
    --add-data "$PROJECT_ROOT/reference_data:reference_data" \
    --add-data "$SRC_DIR/i18n:i18n" \
    main.py

echo "=================================================="
echo "ETAPE 5/6 : Telechargement des outils AppImage"
echo "=================================================="
mkdir -p "$BUILD_DIR/tools"
cd "$BUILD_DIR/tools"

if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget -q --show-progress "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
    chmod +x linuxdeploy-x86_64.AppImage
fi

if [ ! -f linuxdeploy-plugin-qt-x86_64.AppImage ]; then
    wget -q --show-progress "https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/continuous/linuxdeploy-plugin-qt-x86_64.AppImage"
    chmod +x linuxdeploy-plugin-qt-x86_64.AppImage
fi

echo "=================================================="
echo "ETAPE 6/6 : Construction de l'AppDir et generation de l'AppImage"
echo "=================================================="
cd "$BUILD_DIR"
APPDIR="$BUILD_DIR/AppDir"
mkdir -p "$APPDIR/usr/bin"
cp -r "$SRC_DIR/dist/$APP_NAME/"* "$APPDIR/usr/bin/"

mkdir -p "$APPDIR/usr/share/applications"
cat > "$APPDIR/usr/share/applications/vinastudio.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=VINA Studio
Comment=Analyse statistique de docking moleculaire MexAB-OprM/MexR
Exec=$APP_NAME
Icon=vinastudio_icon
Categories=Science;Education;
Terminal=false
DESKTOP

mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp "$SRC_DIR/vinastudio_icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/vinastudio_icon.png"
cp "$SRC_DIR/vinastudio_icon.png" "$APPDIR/vinastudio_icon.png"
cp "$APPDIR/usr/share/applications/vinastudio.desktop" "$APPDIR/vinastudio.desktop"

export QML_SOURCES_PATHS="$SRC_DIR"
cd "$BUILD_DIR/tools"
./linuxdeploy-x86_64.AppImage --appdir "$APPDIR" \
    --executable "$APPDIR/usr/bin/$APP_NAME" \
    --desktop-file "$APPDIR/vinastudio.desktop" \
    --icon-file "$APPDIR/vinastudio_icon.png" \
    --plugin qt \
    --output appimage

mv *.AppImage "$BUILD_DIR/../${APP_NAME}-x86_64.AppImage" 2>/dev/null || true

echo "=================================================="
echo "TERMINE"
echo "AppImage generee : $SRC_DIR/${APP_NAME}-x86_64.AppImage"
echo "Teste-la avec : chmod +x ${APP_NAME}-x86_64.AppImage && ./${APP_NAME}-x86_64.AppImage"
echo "=================================================="
