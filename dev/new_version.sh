#!/usr/bin/env bash
# Usage : ./dev/new_version.sh 1.2.0
# Avant : ajoute une section "## 1.2.0" dans CHANGELOG.md
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."

NEW="${1:?Usage: $0 X.Y.Z}"
[[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Format invalide (attendu X.Y.Z)"; exit 1; }
git diff --quiet -- . ':!CHANGELOG.md' && git diff --cached --quiet -- . ':!CHANGELOG.md' \
  || { echo "Des fichiers sont modifiés : commite-les d'abord (sauf CHANGELOG.md)"; exit 1; }
git rev-parse "v$NEW" >/dev/null 2>&1 && { echo "Le tag v$NEW existe déjà"; exit 1; }

# Notes de la Release = section du CHANGELOG
awk -v v="## $NEW" '$0==v{f=1;next} /^## /{f=0} f' CHANGELOG.md > /tmp/notes_$NEW.md
[ -s /tmp/notes_$NEW.md ] || { echo "Ajoute d'abord une section '## $NEW' dans CHANGELOG.md"; exit 1; }

echo "$NEW" > VERSION
git add VERSION CHANGELOG.md
git commit -m "Version $NEW"
git tag -a "v$NEW" -m "Version $NEW"
git push && git push origin "v$NEW"      # GitHub construit l'installateur Windows

# Build Linux local
./build_deb_package.sh
./build_portable_archive.sh

FILES=()
for f in "vinastudio_${NEW}_amd64.deb" "VinaStudio-Linux-x86_64-${NEW}.tar.gz"; do
  for d in "$HOME/Desktop" "$PWD"; do
    [ -f "$d/$f" ] && { FILES+=("$d/$f"); break; }
  done
done
[ "${#FILES[@]}" -eq 2 ] || { echo "Fichiers Linux introuvables : ${FILES[*]:-aucun}"; exit 1; }

# Release (peut déjà exister : créée par le workflow Windows)
gh release view "v$NEW" >/dev/null 2>&1 \
  || gh release create "v$NEW" --title "VinaStudio $NEW" --notes-file /tmp/notes_$NEW.md
gh release edit "v$NEW" --notes-file /tmp/notes_$NEW.md
gh release upload "v$NEW" "${FILES[@]}" --clobber

echo "Terminé : https://github.com/divin-stoni/VinaStudio/releases/tag/v$NEW"
echo "L'installateur Windows s'ajoutera tout seul dans quelques minutes."
