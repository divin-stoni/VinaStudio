cat > audit_paquets_python.py << 'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit complet des dependances Python (pip) du projet : parcourt tous les
.py du projet via ast (pas de regex fragile), extrait chaque import de
paquet tiers (stdlib et modules locaux exclus), et compare a
requirements-windows.txt pour trouver tout ce qui manquerait au prochain
build Windows -- avant que ca ne plante une fois de plus en prod.
"""

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

EXCLUDE_DIRS = {
    "venv", ".git", "_archive_backups", "_a_supprimer", "_patch_backups",
    "node_modules", "__pycache__", "build", "dist",
}

# Modules locaux au projet (racines de package / fichiers a la racine
# importes directement) -- a ne PAS compter comme dependance externe.
LOCAL_ROOTS = {
    "src", "docking", "ligands", "run_gui", "docking_parser",
    "main_window_broken_blocks", "tests",
}

# Modules stdlib connus en plus de sys.stdlib_module_names (securite
# pour compatibilite si la liste integree est incomplete sur certaines
# versions).
EXTRA_STDLIB = {
    "__future__", "typing_extensions",
}

try:
    STDLIB = set(sys.stdlib_module_names)
except AttributeError:
    STDLIB = set()

STDLIB |= EXTRA_STDLIB


def iter_py_files():
    for path in PROJECT_ROOT.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        yield path


def extract_imports(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
    except SyntaxError:
        return set()

    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # import relatif (from . import x) -> local, ignore
            if node.module:
                found.add(node.module.split(".")[0])
    return found


def main():
    all_imports = {}  # module -> set(fichiers qui l'importent)

    for path in iter_py_files():
        for mod in extract_imports(path):
            all_imports.setdefault(mod, set()).add(str(path.relative_to(PROJECT_ROOT)))

    third_party = {
        mod: files for mod, files in all_imports.items()
        if mod not in STDLIB and mod not in LOCAL_ROOTS and not mod.startswith("_")
    }

    req_windows = PROJECT_ROOT / "requirements-windows.txt"
    req_linux = PROJECT_ROOT / "requirements.txt"

    def load_requirements(path):
        if not path.exists():
            return set()
        names = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # coupe sur les specificateurs de version / extras
            name = line
            for sep in ["==", ">=", "<=", "~=", ">", "<", "[", ";"]:
                name = name.split(sep)[0]
            names.add(name.strip().lower().replace("-", "_"))
        return names

    win_reqs = load_requirements(req_windows)
    linux_reqs = load_requirements(req_linux)

    # Mapping des noms d'import qui different du nom pip (cas connus).
    IMPORT_TO_PIP = {
        "pyside6": "pyside6",
        "pyside2": "pyside2",
        "rdkit": "rdkit",
        "yaml": "pyyaml",
        "sklearn": "scikit_learn",
        "cv2": "opencv_python",
        "PIL": "pillow",
        "bs4": "beautifulsoup4",
        "dateutil": "python_dateutil",
        "dotenv": "python_dotenv",
    }

    print("=" * 72)
    print("PAQUETS TIERS IMPORTES DANS LE PROJET")
    print("=" * 72)

    missing_windows = []
    for mod in sorted(third_party):
        pip_name = IMPORT_TO_PIP.get(mod, mod).lower().replace("-", "_")
        in_win = pip_name in win_reqs
        in_linux = pip_name in linux_reqs
        status = "OK (present)" if in_win else "!!! ABSENT de requirements-windows.txt"
        print(f"\n{mod}  (paquet pip probable: {pip_name})")
        print(f"    Windows : {'present' if in_win else 'ABSENT'}   |   Linux : {'present' if in_linux else 'absent'}")
        print(f"    Utilise dans : {', '.join(sorted(list(third_party[mod])[:5]))}"
              f"{' ...' if len(third_party[mod]) > 5 else ''}")
        if not in_win:
            missing_windows.append((mod, pip_name, sorted(third_party[mod])))

    print()
    print("=" * 72)
    print("RESUME")
    print("=" * 72)
    if not missing_windows:
        print("Aucun paquet tiers manquant dans requirements-windows.txt.")
    else:
        print(f"{len(missing_windows)} paquet(s) importe(s) mais ABSENT(S) de requirements-windows.txt :\n")
        for mod, pip_name, files in missing_windows:
            print(f"  - {mod}  (pip: {pip_name})")
            for f in files:
                print(f"      utilise dans : {f}")

    print()
    print("Contenu actuel de requirements-windows.txt :")
    if req_windows.exists():
        print(req_windows.read_text(encoding="utf-8"))
    else:
        print("!! requirements-windows.txt introuvable")


if __name__ == "__main__":
    main()
PYEOF
echo "Script cree : audit_paquets_python.py"
echo "Exécution :"
echo "  python3 audit_paquets_python.py > audit_paquets_output.txt 2>&1"
echo "  cat audit_paquets_output.txt"
