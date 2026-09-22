#!/usr/bin/env bash
set -euo pipefail

echo "======================================================================"
echo "1) Sauvegarde de .gitignore avant modification"
echo "======================================================================"
cp .gitignore .gitignore.bak_$(date +%Y%m%d_%H%M%S)
echo "Backup cree."

echo
echo "======================================================================"
echo "2) Ligne exacte a retirer (contexte +-2 lignes)"
echo "======================================================================"
grep -n "credit_du_logiciel" .gitignore

echo
echo "======================================================================"
echo "3) Suppression de la ligne 'credit_du_logiciel/' du .gitignore"
echo "======================================================================"
sed -i '/^credit_du_logiciel\/$/d' .gitignore
echo "Ligne supprimee. Verification qu'il n'en reste plus :"
grep -n "credit_du_logiciel" .gitignore || echo "(plus aucune reference -- OK)"

echo
echo "======================================================================"
echo "4) Ajout du dossier a l'index git"
echo "======================================================================"
git add .gitignore
git add credit_du_logiciel

echo
echo "======================================================================"
echo "5) ETAT AVANT COMMIT -- VERIFIE CETTE LISTE AVANT DE CONTINUER"
echo "======================================================================"
git status
echo
echo "Nombre de fichiers ajoutes sous credit_du_logiciel :"
git diff --cached --stat -- credit_du_logiciel | tail -5

echo
echo "======================================================================"
echo "RIEN N'A ETE COMMIT NI POUSSE. Si la liste ci-dessus est correcte :"
echo "  git commit -m \"Fix: credit_du_logiciel etait exclu par erreur du .gitignore\""
echo "  git push origin main"
echo "======================================================================"
