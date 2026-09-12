# -*- coding: utf-8 -*-
"""
Patch : fait pointer vina_engine.py vers le vina.exe embarqué
quand l'app tourne en exécutable packagé (PyInstaller/Windows),
tout en gardant le comportement Linux/dev inchangé ("vina" du PATH).
"""

from pathlib import Path
import shutil
import datetime

TARGET = Path("src/docking/vina_engine.py")

if not TARGET.exists():
    raise SystemExit(f"Fichier introuvable : {TARGET}")

backup = TARGET.with_suffix(
    TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}"
)
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

# 1. Import de field()
old_import = "from dataclasses import dataclass, asdict"
new_import = "from dataclasses import dataclass, asdict, field"
if old_import not in content:
    raise SystemExit("✗ Import 'dataclasses' introuvable, patch annulé.")
content = content.replace(old_import, new_import, 1)

# 2. Ajout de la fonction resolve_vina_executable()
anchor = 'from src.session_runtime import reset_before_docking'
if anchor not in content:
    raise SystemExit("✗ Ancre d'import 'session_runtime' introuvable, patch annulé.")

resolver_function = '''from src.session_runtime import reset_before_docking


# ============================================================================
# RESOLUTION DE L'EXECUTABLE VINA (PATCH WINDOWS PACKAGE)
# ============================================================================

def resolve_vina_executable() -> str:
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

content = content.replace(anchor, resolver_function, 1)

# 3. Le champ par défaut de VinaConfig utilise maintenant le resolver
old_field = 'vina_executable: str = "vina"'
new_field = "vina_executable: str = field(default_factory=resolve_vina_executable)"
if old_field not in content:
    raise SystemExit("✗ Champ 'vina_executable' introuvable, patch annulé.")
content = content.replace(old_field, new_field, 1)

# 4. Les deux profils (MexB, MexR) utilisent aussi le resolver
old_profile = 'vina_executable="vina",'
new_profile = "vina_executable=resolve_vina_executable(),"
count = content.count(old_profile)
if count != 2:
    raise SystemExit(
        f"✗ Attendu 2 occurrences de 'vina_executable=\"vina\",', trouvé {count}. Patch annulé."
    )
content = content.replace(old_profile, new_profile)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée, quelque chose ne va pas.")

TARGET.write_text(content, encoding="utf-8")
print(f"✓ Patch appliqué avec succès sur {TARGET}")
print("  - resolve_vina_executable() ajoutée")
print("  - VinaConfig.vina_executable utilise maintenant le resolver")
print("  - Les 2 profils MexB/MexR utilisent maintenant le resolver")
