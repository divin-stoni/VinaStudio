#!/bin/bash
# diag_spec_vs_src.sh
# Compare le fichier .spec (PyInstaller) avec l'arborescence réelle du projet
# pour repérer ce qui a été ajouté (nouveaux onglets, nouveaux modules, nouvelles
# ressources) mais qui n'est pas encore référencé dans le .spec.
#
# À lancer depuis la racine de MexAB_MexR_Analyzer_BETA :
#   cd ~/MexAB_MexR_Analyzer_BETA
#   bash diag_spec_vs_src.sh

set -uo pipefail

echo "========================================================"
echo " 1. Localisation du fichier .spec"
echo "========================================================"
SPEC_FILE=$(find . -maxdepth 2 -name "*.spec" -not -path "*/venv/*" | head -n1)
if [ -z "$SPEC_FILE" ]; then
    echo "!! Aucun fichier .spec trouvé à la racine ou en 2 niveaux de profondeur."
    echo "   Cherche plus largement..."
    SPEC_FILE=$(find . -name "*.spec" -not -path "*/venv/*" | head -n1)
fi
echo "Fichier .spec utilisé : $SPEC_FILE"
echo

if [ -z "$SPEC_FILE" ]; then
    echo "!! Impossible de continuer sans fichier .spec. Arrêt."
    exit 1
fi

echo "========================================================"
echo " 2. Contenu complet du fichier .spec"
echo "========================================================"
cat -n "$SPEC_FILE"
echo

echo "========================================================"
echo " 3. Modules Python (.py) dans src/ et à la racine"
echo "========================================================"
echo "-- Fichiers .py présents dans le projet (hors venv, backups, archives) --"
find . -name "*.py" \
    -not -path "*/venv/*" \
    -not -path "*/_archive*/*" \
    -not -path "*/_patch_backups/*" \
    -not -path "*/backups/*" \
    -not -path "*/_a_supprimer/*" \
    -not -path "*/build/*" \
    -not -path "*/dist/*" \
    | sort > /tmp/py_files_reels.txt
cat /tmp/py_files_reels.txt
echo
echo "Nombre total de fichiers .py trouvés : $(wc -l < /tmp/py_files_reels.txt)"
echo

echo "========================================================"
echo " 4. Modules référencés dans le .spec (hiddenimports, Analysis)"
echo "========================================================"
echo "-- Bloc hiddenimports détecté --"
grep -n "hiddenimports" "$SPEC_FILE" -A 30 | head -n 60
echo
echo "-- Chemins référencés dans Analysis(...) --"
grep -n "Analysis(" "$SPEC_FILE" -A 15
echo

echo "========================================================"
echo " 5. Fichiers .py qui semblent ABSENTS du .spec"
echo "========================================================"
echo "(comparaison approximative : nom de fichier sans extension"
echo " cherché tel quel dans le texte du .spec)"
echo
while IFS= read -r pyfile; do
    base=$(basename "$pyfile" .py)
    if ! grep -q "$base" "$SPEC_FILE"; then
        echo "MANQUANT probable : $pyfile"
    fi
done < /tmp/py_files_reels.txt
echo

echo "========================================================"
echo " 6. Bloc 'datas' du .spec (ressources embarquées)"
echo "========================================================"
grep -n "datas" "$SPEC_FILE" -A 30 | head -n 60
echo

echo "========================================================"
echo " 7. Ressources réelles (images, icônes, fichiers non .py)"
echo "     dans les dossiers de ressources probables"
echo "========================================================"
for d in image_theme docs credit_du_logiciel receptor_profiles ligands scripts; do
    if [ -d "$d" ]; then
        echo "-- Dossier : $d --"
        find "$d" -type f | sort
        echo
    fi
done

echo "========================================================"
echo " 8. Dossiers de ressources NON mentionnés dans 'datas' du .spec"
echo "========================================================"
for d in image_theme docs credit_du_logiciel receptor_profiles ligands scripts src scientific_analysis; do
    if [ -d "$d" ]; then
        if ! grep -q "$d" "$SPEC_FILE"; then
            echo "MANQUANT probable dans datas : $d/"
        fi
    fi
done
echo

echo "========================================================"
echo " 9. Fichiers .py modifiés récemment (dernières 72h)"
echo "     -> probablement vos nouveaux onglets / options"
echo "========================================================"
find . -name "*.py" -mtime -3 \
    -not -path "*/venv/*" \
    -not -path "*/_archive*/*" \
    -not -path "*/backups/*" \
    | sort
echo

echo "========================================================"
echo " 10. requirements.txt vs venv actif (nouvelles dépendances ?)"
echo "========================================================"
if [ -f requirements.txt ]; then
    echo "-- requirements.txt --"
    cat requirements.txt
    echo
fi
if [ -d venv ]; then
    echo "-- Packages installés dans venv (pip freeze) --"
    ./venv/bin/pip freeze 2>/dev/null | sort
fi
echo

echo "========================================================"
echo " TERMINÉ. Copiez-collez toute cette sortie pour qu'on"
echo " mette à jour le .spec ensemble, ligne par ligne."
echo "========================================================"
