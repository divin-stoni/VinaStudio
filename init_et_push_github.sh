#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
REMOTE_URL="https://github.com/divin-stoni/VinaStudio.git"

cd "$ROOT"

echo "=================================================="
echo "ETAPE 0 : verification de l'identite git"
echo "=================================================="
GIT_NAME="$(git config --get user.name 2>/dev/null || true)"
GIT_EMAIL="$(git config --get user.email 2>/dev/null || true)"
if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
    echo "ERREUR : identite git non configuree sur cette machine."
    echo "Lance d'abord (une seule fois) :"
    echo "  git config --global user.name \"Ton Nom\""
    echo "  git config --global user.email \"ton@email.com\""
    echo "Puis relance ce script."
    exit 1
fi
echo "OK : $GIT_NAME <$GIT_EMAIL>"

echo "=================================================="
echo "ETAPE 1 : initialisation du depot git"
echo "=================================================="
if [ -d .git ]; then
    echo "Deja un depot git ici, on continue."
else
    git init
    git branch -M main
    echo "Depot initialise (branche main)."
fi

echo "=================================================="
echo "ETAPE 2 : ajout de _archive_backups au .gitignore"
echo "=================================================="
if ! grep -qxF "_archive_backups/" .gitignore 2>/dev/null; then
    {
        echo ""
        echo "# Sauvegarde ponctuelle d'un ancien build complet (1.7 Go, fichiers >100 Mo)"
        echo "_archive_backups/"
    } >> .gitignore
    echo "Ajoute au .gitignore."
else
    echo "Deja present dans .gitignore."
fi

echo "=================================================="
echo "ETAPE 3 : mise en zone de staging (git add -A)"
echo "=================================================="
git add -A

echo "=================================================="
echo "ETAPE 4 : VERIFICATION STRICTE -- aucun fichier stage > 90 Mo"
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
    echo "ERREUR FATALE : fichier(s) volumineux dans le commit. Abandon."
    echo "Ajoute-les au .gitignore, puis relance ce script."
    git reset >/dev/null
    exit 1
fi
echo "OK : aucun fichier volumineux stage."

echo "=================================================="
echo "ETAPE 5 : premier commit"
echo "=================================================="
if git diff --cached --quiet; then
    echo "Rien a committer (deja a jour)."
else
    git commit -m "Version initiale : VinaStudio (docking, analyse, visualisation multi-recepteurs, phytomolecules, credits)"
fi

echo "=================================================="
echo "ETAPE 6 : ajout du remote GitHub"
echo "=================================================="
if git remote get-url origin >/dev/null 2>&1; then
    echo "Remote 'origin' deja configure : $(git remote get-url origin)"
else
    git remote add origin "$REMOTE_URL"
    echo "Remote ajoute : $REMOTE_URL"
fi

echo "=================================================="
echo "ETAPE 7 : push vers GitHub"
echo "=================================================="
echo "(Git peut demander tes identifiants GitHub ici -- utilise un"
echo " personal access token comme mot de passe, pas ton mot de passe"
echo " de compte, GitHub ne l'accepte plus en HTTPS.)"
git push -u origin main

echo "=================================================="
echo "TERMINE"
echo "=================================================="
echo "Le push vers main declenche automatiquement build-windows.yml."
echo "Suis la compilation ici :"
echo "  https://github.com/divin-stoni/VinaStudio/actions"
