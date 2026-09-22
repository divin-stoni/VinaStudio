#!/usr/bin/env python3
"""
Diagnostic LECTURE SEULE pour le projet VinaStudio (MexAB_MexR_Analyzer_BETA).
Ne modifie AUCUN fichier. Produit un rapport texte + JSON à renvoyer tel quel.

Usage :
    python3 diagnostic_phytomolecules.py [chemin_racine_projet]

Si aucun chemin n'est donné, essaie ~/MexAB_MexR_Analyzer_BETA puis le
répertoire courant.
"""

import os
import re
import sys
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CANDIDATES = [
    Path.home() / "MexAB_MexR_Analyzer_BETA",
    Path.cwd(),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_archive_backups", "venv", ".venv"}

# mots-clés -> ce qu'on cherche et pourquoi
SEARCHES = {
    "style_system": {
        "patterns": [r"\bCOLORS\s*=", r"\bAPP_STYLE\b", r"setStyleSheet", r"QSS", r"\bTHEME\b"],
        "why": "Système central de style (couleurs, formes, bordures) à réutiliser pour le nouvel onglet.",
    },
    "credits_tab": {
        "patterns": [r"class\s+\w*Credit\w*", r"credits_page"],
        "why": "Pattern de déclaration/enregistrement d'un onglet, à copier pour Phytomolécules.",
    },
    "tab_navigation": {
        "patterns": [r"TopTab", r"switch_primary", r"create_toolbar", r"primary_navigation"],
        "why": "Mécanisme de nav horizontale (patch13) où insérer le nouvel onglet.",
    },
    "sdf_extraction": {
        "patterns": [r"\.sdf\b", r"SDMolSupplier", r"def\s+\w*extract\w*sdf", r"def\s+\w*split\w*sdf"],
        "why": "Script existant d'extraction de SDF groupés, à réutiliser sans le recréer.",
    },
    "translations": {
        "patterns": [r"class\s+\w*Translat", r"def\s+t\(", r"lang_mgr", r"_t_resolve"],
        "why": "Système de traduction (et son garde-fou anti-clé-brute du patch12).",
    },
    "network_calls": {
        "patterns": [r"requests\.get", r"requests\.post", r"urlopen", r"pubchem", r"PubChem"],
        "why": "Module réseau déjà existant à réutiliser pour les appels GBIF/LOTUS/PubChem.",
    },
    "ligand_folder_ref": {
        "patterns": [r"docking/ligands", r"ligand_folder", r"LIGAND_DIR"],
        "why": "Emplacement exact du dossier ligand où déposer les SDF téléchargés.",
    },
}

MAX_SNIPPETS_PER_KEY = 6
CONTEXT_LINES = 2


def find_project_root(arg):
    if arg:
        p = Path(arg).expanduser()
        if p.exists():
            return p
        print(f"[!] Chemin fourni introuvable : {p}", file=sys.stderr)
        sys.exit(1)
    for cand in DEFAULT_CANDIDATES:
        if cand.exists():
            return cand
    print("[!] Aucun projet trouvé automatiquement. Donne le chemin en argument.", file=sys.stderr)
    sys.exit(1)


def iter_source_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith((".py", ".json", ".qss", ".css")):
                yield Path(dirpath) / fn


def scan(root):
    report = {"project_root": str(root), "findings": {}, "translations_source_present": None,
              "compiled_only_modules": []}

    all_files = list(iter_source_files(root))
    report["total_scanned_files"] = len(all_files)

    for key, spec in SEARCHES.items():
        combined = re.compile("|".join(spec["patterns"]))
        matches = []
        for f in all_files:
            try:
                text = f.read_text(errors="ignore")
            except Exception:
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if combined.search(line):
                    start = max(0, i - CONTEXT_LINES)
                    end = min(len(lines), i + CONTEXT_LINES + 1)
                    snippet = "\n".join(lines[start:end])
                    matches.append({
                        "file": str(f.relative_to(root)),
                        "line": i + 1,
                        "snippet": snippet,
                    })
                    if len(matches) >= MAX_SNIPPETS_PER_KEY:
                        break
            if len(matches) >= MAX_SNIPPETS_PER_KEY:
                break
        report["findings"][key] = {"why": spec["why"], "matches": matches}

    # Modules root critiques : source .py présente ou seulement .pyc ?
    critical_modules = ["translations", "session_runtime", "session_manager", "docking_parser", "column_matcher", "stats_engine"]
    for mod in critical_modules:
        py_hits = [f for f in all_files if f.name == f"{mod}.py"]
        pyc_hits = list(root.rglob(f"{mod}.cpython-*.pyc")) + list(root.rglob(f"{mod}.pyc"))
        if py_hits:
            status = "source (.py) présente"
        elif pyc_hits:
            status = "SEULEMENT .pyc compilé — pas de source"
            report["compiled_only_modules"].append(mod)
        else:
            status = "introuvable"
        if mod == "translations":
            report["translations_source_present"] = (status == "source (.py) présente")
        report.setdefault("module_status", {})[mod] = status

    return report


def print_human_report(report):
    print("=" * 78)
    print(f"DIAGNOSTIC VinaStudio — racine : {report['project_root']}")
    print(f"Fichiers scannés : {report['total_scanned_files']}")
    print("=" * 78)

    print("\n--- État des modules critiques (source vs .pyc seul) ---")
    for mod, status in report.get("module_status", {}).items():
        print(f"  {mod:20s} : {status}")

    for key, data in report["findings"].items():
        print(f"\n--- {key} ---")
        print(f"Pourquoi : {data['why']}")
        if not data["matches"]:
            print("  AUCUNE occurrence trouvée.")
            continue
        for m in data["matches"]:
            print(f"  [{m['file']}:{m['line']}]")
            for l in m["snippet"].splitlines():
                print(f"      {l}")
    print("\n" + "=" * 78)
    print("Copie-colle TOUT ce rapport (ou envoie le fichier .json généré à côté)")
    print("dans la conversation pour la suite.")
    print("=" * 78)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    root = find_project_root(arg)
    report = scan(root)
    print_human_report(report)

    out_json = Path.cwd() / "diagnostic_phytomolecules_rapport.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nRapport JSON complet écrit dans : {out_json}")


if __name__ == "__main__":
    main()
