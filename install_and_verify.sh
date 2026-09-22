#!/bin/bash
set -e

DEB_FILE="/home/stoni/MexAB_MexR_Analyzer_BETA/vinastudio_1.0.1_amd64.deb"

echo "=== 1. Installation ==="
sudo dpkg -i "$DEB_FILE"

echo ""
echo "=== 2. Verification dpkg ==="
dpkg -l | grep vinastudio

echo ""
echo "=== 3. L'executable est-il bien present et executable ? ==="
ls -la /opt/vinastudio/VinaStudio

echo ""
echo "=== 4. Test de lancement direct (Ctrl+C pour fermer une fois l'interface visible) ==="
/opt/vinastudio/VinaStudio
