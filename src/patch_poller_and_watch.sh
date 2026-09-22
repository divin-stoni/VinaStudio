#!/usr/bin/env bash
cd ~/MexAB_MexR_Analyzer_BETA/src || exit 1
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p ../_patch_backups
LOG=diag_3d_freeze_$STAMP.log
WATCH=/tmp/watchdog_dump_$STAMP.txt

python3 - << 'PYEOF'
import sys, shutil, py_compile, datetime
from pathlib import Path

MW = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui" / "main_window.py"
BK = MW.parent.parent.parent / "_patch_backups" / f"main_window.py.backup_poller_{datetime.datetime.now():%Y%m%d_%H%M%S}"
text = MW.read_text(encoding="utf-8")

if "QApplication.mouseButtons() == Qt.NoButton" in text:
    print("Poller deja patche. Rien a faire.")
    sys.exit(0)

OLD_A = "    def __init__(self, viewer_widget, interval_ms=16):"
NEW_A = "    def __init__(self, viewer_widget, interval_ms=33):"
OLD_B = "        self.viewer.page().runJavaScript(\"if (typeof viewer !== 'undefined') { viewer.render(); }\")"
NEW_B = (
    "        # Ne rend que pendant un vrai glisser de souris (sinon 60 appels JS/s\n"
    "        # en permanence saturent QtWebEngine et gelent l'interface).\n"
    "        if QApplication.mouseButtons() == Qt.NoButton:\n"
    "            return\n" + OLD_B
)

for label, old in (("intervalle", OLD_A), ("runJavaScript", OLD_B)):
    n = text.count(old)
    if n != 1:
        print(f"ECHEC bloc {label} : {n} occurrence(s) au lieu de 1. Rien modifie.")
        sys.exit(1)

shutil.copy2(MW, BK)
print("Sauvegarde :", BK)
MW.write_text(text.replace(OLD_A, NEW_A).replace(OLD_B, NEW_B), encoding="utf-8")
try:
    py_compile.compile(str(MW), doraise=True)
    print("py_compile : OK  (poller limite au glisser de souris, 33 ms)")
except Exception as exc:
    print("py_compile ECHEC :", exc)
    shutil.copy2(BK, MW)
    print("main_window.py restaure.")
    sys.exit(1)
PYEOF

cat > /tmp/run_with_watchdog.py << 'PYEOF'
import faulthandler, runpy, sys
watch = open(sys.argv[1], "w")
faulthandler.enable()                                   # segfault -> stderr
faulthandler.dump_traceback_later(10, repeat=True, file=watch)  # position des threads toutes les 10 s
sys.argv = ["main.py"]
runpy.run_path("main.py", run_name="__main__")
PYEOF

{
echo "=============== LANCEMENT : va sur la 3D, fais tourner / zoome / change de cible ==============="
echo "Si ca gele : attends ~20 s, puis Ctrl+C dans ce terminal."
timeout 600 python3 /tmp/run_with_watchdog.py "$WATCH" 2>&1 | grep -v "^Extension modules" | tail -60
echo ">>> code de sortie : ${PIPESTATUS[0]} (139 = segfault, 124 = timeout, 130 = Ctrl+C, 0 = fermeture normale)"

echo
echo "=============== DERNIERES POSITIONS DES THREADS (mouchard) ==============="
tail -60 "$WATCH"
} 2>&1 | tee "$LOG"

echo
echo "Log enregistré dans : $(pwd)/$LOG"
