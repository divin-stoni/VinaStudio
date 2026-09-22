#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch en une passe :
  1) main_window.py : message fpocket adapte a la plateforme (Windows =
     "non disponible", plus de "sudo apt install" affiche a un utilisateur
     Windows).
  2) Suppression complete de ChimeraX du logiciel :
       - tool_manager.py       : entree "chimerax", methode check_chimerax(),
                                  entree dans check_all()
       - environment_manager.py: Dependency("ChimeraX"), methode
                                  detect_chimerax(), branche du dispatch
       - structural_validator.py : mention ChimeraX dans le docstring
       - diagnose_docking_ui.py  : "chimerax" retire de DOMAIN_WHITELIST
       - suppression (avec sauvegarde) de 3 fichiers 100% orphelins :
         interaction_3d.py, pose_manager.py, interaction_visualizer.py

Securites :
  - sauvegarde horodatee de chaque fichier AVANT toute modification
  - chaque remplacement est un bloc de texte EXACT (echoue proprement
    si le texte attendu n'est pas trouve, ne devine jamais)
  - verification ast.parse() sur les 4 fichiers .py patches, apres coup
  - rapport clair en fin d'execution

Usage :
    python3 patch_fpocket_et_suppression_chimerax.py           # applique
    python3 patch_fpocket_et_suppression_chimerax.py --check   # verifie seulement
"""

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

CHECK_ONLY = "--check" in sys.argv


# ============================================================================
# UTILITAIRES
# ============================================================================

def backup(path: Path):
    bak = path.with_name(f"{path.name}.bak_chimerax_removal_{BACKUP_TS}")
    shutil.copy2(path, bak)
    return bak


def apply_replacement(path: Path, old: str, new: str, label: str, report: list):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)

    if count == 0:
        report.append(f"[ECHEC] {label} : bloc attendu introuvable dans {path}. Rien modifie pour ce bloc.")
        return False
    if count > 1:
        report.append(f"[ECHEC] {label} : bloc trouve {count} fois (non-unique) dans {path}. Rien modifie pour ce bloc.")
        return False

    new_text = text.replace(old, new, 1)
    path.write_text(new_text, encoding="utf-8")
    report.append(f"[OK] {label}")
    return True


def check_syntax(path: Path, report: list):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        report.append(f"[OK] Syntaxe valide : {path}")
        return True
    except SyntaxError as exc:
        report.append(f"[ERREUR SYNTAXE] {path} : {exc}")
        return False


def delete_with_backup(path: Path, report: list):
    if not path.exists():
        report.append(f"[IGNORE] {path} deja absent.")
        return
    bak = path.with_name(f"{path.name}.deleted_backup_{BACKUP_TS}")
    shutil.move(str(path), str(bak))
    report.append(f"[OK] Supprime (sauvegarde : {bak.name}) : {path}")


# ============================================================================
# BLOCS DE REMPLACEMENT
# ============================================================================

PATCHES = []

# ---- 1) main_window.py : message fpocket adapte a la plateforme ----------
MAIN_WINDOW = PROJECT_ROOT / "src/gui/main_window.py"

OLD_FPOCKET_MSG = '''        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "fpocket introuvable",
                "La commande 'fpocket' n'a pas été trouvée dans le PATH. "
                "Installez fpocket (ex. 'sudo apt install fpocket') puis réessayez.",
            )
            self._fpocket_status_label.setText("")'''

NEW_FPOCKET_MSG = '''        except FileNotFoundError:
            import sys as _vs_sys
            if _vs_sys.platform.startswith("win"):
                QMessageBox.critical(
                    self,
                    "fpocket introuvable",
                    "La détection des poches (fpocket) n'est disponible que sous Linux. "
                    "Cette fonctionnalité n'est pas proposée sous Windows.",
                )
            else:
                QMessageBox.critical(
                    self,
                    "fpocket introuvable",
                    "La commande 'fpocket' n'a pas été trouvée dans le PATH. "
                    "Installez fpocket (ex. 'sudo apt install fpocket') puis réessayez.",
                )
            self._fpocket_status_label.setText("")'''

PATCHES.append((MAIN_WINDOW, OLD_FPOCKET_MSG, NEW_FPOCKET_MSG, "main_window.py : message fpocket adapte a la plateforme"))

# ---- 2) tool_manager.py ----------------------------------------------------
TOOL_MANAGER = PROJECT_ROOT / "src/tools/tool_manager.py"

OLD_TM_DICT = '''            "chimerax": {
                "name": "ChimeraX",
                "required": False,
                "executables": ["chimerax", "ChimeraX"],
            },
        }'''
NEW_TM_DICT = '''        }'''
PATCHES.append((TOOL_MANAGER, OLD_TM_DICT, NEW_TM_DICT, "tool_manager.py : entree 'chimerax' retiree du dict definitions"))

OLD_TM_METHOD = '''    # ------------------------------------------------------------------
    # CHIMERAX
    # ------------------------------------------------------------------

    def check_chimerax(self):
        definition = self.definitions["chimerax"]

        executable = self.find_executable(
            definition["executables"]
        )

        # Recherche complémentaire des emplacements courants.
        candidates = [
            "/usr/lib/ucsf-chimerax/bin/ChimeraX",
            "/usr/bin/chimerax",
            "/usr/local/bin/chimerax",
        ]

        if not executable:
            for candidate in candidates:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    executable = os.path.realpath(candidate)
                    break

        if not executable:
            return ToolResult(
                key="chimerax",
                name=definition["name"],
                status="NOT_FOUND",
                message="ChimeraX introuvable."
            )

        code, output = self.run_command(
            [executable, "--version"],
            timeout=20
        )

        if code != 0:
            return ToolResult(
                key="chimerax",
                name=definition["name"],
                status="FOUND_BUT_NOT_TESTED",
                path=executable,
                message=output
            )

        return ToolResult(
            key="chimerax",
            name=definition["name"],
            status="READY",
            path=executable,
            version=self.clean_version(output)
        )

    # ------------------------------------------------------------------
    # CHECK GLOBAL
    # ------------------------------------------------------------------'''
NEW_TM_METHOD = '''    # ------------------------------------------------------------------
    # CHECK GLOBAL
    # ------------------------------------------------------------------'''
PATCHES.append((TOOL_MANAGER, OLD_TM_METHOD, NEW_TM_METHOD, "tool_manager.py : methode check_chimerax() supprimee"))

OLD_TM_CHECKALL = '''        self.results = {
            "vina": self.check_vina(),
            "openbabel": self.check_openbabel(),
            "pymol": self.check_pymol(),
            "chimerax": self.check_chimerax(),
        }'''
NEW_TM_CHECKALL = '''        self.results = {
            "vina": self.check_vina(),
            "openbabel": self.check_openbabel(),
            "pymol": self.check_pymol(),
        }'''
PATCHES.append((TOOL_MANAGER, OLD_TM_CHECKALL, NEW_TM_CHECKALL, "tool_manager.py : 'chimerax' retire de check_all()"))

# ---- 3) environment_manager.py --------------------------------------------
ENV_MANAGER = PROJECT_ROOT / "src/environment/environment_manager.py"

OLD_EM_DEP = '''            Dependency(
                name="PyMOL",
                key="pymol",
                commands=["pymol"],
                required=False,
            ),

            Dependency(
                name="ChimeraX",
                key="chimerax",
                commands=["chimerax"],
                required=False,
            ),
        ]'''
NEW_EM_DEP = '''            Dependency(
                name="PyMOL",
                key="pymol",
                commands=["pymol"],
                required=False,
            ),
        ]'''
PATCHES.append((ENV_MANAGER, OLD_EM_DEP, NEW_EM_DEP, "environment_manager.py : Dependency('ChimeraX') retiree"))

OLD_EM_METHOD = '''    # ============================================================
    # CHIMERAX
    # ============================================================

    def detect_chimerax(self, dependency):

        path = (
            self.get_saved_path("chimerax")
            or self.find_executable(
                ["chimerax"]
            )
        )

        if not path:

            dependency.status = "NOT_FOUND"
            return

        dependency.path = path

        output = self.run_command(
            [
                path,
                "--version"
            ],
            timeout=15
        )

        if output:

            version = None

            for line in output.splitlines():

                if (
                    "ChimeraX version"
                    in line
                ):

                    version = line.strip()
                    break

            dependency.version = (
                version
                or output.splitlines()[0]
            )

            dependency.status = "READY"

        else:

            dependency.status = (
                "FOUND_BUT_NOT_TESTED"
            )

    # ============================================================
    # SCAN
    # ============================================================'''
NEW_EM_METHOD = '''    # ============================================================
    # SCAN
    # ============================================================'''
PATCHES.append((ENV_MANAGER, OLD_EM_METHOD, NEW_EM_METHOD, "environment_manager.py : methode detect_chimerax() supprimee"))

OLD_EM_DISPATCH = '''        elif dependency.key == "pymol":

            self.detect_pymol(
                dependency
            )

        elif dependency.key == "chimerax":

            self.detect_chimerax(
                dependency
            )'''
NEW_EM_DISPATCH = '''        elif dependency.key == "pymol":

            self.detect_pymol(
                dependency
            )'''
PATCHES.append((ENV_MANAGER, OLD_EM_DISPATCH, NEW_EM_DISPATCH, "environment_manager.py : branche 'chimerax' retiree du dispatch"))

# ---- 4) structural_validator.py -------------------------------------------
STRUCT_VALIDATOR = PROJECT_ROOT / "src/analysis/structural_validator.py"

OLD_SV = "avec ChimeraX ou Discovery Studio."
NEW_SV = "avec un logiciel de visualisation structurale (ex. PyMOL)."
PATCHES.append((STRUCT_VALIDATOR, OLD_SV, NEW_SV, "structural_validator.py : mention ChimeraX retiree du docstring"))

# ---- 5) diagnose_docking_ui.py ---------------------------------------------
DIAG_DOCKING = PROJECT_ROOT / "src/diagnose_docking_ui.py"

OLD_DD = '    "pdb", "pdbqt", "vina", "fpocket", "csv", "gui", "sdf", "chimerax",'
NEW_DD = '    "pdb", "pdbqt", "vina", "fpocket", "csv", "gui", "sdf",'
PATCHES.append((DIAG_DOCKING, OLD_DD, NEW_DD, "diagnose_docking_ui.py : 'chimerax' retire de DOMAIN_WHITELIST"))


# ============================================================================
# FICHIERS A SUPPRIMER ENTIEREMENT (orphelins confirmes)
# ============================================================================

FILES_TO_DELETE = [
    PROJECT_ROOT / "src/visualization/interaction_3d.py",
    PROJECT_ROOT / "src/visualization/pose_manager.py",
    PROJECT_ROOT / "src/visualization/interaction_visualizer.py",
]


# ============================================================================
# EXECUTION
# ============================================================================

def main():
    report = []
    touched_files = set()

    mode = "VERIFICATION SEULE (--check)" if CHECK_ONLY else "APPLICATION"
    print(f"=== Mode : {mode} ===\n")

    if CHECK_ONLY:
        for path, old, _new, label in PATCHES:
            if not path.exists():
                report.append(f"[ABSENT] {path}")
                continue
            text = path.read_text(encoding="utf-8")
            count = text.count(old)
            if count == 1:
                report.append(f"[PRESENT] {label} -- pret a etre patche")
            elif count == 0:
                report.append(f"[DEJA APPLIQUE OU DIFFERENT] {label} -- bloc non trouve tel quel")
            else:
                report.append(f"[AMBIGU] {label} -- bloc trouve {count} fois")
        for path in FILES_TO_DELETE:
            report.append(f"[{'PRESENT, sera supprime' if path.exists() else 'DEJA ABSENT'}] {path}")
        print("\n".join(report))
        return

    # --- Sauvegardes ---
    all_paths = {p for p, *_ in PATCHES} | set(FILES_TO_DELETE)
    for path in all_paths:
        if path.exists():
            bak = backup(path)
            report.append(f"[BACKUP] {path} -> {bak.name}")

    # --- Remplacements ---
    for path, old, new, label in PATCHES:
        if not path.exists():
            report.append(f"[ECHEC] {label} : fichier introuvable {path}")
            continue
        ok = apply_replacement(path, old, new, label, report)
        if ok:
            touched_files.add(path)

    # --- Suppressions ---
    for path in FILES_TO_DELETE:
        delete_with_backup(path, report)

    # --- Verification syntaxique ---
    print("\n--- Verification ast.parse() sur les fichiers modifies ---")
    all_ok = True
    for path in touched_files:
        if not check_syntax(path, report):
            all_ok = False

    print("\n".join(report))
    print("\n=== RESULTAT GLOBAL ===")
    if all_ok:
        print("Tous les fichiers modifies sont syntaxiquement valides.")
    else:
        print("!! Au moins un fichier a une erreur de syntaxe -- verifier au-dessus avant de lancer l'app.")


if __name__ == "__main__":
    main()
