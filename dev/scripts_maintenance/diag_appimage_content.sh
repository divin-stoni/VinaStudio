#!/bin/bash
echo "=================================================="
echo "CONTENU DE AppRun (celui reellement embarque)"
echo "=================================================="
cat squashfs-root/AppRun
echo ""
echo "=================================================="
echo "STRUCTURE de usr/bin (2 niveaux)"
echo "=================================================="
find squashfs-root/usr/bin -maxdepth 2

echo "=================================================="
echo "OU EST VRAIMENT l'executable VinaStudio ?"
echo "=================================================="
find squashfs-root -iname "VinaStudio" -type f

echo "=================================================="
echo "LE .desktop EMBARQUE"
echo "=================================================="
cat squashfs-root/vinastudio.desktop 2>/dev/null || cat squashfs-root/*.desktop
