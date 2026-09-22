#!/bin/bash
# Désinstallation complète de VinaStudio (toutes les méthodes d'installation
# connues), pour repartir sur une base propre avant un nouveau test.
#
# Ne touche JAMAIS à ~/MexAB_MexR_Analyzer_BETA (ton dossier de dev/code
# source) : uniquement les installations "utilisateur final".

set -uo pipefail

echo "=================================================="
echo "1) Désinstallation du paquet .deb (si installé via apt)"
echo "=================================================="
if dpkg -l | grep -qw vinastudio; then
    sudo apt remove --purge -y vinastudio
    echo "OK : paquet .deb désinstallé."
else
    echo "Rien à faire (pas installé via apt)."
fi
echo

echo "=================================================="
echo "2) Installation locale utilisateur (~/.local/...)"
echo "=================================================="
rm -f  "$HOME/.local/bin/vinastudio"
rm -f  "$HOME/.local/share/applications/vinastudio.desktop"
rm -rf "$HOME/.local/share/VinaStudio"
rm -f  "$HOME/.local/share/icons/hicolor/256x256/apps/vinastudio_icon.png"
echo "OK : fichiers de ~/.local nettoyés."
echo

echo "=================================================="
echo "3) Mise à jour de la base des raccourcis du menu"
echo "=================================================="
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
echo "OK."
echo

echo "=================================================="
echo "4) Résidus de builds intermédiaires (dist/ à la racine du projet)"
echo "   -> NE touche PAS à src/dist (build source), ni au code."
echo "=================================================="
if [ -d "$HOME/MexAB_MexR_Analyzer_BETA/dist" ]; then
    rm -rf "$HOME/MexAB_MexR_Analyzer_BETA/dist"
    echo "OK : dossier dist/ (racine projet) supprimé."
else
    echo "Rien à faire."
fi
echo

echo "=================================================="
echo "Vérification finale : plus aucune trace de VinaStudio installé ?"
echo "=================================================="
find "$HOME" -maxdepth 4 \( -iname "*vinastudio*" \) \
    -not -path "$HOME/MexAB_MexR_Analyzer_BETA/*" \
    -not -path "*/.local/share/Trash/*" \
    2>/dev/null

echo
echo "=================================================="
echo "TERMINÉ."
echo "Ce qui reste volontairement intact :"
echo "  - ~/MexAB_MexR_Analyzer_BETA  (ton code source, jamais touché)"
echo "  - ~/.local/share/Trash        (corbeille, à vider toi-même si besoin)"
echo "  - les .deb sur ~/Desktop      (tes archives de publication)"
echo "=================================================="
