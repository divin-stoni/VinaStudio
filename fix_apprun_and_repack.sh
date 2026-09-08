#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
APPDIR="$PROJECT_ROOT/squashfs-root"
APP_NAME="VinaStudio"

echo "=================================================="
echo "SAUVEGARDE de l'ancien AppRun"
echo "=================================================="
cp "$APPDIR/AppRun" "$APPDIR/AppRun.bak_$(date +%Y%m%d_%H%M%S)"

echo "=================================================="
echo "ECRITURE du nouvel AppRun (utilise \$APPDIR fourni par le runtime)"
echo "=================================================="
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/bin/bash
HERE="${APPDIR:-$(dirname "$(readlink -f "${0}")")}"
export QT_QPA_PLATFORM_PLUGIN_PATH="$HERE/usr/bin/_internal/PySide6/Qt/plugins/platforms"
export LD_LIBRARY_PATH="$HERE/usr/bin:$HERE/usr/lib:$LD_LIBRARY_PATH"
exec "$HERE/usr/bin/VinaStudio" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

echo "=================================================="
echo "TEST DIRECT (sans montage FUSE, simule ce que fait le runtime)"
echo "=================================================="
APPDIR="$APPDIR" timeout 5 "$APPDIR/AppRun" &
TESTPID=$!
sleep 3
if kill -0 $TESTPID 2>/dev/null; then
    echo "OK : le processus tourne toujours apres 3 secondes (bon signe, l'appli se lance)"
    kill $TESTPID 2>/dev/null || true
else
    wait $TESTPID
    echo "ATTENTION : le processus s'est arrete tout seul avant 3 secondes, voir message d'erreur ci-dessus"
fi

echo "=================================================="
echo "REPACKAGING avec appimagetool (pas besoin de refaire PyInstaller/linuxdeploy)"
echo "=================================================="
cd "$PROJECT_ROOT/src/appimage_build/tools"
rm -f "$PROJECT_ROOT/${APP_NAME}-x86_64.AppImage"
./appimagetool-x86_64.AppImage "$APPDIR" "$PROJECT_ROOT/${APP_NAME}-x86_64.AppImage"

echo "=================================================="
echo "TERMINE"
echo "Nouvelle AppImage : $PROJECT_ROOT/${APP_NAME}-x86_64.AppImage"
echo "=================================================="
