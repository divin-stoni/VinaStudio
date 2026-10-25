#!/bin/bash
# Publication de VinaStudio : verifications, commit, compilation Linux
# (.deb et .tar.gz), puis push GitHub (declenche la compilation Windows).
# A lancer depuis n'importe ou : bash release_vinastudio.sh
set -uo pipefail
PROJ="$HOME/MexAB_MexR_Analyzer_BETA"
cd "$PROJ" || exit 1
STAMP=$(date +%Y%m%d_%H%M%S)
MARK=$(mktemp)
PY="$PROJ/venv/bin/python"; [ -x "$PY" ] || PY=python3
step(){ echo; echo "=================================================="; echo "$1"; echo "=================================================="; }
die(){ echo "ERREUR : $1"; exit 1; }
FILES="src/gui/main_window.py src/gui/viewer_template.py src/gui/phyto_page.py src/phyto_api.py src/residue_center.py src/translations.py"

step "1. Verification du code"
for k in "residue_block:src/gui/main_window.py" "_couple_receptors_dialog:src/gui/main_window.py" "split_sdf_by_cid:src/gui/phyto_page.py" "PROTEIN_COLOR:src/gui/viewer_template.py"; do
  pat=${k%%:*}; f=${k##*:}
  grep -q "$pat" "$f" || die "patch absent : $pat dans $f"
done
for f in $FILES; do "$PY" -m py_compile "$f" || die "syntaxe $f"; done
QT_QPA_PLATFORM=offscreen "$PY" -c "import src.gui.main_window, src.gui.phyto_page" || die "import des modules"
echo "OK"

step "2. Tests (resume)"
QT_QPA_PLATFORM=offscreen timeout 300 "$PY" -m pytest -q 2>&1 | tail -8

step "3. Commit local (fichiers de code uniquement)"
git add $FILES
git commit -q -m "feat: couplage de récepteurs, centrage sur résidu, noms de fichiers SDF par CID" \
  -m "- téléchargement SDF 3D PubChem avec repli 2D vers 3D local, saisie nom ou CID
- fichiers SDF nommés par CID avec index CSV
- récepteurs importés : configuration enregistrée et réutilisée
- bouton Coupler deux récepteurs, import individuel uniquement
- visualiseur : protéine d'une couleur, grid box épaisse
- champ de centrage de la grid box sur un résidu de référence" || echo "(rien de nouveau a committer)"
[ -z "$(git status --short -- $FILES)" ] || die "commit echoue (git config user.name / user.email ?)"
git log --oneline -3

step "4. Compilation Linux (PyInstaller)"
[ -f src/VinaStudio.spec ] || die "src/VinaStudio.spec introuvable"
[ -f dev/scripts_maintenance/install_vinastudio_local.sh ] || die "install_vinastudio_local.sh introuvable"
rm -rf src/build src/dist
PYI="$PROJ/venv/bin/pyinstaller"; [ -x "$PYI" ] || PYI="$PY -m PyInstaller"
( cd src && $PYI --noconfirm VinaStudio.spec ) || die "PyInstaller"
[ -f src/dist/VinaStudio/VinaStudio ] || die "executable absent apres le build"
if grep -rq "residue_center" src/build/VinaStudio 2>/dev/null; then echo "module residue_center inclus dans le build"; else echo "ATTENTION : residue_center non detecte dans le build"; fi
[ -d src/dist/VinaStudio/credit_du_logiciel ] || cp -r credit_du_logiciel src/dist/VinaStudio/credit_du_logiciel

step "5. Paquets .deb et archive compressee"
DEB="$HOME/Desktop/vinastudio_1.0.3_amd64.deb"
TGZ="$HOME/Desktop/VinaStudio-Linux-x86_64-1.0.3.tar.gz"
mkdir -p "$HOME/Desktop" "_archive_backups/releases_$STAMP"
for f in "$DEB" "$TGZ" "$PROJ/vinastudio_1.0.3_amd64.deb" "$PROJ/VinaStudio-Linux-x86_64-1.0.3.tar.gz"; do
  [ -f "$f" ] && mv "$f" "_archive_backups/releases_$STAMP/$(basename "$(dirname "$f")")_$(basename "$f")"
done
bash build_deb_final.sh || die "build_deb_final.sh"
[ "$DEB" -nt "$MARK" ] || { bash build_deb_package.sh || die "build_deb_package.sh"; }
bash build_portable_archive.sh || die "build_portable_archive.sh"
[ "$DEB" -nt "$MARK" ] || die "le .deb n'a pas ete regenere"
[ "$TGZ" -nt "$MARK" ] || die "l'archive n'a pas ete regeneree"
cp -f "$DEB" "$TGZ" "$PROJ/"
echo; ls -lh "$PROJ/vinastudio_1.0.3_amd64.deb" "$PROJ/VinaStudio-Linux-x86_64-1.0.3.tar.gz"
sha256sum "$PROJ/vinastudio_1.0.3_amd64.deb" "$PROJ/VinaStudio-Linux-x86_64-1.0.3.tar.gz"

step "6. Push GitHub (declenche la compilation Windows)"
git fetch -q origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && die "le depot distant a $BEHIND commit(s) absents en local : fais d'abord git pull --rebase"
git push origin main || die "push (identifiants GitHub ou reseau)"
echo
echo "TERMINE."
echo "Windows : https://github.com/divin-stoni/VinaStudio/actions (l'.exe sera dans les artifacts du run)"
echo "Linux   : $PROJ/vinastudio_1.0.3_amd64.deb et $PROJ/VinaStudio-Linux-x86_64-1.0.3.tar.gz (copies sur le Bureau)"
