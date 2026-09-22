import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.scientific_fusion import create_scientific_scores
from src.stats_engine import detect_analysis_mode, prepare_analysis_groups


class AnalysisPipelinePriorityTests(unittest.TestCase):
    def test_family_column_is_preserved_as_group(self):
        df = pd.DataFrame(
            {
                "molecule": ["A", "B", "C"],
                "family": ["Antidepressant", "Antidepressant", "SSRI"],
                "best_affinity_mexb": [-5.5, -6.0, -4.8],
                "best_affinity_mexr": [-6.2, -6.7, -5.0],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "sample.csv"
            df.to_csv(csv_path, index=False)

            grouped_csv, _ = create_scientific_scores(str(csv_path), output_dir=Path(tmpdir))
            scored = pd.read_csv(grouped_csv)

            self.assertIn("groupe", scored.columns)
            self.assertEqual(set(scored["groupe"].unique()), {"Antidepressant", "SSRI"})

    def test_analysis_mode_detects_family_synonyms(self):
        df = pd.DataFrame(
            {
                "molecule": ["A", "B", "C"],
                "group": ["Fam1", "Fam1", "Fam2"],
                "dg_mexb": [-5.5, -6.0, -4.8],
                "dg_mexr": [-6.2, -6.7, -5.0],
            }
        )

        mode = detect_analysis_mode(df)
        prepared, prepared_mode = prepare_analysis_groups(df)

        self.assertEqual(mode, "GROUPES")
        self.assertEqual(prepared_mode, "GROUPES")
        self.assertIn("groupe", prepared.columns)


if __name__ == "__main__":
    unittest.main()
