#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "environment.json"


@dataclass
class Dependency:

    name: str
    key: str
    commands: list[str]
    required: bool = False

    path: Optional[str] = None
    version: Optional[str] = None
    python_path: Optional[str] = None

    status: str = "NOT_FOUND"


class EnvironmentManager:

    def __init__(self):

        self.dependencies = [

            Dependency(
                name="AutoDock Vina",
                key="vina",
                commands=["vina"],
                required=True,
            ),

            Dependency(
                name="Open Babel",
                key="openbabel",
                commands=["obabel"],
                required=True,
            ),

            Dependency(
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
        ]

        self.saved_config = self.load_config()

    # ============================================================
    # CONFIGURATION
    # ============================================================

    def load_config(self):

        if not CONFIG_FILE.exists():
            return {}

        try:

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except (
            json.JSONDecodeError,
            OSError,
        ):

            return {}

    def save_config(self):

        CONFIG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        data = {
            "application": {
                "python": sys.executable,
                "python_version": sys.version.split()[0],
            },

            "dependencies": {}
        }

        for dependency in self.dependencies:

            data["dependencies"][
                dependency.key
            ] = {

                "name": dependency.name,

                "path": dependency.path,

                "version": dependency.version,

                "python_path": dependency.python_path,

                "required": dependency.required,

                "status": dependency.status,
            }

        temporary_file = CONFIG_FILE.with_suffix(
            ".tmp"
        )

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        temporary_file.replace(
            CONFIG_FILE
        )

    # ============================================================
    # COMMANDS
    # ============================================================

    @staticmethod
    def find_executable(commands):

        for command in commands:

            path = shutil.which(command)

            if path:
                return os.path.realpath(path)

        return None

    @staticmethod
    def run_command(
        command,
        timeout=10
    ):

        try:

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
            )

            output = result.stdout.strip()

            if output:
                return output

        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            OSError,
        ):

            pass

        return None

    # ============================================================
    # SAVED PATH
    # ============================================================

    def get_saved_path(self, key):

        dependency_data = (
            self.saved_config
            .get("dependencies", {})
            .get(key, {})
        )

        path = dependency_data.get("path")

        if path and os.path.exists(path):

            return path

        return None

    # ============================================================
    # VINA
    # ============================================================

    def detect_vina(self, dependency):

        path = (
            self.get_saved_path("vina")
            or self.find_executable(
                ["vina"]
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
            ]
        )

        if output:

            dependency.version = (
                output.splitlines()[0]
            )

            dependency.status = "READY"

        else:

            dependency.status = (
                "FOUND_BUT_NOT_TESTED"
            )

    # ============================================================
    # OPEN BABEL
    # ============================================================

    def detect_openbabel(self, dependency):

        path = (
            self.get_saved_path("openbabel")
            or self.find_executable(
                ["obabel"]
            )
        )

        if not path:

            dependency.status = "NOT_FOUND"
            return

        dependency.path = path

        output = self.run_command(
            [
                path,
                "-V"
            ]
        )

        if output:

            dependency.version = (
                output.splitlines()[0]
            )

            dependency.status = "READY"

        else:

            dependency.status = (
                "FOUND_BUT_NOT_TESTED"
            )

    # ============================================================
    # PYMOL
    # ============================================================

    def detect_pymol(self, dependency):

        path = (
            self.get_saved_path("pymol")
            or self.find_executable(
                ["pymol"]
            )
        )

        if not path:

            dependency.status = "NOT_FOUND"
            return

        dependency.path = path

        python_candidates = []

        saved_python = (
            self.saved_config
            .get("dependencies", {})
            .get("pymol", {})
            .get("python_path")
        )

        if saved_python:
            python_candidates.append(
                saved_python
            )

        python_candidates.extend([
            "/usr/bin/python3",
            shutil.which("python3"),
        ])

        tested = set()

        for python_path in python_candidates:

            if not python_path:
                continue

            python_path = os.path.realpath(
                python_path
            )

            if python_path in tested:
                continue

            tested.add(python_path)

            if not os.path.exists(
                python_path
            ):
                continue

            test = self.run_command(
                [
                    python_path,
                    "-c",
                    "import pymol; "
                    "print(pymol.__file__)"
                ]
            )

            if not test:
                continue

            dependency.python_path = (
                python_path
            )

            version = self.run_command(
                [
                    python_path,
                    "-c",
                    (
                        "import pymol; "
                        "print("
                        "getattr("
                        "pymol,"
                        "'__version__',"
                        "'unknown'"
                        ")"
                        ")"
                    )
                ]
            )

            dependency.version = (
                version.splitlines()[0]
                if version
                else "Detected"
            )

            dependency.status = "READY"

            return

        dependency.status = (
            "FOUND_BUT_NOT_TESTED"
        )

    # ============================================================
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
    # ============================================================

    def scan_dependency(self, dependency):

        if dependency.key == "vina":

            self.detect_vina(dependency)

        elif dependency.key == "openbabel":

            self.detect_openbabel(
                dependency
            )

        elif dependency.key == "pymol":

            self.detect_pymol(
                dependency
            )

        elif dependency.key == "chimerax":

            self.detect_chimerax(
                dependency
            )

    def scan(self):

        for dependency in self.dependencies:

            self.scan_dependency(
                dependency
            )

        self.save_config()

        return self.dependencies

    # ============================================================
    # REPORT
    # ============================================================

    def print_dependency(
        self,
        dependency
    ):

        if dependency.status == "READY":

            symbol = "✓"

        elif dependency.status == (
            "FOUND_BUT_NOT_TESTED"
        ):

            symbol = "⚠"

        else:

            symbol = "✗"

        requirement = (
            "REQUIRED"
            if dependency.required
            else "OPTIONAL"
        )

        print(
            f"{dependency.name:<20}"
            f" {symbol} "
            f"{dependency.status}"
        )

        print(
            f"  Type    : {requirement}"
        )

        if dependency.path:

            print(
                f"  Path    : "
                f"{dependency.path}"
            )

        if dependency.version:

            print(
                f"  Version : "
                f"{dependency.version}"
            )

        if dependency.python_path:

            print(
                f"  Python  : "
                f"{dependency.python_path}"
            )

        print()

    def report(self):

        print("=" * 70)
        print(
            "MEXAB/MEXR ANALYZER "
            "— ENVIRONMENT CHECK"
        )
        print("=" * 70)
        print()

        print("APPLICATION PYTHON")
        print("-" * 70)

        print(
            f"Version : "
            f"{sys.version.split()[0]}"
        )

        print(
            f"Path    : "
            f"{sys.executable}"
        )

        print()

        print(
            "SCIENTIFIC DEPENDENCIES"
        )

        print("-" * 70)

        dependencies = self.scan()

        for dependency in dependencies:

            self.print_dependency(
                dependency
            )

        required = [
            d for d in dependencies
            if d.required
        ]

        optional = [
            d for d in dependencies
            if not d.required
        ]

        required_ready = [
            d for d in required
            if d.status == "READY"
        ]

        optional_ready = [
            d for d in optional
            if d.status == "READY"
        ]

        print("=" * 70)
        print("ENVIRONMENT SUMMARY")
        print("=" * 70)

        print(
            f"Required components : "
            f"{len(required_ready)}/"
            f"{len(required)}"
        )

        print(
            f"Optional components : "
            f"{len(optional_ready)}/"
            f"{len(optional)}"
        )

        if (
            len(required_ready)
            == len(required)
        ):

            print(
                "Environment         : READY"
            )

        else:

            print(
                "Environment         : "
                "INCOMPLETE"
            )

        print()

        print(
            f"Configuration : "
            f"{CONFIG_FILE}"
        )

        print("=" * 70)


def main():

    manager = EnvironmentManager()

    manager.report()


if __name__ == "__main__":

    main()
