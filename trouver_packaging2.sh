#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/MexAB_MexR_Analyzer_BETA}"

show() {
    local f="$1"
    echo "############################################################"
    echo "# $f ($(wc -l < "$f" 2>/dev/null || echo '?') lignes)"
    echo "############################################################"
    if [ -f "$f" ]; then
        nl -ba "$f"
    else
        echo "(absent)"
    fi
    echo
}

show "$ROOT/src/VinaStudio.spec"
show "$ROOT/patch_spec_datas.sh"
show "$ROOT/build_deb_final.sh"
show "$ROOT/build_and_package_v2.sh"
show "$ROOT/build_portable_archive.sh"
