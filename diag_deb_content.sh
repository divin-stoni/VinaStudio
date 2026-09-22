#!/bin/bash
PROJ="/home/stoni/MexAB_MexR_Analyzer_BETA"
PKGNAME="vinastudio"

echo "=== 1. Le dossier dist/VinaStudio (sortie PyInstaller) contient-il l'executable ? ==="
ls -la "$PROJ/src/dist/VinaStudio/" 2>/dev/null | head -20

echo ""
echo "=== 2. Fichiers .deb presents dans le projet ==="
ls -la "$PROJ"/*.deb 2>/dev/null

echo ""
echo "=== 3. Contenu exact du .deb le plus recent (sans l'installer) ==="
DEB_FILE=$(ls -t "$PROJ"/${PKGNAME}_*_amd64.deb 2>/dev/null | head -1)
echo "Fichier examine : $DEB_FILE"
if [ -n "$DEB_FILE" ]; then
    dpkg-deb --contents "$DEB_FILE" | grep -i "opt/$PKGNAME"
fi

echo ""
echo "=== 4. Le .deb est-il enregistre dans dpkg (meme partiellement/casse) ? ==="
dpkg -l | grep -i "$PKGNAME"
dpkg --audit 2>/dev/null | grep -i "$PKGNAME"

echo ""
echo "=== 5. Depuis quand /opt/vinastudio existe-t-il, et par quel moyen (log apt/dpkg) ? ==="
grep -i "$PKGNAME" /var/log/dpkg.log 2>/dev/null | tail -20

echo ""
echo "=== 6. Espace disque disponible (build/installation coupee court ?) ==="
df -h /opt /home /tmp
