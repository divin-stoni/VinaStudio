#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
APPDIR="$PROJECT_ROOT/squashfs-root"
APP_NAME="VinaStudio"

echo "=================================================="
echo "DIAGNOSTIC : tailles des variables d'environnement actuelles"
echo "=================================================="
echo "Taille de \$LD_LIBRARY_PATH : ${#LD_LIBRARY_PATH} caracteres"
echo "Taille de \$PATH : ${#PATH} caracteres"
echo "Taille totale de l'environnement (nombre de variables) :"
env | wc -l
echo "Les 3 variables d'environnement les plus longues :"
env | awk -F= '{print length($0), $1}' | sort -rn | head -3

echo "=================================================="
echo "TYPE REEL du fichier VinaStudio (confirme ELF)"
echo "=================================================="
file "$APPDIR/usr/bin/VinaStudio"

echo "=================================================="
echo "TEST avec environnement completement propre (env -i)"
echo "=================================================="
env -i HOME="$HOME" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" bash -c "
    export QT_QPA_PLATFORM_PLUGIN_PATH='$APPDIR/usr/bin/_internal/PySide6/Qt/plugins/platforms'
    export LD_LIBRARY_PATH='$APPDIR/usr/bin:$APPDIR/usr/lib'
    timeout 5 '$APPDIR/usr/bin/VinaStudio' &
    TESTPID=\$!
    sleep 3
    if kill -0 \$TESTPID 2>/dev/null; then
        echo 'OK : ca tourne avec un environnement propre (confirme la pollution de LD_LIBRARY_PATH/PATH)'
        kill \$TESTPID 2>/dev/null || true
    else
        wait \$TESTPID
        echo 'ECHEC meme avec environnement propre, ce n est donc pas un probleme de pollution env'
    fi
"

echo "=================================================="
echo "CORRECTION de AppRun : ne plus heriter de LD_LIBRARY_PATH/PATH externes"
echo "=================================================="
cp "$APPDIR/AppRun" "$APPDIR/AppRun.bak_$(date +%Y%m%d_%H%M%S)"
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/bin/bash
HERE="${APPDIR:-$(dirname "$(readlink -f "${0}")")}"
export QT_QPA_PLATFORM_PLUGIN_PATH="$HERE/usr/bin/_internal/PySide6/Qt/plugins/platforms"
unset LD_LIBRARY_PATH
export LD_LIBRARY_PATH="$HERE/usr/bin:$HERE/usr/lib"
exec "$HERE/usr/bin/VinaStudio" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

echo "=================================================="
echo "REPACKAGING"
echo "=================================================="
cd "$PROJECT_ROOT/src/appimage_build/tools"
rm -f "$PROJECT_ROOT/${APP_NAME}-x86_64.AppImage"
./appimagetool-x86_64.AppImage "$APPDIR" "$PROJECT_ROOT/${APP_NAME}-x86_64.AppImage"
chmod +x "$PROJECT_ROOT/${APP_NAME}-x86_64.AppImage"

echo "=================================================="
echo "TERMINE - relance maintenant avec :"
echo "cd $PROJECT_ROOT && ./${APP_NAME}-x86_64.AppImage"
echo "=================================================="
