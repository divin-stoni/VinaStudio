#!/bin/bash
PROJ=/home/stoni/MexAB_MexR_Analyzer_BETA
cd "$PROJ" || { echo "Dossier projet introuvable : $PROJ"; exit 1; }

echo "=== 1. Fichiers .spec presents dans le projet ==="
find . -maxdepth 2 -iname "*.spec"

echo ""
echo "=== 2. Contenu du/des fichier(s) .spec ==="
for f in $(find . -maxdepth 2 -iname "*.spec"); do
    echo "--- $f ---"
    cat -n "$f"
    echo ""
done

echo ""
echo "=== 3. Recherche d'anciens chemins absolus fige en dur (hors venv/ et .git/) ==="
grep -rn "/home/" --include="*.spec" --include="*.py" --include="*.desktop" --include="*.sh" \
    --exclude-dir=venv --exclude-dir=.git --exclude-dir=dist --exclude-dir=build . 2>/dev/null

echo ""
echo "=== 4. Anciens dossiers build/dist deja presents (a nettoyer avant rebuild) ==="
find . -maxdepth 2 -iname "build" -o -maxdepth 2 -iname "dist"
echo "-- dates de derniere modif --"
[ -d build ] && stat -c '%y %n' build
[ -d dist ] && stat -c '%y %n' dist

echo ""
echo "=== 5. Scripts de packaging .deb existants (fpm, dpkg-deb, pkgbuild...) ==="
find . -maxdepth 3 -iname "*.deb" -o -maxdepth 3 -iname "*pkgbuild*" -o -maxdepth 3 -iname "build-deb*" -o -maxdepth 3 -iname "*fpm*" 2>/dev/null

echo ""
echo "=== 6. Dossiers pkgbuild non trackes deja mentionnes precedemment ==="
find . -maxdepth 2 -iname "mexab-mexr-analyzer_*_amd64" -o -maxdepth 2 -iname "pkgbuild*"

echo ""
echo "=== 7. Nom/version actuels dans le .spec (App name) ==="
grep -n "name=" *.spec 2>/dev/null

echo ""
echo "=== 8. Fichiers .desktop existants (raccourci menu) ==="
find . -maxdepth 3 -iname "*.desktop"
find ~/.local/share/applications -iname "*mexab*" -o -iname "*vina*" 2>/dev/null

echo ""
echo "=== FIN DIAGNOSTIC ==="
