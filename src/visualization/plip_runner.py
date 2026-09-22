
from pathlib import Path
import subprocess


def _pdb_atom_serial(line):
    if not line.startswith(("ATOM  ", "HETATM")):
        return None
    try:
        return int(line[6:11])
    except ValueError:
        return None


def _renumber_pdb_block(lines, offset):
    serial_map = {}
    for line in lines:
        serial = _pdb_atom_serial(line)
        if serial is not None:
            serial_map[serial] = serial + offset

    output = []
    for line in lines:
        serial = _pdb_atom_serial(line)
        if serial is not None:
            line = line[:6] + f"{serial_map[serial]:5d}" + line[11:]
        elif line.startswith("CONECT"):
            fields = [line[index:index + 5] for index in range(6, len(line), 5)]
            mapped = []
            for field in fields:
                try:
                    value = serial_map[int(field)]
                except (ValueError, KeyError):
                    continue
                mapped.append(f"{value:5d}")
            line = "CONECT" + "".join(mapped)
        output.append(line)
    return output, serial_map


def _merge_pdb_files(receptor_path, ligand_path, output_path):
    receptor_lines = receptor_path.read_text(errors="ignore").splitlines()
    ligand_lines = ligand_path.read_text(errors="ignore").splitlines()

    receptor_block, receptor_map = _renumber_pdb_block(receptor_lines, 0)
    receptor_max = max(receptor_map.values(), default=0)
    ligand_block, _ = _renumber_pdb_block(ligand_lines, receptor_max)

    merged = []
    for line in receptor_block:
        if line.startswith(("END", "MASTER")):
            continue
        merged.append(line)
    merged.append("TER")
    for line in ligand_block:
        if line.startswith(("END", "MASTER")):
            continue
        merged.append(line)
    merged.append("END")
    output_path.write_text("\n".join(merged) + "\n")


class PLIPRunner:


    def __init__(self, workdir="visualization_results/plip"):

        self.workdir = Path(workdir)
        self.workdir.mkdir(
            parents=True,
            exist_ok=True
        )


    def extract_first_pose(
        self,
        pdbqt,
        output
    ):

        pdbqt = Path(pdbqt)
        output = Path(output)


        lines = pdbqt.read_text().splitlines()


        has_model = any(
            l.startswith("MODEL")
            for l in lines
        )


        with output.open("w") as out:


            if has_model:

                inside = False

                for line in lines:

                    if line.startswith("MODEL 1"):
                        inside = True
                        continue


                    if line.startswith("ENDMDL"):
                        break


                    if inside:
                        out.write(line + "\n")


            else:

                for line in lines:

                    if (
                        line.startswith("ATOM")
                        or line.startswith("HETATM")
                        or line.startswith("TER")
                    ):
                        out.write(line + "\n")


                out.write("END\n")


        count = sum(
            1
            for l in output.read_text().splitlines()
            if l.startswith("ATOM")
        )


        print(
            "Extraction PDBQT:",
            output,
            "ATOM=",
            count
        )
    def convert_pdbqt_to_pdb(
        self,
        pdbqt,
        output
    ):

        tmp = Path(str(output)+".pdbqt")

        self.extract_first_pose(
            pdbqt,
            tmp
        )


        from src.tools.obabel_locator import (
            resolve_obabel_executable,
            obabel_subprocess_env,
        )

        subprocess.run(
            [
                resolve_obabel_executable(),
                "-ipdbqt",
                str(tmp),
                "-opdb",
                "-O",
                str(output)
            ],
            check=True,
            env=obabel_subprocess_env(),
        )


        # Conversion ligand ATOM -> HETATM pour PLIP
        lines = []

        for line in output.read_text().splitlines():

            if (
                line.startswith("ATOM")
                and " UNL " in line
            ):

                line = (
                    "HETATM"
                    + line[6:]
                )

                # insertion chaine A
                line = (
                    line[:21]
                    + "A"
                    + line[22:]
                )

            lines.append(line)


        output.write_text(
            "\n".join(lines)
            + "\n"
        )


        tmp.unlink()


    def prepare_complex(
        self,
        receptor,
        pose,
        ligand_id
    ):


        receptor_pdb = (
            self.workdir /
            "receptor.pdb"
        )

        ligand_pdb = (
            self.workdir /
            f"{ligand_id}_ligand.pdb"
        )


        self.convert_pdbqt_to_pdb(
            receptor,
            receptor_pdb
        )


        # Vérification récepteur
        atom_count = 0

        for line in receptor_pdb.read_text().splitlines():

            if line.startswith("ATOM"):
                atom_count += 1


        if atom_count < 100:

            raise RuntimeError(
                f"Récepteur invalide : seulement {atom_count} atomes"
            )


        self.convert_pdbqt_to_pdb(
            pose,
            ligand_pdb
        )


        complex_file = (
            self.workdir /
            f"{ligand_id}_complex.pdb"
        )


        # Les deux PDB produits par Open Babel commencent leur numerotation
        # atomique a 1. Les concatener tels quels fait interpreter les
        # CONECT du ligand comme des liaisons vers les premiers atomes du
        # recepteur. Le ligand doit donc etre renumerote avant la fusion.
        _merge_pdb_files(receptor_pdb, ligand_pdb, complex_file)


        return complex_file



    def run(
        self,
        receptor,
        pose,
        ligand_id
    ):


        complex_file = self.prepare_complex(
            receptor,
            pose,
            ligand_id
        )


        # Dossier PLIP isolé pour chaque molécule.
        # Évite le mélange des rapports XML entre plusieurs hits.
        molecule_workdir = self.workdir / ligand_id
        molecule_workdir.mkdir(
            parents=True,
            exist_ok=True
        )

        import sys

        if getattr(sys, "frozen", False):
            command = [
                sys.executable,
                "--plip-worker",
                "-f",
                str(complex_file),
                "-o",
                str(molecule_workdir),
                "-x",
            ]
        else:
            import shutil as _shutil

            plip_exe = _shutil.which("plip")

            if plip_exe:
                command = [
                    plip_exe,
                    "-f",
                    str(complex_file),
                    "-o",
                    str(molecule_workdir),
                    "-x",
                ]
            else:
                try:
                    import plip  # noqa: F401
                except ImportError as exc:
                    raise RuntimeError(
                        "PLIP introuvable : ni la commande 'plip' sur le PATH, "
                        "ni le module 'plip' importable depuis l'interpreteur "
                        f"actuel ({sys.executable}). Verifie que PLIP est "
                        "installe dans le meme environnement Python que celui "
                        "qui execute l'application, ou active le venv du "
                        "projet avant de la lancer."
                    ) from exc

                command = [
                    sys.executable,
                    "-m",
                    "plip.plipcmd",
                    "-f",
                    str(complex_file),
                    "-o",
                    str(molecule_workdir),
                    "-x",
                ]

        from src.tools.obabel_locator import obabel_subprocess_env

        subprocess.run(command, check=True, env=obabel_subprocess_env())

        # PLIP produit normalement :
        # <complex_name>_report.xml
        expected_xml = (
            molecule_workdir /
            f"{complex_file.stem}_report.xml"
        )

        if not expected_xml.exists():

            xmls = sorted(
                molecule_workdir.glob("*_report.xml"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            if not xmls:
                raise RuntimeError(
                    f"Aucun XML PLIP généré pour {ligand_id}. "
                    f"Dossier : {molecule_workdir}"
                )

            expected_xml = xmls[0]

        return {
            "complex": str(complex_file),
            "xml": str(expected_xml)
        }
