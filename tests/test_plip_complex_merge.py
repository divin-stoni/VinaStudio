import tempfile
import unittest
from pathlib import Path

from src.visualization.plip_runner import _merge_pdb_files


class PlipComplexMergeTests(unittest.TestCase):
    def test_ligand_atoms_and_conect_are_renumbered(self):
        receptor = (
            "ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N  \n"
            "ATOM      2  C   ALA A   1       1.200   0.000   0.000  1.00  0.00           C  \n"
            "CONECT    1    2\n"
            "END\n"
        )
        ligand = (
            "HETATM    1  C1  UNL A   1       5.000   0.000   0.000  1.00  0.00           C  \n"
            "HETATM    2  O1  UNL A   1       6.200   0.000   0.000  1.00  0.00           O  \n"
            "CONECT    1    2\n"
            "END\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            receptor_path = directory / "receptor.pdb"
            ligand_path = directory / "ligand.pdb"
            output_path = directory / "complex.pdb"
            receptor_path.write_text(receptor)
            ligand_path.write_text(ligand)

            _merge_pdb_files(receptor_path, ligand_path, output_path)

            lines = output_path.read_text().splitlines()
            atoms = [line for line in lines if line.startswith(("ATOM  ", "HETATM"))]
            serials = [int(line[6:11]) for line in atoms]
            conect = [line for line in lines if line.startswith("CONECT")]

            self.assertEqual(serials, [1, 2, 3, 4])
            self.assertEqual(conect, ["CONECT    1    2", "CONECT    3    4"])


if __name__ == "__main__":
    unittest.main()