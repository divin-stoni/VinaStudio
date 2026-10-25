import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.campaign_table import CANONICAL_COLUMNS, normalize_docking_csv
from src.scientific_fusion import create_scientific_scores


def _wide(molecules, mexb, mexr, **extra):
    data = {
        "molecule": molecules,
        "best_affinity_mexb": mexb,
        "best_affinity_mexr": mexr,
    }
    data.update(extra)
    return pd.DataFrame(data)


def _row(table, molecule, receptor_id):
    sel = table[(table["molecule"] == molecule) & (table["receptor_id"] == receptor_id)]
    return sel.iloc[0]


class NormalizeFormatsTests(unittest.TestCase):
    def test_wide_format_gives_one_row_per_molecule_and_receptor(self):
        table = normalize_docking_csv(_wide(["A", "B"], [-5.5, -6.0], [-6.2, -6.7]))
        self.assertEqual(len(table), 4)
        self.assertEqual(set(table["receptor_id"]), {"mexb", "mexr"})
        self.assertEqual(set(table["source_format"]), {"large"})
        self.assertEqual(list(table.columns[: len(CANONICAL_COLUMNS)]), CANONICAL_COLUMNS)
        self.assertAlmostEqual(_row(table, "A", "mexb")["best_affinity"], -5.5)
        self.assertAlmostEqual(_row(table, "B", "mexr")["best_affinity"], -6.7)

    def test_legacy_roles_and_labels_for_mexb_mexr(self):
        table = normalize_docking_csv(_wide(["A"], [-5.5], [-6.2]))
        self.assertEqual(_row(table, "A", "mexb")["role"], "pump")
        self.assertEqual(_row(table, "A", "mexr")["role"], "repressor")
        self.assertEqual(_row(table, "A", "mexb")["receptor_label"], "MexB")
        self.assertEqual(_row(table, "A", "mexr")["receptor_label"], "MexR")

    def test_long_format_is_recognised(self):
        df = pd.DataFrame(
            {
                "molecule": ["A", "A"],
                "receptor_id": ["MexB", "MexR"],
                "best_affinity": [-5.5, -6.2],
            }
        )
        table = normalize_docking_csv(df)
        self.assertEqual(len(table), 2)
        self.assertEqual(set(table["source_format"]), {"long"})
        self.assertEqual(set(table["receptor_id"]), {"mexb", "mexr"})
        self.assertEqual(_row(table, "A", "mexr")["role"], "repressor")

    def test_single_target_uses_hint_or_default(self):
        df = pd.DataFrame({"molecule": ["A", "B"], "best_affinity": [-5.5, -6.0]})
        with_hint = normalize_docking_csv(df, target_hint="mexb")
        self.assertEqual(set(with_hint["receptor_id"]), {"mexb"})
        self.assertEqual(set(with_hint["source_format"]), {"cible_seule"})
        self.assertEqual(set(with_hint["role"]), {"pump"})
        without_hint = normalize_docking_csv(df)
        self.assertEqual(set(without_hint["receptor_id"]), {"cible_unique"})

    def test_target_is_deduced_from_folder_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "acrb_site2_ecoli"
            folder.mkdir()
            csv_path = folder / "docking_results.csv"
            pd.DataFrame({"molecule": ["A"], "best_affinity": [-7.1]}).to_csv(csv_path, index=False)
            table = normalize_docking_csv(csv_path)
            self.assertEqual(set(table["receptor_id"]), {"acrb_site2_ecoli"})

    def test_custom_roles_and_labels_are_respected(self):
        df = pd.DataFrame(
            {
                "molecule": ["A"],
                "best_affinity_acrb": [-8.0],
                "best_affinity_acrr": [-6.0],
            }
        )
        table = normalize_docking_csv(
            df,
            roles={"acrb": "pump", "acrr": "repressor"},
            labels={"acrb": "AcrB"},
        )
        self.assertEqual(_row(table, "A", "acrb")["role"], "pump")
        self.assertEqual(_row(table, "A", "acrr")["role"], "repressor")
        self.assertEqual(_row(table, "A", "acrb")["receptor_label"], "AcrB")
        self.assertEqual(_row(table, "A", "acrr")["receptor_label"], "acrr")


class NormalizeContentTests(unittest.TestCase):
    def test_missing_affinity_gets_missing_status(self):
        table = normalize_docking_csv(_wide(["A", "B"], [-5.5, -6.0], [-6.2, float("nan")]))
        self.assertEqual(_row(table, "B", "mexr")["status"], "MISSING")
        self.assertEqual(_row(table, "A", "mexr")["status"], "OK")
        self.assertEqual(_row(table, "B", "mexb")["status"], "OK")

    def test_cid_is_extracted_from_molecule_name(self):
        table = normalize_docking_csv(_wide(["Hesperidin_CID10621", "Sertraline"], [-8.0, -7.0], [-6.0, -6.5]))
        self.assertEqual(_row(table, "Hesperidin_CID10621", "mexb")["cid"], "10621")
        self.assertEqual(_row(table, "Sertraline", "mexb")["cid"], "")

    def test_no_group_values_become_empty(self):
        df = _wide(["A", "B"], [-5.5, -6.0], [-6.2, -6.7], groupe=["Antidepressant", "global"])
        table = normalize_docking_csv(df)
        self.assertEqual(set(table[table["molecule"] == "A"]["groupe"]), {"Antidepressant"})
        self.assertEqual(set(table[table["molecule"] == "B"]["groupe"]), {""})

    def test_molecule_columns_are_kept_and_old_index_is_dropped(self):
        df = _wide(
            ["A", "B"], [-5.5, -6.0], [-6.2, -6.7],
            MW=[300.1, 250.2], indice_selectivite=[9.9, 9.9],
        )
        table = normalize_docking_csv(df)
        self.assertIn("MW", table.columns)
        self.assertNotIn("indice_selectivite", table.columns)
        self.assertAlmostEqual(_row(table, "A", "mexb")["MW"], 300.1)
        self.assertAlmostEqual(_row(table, "A", "mexr")["MW"], 300.1)


class NormalizeErrorTests(unittest.TestCase):
    def test_missing_molecule_column_raises(self):
        with self.assertRaises(ValueError):
            normalize_docking_csv(pd.DataFrame({"poids": [1.0], "best_affinity": [-5.0]}))

    def test_missing_affinity_column_raises(self):
        with self.assertRaises(ValueError):
            normalize_docking_csv(pd.DataFrame({"molecule": ["A"], "poids": [1.0]}))


class SelectivityIndexTests(unittest.TestCase):
    # SI = DeltaG(repressor) - DeltaG(pump) ; positif = la pompe lie plus fort.
    def _score(self, df):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        csv_path = Path(tmp.name) / "sample.csv"
        df.to_csv(csv_path, index=False)
        grouped_csv, _ = create_scientific_scores(str(csv_path), output_dir=Path(tmp.name))
        return pd.read_csv(grouped_csv), Path(tmp.name)

    def _base(self):
        return pd.DataFrame(
            {
                "molecule": ["A", "B", "C"],
                "family": ["Antidepressant", "Antidepressant", "SSRI"],
                "best_affinity_mexb": [-9.0, -5.0, -6.0],
                "best_affinity_mexr": [-6.713, -7.0, -6.0],
            }
        )

    def test_index_is_repressor_minus_pump(self):
        scored, _ = self._score(self._base())
        si = scored.set_index("molecule")["indice_selectivite"]
        self.assertAlmostEqual(si["A"], 2.287, places=3)
        self.assertAlmostEqual(si["B"], -2.0, places=3)
        self.assertAlmostEqual(si["C"], 0.0, places=3)
        self.assertGreater(si["A"], 0)

    def test_molecule_without_repressor_value_is_dropped(self):
        df = self._base()
        df.loc[len(df)] = ["D", "SSRI", -6.0, float("nan")]
        scored, _ = self._score(df)
        self.assertNotIn("D", set(scored["molecule"]))
        self.assertEqual(set(scored["molecule"]), {"A", "B", "C"})

    def test_global_file_has_same_index(self):
        _, folder = self._score(self._base())
        global_csv = folder / "scores_fusionnes_global.csv"
        self.assertTrue(global_csv.exists())
        si = pd.read_csv(global_csv).set_index("molecule")["indice_selectivite"]
        self.assertAlmostEqual(si["A"], 2.287, places=3)


if __name__ == "__main__":
    unittest.main()
