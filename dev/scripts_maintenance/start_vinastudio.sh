#!/usr/bin/env bash
set -e

# Retourne à la racine du projet
cd "$(dirname "$0")/../.."

if [ "${1:-}" = "--headless" ]; then
    export QT_QPA_PLATFORM=offscreen
    shift
fi

# Utilise le venv situé à la racine
exec ./venv/bin/python run_gui.py "$@"

