# -*- coding: utf-8 -*-

"""
sdf_preparer.py

Préparation de ligands depuis un ou plusieurs fichiers SDF
et/ou dossiers contenant des fichiers SDF vers PDBQT.

Le module ne lance aucun docking.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess


def _safe_name(name: str, fallback: str) -> str:
    value = str(name or "").strip()

    if not value:
        value = fallback

    value = re.sub(
        r"[^\w.\-]+",
        "_",
        value,
    )

    value = value.strip("._")

    return value or fallback


def _check_obabel() -> str:
    from src.tools.obabel_locator import resolve_obabel_executable

    executable = resolve_obabel_executable()

    if executable != "obabel" and not Path(executable).exists():
        raise RuntimeError(
            "Open Babel (obabel) est introuvable."
        )

    if executable == "obabel" and shutil.which("obabel") is None:
        raise RuntimeError(
            "Open Babel (obabel) est introuvable."
        )

    return executable


def _collect_sdf_files(
    inputs: list[str | Path],
) -> list[Path]:
    """
    Collecte les fichiers SDF provenant :
        - de fichiers SDF individuels ;
        - de dossiers contenant des SDF.

    Les fichiers sont triés et les doublons supprimés.
    """

    collected: list[Path] = []
    seen: set[Path] = set()

    for item in inputs:

        path = (
            Path(item)
            .expanduser()
            .resolve()
        )

        if not path.exists():
            raise FileNotFoundError(
                "Chemin introuvable :\n"
                + str(path)
            )

        if path.is_file():

            if path.suffix.lower() != ".sdf":
                raise ValueError(
                    "Le fichier sélectionné n'est pas un SDF :\n"
                    + str(path)
                )

            if path not in seen:
                collected.append(path)
                seen.add(path)

        elif path.is_dir():

            files = sorted(
                p.resolve()
                for p in path.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".sdf"
            )

            for sdf_file in files:

                if sdf_file not in seen:
                    collected.append(sdf_file)
                    seen.add(sdf_file)

        else:
            raise ValueError(
                "Chemin invalide :\n"
                + str(path)
            )

    if not collected:
        raise ValueError(
            "Aucun fichier SDF trouvé."
        )

    return collected


def _split_sdf(
    sdf_path: Path,
    work_dir: Path,
    prefix: str,
) -> list[Path]:
    """
    Sépare un SDF multi-molécules en fichiers SDF individuels.
    """

    text = sdf_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    blocks = [
        block.strip() + "\n$$$$\n"
        for block in text.split("$$$$")
        if block.strip()
    ]

    if not blocks:
        raise ValueError(
            "Le fichier SDF ne contient aucune molécule :\n"
            + str(sdf_path)
        )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    outputs = []

    for index, block in enumerate(
        blocks,
        start=1,
    ):

        output = (
            work_dir
            / f"{prefix}_{index:06d}.sdf"
        )

        output.write_text(
            block,
            encoding="utf-8",
        )

        outputs.append(output)

    return outputs


def _molecule_name_from_sdf(
    sdf_file: Path,
    index: int,
) -> str:

    try:
        first_line = (
            sdf_file
            .read_text(
                encoding="utf-8",
                errors="replace",
            )
            .splitlines()[0]
            .strip()
        )
    except Exception:
        first_line = ""

    return _safe_name(
        first_line,
        f"compose_{index}",
    )


def _unique_output_path(
    output_dir: Path,
    molecule_name: str,
) -> Path:
    """
    Évite d'écraser un ligand existant lorsque deux molécules
    portent le même nom.
    """

    candidate = (
        output_dir
        / f"{molecule_name}.pdbqt"
    )

    if not candidate.exists():
        return candidate

    index = 2

    while True:

        candidate = (
            output_dir
            / f"{molecule_name}_{index}.pdbqt"
        )

        if not candidate.exists():
            return candidate

        index += 1


def prepare_sdf(
    sdf_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """
    Compatibilité avec l'ancien appel :

        prepare_sdf(un_fichier_sdf, dossier_sortie)

    """

    return prepare_sdf_files(
        [sdf_path],
        output_dir,
    )


def prepare_sdf_files(
    inputs: list[str | Path],
    output_dir: str | Path,
) -> list[Path]:
    """
    Convertit toutes les molécules provenant de plusieurs SDF
    et/ou dossiers en PDBQT.

    Parameters
    ----------
    inputs:
        Liste de fichiers SDF et/ou dossiers.

    output_dir:
        Dossier de sortie des PDBQT.

    Returns
    -------
    list[Path]
        Liste des PDBQT créés.
    """

    if not inputs:
        raise ValueError(
            "Aucun fichier ou dossier SDF fourni."
        )

    output_dir = (
        Path(output_dir)
        .expanduser()
        .resolve()
    )

    sdf_files = _collect_sdf_files(
        list(inputs)
    )

    obabel = _check_obabel()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    work_dir = (
        output_dir
        / ".sdf_split"
    )

    if work_dir.exists():
        shutil.rmtree(work_dir)

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated: list[Path] = []

    global_index = 1

    try:

        for sdf_index, sdf_file in enumerate(
            sdf_files,
            start=1,
        ):

            prefix = (
                f"sdf_{sdf_index:04d}"
            )

            individual_sdf_files = _split_sdf(
                sdf_file,
                work_dir,
                prefix,
            )

            for individual_sdf in individual_sdf_files:

                molecule_name = (
                    _molecule_name_from_sdf(
                        individual_sdf,
                        global_index,
                    )
                )

                output_pdbqt = _unique_output_path(
                    output_dir,
                    molecule_name,
                )

                command = [
                    obabel,
                    "-isdf",
                    str(individual_sdf),
                    "-opdbqt",
                    "-O",
                    str(output_pdbqt),
                    "-h",
                ]

                from src.tools.obabel_locator import obabel_subprocess_env

                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    env=obabel_subprocess_env(),
                )

                if process.returncode != 0:

                    message = (
                        process.stderr.strip()
                        or process.stdout.strip()
                        or "Erreur Open Babel inconnue."
                    )

                    raise RuntimeError(
                        "Échec de préparation pour "
                        + molecule_name
                        + " :\n"
                        + message
                    )

                if (
                    not output_pdbqt.exists()
                    or output_pdbqt.stat().st_size == 0
                ):

                    raise RuntimeError(
                        "Open Babel n'a pas produit le PDBQT pour "
                        + molecule_name
                        + "."
                    )

                generated.append(
                    output_pdbqt
                )

                global_index += 1

    finally:

        if work_dir.exists():
            shutil.rmtree(work_dir)

    if not generated:
        raise RuntimeError(
            "Aucun ligand PDBQT n'a été préparé."
        )

    return generated
