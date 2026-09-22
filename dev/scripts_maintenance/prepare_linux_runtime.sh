#!/bin/bash
set -e

echo "=== Nettoyage des anciens dossiers runtime ==="
rm -rf docking/bin obabel_runtime runtime_libs
mkdir -p docking/bin
mkdir -p obabel_runtime/bin
mkdir -p obabel_runtime/share/openbabel
mkdir -p obabel_runtime/lib/openbabel
mkdir -p runtime_libs

echo "=== Copie des binaires ==="
cp /usr/bin/vina docking/bin/vina
cp /usr/bin/obabel obabel_runtime/bin/obabel
chmod +x docking/bin/vina obabel_runtime/bin/obabel

echo "=== Copie des bibliotheques partagees (avec noms SONAME corrects) ==="
cp -L /usr/lib/x86_64-linux-gnu/libboost_thread.so.1.88.0 runtime_libs/
cp -L /usr/lib/x86_64-linux-gnu/libboost_filesystem.so.1.88.0 runtime_libs/
cp -L /usr/lib/x86_64-linux-gnu/libboost_program_options.so.1.88.0 runtime_libs/
cp -L /usr/lib/x86_64-linux-gnu/libopenbabel.so.7.0.0 runtime_libs/libopenbabel.so.7
cp -L /usr/lib/x86_64-linux-gnu/libinchi.so.1.07 runtime_libs/libinchi.so.1.07
cp -L /usr/lib/x86_64-linux-gnu/libmaeparser.so.1.3.3 runtime_libs/libmaeparser.so.1

echo "=== Copie des plugins de formats OpenBabel ==="
cp /usr/lib/x86_64-linux-gnu/openbabel/3.1.1/*.so obabel_runtime/lib/openbabel/

echo "=== Copie des donnees OpenBabel (forcefields, tables, etc.) ==="
cp -r /usr/share/openbabel/3.1.1/* obabel_runtime/share/openbabel/

echo ""
echo "=== Verification ==="
echo "-- vina --"; ls -la docking/bin/
echo "-- obabel --"; ls -la obabel_runtime/bin/
echo "-- runtime_libs --"; ls -la runtime_libs/
echo "-- plugins obabel --"; ls obabel_runtime/lib/openbabel/ | wc -l
echo "-- donnees obabel --"; ls obabel_runtime/share/openbabel/ | wc -l

echo ""
echo "TERMINE : dossiers prets a etre embarques dans le .spec"
