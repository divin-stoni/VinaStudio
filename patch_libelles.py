# -*- coding: utf-8 -*-
"""
patch_libelles.py

Patch reversible : les noms des recepteurs (AcrB, AcrR, MexB, MexR...)
circulent de la fusion jusqu'aux figures et au texte de l'interface,
et chaque famille a sa propre couleur.

  1. src/scientific_fusion.py
       ecrit scores_fusionnes_meta.json (noms des deux recepteurs)
       a cote des CSV scientifiques.
  2. src/analysis/statistics_pipeline.py
       lit ce fichier et remplit result["labels"] ;
       les noms sont aussi poses sur les tableaux (.attrs).
  3. src/plotting.py
       les axes des figures utilisent ces noms (MexB/MexR par defaut) ;
       les familles a nom libre ont chacune une couleur distincte.
  4. src/gui/main_window.py
       le texte du filtre a double selectivite decrit les criteres
       reellement appliques (recepteur, percentile, seuil).

Rien ne change pour un couple MexB / MexR.

Usage, depuis la racine du projet :
    python3 patch_libelles.py --check
    python3 patch_libelles.py
    python3 patch_libelles.py --revert
"""

import ast
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

FILES = {
    "fusion": Path("src/scientific_fusion.py"),
    "pipeline": Path("src/analysis/statistics_pipeline.py"),
    "plotting": Path("src/plotting.py"),
    "main_window": Path("src/gui/main_window.py"),
}

BACKUP_TAG = ".bak_libelles_"

# ----------------------------------------------------------------------
# 1. scientific_fusion.py
# ----------------------------------------------------------------------

OLD_FUSION_DEF = '''def detect_groups(df, group_col="groupe"):'''

NEW_FUSION_DEF = '''def _receptor_label(name):
    """Nom court affichable d'un recepteur (MexB, AcrB, ...)."""
    raw = str(name or "").strip()
    slug = _target_slug(raw)
    for prefix in ("best_affinity_", "deltag_", "dg_"):
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
            break
    try:
        from src.docking.receptor_profile import (
            resolve_target_profile,
            short_label,
        )
        return str(short_label(resolve_target_profile(slug)))
    except Exception:
        pass
    return {"mexb": "MexB", "mexr": "MexR"}.get(slug, slug or raw)


def detect_groups(df, group_col="groupe"):'''

OLD_FUSION_RETURN = '''return grouped_csv, global_csv'''

NEW_FUSION_RETURN = '''# patch-libelles : noms des recepteurs pour les graphiques et l'interface
try:
    import json as _json

    meta = {
        "pump": {
            "id": str(pump_name),
            "label": _receptor_label(pump_name),
            "column": pump_output_col,
        },
        "repressor": {
            "id": str(repressor_name),
            "label": _receptor_label(repressor_name),
            "column": repressor_output_col,
        },
        "source_csv": str(input_csv),
    }
    (output_dir / "scores_fusionnes_meta.json").write_text(
        _json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
except Exception:
    pass

return grouped_csv, global_csv'''

# ----------------------------------------------------------------------
# 2. analysis/statistics_pipeline.py
# ----------------------------------------------------------------------

OLD_PIPE_DEF = '''def run_statistics_pipeline(csv_path):'''

NEW_PIPE_DEF = '''def _receptor_labels(csv_path, x_col, y_col):
    """Noms des deux recepteurs : fichier meta de la fusion, sinon defauts."""
    labels = {"x": None, "y": None}
    try:
        import json

        meta_path = Path(csv_path).parent / "scores_fusionnes_meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pump = meta.get("pump") or {}
            repressor = meta.get("repressor") or {}
            # Le fichier meta ne sert que s'il decrit bien ces colonnes.
            if pump.get("column") == x_col and repressor.get("column") == y_col:
                labels["x"] = pump.get("label")
                labels["y"] = repressor.get("label")
    except Exception:
        pass
    defaults = {
        "dg_mexb": "MexB",
        "dg_mexr": "MexR",
        "dg_pump": "Pompe",
        "dg_repressor": "Répresseur",
    }
    labels["x"] = labels["x"] or defaults.get(x_col, str(x_col))
    labels["y"] = labels["y"] or defaults.get(y_col, str(y_col))
    return labels


def run_statistics_pipeline(csv_path):'''

OLD_PIPE_CLASS = '''result["classification"] = (
    compute_si_and_classification(df, x_col=x_col, y_col=y_col)
)'''

NEW_PIPE_CLASS = '''result["classification"] = (
    compute_si_and_classification(df, x_col=x_col, y_col=y_col)
)

# patch-libelles : noms des recepteurs (fusion -> meta -> pipeline -> figures)
result["labels"] = _receptor_labels(csv_path, x_col, y_col)
for _frame in (result["classification"], df):
    _frame.attrs["x_label"] = result["labels"]["x"]
    _frame.attrs["y_label"] = result["labels"]["y"]'''

# ----------------------------------------------------------------------
# 3. plotting.py
# ----------------------------------------------------------------------

OLD_COLOR = '''def _color_for(g):
    return PALETTE.get(g, "#999999")'''

NEW_COLOR = '''_DYNAMIC_CYCLE = [
    "#E5A823", "#2A9D8F", "#E76F51", "#6A4C93", "#1D3557",
    "#B5838D", "#588157", "#BC6C25", "#457B9D", "#9C89B8",
]
_DYNAMIC_COLORS = {}


def _color_for(g):
    # patch-libelles : une couleur distincte par famille, meme a nom libre
    if g in PALETTE:
        return PALETTE[g]
    if str(g).strip().lower() in ("sans_groupe", "sans famille"):
        return "#999999"
    if g not in _DYNAMIC_COLORS:
        _DYNAMIC_COLORS[g] = _DYNAMIC_CYCLE[len(_DYNAMIC_COLORS) % len(_DYNAMIC_CYCLE)]
    return _DYNAMIC_COLORS[g]'''

OLD_HIST = '''ax.set_xlabel("Indice de sélectivité SI = ΔG(MexR) − ΔG(MexB)")'''

NEW_HIST = '''ax.set_xlabel("Indice de sélectivité SI = ΔG(" + df_classified.attrs.get("y_label", "MexR") + ") − ΔG(" + df_classified.attrs.get("x_label", "MexB") + ")")  # patch-libelles : SI'''

OLD_SCATTER = '''ax.set_xlabel("ΔG(MexB) (kcal/mol)")
ax.set_ylabel("ΔG(MexR) (kcal/mol)")
ax.set_title("Corrélation ΔG(MexB) – ΔG(MexR) par famille")'''

NEW_SCATTER = '''# patch-libelles : scatter avec les noms des recepteurs
_xl = df.attrs.get("x_label", "MexB")
_yl = df.attrs.get("y_label", "MexR")
ax.set_xlabel("ΔG(" + _xl + ") (kcal/mol)")
ax.set_ylabel("ΔG(" + _yl + ") (kcal/mol)")
ax.set_title("Corrélation ΔG(" + _xl + ") – ΔG(" + _yl + ") par famille")'''

# ----------------------------------------------------------------------
# 4. gui/main_window.py
# ----------------------------------------------------------------------

OLD_GUI = r'''"Critères :\n"
"- SI percentile > 50\n"
"- ΔG MexR meilleur que le seuil piocyanine (-8.289 kcal/mol)"'''

NEW_GUI = r'''"Critères :\n"
+ "- SI percentile > " + ("%g" % dual.get("threshold_percentile", 50)) + "\n"
+ "- ΔG " + str((result.get("labels") or {}).get("y", "MexR"))
+ " meilleur que le seuil "
+ str((getattr(classification, "attrs", None) or {}).get("ref_name", "pyocyanine")).replace("pyocyanine", "piocyanine")
+ " (" + str((getattr(classification, "attrs", None) or {}).get("seuil_risque_absolu", -8.289)) + " kcal/mol)"  # patch-libelles-gui'''

EDITS = [
    ("fusion", "fonction _receptor_label (nom court d'un recepteur)",
     OLD_FUSION_DEF, NEW_FUSION_DEF, "def _receptor_label(name):"),
    ("fusion", "ecriture de scores_fusionnes_meta.json",
     OLD_FUSION_RETURN, NEW_FUSION_RETURN, "patch-libelles : noms des recepteurs pour"),
    ("pipeline", "fonction _receptor_labels (lecture du fichier meta)",
     OLD_PIPE_DEF, NEW_PIPE_DEF, "def _receptor_labels(csv_path"),
    ("pipeline", "result['labels'] et noms poses sur les tableaux",
     OLD_PIPE_CLASS, NEW_PIPE_CLASS, "patch-libelles : noms des recepteurs (fusion"),
    ("plotting", "couleur distincte par famille",
     OLD_COLOR, NEW_COLOR, "_DYNAMIC_COLORS = {}"),
    ("plotting", "axe de l'histogramme SI",
     OLD_HIST, NEW_HIST, "patch-libelles : SI"),
    ("plotting", "axes et titre du nuage de points",
     OLD_SCATTER, NEW_SCATTER, "patch-libelles : scatter"),
    ("main_window", "texte du filtre a double selectivite",
     OLD_GUI, NEW_GUI, "patch-libelles-gui"),
]


# ----------------------------------------------------------------------
# Outils
# ----------------------------------------------------------------------

def build_pattern(old):
    tokens = old.split()
    return re.compile(r"\s*".join(re.escape(t) for t in tokens))


def find_matches(text, old):
    return list(build_pattern(old).finditer(text))


def replace_once(text, match, new):
    line_start = text.rfind("\n", 0, match.start()) + 1
    prefix = text[line_start:match.start()]
    indent = re.match(r"[ \t]*", prefix).group(0)
    lines = new.split("\n")
    out = lines[0] + "".join(
        "\n" + (indent + line if line.strip() else line) for line in lines[1:]
    )
    return text[:match.start()] + out + text[match.end():]


def already_applied(text, marker):
    return re.sub(r"\s+", " ", marker) in re.sub(r"\s+", " ", text)


def read(path):
    return path.read_text(encoding="utf-8")


def check_files_exist():
    missing = [str(p) for p in FILES.values() if not p.is_file()]
    if missing:
        print("Fichier(s) introuvable(s) : " + ", ".join(missing))
        print("Lance ce script depuis la racine du projet (~/MexAB_MexR_Analyzer_BETA).")
        raise SystemExit(1)


# ----------------------------------------------------------------------
# Modes
# ----------------------------------------------------------------------

def do_check():
    check_files_exist()
    texts = {k: read(p) for k, p in FILES.items()}
    ok = True
    for key, label, old, new, marker in EDITS:
        text = texts[key]
        if already_applied(text, marker):
            state = "deja applique"
        else:
            n = len(find_matches(text, old))
            if n == 1:
                state = "applicable"
            else:
                state = "BLOQUE (%d correspondance(s), 1 attendue)" % n
                ok = False
        print("[%s] %s : %s" % (FILES[key].name, label, state))
    return 0 if ok else 1


def do_apply():
    check_files_exist()
    texts = {k: read(p) for k, p in FILES.items()}
    new_texts = dict(texts)
    todo = []

    for key, label, old, new, marker in EDITS:
        text = new_texts[key]
        if already_applied(text, marker):
            print("= deja applique : " + label)
            continue
        matches = find_matches(text, old)
        if len(matches) != 1:
            print("X BLOQUE : [%s] %s (%d correspondance(s), 1 attendue)" % (
                FILES[key].name, label, len(matches)))
            print("Aucun fichier n'a ete modifie.")
            return 1
        new_texts[key] = replace_once(text, matches[0], new)
        todo.append(label)

    if not todo:
        print("Rien a faire : tout est deja applique.")
        return 0

    for key, text in new_texts.items():
        try:
            ast.parse(text)
        except SyntaxError as exc:
            print("X Le resultat pour %s ne compile pas (%s)." % (FILES[key].name, exc))
            print("Aucun fichier n'a ete modifie.")
            return 1

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for key, path in FILES.items():
        if new_texts[key] != texts[key]:
            backup = Path(str(path) + BACKUP_TAG + stamp)
            shutil.copy2(path, backup)
            path.write_text(new_texts[key], encoding="utf-8")
            ast.parse(read(path))
            print("+ %s modifie (sauvegarde : %s)" % (path, backup.name))

    for label in todo:
        print("  ok : " + label)
    print("Termine. Pour annuler : python3 patch_libelles.py --revert")
    return 0


def do_revert():
    restored = 0
    for key, path in FILES.items():
        backups = sorted(glob.glob(str(path) + BACKUP_TAG + "*"))
        if not backups:
            print("- %s : aucune sauvegarde, rien a restaurer." % path.name)
            continue
        oldest = backups[0]
        shutil.copy2(oldest, path)
        ast.parse(read(path))
        print("+ %s restaure depuis %s" % (path.name, Path(oldest).name))
        restored += 1
    if restored == 0:
        print("Rien n'a ete restaure.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--check"]:
        raise SystemExit(do_check())
    if args == ["--revert"]:
        raise SystemExit(do_revert())
    if args == []:
        raise SystemExit(do_apply())
    print("Usage : python3 patch_libelles.py [--check | --revert]")
    raise SystemExit(1)
