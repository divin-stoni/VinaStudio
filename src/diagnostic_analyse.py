#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic LECTURE SEULE de la partie Docking -> Analyse.

Ce script ne modifie rien, n'importe aucun module du projet (donc ne lance
ni l'interface ni le moteur), n'utilise pas Internet. Il lit les fichiers et
ecrit UN rapport texte : diagnostic_analyse.txt

Il repond a ces questions :
  1. Quelles sont les structures (colonnes) des fichiers CSV produits ?
  2. Ou "MexB" / "MexR" sont-ils encore ecrits en dur dans le code ?
  3. Ou sont les seuils / references fixes (ex. -8.289, piocyanine) ?
  4. Quelles fonctions existent dans le moteur (analyse, fusion, docking) ?
  5. Quelles fonctions ecrivent les CSV ?

Utilisation (depuis le dossier src/ du projet, comme pour le patch) :

    python3 diagnostic_analyse.py

Puis envoie-moi le fichier diagnostic_analyse.txt.
"""

import ast
import csv
import os
import re
import sys
import time
from collections import defaultdict
from importlib import metadata
from pathlib import Path

REPORT_NAME = "diagnostic_analyse.txt"

EXCLUDE_DIRS = {
    ".git", "venv", ".venv", "env", "__pycache__", "node_modules",
    "site-packages", "credit_du_logiciel", ".mypy_cache", ".pytest_cache",
    ".idea", ".vscode",
}

# Fichiers "moteur" dont on detaille le contenu (chemins relatifs a src/).
ENGINE_PATTERNS = (
    "analysis/", "docking/", "plotting", "visualization/",
    "scientific_fusion", "fusion",
)

RE_MEX = re.compile(r"mex[br]", re.IGNORECASE)
RE_REFERENCE = re.compile(
    r"-?8\.289|piocyan|pyocyan|r[eé]f[eé]rence|reference|seuil|threshold|"
    r"cutoff|percentile|bootstrap|leave[_ -]?one|spearman|pearson|"
    r"selectivit|(?-i:\bSI\b)",
    re.IGNORECASE,
)
RE_CSV_WRITE = re.compile(
    r"DictWriter|fieldnames|to_csv|writerow|best_affinity|_mexb|_mexr|"
    r"pair_roles|\"pump\"|\"repressor\"|\.columns",
)

MAX_LINES_PER_SECTION = 450
MAX_CSV_BYTES = 60 * 1024 * 1024


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def find_root(arg):
    start = Path(arg).resolve() if arg else Path.cwd().resolve()
    for cand in [start] + list(start.parents):
        if (cand / "src").is_dir() and (cand / "src" / "gui").exists():
            return cand
        if cand.name == "src" and (cand / "gui").exists():
            return cand.parent
    return None


def walk(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.endswith(".egg-info")
        )
        yield Path(dirpath), sorted(filenames)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def short(text, n=110):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def is_engine(rel):
    rel = rel.replace(os.sep, "/")
    return any(pat in rel for pat in ENGINE_PATTERNS)


class Report:
    def __init__(self):
        self.lines = []

    def title(self, text):
        self.lines += ["", "=" * 78, text, "=" * 78]

    def add(self, text=""):
        self.lines.append(text)

    def capped(self, items, label="lignes"):
        for i, item in enumerate(items):
            if i >= MAX_LINES_PER_SECTION:
                self.add(f"... ({len(items) - i} {label} de plus, tronque)")
                break
            self.add(item)

    def text(self):
        return "\n".join(self.lines) + "\n"


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------

def section_env(rep, root, src):
    rep.title("1. ENVIRONNEMENT")
    rep.add(f"Date            : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    rep.add(f"Python          : {sys.version.split()[0]}")
    rep.add(f"Racine projet   : {root}")
    rep.add(f"Dossier src     : {src}")
    for pkg in ("PySide6", "pandas", "numpy", "scipy", "statsmodels",
                "matplotlib", "scikit-learn", "rdkit", "vina"):
        try:
            rep.add(f"{pkg:<15} : {metadata.version(pkg)}")
        except Exception:
            rep.add(f"{pkg:<15} : (non installe)")


def section_tree(rep, src, py_files):
    rep.title("2. FICHIERS PYTHON DE src/ (lignes)")
    items = []
    for path in py_files:
        rel = path.relative_to(src)
        n = len(read_text(path).splitlines())
        mark = "  <- moteur" if is_engine(str(rel)) else ""
        items.append(f"{n:>6}  {rel}{mark}")
    rep.capped(items)


def section_hardcoded(rep, src, py_files):
    rep.title("3. \"MexB\" / \"MexR\" ECRITS EN DUR (nombre par fichier)")
    counts = []
    for path in py_files:
        n = len(RE_MEX.findall(read_text(path)))
        if n:
            counts.append((n, str(path.relative_to(src))))
    counts.sort(reverse=True)
    rep.capped([f"{n:>6}  {rel}" for n, rel in counts])
    # Fichiers de traduction / config (json)
    extra = []
    for base, files in walk(src):
        for name in files:
            if name.lower().endswith((".json", ".yaml", ".yml", ".toml", ".ini")):
                p = base / name
                try:
                    if p.stat().st_size > 2_000_000:
                        continue
                except OSError:
                    continue
                n = len(RE_MEX.findall(read_text(p)))
                if n:
                    extra.append(f"{n:>6}  {p.relative_to(src)}")
    if extra:
        rep.add("")
        rep.add("Fichiers de config / traduction concernes :")
        rep.capped(extra)

    rep.title("3b. DETAIL DANS LE MOTEUR (analysis, docking, fusion, plotting)")
    detail = []
    for path in py_files:
        rel = str(path.relative_to(src))
        if not is_engine(rel):
            continue
        for i, line in enumerate(read_text(path).splitlines(), 1):
            if RE_MEX.search(line):
                detail.append(f"{rel}:{i}: {short(line.strip())}")
    rep.capped(detail)


def section_references(rep, src, py_files):
    rep.title("4. SEUILS / REFERENCES / METHODES STATISTIQUES (moteur)")
    detail = []
    for path in py_files:
        rel = str(path.relative_to(src))
        if not is_engine(rel):
            continue
        for i, line in enumerate(read_text(path).splitlines(), 1):
            if RE_REFERENCE.search(line):
                detail.append(f"{rel}:{i}: {short(line.strip())}")
    rep.capped(detail)


def signature(fn):
    a = fn.args
    parts = []
    positional = a.posonlyargs + a.args
    n_def = len(a.defaults)
    for idx, arg in enumerate(positional):
        has_default = idx >= len(positional) - n_def
        parts.append(arg.arg + ("=…" if has_default else ""))
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(arg.arg + ("=…" if default is not None else ""))
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return f"{fn.name}({', '.join(parts)})"


def returned_keys(fn):
    keys = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for k in node.value.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.append(k.value)
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (
                    isinstance(t, ast.Subscript)
                    and isinstance(t.value, ast.Name)
                    and t.value.id in {"result", "results", "out", "output", "res", "stats"}
                    and isinstance(t.slice, ast.Constant)
                    and isinstance(t.slice.value, str)
                ):
                    keys.append(t.slice.value)
    seen, uniq = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def section_outline(rep, src, py_files):
    rep.title("5. FONCTIONS ET CLASSES DU MOTEUR")
    out = []
    for path in py_files:
        rel = str(path.relative_to(src))
        if not is_engine(rel):
            continue
        text = read_text(path)
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            out.append(f"\n[{rel}] ERREUR DE SYNTAXE : {exc}")
            continue
        out.append(f"\n[{rel}]")
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = (ast.get_docstring(node) or "").strip().splitlines()
                out.append(f"  def {signature(node)}   (l.{node.lineno})")
                if doc:
                    out.append(f"      \"{short(doc[0], 100)}\"")
                keys = returned_keys(node)
                if keys:
                    out.append(f"      cles produites : {', '.join(keys[:25])}")
            elif isinstance(node, ast.ClassDef):
                out.append(f"  class {node.name}   (l.{node.lineno})")
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.append(f"      def {signature(sub)}   (l.{sub.lineno})")
                        keys = returned_keys(sub)
                        if keys:
                            out.append(f"          cles produites : {', '.join(keys[:25])}")
    rep.capped(out)


def section_csv_writers(rep, src, py_files):
    rep.title("6. OU LES CSV SONT ECRITS / COLONNES CONSTRUITES (moteur)")
    detail = []
    for path in py_files:
        rel = str(path.relative_to(src))
        if not is_engine(rel):
            continue
        for i, line in enumerate(read_text(path).splitlines(), 1):
            if RE_CSV_WRITE.search(line):
                detail.append(f"{rel}:{i}: {short(line.strip(), 120)}")
    rep.capped(detail)


def sniff_delimiter(first_line):
    best = max((",", ";", "\t"), key=first_line.count)
    return best if first_line.count(best) else ","


def section_csv_files(rep, root):
    rep.title("7. FICHIERS CSV TROUVES (regroupes par structure de colonnes)")
    groups = defaultdict(list)
    n_seen = 0
    for base, files in walk(root):
        for name in files:
            if not name.lower().endswith(".csv"):
                continue
            p = base / name
            try:
                st = p.stat()
            except OSError:
                continue
            n_seen += 1
            if st.st_size > MAX_CSV_BYTES:
                groups[("<fichier trop gros>",)].append((st.st_mtime, p, 0, []))
                continue
            try:
                with p.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
                    first = fh.readline()
                    delim = sniff_delimiter(first)
                    fh.seek(0)
                    reader = csv.reader(fh, delimiter=delim)
                    header = tuple(next(reader, []))
                    samples, n_rows = [], 0
                    for row in reader:
                        n_rows += 1
                        if len(samples) < 2:
                            samples.append([short(c, 28) for c in row])
            except Exception as exc:
                groups[(f"<illisible : {exc}>",)].append((st.st_mtime, p, 0, []))
                continue
            groups[header].append((st.st_mtime, p, n_rows, samples))

    rep.add(f"{n_seen} fichier(s) CSV trouve(s), {len(groups)} structure(s) differente(s).")
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    out = []
    for header, entries in ordered:
        entries.sort(key=lambda e: -e[0])
        newest = entries[0]
        out.append("")
        out.append(f"--- STRUCTURE ({len(entries)} fichier(s)) ---")
        out.append("Colonnes : " + " | ".join(header))
        mex_cols = [c for c in header if RE_MEX.search(c)]
        if mex_cols:
            out.append("  >> colonnes liees a une cible precise : " + ", ".join(mex_cols))
        for _, p, n_rows, _s in entries[:4]:
            out.append(f"  ex: {p.relative_to(root)}  ({n_rows} ligne(s))")
        if len(entries) > 4:
            out.append(f"  ... +{len(entries) - 4} autre(s)")
        for s in newest[3]:
            out.append("  echantillon : " + " | ".join(s))
    rep.capped(out)


def section_profiles(rep, root):
    rep.title("8. FICHIERS DE PROFIL / CONFIG DE RECEPTEURS (json)")
    import json
    found = []
    for base, files in walk(root):
        for name in files:
            low = name.lower()
            if low.endswith(".json") and any(k in low for k in ("profile", "receptor", "config", "target")):
                p = base / name
                try:
                    if p.stat().st_size > 400_000:
                        found.append(f"{p.relative_to(root)}  (gros fichier, ignore)")
                        continue
                    data = json.loads(read_text(p) or "null")
                except Exception:
                    found.append(f"{p.relative_to(root)}  (json illisible)")
                    continue
                if isinstance(data, dict):
                    found.append(f"{p.relative_to(root)}  cles: {', '.join(list(data.keys())[:20])}")
                else:
                    found.append(f"{p.relative_to(root)}  ({type(data).__name__})")
    if not found:
        rep.add("(aucun)")
    rep.capped(found)


# --------------------------------------------------------------------------

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    root = find_root(arg)
    if root is None:
        print("ERREUR : dossier du projet introuvable. Lance le script depuis "
              "le dossier src/ (ou donne le chemin du projet en argument).")
        return 2
    src = root / "src"

    py_files = []
    for base, files in walk(src):
        for name in files:
            if name.endswith(".py"):
                py_files.append(base / name)

    rep = Report()
    rep.add("DIAGNOSTIC DOCKING -> ANALYSE (lecture seule)")
    section_env(rep, root, src)
    section_tree(rep, src, py_files)
    section_hardcoded(rep, src, py_files)
    section_references(rep, src, py_files)
    section_outline(rep, src, py_files)
    section_csv_writers(rep, src, py_files)
    section_csv_files(rep, root)
    section_profiles(rep, root)

    out_path = Path.cwd() / REPORT_NAME
    out_path.write_text(rep.text(), encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"Rapport ecrit : {out_path}  ({size_kb:.0f} Ko, {len(rep.lines)} lignes)")
    print("Envoie-moi ce fichier. Rien n'a ete modifie dans ton projet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
