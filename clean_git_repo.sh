#!/bin/bash
set -e

PROJECT_ROOT="$HOME/MexAB_MexR_Analyzer_BETA"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "ETAPE 1 : .gitignore corrige et complet"
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
src.zip

# Sauvegardes accumulees pendant le developpement (tous formats rencontres)
*.backup_*
*.bak
*.bak2
*.bak_*
*_before_*
*.indent_backup
*.v1_backup
*(Copie)*
*_report.txt
*_log.txt

# Doublons / fichiers generes a la racine deja presents dans src/
/visualization_bridge.py

# Donnees de test / resultats generes (pas la reference officielle)
*_test.csv
docking_results_combined.csv
analysis_ready.csv

# Donnees volumineuses generees (optionnel, a garder si tu veux les versionner)
docking/results/
GITIGNORE
echo "OK : .gitignore corrige"

echo "=================================================="
echo "ETAPE 2 : retrait des fichiers indesirables du suivi Git"
echo "(ils restent sur ton disque, juste plus suivis par Git)"
echo "=================================================="
git rm -r --cached \
  src/gui/main_window.py.bak_20260907_044242 \
  src/gui/main_window.py.bak_20260907_044738 \
  src/gui/main_window.py.bak_20260907_045107 \
  src/gui/main_window.py.bak_20260907_045720 \
  src/gui/main_window_before_double_config_fix.py \
  "src/gui/main_window_before_menu_toolbar_fix_20260907_061201.py" \
  src/gui/main_window_before_real_results.py \
  src/gui/main_window_before_results_csv_fix.py \
  src/gui/main_window_before_results_path_fix.py \
  src/gui/main_window_before_results_refresh.py \
  src/gui/main_window_before_results_table_fix.py \
  src/gui/main_window_before_stats_sync_fix.py \
  "src/visualization/plip_runner (Copie).py" \
  src/visualization/plip_runner.py.indent_backup \
  src/visualization/plip_runner.py.v1_backup \
  src.zip \
  visualization_bridge.py \
  docking_results_combined.csv \
  analysis_ready.csv \
  reference_data/scores_fusionnes_global_test.csv \
  reference_data/scores_fusionnes_test.csv \
  2>&1 | grep -v "^rm '" || true

echo "OK : fichiers retires du suivi (toujours presents sur le disque)"

echo "=================================================="
echo "ETAPE 3 : verification qu'il ne reste rien d'indesirable"
echo "=================================================="
git status --short

echo "=================================================="
echo "ETAPE 4 : commit d'amend (remplace le commit racine, historique propre)"
echo "=================================================="
git add -A
git commit --amend -m "Version stable VINA Studio - avant packaging Windows"

echo "=================================================="
echo "ETAPE 5 : verification finale du contenu suivi"
echo "=================================================="
echo "Fichiers suivis par Git (doit etre propre, sans .bak/_before_/test/etc.) :"
git ls-files | grep -E '\.bak|_before_|test\.csv|indent_backup|v1_backup|Copie|src\.zip' && echo "ATTENTION : des fichiers indesirables sont encore suivis !" || echo "OK : rien d'indesirable detecte."

echo "=================================================="
echo "TERMINE"
echo "Historique propre. Etape suivante : creer le depot sur github.com/new"
echo "=================================================="
