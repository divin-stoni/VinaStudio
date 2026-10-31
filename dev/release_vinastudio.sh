#!/usr/bin/env bash
# Release locale VINA Studio : verification, build Linux, installation locale,
# paquets versionnes et publication GitHub (le workflow GitHub construit Windows).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

usage() {
    cat <<'USAGE'
Usage:
  bash dev/release_vinastudio.sh VERSION [--push]

VERSION doit etre une nouvelle version semver, par exemple 1.1.3.
Sans --push, le build et l'installation locale sont effectues mais aucun
commit, tag ou push GitHub n'est realise.
USAGE
}

[[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
VERSION="$1"
PUSH=false
[[ "${2:-}" == "--push" ]] && PUSH=true
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || {
    echo "ERREUR : version invalide : $VERSION" >&2
    exit 2
}

PY="$PROJECT_ROOT/venv/bin/python"
[[ -x "$PY" ]] || PY=python3
PYI="$PROJECT_ROOT/venv/bin/pyinstaller"

step() {
    echo
    echo "=================================================="
    echo "$1"
    echo "=================================================="
}

die() {
    echo "ERREUR : $1" >&2
    exit 1
}

step "1. Preparation de la version $VERSION"
CURRENT_VERSION="$(tr -d '[:space:]' < VERSION)"
[[ "$VERSION" != "$CURRENT_VERSION" ]] || die "VERSION est deja $VERSION ; choisis une nouvelle version"
git diff --check || die "espaces ou conflits detectes par git diff --check"
printf '%s\n' "$VERSION" > VERSION
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    die "le tag v$VERSION existe deja"
fi

step "2. Verification du code et tests"
python_files=(
    src/docking/receptor_profile.py
    src/gui/main_window.py
    src/gui/quick_themes.py
    src/reference_inhibitors.py
    src/translations.py
)
for file in "${python_files[@]}"; do
    "$PY" -m py_compile "$file" || die "syntaxe invalide : $file"
done
QT_QPA_PLATFORM=offscreen "$PY" -m pytest -q || die "les tests ont echoue"

step "3. Nettoyage cible des anciens artefacts compiles"
# Seules les sorties explicitement generees par les scripts de release sont
# supprimees. Les profils, rapports, sauvegardes et donnees utilisateur restent.
rm -rf "$PROJECT_ROOT/src/build" "$PROJECT_ROOT/src/dist" "$PROJECT_ROOT/dist"
find "$HOME/Desktop" -maxdepth 1 -type f \( \
    -name 'vinastudio_*_amd64.deb' -o \
    -name 'VinaStudio-Linux-x86_64-*.tar.gz' \
\) -delete 2>/dev/null || true
find "$PROJECT_ROOT" -maxdepth 1 -type f \( \
    -name 'vinastudio_*_amd64.deb' -o \
    -name 'VinaStudio-Linux-x86_64-*.tar.gz' \
\) -delete

step "4. Compilation Linux avec PyInstaller"
[[ -x "$PYI" ]] || die "PyInstaller absent : $PYI"
(cd src && "$PYI" --noconfirm VinaStudio.spec) || die "PyInstaller"
[[ -x src/dist/VinaStudio/VinaStudio ]] || die "executable Linux absent apres le build"

step "5. Installation locale de cette version"
mkdir -p dist
cp -a src/dist/VinaStudio dist/VinaStudio
bash dev/scripts_maintenance/install_vinastudio_local.sh

step "6. Generation des paquets Linux"
bash build_deb_package.sh
bash build_portable_archive.sh
DEB="$HOME/Desktop/vinastudio_${VERSION}_amd64.deb"
TGZ="$HOME/Desktop/VinaStudio-Linux-x86_64-${VERSION}.tar.gz"
[[ -f "$DEB" ]] || die ".deb absent : $DEB"
[[ -f "$TGZ" ]] || die "archive absente : $TGZ"
cp -f "$DEB" "$TGZ" .
sha256sum "$DEB" "$TGZ"

step "7. Commit et publication GitHub"
git add VERSION \
    .github/workflows/build-windows.yml VinaStudio.iss \
    dev/release_vinastudio.sh dev/scripts_maintenance/install_vinastudio_local.sh \
    build_portable_archive.sh \
    src/docking/receptor_profile.py src/gui/main_window.py \
    src/gui/quick_themes.py src/gui/viewer_template.py \
    src/reference_inhibitors.py src/translations.py \
    image_theme _corbeille_theme_images
git diff --cached --check || die "erreur de format dans les fichiers prepares"
git diff --cached --quiet && die "aucune modification de release a committer"
git commit -m "release: VinaStudio $VERSION"
git tag -a "v$VERSION" -m "VinaStudio $VERSION"

if [[ "$PUSH" == true ]]; then
    git fetch origin
    [[ "$(git rev-list --count HEAD..origin/main)" == 0 ]] || die "origin/main contient des commits absents localement"
    git push origin main
    git push origin "v$VERSION"
    echo "Publication terminee : https://github.com/divin-stoni/VinaStudio/releases"
else
    echo "Build termine sans push. Pour publier : git push origin main && git push origin v$VERSION"
fi

echo
echo "Version installee : $VERSION"
echo ".deb : $DEB"
echo "Archive : $TGZ"
echo "Le .exe Windows sera produit par GitHub Actions sur le tag v$VERSION."
