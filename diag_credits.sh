#!/usr/bin/env bash
ROOT="${ROOT:-$HOME/MexAB_MexR_Analyzer_BETA}"
cd "$ROOT" || exit 1
LOG=diag_credits_$(date +%Y%m%d_%H%M%S).log

cat > /tmp/diag_credits.py << 'PYEOF'
import os, sys, collections, subprocess, shutil, re
from pathlib import Path

ROOT = Path(os.environ["ROOT"])
CRED = ROOT / "credit_du_logiciel"
IMG = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".avif"}
VID = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg"}
TXT = {".txt", ".md", ".json", ".csv", ".yaml", ".yml"}

def human(n):
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or u == "Go":
            return f"{n:.1f} {u}"
        n /= 1024

print("=============== 1. DOSSIER ===============")
print("Chemin :", CRED, "| existe :", CRED.exists())
if not CRED.exists():
    sys.exit(0)

files = []
dirs = []
for dp, dn, fn in os.walk(CRED):
    dn.sort()
    rel = Path(dp).relative_to(CRED)
    dirs.append((rel, len(fn)))
    for f in sorted(fn):
        p = Path(dp) / f
        try:
            files.append((p, p.stat().st_size))
        except OSError:
            pass

tot = sum(s for _, s in files)
print(f"{len(files)} fichiers, {len(dirs)-1} sous-dossiers, taille totale {human(tot)}")

print("\n=============== 2. EXTENSIONS ===============")
ext = collections.Counter(p.suffix.lower() for p, _ in files)
esize = collections.Counter()
for p, s in files:
    esize[p.suffix.lower()] += s
for e, c in ext.most_common():
    kind = "image" if e in IMG else "video" if e in VID else "texte" if e in TXT else "autre"
    print(f"{e or '(aucune)':10s} x{c:5d}  {human(esize[e]):>10s}  [{kind}]")

print("\n=============== 3. SOUS-DOSSIERS (ordre alphabetique) ===============")
for rel, n in dirs:
    d = CRED / rel
    fs = [p for p, _ in files if p.parent == d]
    ni = sum(1 for p in fs if p.suffix.lower() in IMG)
    nv = sum(1 for p in fs if p.suffix.lower() in VID)
    sz = sum(p.stat().st_size for p in fs)
    name = str(rel) if str(rel) != "." else "(racine)"
    print(f"- {name!r:45s} images={ni:4d} videos={nv:3d} autres={len(fs)-ni-nv:3d}  {human(sz)}")

print("\n=============== 4. EXEMPLES DE NOMS DE FICHIERS (8 premiers par dossier) ===============")
for rel, n in dirs:
    d = CRED / rel
    names = sorted(p.name for p, _ in files if p.parent == d)[:8]
    if names:
        print(f"[{rel}] {names}")

print("\n=============== 5. 15 PLUS GROS FICHIERS ===============")
for p, s in sorted(files, key=lambda x: -x[1])[:15]:
    print(f"{human(s):>10s}  {p.relative_to(CRED)}")

print("\n=============== 6. IMAGES : dimensions ===============")
try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    big = []; sizes = collections.Counter(); animated = 0; fails = []
    for p, s in files:
        if p.suffix.lower() in IMG:
            try:
                with Image.open(p) as im:
                    w, h = im.size
                    sizes["> 4000 px"] += (max(w, h) > 4000)
                    sizes["2000-4000 px"] += (2000 < max(w, h) <= 4000)
                    sizes["<= 2000 px"] += (max(w, h) <= 2000)
                    if getattr(im, "is_animated", False):
                        animated += 1
                    if max(w, h) > 4000:
                        big.append((w, h, p.relative_to(CRED)))
            except Exception as e:
                fails.append((p.relative_to(CRED), repr(e)[:60]))
    print(dict(sizes), "| animees :", animated, "| illisibles :", len(fails))
    for w, h, r in big[:10]:
        print(f"  grande image {w}x{h}  {r}")
    for r, e in fails[:10]:
        print("  ILLISIBLE", r, e)
except ImportError:
    print("Pillow absent : dimensions non lues.")

print("\n=============== 7. VIDEOS (ffprobe) ===============")
ffprobe = shutil.which("ffprobe")
print("ffprobe :", ffprobe or "ABSENT (sudo apt install ffmpeg pour l'avoir)")
vids = [(p, s) for p, s in files if p.suffix.lower() in VID]
print(f"{len(vids)} video(s), total {human(sum(s for _, s in vids))}, plus grosse {human(max((s for _, s in vids), default=0))}")
if ffprobe:
    codecs = collections.Counter()
    for p, s in vids[:60]:
        try:
            out = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                 "stream=codec_name,width,height:format=duration", "-of", "default=nw=1", str(p)],
                capture_output=True, text=True, timeout=20).stdout
            d = dict(l.split("=", 1) for l in out.split() if "=" in l)
            codecs[d.get("codec_name", "?")] += 1
            dur = float(d.get("duration", 0) or 0)
            print(f"  {p.relative_to(CRED)}  {d.get('codec_name')} {d.get('width')}x{d.get('height')}  {dur:.0f}s  {human(s)}")
        except Exception as e:
            print("  ffprobe echec", p.name, repr(e)[:50])
    print("Codecs :", dict(codecs))

print("\n=============== 8. FICHIERS TEXTE / LEGENDES DEJA PRESENTS ===============")
for p, s in files:
    if p.suffix.lower() in TXT:
        print(f"  {p.relative_to(CRED)} ({human(s)})")
        try:
            print("    ", p.read_text(encoding="utf-8", errors="ignore")[:200].replace("\n", " | "))
        except Exception:
            pass

print("\n=============== 9. NOMS PROBLEMATIQUES ===============")
odd = [p.relative_to(CRED) for p, _ in files if re.search(r"[^\w\-. ()àâäçéèêëîïôöùûüÿœÀÉÈ]", p.name)]
print(len(odd), "nom(s) avec caracteres speciaux", odd[:8])
hidden = [p.relative_to(CRED) for p, _ in files if p.name.startswith(".")]
print(len(hidden), "fichier(s) caches", hidden[:8])

print("\n=============== 10. OUTILS PYTHON / QT ===============")
print("Python :", sys.version.split()[0])
for mod in ("PIL", "cryptography", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"):
    try:
        __import__(mod)
        print(f"  {mod:32s} OK")
    except Exception as e:
        print(f"  {mod:32s} ABSENT ({repr(e)[:60]})")
try:
    from PySide6.QtMultimedia import QMediaFormat
    mf = QMediaFormat()
    print("  Formats video lus par Qt :", [str(f).split('.')[-1] for f in mf.supportedFileFormats(QMediaFormat.Decode)][:15])
except Exception as e:
    print("  QMediaFormat indisponible :", repr(e)[:80])

print("\n=============== 11. INTEGRATION DANS LE PROJET ===============")
mw = ROOT / "src" / "gui" / "main_window.py"
t = mw.read_text(encoding="utf-8")
for label, needle in (
    ("boucle des onglets", 'for index, text in enumerate(["Docking", "Analyse", "Visualisation"]):'),
    ("page visualisation ajoutee au workspace", "self.workspace.addWidget(\n            self.visualization_page\n        )"),
    ("liste des noms switch_primary", '"Visualisation",\n        ]\n\n        if 0 <= index'),
    ("presence 'credit' dans main_window", "credit"),
):
    print(f"  {label:45s}: {t.count(needle)} occurrence(s)")
print("  fichiers src/gui :", sorted(x.name for x in (ROOT/'src'/'gui').glob('*.py')))

print("\n=============== 12. GIT / PACKAGING ===============")
def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT).stdout.strip()
print("git check-ignore :", run("git check-ignore -v credit_du_logiciel || echo '(NON ignore : les medias iraient sur GitHub !)'"))
print("fichiers suivis par git dans credit_du_logiciel :", run("git ls-files credit_du_logiciel | wc -l"))
for f in ("VinaStudio.spec", "VinaStudio.iss", "build_deb_final.sh", ".gitignore"):
    pth = ROOT / f
    if pth.exists():
        print(f"  {f}: mentions 'credit' -> {pth.read_text(errors='ignore').lower().count('credit')}")
PYEOF

ROOT="$ROOT" python3 /tmp/diag_credits.py 2>&1 | tee "$LOG"
echo
echo "Log enregistré dans : $ROOT/$LOG"
