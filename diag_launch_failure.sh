#!/bin/bash
PKGNAME="vinastudio"

echo "=== 1. Le paquet est-il installe ? ==="
dpkg -l | grep -i "$PKGNAME"

echo ""
echo "=== 2. Contenu installe dans /opt ==="
ls -la "/opt/$PKGNAME" 2>/dev/null || echo "-> /opt/$PKGNAME introuvable"

echo ""
echo "=== 3. Le binaire est-il executable ? ==="
ls -la "/opt/$PKGNAME/VinaStudio" 2>/dev/null

echo ""
echo "=== 4. Lancement direct du binaire installe (affiche l'erreur reelle) ==="
"/opt/$PKGNAME/VinaStudio"
echo "Code de sortie : $?"
