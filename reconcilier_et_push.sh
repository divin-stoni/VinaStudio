#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/MexAB_MexR_Analyzer_BETA"

echo "=================================================="
echo "ETAPE 1 : verification de la branche courante"
echo "=================================================="
CURRENT_BRANCH=$(git branch --show-current)
echo "Branche courante : $CURRENT_BRANCH"
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "ERREUR : attendu 'main', trouve '$CURRENT_BRANCH'. Abandon par securite."
    exit 1
fi

echo "=================================================="
echo "ETAPE 2 : reset souple sur origin/main"
echo "(deplace juste le pointeur de branche -- ne touche"
echo " NI a l'index NI au contenu du disque)"
echo "=================================================="
git reset --soft origin/main

echo "=================================================="
echo "ETAPE 3 : etat apres reset (doit lister un gros diff 'a committer')"
echo "=================================================="
TOTAL=$(git status --short | wc -l)
git status --short | head -20
echo "... ($TOTAL entree(s) au total)"

echo "=================================================="
echo "ETAPE 4 : RE-VERIFICATION -- aucun fichier stage > 90 Mo"
echo "=================================================="
BIG_FOUND=0
while IFS= read -r -d '' f; do
    if [ -f "$f" ]; then
        size_mb=$(du -m "$f" | cut -f1)
        if [ "$size_mb" -gt 90 ]; then
            echo "TROP GROS ($size_mb Mo) : $f"
            BIG_FOUND=1
        fi
    fi
done < <(git diff --cached --name-only -z)

if [ "$BIG_FOUND" -eq 1 ]; then
    echo "ERREUR FATALE : fichier(s) volumineux detectes. Abandon."
    exit 1
fi
echo "OK : aucun fichier volumineux."

echo "=================================================="
echo "ETAPE 5 : nouveau commit au-dessus du veritable historique"
echo "=================================================="
if git diff --cached --quiet; then
    echo "Rien a committer -- deja a jour avec origin/main."
else
    git commit -m "Ajout Credits (dock vertical, lien depuis A propos, coupure video), fix multi-recepteurs (visualisation), packaging .deb/tar.gz + build Windows a jour (i18n, credit_du_logiciel)"
fi

echo "=================================================="
echo "ETAPE 6 : push (fast-forward, plus de rejet attendu)"
echo "=================================================="
git push origin main

echo "=================================================="
echo "TERMINE"
echo "=================================================="
echo "Historique complet preserve (32 commits + tags), avec le nouveau"
echo "commit au sommet. Suivi du build Windows :"
echo "  https://github.com/divin-stoni/VinaStudio/actions"
