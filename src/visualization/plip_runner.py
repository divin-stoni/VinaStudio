
from pathlib import Path
import subprocess


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


        with open(complex_file, "w") as out:

            # IMPORTANT : receptor_pdb et ligand_pdb sont chacun produits
            # par obabel, qui termine son PDB par une ligne END/ENDMDL.
            # Si on les concatene tels quels, ce END se retrouve AU MILIEU
            # du complexe -> PLIP arrete de lire le fichier juste apres le
            # recepteur et ne voit JAMAIS le ligand (aucun crash, mais
            # 0 interaction detectee). On filtre donc ces lignes de fin
            # dans chaque bloc, et on n'ecrit qu'un seul END, a la toute
            # fin du fichier complet.

            for i, f in enumerate([receptor_pdb, ligand_pdb]):

                for line in f.read_text().splitlines():

                    if line.startswith("END"):
                        # capture END et ENDMDL, qu'on ne veut pas ici
                        continue

                    out.write(line + "\n")

                if i == 0:
                    # separateur propre entre recepteur et ligand
                    out.write("TER\n")

            out.write("END\n")


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
            command = [
                "plip",
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
