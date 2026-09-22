import ast, re
from pathlib import Path
from collections import defaultdict

MW = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui" / "main_window.py"
text = MW.read_text(encoding="utf-8")
lines = text.splitlines()
tree = ast.parse(text)

def lum(r, g, b):
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

def show(node, label, cap=220):
    seg = lines[node.lineno - 1:node.end_lineno]
    print(f"\n----- {label} {node.name} (lignes {node.lineno}-{node.end_lineno}) -----")
    print("\n".join(seg[:cap]))
    if len(seg) > cap:
        print(f"... [{len(seg) - cap} lignes omises]")

print("=============== 1. CONSTANTES DE THEME (COLORS, GLASS_PREFERENCES, defaults, APP_STYLE) ===============")
pat = re.compile(r"(COLOR|GLASS|PREF|DEFAULT|THEME|APP_STYLE|PALETTE)", re.I)
for node in tree.body:
    if isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if any(pat.search(n) for n in names):
            seg = lines[node.lineno - 1:node.end_lineno]
            print(f"\n----- {', '.join(names)} (lignes {node.lineno}-{node.end_lineno}) -----")
            print("\n".join(seg[:150]))
            if len(seg) > 150:
                print(f"... [{len(seg) - 150} lignes omises]")

print("\n\n=============== 2. FONCTIONS QUI CONSTRUISENT / APPLIQUENT LE THEME ===============")
FUNCS = {
    "_build_app_style", "_runtime_preferences_style", "_runtime_results_tab_style",
    "_inline_color_map", "_rewrite_inline", "_restyle_widget", "_apply_app_palette",
    "_refresh_preference_palette", "apply_runtime_preferences",
}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FUNCS:
        show(node, "def")

print("\n\n=============== 3. INVENTAIRE DES COULEURS SOMBRES ECRITES EN DUR (hex + rgba) ===============")
hex_re = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
rgba_re = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
sel_re = re.compile(r"^\s*([A-Za-z#:\.\[\]\"'=_\-\s,>\*]+?)\s*\{")

def context(i):
    for j in range(i, max(-1, i - 40), -1):
        m = sel_re.match(lines[j])
        if m:
            return m.group(1).strip()[:70]
    return "?"

found = defaultdict(list)
for i, ln in enumerate(lines):
    for m in hex_re.finditer(ln):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if lum(r, g, b) < 0.30:
            found["#" + h.lower()].append(i)
    for m in rgba_re.finditer(ln):
        r, g, b = map(int, m.groups())
        if lum(r, g, b) < 0.30:
            found[f"rgb({r},{g},{b})"].append(i)

print(f"{len(found)} couleurs sombres distinctes.\n")
for col, idx in sorted(found.items(), key=lambda kv: -len(kv[1]))[:45]:
    ctxs = []
    for i in idx[:6]:
        c = context(i)
        if c not in ctxs:
            ctxs.append(c)
    print(f"{col:18s} x{len(idx):3d}  lignes {[k + 1 for k in idx[:6]]}")
    print(f"{'':18s} selecteurs proches : {ctxs}")

print("\n\n=============== 4. QSS DES WIDGETS SOMBRES (selecteurs ciblant champs / listes / tableaux / dialogues) ===============")
sel_kw = re.compile(
    r"(QLineEdit|QComboBox|QSpinBox|QDoubleSpinBox|QHeaderView|QDialog|QTableWidget|QTableView|"
    r"QPlainTextEdit|QTextEdit|QListWidget|QAbstractItemView|QGroupBox|QMessageBox|QFileDialog|"
    r"QCheckBox::indicator|QRadioButton::indicator|QToolTip|QMenu)"
)
n = 0
for i, ln in enumerate(lines):
    if sel_kw.search(ln) and "{" in ln:
        print(f"{i + 1:6d}: {ln.strip()[:130]}")
        n += 1
        if n >= 140:
            print("... (tronque)")
            break

print("\n\n=============== 5. BOITES DE DIALOGUE (classes QDialog + leurs setStyleSheet) ===============")
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases]
        if any("Dialog" in b for b in bases):
            body = "\n".join(lines[node.lineno - 1:node.end_lineno])
            ss = body.count("setStyleSheet")
            print(f"class {node.name}({', '.join(bases)})  lignes {node.lineno}-{node.end_lineno}  setStyleSheet x{ss}")

print("\n--- textes reperes dans les captures ---")
for kw in ["Choisir un récepteur", "Import de récepteur", "Choisir les familles", "Indice de réfraction",
           "Couleur d'accent générale", "Liste déroulante", "Tester un menu", "Pompe d'efflux", "Aperçu"]:
    hits = [i + 1 for i, ln in enumerate(lines) if kw in ln]
    print(f"{kw!r}: lignes {hits[:8]}")

print("\n\n=============== 6. CLES DE PREFERENCES DEJA UTILISEES ===============")
keys = set(re.findall(r"GLASS_PREFERENCES(?:\.get\(|\[)\s*[\"']([a-z_0-9]+)[\"']", text))
print(sorted(keys))

print("\n\n=============== 7. NOMS D'OBJETS (setObjectName) LES PLUS FREQUENTS ===============")
names = defaultdict(int)
for nm in re.findall(r"setObjectName\(\s*[\"']([^\"']+)[\"']", text):
    names[nm] += 1
for nm, c in sorted(names.items(), key=lambda kv: -kv[1])[:60]:
    print(f"{nm}: {c}")
