#!/usr/bin/env bash
set -uo pipefail

# Ne regarde QUE le code de l'application elle-meme (ce qui peut etre
# reellement importe/execute au demarrage de run_gui.py), pas nos
# scripts de diagnostic/patch a la racine.
APP_DIRS="src docking run_gui.py docking_parser.py"

echo "======================================================================"
echo "1) Modules stdlib qui n'existent PAS sous Windows, importes dans l'app"
echo "   (provoqueraient un crash immediat au demarrage, comme ChimeraX)"
echo "======================================================================"
UNIX_ONLY="fcntl pwd grp termios tty curses resource syslog posix crypt spwd nis ossaudiodev"
FOUND_UNIX_ONLY=0
for mod in $UNIX_ONLY; do
    HITS=$(grep -rn -E "^\s*(import $mod\b|from $mod\b)" $APP_DIRS 2>/dev/null)
    if [[ -n "$HITS" ]]; then
        echo "--- $mod ---"
        echo "$HITS"
        FOUND_UNIX_ONLY=1
    fi
done
if [[ "$FOUND_UNIX_ONLY" -eq 0 ]]; then
    echo "Aucun module Unix-only importe dans le code de l'app. OK."
fi

echo
echo "======================================================================"
echo "2) Appels a os.fork / os.setsid / os.uname / signal Unix-only dans l'app"
echo "======================================================================"
grep -rn -E "os\.fork\(|os\.setsid\(|os\.uname\(|signal\.SIGHUP|signal\.SIGCHLD|os\.geteuid|os\.getuid" $APP_DIRS 2>/dev/null || echo "Aucun trouve. OK."

echo
echo "======================================================================"
echo "3) Chemins codes en dur /usr/, /tmp/, /home/, /etc/ dans le code de l'app"
echo "   (hors shebang '#!/usr/bin/env python3', qui est inoffensif)"
echo "======================================================================"
grep -rn -E "['\"]\s*/(usr|tmp|home|etc)/[a-zA-Z0-9_/.-]*['\"]" $APP_DIRS 2>/dev/null | grep -v "^\S*:1:#!/usr/bin/env"

echo
echo "======================================================================"
echo "4) Utilisation de '/tmp' pour des fichiers temporaires (Windows n'a pas /tmp)"
echo "======================================================================"
grep -rn '"/tmp\|'"'"'/tmp' $APP_DIRS 2>/dev/null || echo "Aucun /tmp code en dur. OK (le code doit utiliser tempfile.gettempdir() ou tempfile.mkdtemp())."

echo
echo "======================================================================"
echo "5) Rappel : le code utilise-t-il bien tempfile pour les dossiers temporaires ?"
echo "======================================================================"
grep -rln "tempfile\." $APP_DIRS 2>/dev/null | head -10

echo
echo "======================================================================"
echo "6) Separateurs de chemin ecrits en dur avec '/' dans des f-strings/concat"
echo "   (fonctionne sur Windows via Path, mais signale les concatenations"
echo "   manuelles de type chaine + '/' + chaine, plus fragiles)"
echo "======================================================================"
grep -rn -E '"[a-zA-Z_]+/" *\+|"\/" *\+ *[a-zA-Z_]' $APP_DIRS 2>/dev/null | grep -v "\.pyc" | head -20

echo
echo "======================================================================"
echo "7) Tous les dossiers de donnees reellement ouverts/lus par le code"
echo "   (Path(...) / \"nom_dossier\"), pour re-verifier contre le workflow Windows"
echo "======================================================================"
grep -rhoE 'Path\([^)]*\)\s*/\s*"[a-zA-Z0-9_]+"' $APP_DIRS 2>/dev/null | sort -u | head -40

echo
echo "======================================================================"
echo "8) sys.platform / platform.system() -- ou le code gere DEJA le multi-OS"
echo "   (bon signe : la ou c'est present, quelqu'un a deja pense a Windows)"
echo "======================================================================"
grep -rln -E "sys\.platform|platform\.system\(\)" $APP_DIRS 2>/dev/null

echo
echo "======================================================================"
echo "FIN"
echo "======================================================================"
