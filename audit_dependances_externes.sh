#!/usr/bin/env bash
set -uo pipefail

EXCLUDES='--exclude-dir=venv --exclude-dir=.git --exclude-dir=_archive_backups --exclude-dir=_a_supprimer --exclude-dir=_patch_backups'

echo "======================================================================"
echo "1) Registre central : src/tools/tool_manager.py"
echo "   (toutes les cles 'executables'/'commands' declarees)"
echo "======================================================================"
if [[ -f src/tools/tool_manager.py ]]; then
    grep -n -B2 -A4 '"executables"\|"commands"' src/tools/tool_manager.py
else
    echo "!! Fichier introuvable"
fi

echo
echo "======================================================================"
echo "2) Registre central : src/environment/environment_manager.py"
echo "   (toutes les cles 'commands' declarees)"
echo "======================================================================"
if [[ -f src/environment/environment_manager.py ]]; then
    grep -n -B2 -A4 'commands=\[' src/environment/environment_manager.py
else
    echo "!! Fichier introuvable"
fi

echo
echo "======================================================================"
echo "3) Toute la liste des outils/dependances declares (noms complets)"
echo "======================================================================"
echo "--- Cles 'key=' dans tool_manager.py ---"
grep -oP '(?<=key=")[^"]+' src/tools/tool_manager.py 2>/dev/null | sort -u
echo
echo "--- Cles 'key=' dans environment_manager.py ---"
grep -oP '(?<=key=")[^"]+' src/environment/environment_manager.py 2>/dev/null | sort -u

echo
echo "======================================================================"
echo "4) TOUS les appels directs a un binaire externe dans le code"
echo "   (subprocess.run/Popen/check_output/call, shutil.which)"
echo "   -- pour attraper ce qui NE PASSE PAS par les registres ci-dessus"
echo "======================================================================"
grep -rn $EXCLUDES -E "subprocess\.(run|Popen|check_output|call)|shutil\.which" \
    --include="*.py" . 2>/dev/null | grep -v "^\./tests/"

echo
echo "======================================================================"
echo "5) Chemins binaires codes en dur type /usr/... ou /usr/local/... "
echo "   (souvent signe d'un outil installe manuellement, comme fpocket)"
echo "======================================================================"
grep -rn $EXCLUDES -E "/usr/(local/)?bin/[a-zA-Z_-]+|/usr/lib/[a-zA-Z_-]+" \
    --include="*.py" . 2>/dev/null | grep -v "^\./tests/"

echo
echo "======================================================================"
echo "6) Nom de chaque binaire externe trouve (extraction, dedoublonnee)"
echo "======================================================================"
{
    grep -rhoP $EXCLUDES '(?<=/usr/local/bin/)[a-zA-Z_-]+' --include="*.py" . 2>/dev/null
    grep -rhoP $EXCLUDES '(?<=/usr/bin/)[a-zA-Z_-]+' --include="*.py" . 2>/dev/null
} | sort -u

echo
echo "======================================================================"
echo "7) Rappel : ce qui est DEJA embarque dans le workflow Windows"
echo "   (--add-data / --add-binary, extrait direct du fichier)"
echo "======================================================================"
grep -oE -- '--add-(data|binary)[= ]"[^"]+"' .github/workflows/build-windows.yml 2>/dev/null

echo
echo "======================================================================"
echo "8) pocket_detector.py -- comment fpocket est localise/appele"
echo "======================================================================"
if [[ -f src/analysis/pocket_detector.py ]]; then
    grep -n -B2 -A5 "fpocket" src/analysis/pocket_detector.py
fi

echo
echo "======================================================================"
echo "9) Recherche large de TOUT nom de binaire externe connu du projet"
echo "   (obabel, vina, fpocket, chimerax + tout autre trouve en 3/6)"
echo "======================================================================"
for tool in obabel vina fpocket chimerax; do
    echo "--- $tool ---"
    echo "Reference dans le code (hors venv/tests) :"
    grep -rlc $EXCLUDES "\b$tool\b" --include="*.py" . 2>/dev/null | grep -v "^\./tests/" | wc -l
    echo "Embarque dans le workflow Windows :"
    grep -c "$tool" .github/workflows/build-windows.yml 2>/dev/null || echo 0
    echo
done

echo
echo "======================================================================"
echo "FIN DE L'AUDIT"
echo "======================================================================"
