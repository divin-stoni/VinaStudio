#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "ETAPE 1 : creation du .gitignore"
echo "=================================================="
cat > .gitignore << 'GITIGNORE'
# Environnement virtuel (jamais sur Git, trop lourd)
venv/
__pycache__/
*.pyc

# Builds locaux
build/
dist/
appimage_build/
squashfs-root/
*.spec

# Archives et paquets generes (trop lourds pour Git, iront en Release)
*.tar.gz
*.deb
*.AppImage

# Sauvegardes accumulees pendant le developpement
*.backup_*
*.bak
*.bak2
*_report.txt
*_log.txt
main.py.backup_*
translations.py.backup_*

# Donnees volumineuses generees (optionnel, a garder si tu veux les versionner)
docking/results/
GITIGNORE
echo "OK : .gitignore cree"

echo "=================================================="
echo "ETAPE 2 : statut Git actuel"
echo "=================================================="
if [ ! -d .git ]; then
    echo "Aucun depot Git, initialisation..."
    git init
else
    echo "Depot Git deja existant."
fi
git status --short | head -20
echo "(...)"
echo "Nombre total de fichiers qui seraient suivis :"
git add -A --dry-run | wc -l

echo "=================================================="
echo "ETAPE 3 : premier commit propre"
echo "=================================================="
git add -A
git commit -m "Version stable VINA Studio - avant packaging Windows" || echo "Rien de nouveau a commiter (peut-etre deja fait)"

echo "=================================================="
echo "TERMINE"
echo "Le depot local est pret. Etape suivante : creer le depot sur github.com"
echo "=================================================="
