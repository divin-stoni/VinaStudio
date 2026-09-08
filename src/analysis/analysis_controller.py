# -*- coding: utf-8 -*-

"""
Contrôleur d'analyse scientifique.

Flux :
CSV docking
    ->
scientific_fusion
    ->
statistics_pipeline
    ->
résultats GUI
"""

from src.scientific_fusion import create_scientific_scores
from src.analysis.statistics_pipeline import run_statistics_pipeline


def analyze_docking_csv(csv_path):

    grouped_csv, global_csv = create_scientific_scores(
        csv_path
    )

    result = run_statistics_pipeline(
        grouped_csv
    )

    result["source_docking"] = str(csv_path)
    result["scientific_csv"] = str(grouped_csv)
    result["global_csv"] = str(global_csv)

    return result
