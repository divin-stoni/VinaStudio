#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) receptor_profile.py existe-t-il localement, et est-il suivi par git ?"
echo "======================================================================"
ls -la src/docking/receptor_profile.py 2>&1
echo
git ls-files -- src/docking/receptor_profile.py

echo
echo "======================================================================"
echo "2) Est-il present sur origin/main (l'etat reel sur GitHub) ?"
echo "======================================================================"
git fetch origin main --quiet
git ls-tree -r --name-only origin/main -- src/docking/ | sort

echo
echo "======================================================================"
echo "3) Comparaison complete src/docking/ : local HEAD vs origin/main"
echo "======================================================================"
git diff --stat HEAD origin/main -- src/docking/

echo
echo "======================================================================"
echo "4) Y a-t-il des modifications non commitees dans src/docking/ ?"
echo "======================================================================"
git status --porcelain -- src/docking/

echo
echo "======================================================================"
echo "5) Historique de receptor_profile.py (renommages eventuels detectes par git)"
echo "======================================================================"
git log --follow --oneline -- src/docking/receptor_profile.py | head -10

echo
echo "======================================================================"
echo "6) receptor_profile.py est-il ignore par un .gitignore ?"
echo "======================================================================"
git check-ignore -v src/docking/receptor_profile.py 2>&1 || echo "(pas ignore)"

echo
echo "======================================================================"
echo "7) Ligne exacte de l'import dans vina_engine.py (autour de la ligne 43)"
echo "======================================================================"
sed -n '1,50p' src/docking/vina_engine.py | nl -ba -v1

echo
echo "======================================================================"
echo "8) Tous les fichiers de src/docking/ actuellement, local vs suivi par git"
echo "======================================================================"
echo "--- Sur disque ---"
ls -1 src/docking/*.py | sort
echo
echo "--- Suivis par git (HEAD) ---"
git ls-files -- 'src/docking/*.py' | sort

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
