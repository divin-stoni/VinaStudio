#!/usr/bin/env bash
# diag18_segfault.sh
#
# Diagnostic du "Erreur de segmentation (core dumped)" au lancement.
# Étape 1 : relance avec le fichier D'AVANT patch17 (ta sauvegarde
#           automatique) pour savoir si le patch en est la cause.
# Étape 2 : quelle que soit la réponse, tente de capturer une vraie
#           trace du crash via gdb (si installé) pour voir la fonction
#           C/C++ exacte qui plante (Chromium, Qt, driver...).
#
# Usage :
#   cd ~/MexAB_MexR_Analyzer_BETA/src
#   bash diag18_segfault.sh

set -u
cd "$(dirname "$0")" 2>/dev/null || true

MAIN="gui/main_window.py"

if [ ! -f "$MAIN" ]; then
    echo "[ERREUR] $MAIN introuvable. Lance ce script depuis le dossier src/."
    exit 1
fi

# --- Étape 1 : identifier la sauvegarde créée par patch17 -----------------
LAST_BAK=$(ls -t gui/main_window.py.bak_* 2>/dev/null | head -n1)

if [ -z "$LAST_BAK" ]; then
    echo "[ATTENTION] Aucune sauvegarde .bak_* trouvée dans gui/ -- impossible"
    echo "de tester automatiquement 'avant patch17'. On passe direct à l'étape 2."
else
    echo "=============================================================="
    echo " ETAPE 1 : test AVEC L'ANCIEN CODE (avant patch17)"
    echo " Sauvegarde utilisée : $LAST_BAK"
    echo "=============================================================="
    cp "$MAIN" "gui/main_window.py.patch17_current"
    cp "$LAST_BAK" "$MAIN"

    echo ">>> Lancement (10s max, Ctrl+C si ça tourne normalement)..."
    timeout 10 python3 main.py
    RC=$?

    # Restaure le code patché (patch17) quoi qu'il arrive
    cp "gui/main_window.py.patch17_current" "$MAIN"
    rm -f "gui/main_window.py.patch17_current"

    echo
    if [ $RC -eq 139 ]; then
        echo "[RESULTAT ETAPE 1] Ça plante PAREIL avec l'ancien code (code 139 = segfault)."
        echo "==> Le patch17 n'est donc PAS la cause. Le bug est ailleurs (préexistant)."
    elif [ $RC -eq 124 ]; then
        echo "[RESULTAT ETAPE 1] Le logiciel a tourné 10s sans planter (timeout normal)."
        echo "==> Sans le patch17, pas de crash immédiat -- le patch17 est probablement en cause."
        echo "    (Mais teste aussi un vrai drag de souris avec l'ancien code si tu as le temps,"
        echo "    au cas où le segfault dépende justement de cette interaction.)"
    else
        echo "[RESULTAT ETAPE 1] Code de sortie inattendu : $RC (voir la sortie ci-dessus)."
    fi
    echo
fi

# --- Étape 2 : capture d'une vraie trace via gdb ---------------------------
echo "=============================================================="
echo " ETAPE 2 : capture d'une trace du crash (code actuel, avec patch17)"
echo "=============================================================="

if ! command -v gdb >/dev/null 2>&1; then
    echo "[INFO] gdb n'est pas installé. Pour l'installer :"
    echo "    sudo apt-get update && sudo apt-get install -y gdb"
    echo "Relance ensuite ce script pour obtenir la trace."
    exit 0
fi

echo ">>> Lancement sous gdb -- reproduis le crash normalement (attends le"
echo "    segfault comme avant). La trace sera sauvegardée dans crash_trace.txt"
echo

gdb -q -batch \
    -ex run \
    -ex "thread apply all bt" \
    --args python3 main.py \
    > crash_trace.txt 2>&1

echo
echo "[OK] Terminé. Trace complète dans : $(pwd)/crash_trace.txt"
echo "Envoie-moi ce fichier (ou juste les 30-40 dernières lignes,"
echo "en particulier tout ce qui contient 'Qt', 'Chromium', 'libGL', 'swiftshader')."
