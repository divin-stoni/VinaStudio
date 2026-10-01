import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.scientific_fusion import create_scientific_scores
from src.session_manager import SessionManager
from src.stats_engine import (
    bootstrap_ci_by_group,
    detect_analysis_mode,
    dual_filter,
    prepare_analysis_groups,
    top_candidates,
)


class SessionExportTests(unittest.TestCase):
    def test_session_export_copies_all_files_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SessionManager(project_root)
            session = manager.create_session()

            (session / "input").mkdir(exist_ok=True)
            (session / "prepared").mkdir(exist_ok=True)
            (session / "results" / "sub").mkdir(parents=True, exist_ok=True)

            (session / "input" / "ligand.csv").write_text("molecule\nA\n", encoding="utf-8")
            (session / "prepared" / "mol.pdbqt").write_text("MODEL\nENDMDL\n", encoding="utf-8")
            (session / "results" / "sub" / "score.csv").write_text("score\n-4.5\n", encoding="utf-8")

            export_root, exported_files = manager.export_session(project_root / "exports")

            self.assertTrue(export_root.exists())
            self.assertTrue((export_root / "MANIFEST.txt").exists())
            self.assertGreater(len(exported_files), 3)

            relative_names = {str(path.relative_to(export_root)) for path in exported_files}
            self.assertIn("MANIFEST.txt", relative_names)
            self.assertIn("input/ligand.csv", relative_names)
            self.assertIn("prepared/mol.pdbqt", relative_names)
            self.assertIn("results/sub/score.csv", relative_names)

    def test_require_session_raises_without_active_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            with self.assertRaises(RuntimeError):
                manager.require_session()

    def test_import_file_copies_under_input_with_custom_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))
            manager.create_session()

            source = Path(tmpdir) / "source_ligand.sdf"
            source.write_text("MOLECULE\n", encoding="utf-8")

            copied = manager.import_file(source, destination_name="renamed.sdf")

            self.assertEqual(copied.name, "renamed.sdf")
            self.assertTrue((manager.input_dir / "renamed.sdf").exists())
            self.assertEqual((manager.input_dir / "renamed.sdf").read_text(encoding="utf-8"), "MOLECULE\n")


class StatisticsEngineTests(unittest.TestCase):
    def test_detect_analysis_mode_and_group_preparation(self):
        df = pd.DataFrame(
            {
                "molecule": ["M1", "M2", "M3"],
                "groupe": ["A", "", "B"],
                "dg_mexb": [-4.2, -5.1, -3.9],
                "dg_mexr": [-6.5, -7.0, -5.8],
            }
        )

        self.assertEqual(detect_analysis_mode(df), "GROUPES")

        prepared, mode = prepare_analysis_groups(df)

        self.assertEqual(mode, "GROUPES")
        self.assertIn("groupe", prepared.columns)
        self.assertSetEqual(
            set(prepared["groupe"].astype(str).str.strip().unique()),
            {"A", "B", ""},
        )

    def test_bootstrap_ci_by_group_returns_group_rows(self):
        df = pd.DataFrame(
            {
                "molecule": ["A", "B", "C", "D", "E", "F"],
                "groupe": ["A", "A", "A", "B", "B", "B"],
                "dg_mexb": [-4.0, -4.5, -5.0, -3.8, -4.1, -4.4],
                "dg_mexr": [-6.0, -6.4, -7.0, -5.8, -6.1, -6.5],
            }
        )

        ci = bootstrap_ci_by_group(df, n_boot=200, ci=95)

        self.assertIn("groupe", ci.columns)
        self.assertIn("IC_low", ci.columns)
        self.assertIn("IC_high", ci.columns)
        self.assertTrue({"A", "B"}.issubset(set(ci["groupe"].unique())))

    def test_dual_filter_and_top_candidates_are_consistent(self):
        df = pd.DataFrame(
            {
                "molecule": ["M1", "M2", "M3", "M4"],
                "SI_calc": [12.0, 8.0, 3.0, 1.0],
                "percentile_SI": [95.0, 80.0, 55.0, 20.0],
                "statut_risque": [
                    "Favorable",
                    "Favorable",
                    "À risque (dérépression possible)",
                    "Favorable",
                ],
            }
        )

        valid, excluded = dual_filter(df, percentile_seuil=50)

        self.assertEqual(list(valid["molecule"]), ["M1", "M2"])
        self.assertEqual(list(excluded["molecule"]), ["M3"])

        top = top_candidates(df, n=2)
        self.assertEqual(list(top["molecule"]), ["M1", "M2"])


class ScientificFusionTests(unittest.TestCase):
    def test_scientific_fusion_creates_grouped_and_global_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "docking.csv"
            df = pd.DataFrame(
                {
                    "molecule": ["A", "B", "C"],
                    "family": ["Group1", "Group1", "Group2"],
                    "best_affinity_mexb": [-5.1, -6.2, -4.5],
                    "best_affinity_mexr": [-7.0, -7.4, -5.8],
                }
            )
            df.to_csv(csv_path, index=False)

            grouped_csv, global_csv = create_scientific_scores(csv_path, output_dir=Path(tmpdir))

            self.assertTrue(Path(grouped_csv).exists())
            self.assertTrue(Path(global_csv).exists())

            grouped = pd.read_csv(grouped_csv)
            self.assertIn("groupe", grouped.columns)
            self.assertIn("dg_mexb", grouped.columns)
            self.assertIn("dg_mexr", grouped.columns)
            self.assertIn("indice_selectivite", grouped.columns)

            self.assertSetEqual(set(grouped["groupe"].unique()), {"Group1", "Group2"})
            self.assertTrue(pd.api.types.is_numeric_dtype(grouped["indice_selectivite"]))
            self.assertFalse(grouped["indice_selectivite"].isna().any())

            global_df = pd.read_csv(global_csv)
            self.assertEqual(global_df.shape[1], 4)

    def test_scientific_fusion_keeps_signed_selectivity_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "signed_selectivity.csv"
            df = pd.DataFrame(
                {
                    "molecule": ["M1", "M2"],
                    "groupe": ["Group1", "Group2"],
                    "best_affinity_mexb": [-5.0, -4.2],
                    "best_affinity_mexr": [-6.1, -3.8],
                }
            )
            df.to_csv(csv_path, index=False)

            grouped_csv, _ = create_scientific_scores(csv_path, output_dir=Path(tmpdir))
            grouped = pd.read_csv(grouped_csv)

            self.assertIn("indice_selectivite", grouped.columns)
            self.assertEqual(list(grouped["indice_selectivite"].round(6)), [-1.1, 0.4])
            self.assertFalse(grouped["indice_selectivite"].isna().any())

    def test_scientific_fusion_assigns_default_group_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "missing_group.csv"
            df = pd.DataFrame(
                {
                    "molecule": ["M1", "M2"],
                    "groupe": ["", None],
                    "best_affinity_mexb": [-5.0, -4.5],
                    "best_affinity_mexr": [-6.0, -5.5],
                }
            )
            df.to_csv(csv_path, index=False)

            grouped_csv, _ = create_scientific_scores(csv_path, output_dir=Path(tmpdir))
            grouped = pd.read_csv(grouped_csv)

            self.assertIn("SANS_GROUPE", set(grouped["groupe"].unique()))


if __name__ == "__main__":
    unittest.main()
