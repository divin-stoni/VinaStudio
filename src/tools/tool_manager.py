#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
ENV_FILE = CONFIG_DIR / "environment.json"


@dataclass
class ToolResult:
    key: str
    name: str
    status: str
    path: str | None = None
    version: str | None = None
    runtime: str | None = None
    module: str | None = None
    message: str | None = None


class ToolManager:
    """
    Gestionnaire central des outils externes.

    Objectifs :
    - détecter automatiquement les outils ;
    - tester leur véritable exécution ;
    - gérer les outils Python installés hors du venv ;
    - mémoriser les chemins détectés ;
    - fournir une API commune au reste de l'application.
    """

    def __init__(self):
        self.results = {}

        self.definitions = {
            "vina": {
                "name": "AutoDock Vina",
                "required": True,
                "executables": ["vina"],
            },
            "openbabel": {
                "name": "Open Babel",
                "required": True,
                "executables": ["obabel"],
            },
            "pymol": {
                "name": "PyMOL",
                "required": False,
                "executables": ["pymol"],
                "python_modules": ["pymol"],
                "python_runtimes": [
                    "/usr/bin/python3",
                    "/usr/local/bin/python3",
                ],
            },
            "chimerax": {
                "name": "ChimeraX",
                "required": False,
                "executables": ["chimerax", "ChimeraX"],
            },
        }

    # ------------------------------------------------------------------
    # UTILITAIRES
    # ------------------------------------------------------------------

    @staticmethod
    def find_executable(names):
        for name in names:
            path = shutil.which(name)
            if path:
                return os.path.realpath(path)
        return None

    @staticmethod
    def run_command(command, timeout=10):
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )

            return result.returncode, result.stdout.strip()

        except subprocess.TimeoutExpired:
            return -1, "TIMEOUT"

        except Exception as exc:
            return -1, str(exc)

    @staticmethod
    def clean_version(output):
        if not output:
            return "unknown"

        lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        if not lines:
            return "unknown"

        return lines[0][:300]

    # ------------------------------------------------------------------
    # PYTHON MODULE DETECTION
    # ------------------------------------------------------------------

    @staticmethod
    def python_has_module(python_path, module):
        code = (
            "import importlib.util; "
            f"spec=importlib.util.find_spec('{module}'); "
            "print(spec.origin if spec else '')"
        )

        code_return, output = ToolManager.run_command(
            [python_path, "-c", code]
        )

        if code_return != 0:
            return None

        output = output.strip()

        if not output or output == "None":
            return None

        return output

    def find_python_module(self, module, runtimes):
        """
        Recherche un module Python dans plusieurs runtimes.

        Priorité :
        1. Python actuellement utilisé
        2. Python système
        3. autres runtimes connus
        """

        candidates = []

        current_python = sys.executable
        if current_python:
            candidates.append(current_python)

        candidates.extend(runtimes)

        seen = set()

        for python_path in candidates:
            if not python_path:
                continue

            python_path = os.path.realpath(python_path)

            if python_path in seen:
                continue

            seen.add(python_path)

            if not os.path.exists(python_path):
                continue

            module_path = self.python_has_module(
                python_path,
                module
            )

            if module_path:
                return python_path, module_path

        return None, None

    # ------------------------------------------------------------------
    # VINA
    # ------------------------------------------------------------------

    def check_vina(self):
        definition = self.definitions["vina"]

        path = self.find_executable(
            definition["executables"]
        )

        if not path:
            return ToolResult(
                key="vina",
                name=definition["name"],
                status="NOT_FOUND",
                message="Executable introuvable."
            )

        code, output = self.run_command(
            [path, "--version"]
        )

        if code != 0:
            return ToolResult(
                key="vina",
                name=definition["name"],
                status="BROKEN",
                path=path,
                message=output
            )

        return ToolResult(
            key="vina",
            name=definition["name"],
            status="READY",
            path=path,
            version=self.clean_version(output)
        )

    # ------------------------------------------------------------------
    # OPEN BABEL
    # ------------------------------------------------------------------

    def check_openbabel(self):
        definition = self.definitions["openbabel"]

        path = self.find_executable(
            definition["executables"]
        )

        if not path:
            return ToolResult(
                key="openbabel",
                name=definition["name"],
                status="NOT_FOUND",
                message="Executable introuvable."
            )

        code, output = self.run_command(
            [path, "-V"]
        )

        if code != 0:
            return ToolResult(
                key="openbabel",
                name=definition["name"],
                status="BROKEN",
                path=path,
                message=output
            )

        return ToolResult(
            key="openbabel",
            name=definition["name"],
            status="READY",
            path=path,
            version=self.clean_version(output)
        )

    # ------------------------------------------------------------------
    # PYMOL
    # ------------------------------------------------------------------

    def check_pymol(self):
        definition = self.definitions["pymol"]

        executable = self.find_executable(
            definition["executables"]
        )

        python_path, module_path = self.find_python_module(
            "pymol",
            definition["python_runtimes"]
        )

        # Cas idéal : module PyMOL détecté avec un Python valide.
        if python_path and module_path:

            code, output = self.run_command(
                [
                    python_path,
                    "-m",
                    "pymol.__init__",
                    "-cq"
                ],
                timeout=20
            )

            if code == 0:
                return ToolResult(
                    key="pymol",
                    name=definition["name"],
                    status="READY",
                    path=executable or module_path,
                    version="validated",
                    runtime=python_path,
                    module=module_path
                )

            return ToolResult(
                key="pymol",
                name=definition["name"],
                status="BROKEN",
                path=executable or module_path,
                runtime=python_path,
                module=module_path,
                message=output
            )

        if executable:
            return ToolResult(
                key="pymol",
                name=definition["name"],
                status="FOUND_BUT_NOT_READY",
                path=executable,
                message=(
                    "PyMOL executable trouvé, mais aucun "
                    "runtime Python contenant le module pymol "
                    "n'a été détecté."
                )
            )

        return ToolResult(
            key="pymol",
            name=definition["name"],
            status="NOT_FOUND",
            message="PyMOL introuvable."
        )

    # ------------------------------------------------------------------
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
    # ------------------------------------------------------------------

    def check_all(self):
        self.results = {
            "vina": self.check_vina(),
            "openbabel": self.check_openbabel(),
            "pymol": self.check_pymol(),
            "chimerax": self.check_chimerax(),
        }

        return self.results

    # ------------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------------

    def build_environment_config(self):
        application_python = os.path.realpath(sys.executable)

        config = {
            "application": {
                "python": application_python,
                "python_version": sys.version.split()[0],
            },
            "tools": {},
        }

        for key, result in self.results.items():
            definition = self.definitions[key]

            config["tools"][key] = {
                "name": result.name,
                "path": result.path,
                "version": result.version,
                "runtime": result.runtime,
                "module": result.module,
                "required": definition["required"],
                "status": result.status,
                "message": result.message,
            }

        return config

    def save_environment(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        config = self.build_environment_config()

        with open(ENV_FILE, "w", encoding="utf-8") as handle:
            json.dump(
                config,
                handle,
                indent=4,
                ensure_ascii=False
            )

        return ENV_FILE

    # ------------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------------

    def print_report(self):

        print("=" * 70)
        print("MEXAB/MEXR ANALYZER — TOOL MANAGER")
        print("=" * 70)

        for key, result in self.results.items():

            definition = self.definitions[key]

            print()
            print(result.name)
            print("-" * 70)
            print(f"Status  : {result.status}")
            print(f"Required: {'YES' if definition['required'] else 'NO'}")
            print(f"Path    : {result.path or 'N/A'}")

            if result.version:
                print(f"Version : {result.version}")

            if result.runtime:
                print(f"Runtime : {result.runtime}")

            if result.module:
                print(f"Module  : {result.module}")

            if result.message:
                print(f"Message : {result.message}")

        print()
        print("=" * 70)
        print("===== TEST PATHS =====")
        print("=" * 70)

        for key, result in self.results.items():
            print(
                f"{key:<12} -> "
                f"{result.path or 'NOT FOUND'}"
            )

        config_path = self.save_environment()

        print()
        print("=" * 70)
        print(f"Configuration sauvegardée : {config_path}")
        print("=" * 70)


def main():
    manager = ToolManager()
    manager.check_all()
    manager.print_report()


if __name__ == "__main__":
    main()
