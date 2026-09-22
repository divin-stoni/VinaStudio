#!/usr/bin/env bash
set -uo pipefail

echo "======================================================================"
echo "1) Le dossier existe-t-il localement ?"
echo "======================================================================"
ls -la credit_du_logiciel 2>&1 | head -5

echo
echo "======================================================================"
echo "2) Est-il suivi par git (index local) ?"
echo "======================================================================"
git ls-files -- credit_du_logiciel | head -20
COUNT_TRACKED=$(git ls-files -- credit_du_logiciel | wc -l)
echo "Nombre de fichiers suivis sous credit_du_logiciel : $COUNT_TRACKED"

echo
echo "======================================================================"
echo "3) Est-il ignore par un .gitignore quelque part ?"
echo "======================================================================"
git check-ignore -v credit_du_logiciel 2>&1
git check-ignore -v credit_du_logiciel/captions.json 2>&1
echo "(si rien ne s'affiche ci-dessus : pas ignore)"

echo
echo "======================================================================"
echo "4) Y a-t-il des fichiers non commites (git status) dans ce dossier ?"
echo "======================================================================"
git status --porcelain -- credit_du_logiciel

echo
echo "======================================================================"
echo "5) Est-il present dans le dernier commit LOCAL (HEAD) ?"
echo "======================================================================"
git show --stat HEAD -- credit_du_logiciel | head -20

echo
echo "======================================================================"
echo "6) Est-il present sur origin/main (l'etat reellement sur GitHub) ?"
echo "======================================================================"
git fetch origin main --quiet
echo "--- Fichiers sous credit_du_logiciel dans origin/main ---"
git ls-tree -r --name-only origin/main -- credit_du_logiciel | head -20
COUNT_REMOTE=$(git ls-tree -r --name-only origin/main -- credit_du_logiciel | wc -l)
echo "Nombre de fichiers sous credit_du_logiciel dans origin/main : $COUNT_REMOTE"

echo
echo "======================================================================"
echo "7) Comparaison locale HEAD vs origin/main sur ce dossier"
echo "======================================================================"
git diff --stat HEAD origin/main -- credit_du_logiciel

echo
echo "======================================================================"
echo "8) Taille totale du dossier (verifier une limite GitHub eventuelle)"
echo "======================================================================"
du -sh credit_du_logiciel 2>&1
find credit_du_logiciel -type f -size +50M -exec ls -lh {} \; 2>&1
echo "(GitHub bloque tout fichier individuel > 100 Mo sans Git LFS, avertit des 50 Mo)"

echo
echo "======================================================================"
echo "FIN DU DIAGNOSTIC"
echo "======================================================================"
