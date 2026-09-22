#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-$HOME/MexAB_MexR_Analyzer_BETA/src/gui/main_window.py}"

sed -n '9508,10011p' "$FILE" | nl -ba -v 9508
