# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime


def backup_and_read(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Fichier introuvable : {path}")
    backup = path.with_suffix(path.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(path, backup)
    print(f"✓ Sauvegarde créée : {backup}")
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------
# 1. vina_engine.py
# --------------------------------------------------------------------
vina_path = Path("src/docking/vina_engine.py")
content = backup_and_read(vina_path)
original = content

old = '''def resolve_vina_executable() -> str:
    """
    Determine le chemin de l'executable Vina a utiliser.

    - Si l'application tourne en executable package (PyInstaller,
      typiquement sur Windows) ET qu'un vina.exe embarque existe
      dans docking/bin/, on l'utilise directement.
    - Sinon (execution normale en Python, notamment sur Linux),
      on garde le comportement historique : "vina" recherche
      dans le PATH systeme.
    """
    if getattr(sys, "frozen", False):
        bundled = PROJECT_ROOT / "docking" / "bin" / "vina.exe"
        if bundled.exists():
            return str(bundled)

    return "vina"'''

new = '''def resolve_vina_executable() -> str:
    """
    Determine le chemin de l'executable Vina a utiliser.

    - Si l'application tourne en executable package (PyInstaller)
      ET qu'un binaire vina embarque existe, on l'utilise
      directement (docking/bin/vina.exe sur Windows,
      docking/bin/vina sur Linux).
    - Sinon (execution normale en Python), on garde le
      comportement historique : "vina" recherche dans le PATH
      systeme.
    """
    from src.tools.runtime_env import configure_bundled_runtime
    configure_bundled_runtime()

    if getattr(sys, "frozen", False):
        if sys.platform.startswith("linux"):
            bundled = PROJECT_ROOT / "docking" / "bin" / "vina"
        else:
            bundled = PROJECT_ROOT / "docking" / "bin" / "vina.exe"

        if bundled.exists():
            return str(bundled)

    return "vina"'''

if old not in content:
    raise SystemExit("✗ Fonction resolve_vina_executable() introuvable telle qu'attendue, patch annulé.")
content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée sur vina_engine.py.")
vina_path.write_text(content, encoding="utf-8")
print("✓ vina_engine.py patché (support Linux packagé)")


# --------------------------------------------------------------------
# 2. obabel_locator.py
# --------------------------------------------------------------------
obabel_path = Path("src/tools/obabel_locator.py")
content = backup_and_read(obabel_path)
original = content

old = '''def resolve_obabel_executable() -> str:
    """
    Determine le chemin de l'executable obabel a utiliser.

    - Si l'application tourne en executable package (PyInstaller,
      typiquement sur Windows) ET qu'un obabel.exe embarque existe
      dans obabel_runtime/bin/, on l'utilise directement.
    - Sinon (execution normale en Python, notamment sur Linux),
      on garde le comportement historique : "obabel" recherche
      dans le PATH systeme.
    """
    if getattr(sys, "frozen", False):
        bundled = PROJECT_ROOT / "obabel_runtime" / "bin" / "obabel.exe"
        if bundled.exists():
            return str(bundled)

    return "obabel"'''

new = '''def resolve_obabel_executable() -> str:
    """
    Determine le chemin de l'executable obabel a utiliser.

    - Si l'application tourne en executable package (PyInstaller)
      ET qu'un binaire obabel embarque existe, on l'utilise
      directement (obabel_runtime/bin/obabel.exe sur Windows,
      obabel_runtime/bin/obabel sur Linux).
    - Sinon (execution normale en Python), on garde le
      comportement historique : "obabel" recherche dans le PATH
      systeme.
    """
    from src.tools.runtime_env import configure_bundled_runtime
    configure_bundled_runtime()

    if getattr(sys, "frozen", False):
        if sys.platform.startswith("linux"):
            bundled = PROJECT_ROOT / "obabel_runtime" / "bin" / "obabel"
        else:
            bundled = PROJECT_ROOT / "obabel_runtime" / "bin" / "obabel.exe"

        if bundled.exists():
            return str(bundled)

    return "obabel"'''

if old not in content:
    raise SystemExit("✗ Fonction resolve_obabel_executable() introuvable telle qu'attendue, patch annulé.")
content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée sur obabel_locator.py.")
obabel_path.write_text(content, encoding="utf-8")
print("✓ obabel_locator.py patché (support Linux packagé)")
