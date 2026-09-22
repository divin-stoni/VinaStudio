#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) Toute reference a ChimeraX dans le code source (hors venv/.git)"
echo "======================================================================"
grep -rni "chimerax" --include="*.py" --include="*.md" --include="*.txt" \
    --exclude-dir=venv --exclude-dir=.git --exclude-dir=_archive_backups \
    --exclude-dir=_a_supprimer --exclude-dir=node_modules . 2>/dev/null
echo "--- Fin de la recherche (rien au-dessus = aucune reference restante) ---"

echo
echo "======================================================================"
echo "2) Tags git existants (versions reperees dans l'historique)"
echo "======================================================================"
git tag --list --sort=-creatordate 2>&1

echo
echo "======================================================================"
echo "3) Derniers 40 commits (pour reperer ce qui a change recemment)"
echo "======================================================================"
git log --oneline -40

echo
echo "======================================================================"
echo "4) Fichiers sources modifies depuis le dernier tag (si un tag existe)"
echo "======================================================================"
LAST_TAG=$(git tag --list --sort=-creatordate | head -1)
if [[ -n "$LAST_TAG" ]]; then
    echo "Dernier tag : $LAST_TAG"
    git diff --stat "$LAST_TAG" HEAD -- src/ docking/ run_gui.py 2>&1 | grep -v "venv\|_archive\|_a_supprimer"
else
    echo "Aucun tag trouve. A defaut, fichiers .py modifies dans les 30 derniers jours :"
    find src/ docking/ -name "*.py" -newer <(date -d '30 days ago' +%Y%m%d 2>/dev/null || date -v-30d +%Y%m%d) 2>/dev/null | grep -v "\.bak\|\.backup\|\.before"
fi

echo
echo "======================================================================"
echo "5) Liste des modules Python actuels par domaine (etat reel du code)"
echo "======================================================================"
echo "--- src/analysis/ ---"
ls -1 src/analysis/*.py 2>/dev/null | xargs -n1 basename
echo
echo "--- src/docking/ ---"
ls -1 src/docking/*.py 2>/dev/null | xargs -n1 basename
echo
echo "--- src/visualization/ ---"
ls -1 src/visualization/*.py 2>/dev/null | xargs -n1 basename
echo
echo "--- src/gui/ (fichiers .py uniquement, pas les .bak) ---"
ls -1 src/gui/*.py 2>/dev/null | xargs -n1 basename

echo
echo "======================================================================"
echo "6) Profils recepteurs actuellement definis (fonctionnalite multi-cible)"
echo "======================================================================"
ls -1 receptor_profiles/*.json 2>/dev/null | xargs -n1 basename

echo
echo "======================================================================"
echo "FIN DU DIAGNOSTIC"
echo "======================================================================"
