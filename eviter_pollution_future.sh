#!/usr/bin/env bash
set -euo pipefail

TS=$(date +%Y%m%d_%H%M%S)
cp .gitignore ".gitignore.bak_${TS}"

cat >> .gitignore << 'EOF'

# Scripts de diagnostic/patch ponctuels (session de debug) -- ne pas
# suivre par defaut. Un script vraiment utile a garder doit etre
# deplace explicitement dans dev/ ou dev/archive_patchs_diagnostics/
# et ajoute avec 'git add -f'.
/diag_*.sh
/diag_*.py
/diagnose_*.py
/diagnostic_*.py
/trouver_*.sh
/verif_*.sh
/audit_*.sh
/audit_*.py
/fix_*.sh
/fix_*.py
/patch_*.py
/patch[0-9]*_*.py
*.bak_*
*_output.txt
EOF

echo "Regle ajoutee a .gitignore (backup : .gitignore.bak_${TS})"
echo
echo "--- Nouvelles lignes ajoutees ---"
tail -18 .gitignore
