"""
folder_scanner.py
Scan récursif d'un dossier à la recherche de fichiers CSV compatibles
avec MexAB-OprM Analyzer (Mode 1 / Mode 2), via column_matcher.detect_columns.
Logique séparée de l'UI (scan_dialog.py) pour rester testable sans Qt.
"""
import os
import pandas as pd

from column_matcher import detect_columns


def _count_rows(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            n = sum(1 for _ in f)
        return max(n - 1, 0)  # moins la ligne d'en-tête
    except Exception:
        return None


def scan_folder(root_dir, recursive=True, min_score=0.3):
    """
    Scanne root_dir à la recherche de fichiers .csv et classe chacun selon
    le mode d'analyse qu'il permet.

    Retourne une liste de dicts :
        {
            "path": str,
            "filename": str,
            "mapping": dict | None,   # sortie de detect_columns (None si erreur de lecture)
            "modes": list[str],       # sous-ensemble de ["mode1", "mode2"]
            "rows": int | None,
            "error": str | None,
        }
    """
    results = []

    if recursive:
        paths = (
            os.path.join(dirpath, fname)
            for dirpath, _, filenames in os.walk(root_dir)
            for fname in filenames
            if fname.lower().endswith(".csv")
        )
    else:
        paths = (
            os.path.join(root_dir, fname)
            for fname in sorted(os.listdir(root_dir))
            if fname.lower().endswith(".csv")
            and os.path.isfile(os.path.join(root_dir, fname))
        )

    for path in paths:
        entry = {
            "path": path,
            "filename": os.path.basename(path),
            "mapping": None,
            "modes": [],
            "rows": None,
            "error": None,
        }
        try:
            # On ne lit que l'en-tête : détection de colonnes rapide, pas
            # besoin du fichier entier à ce stade.
            header_df = pd.read_csv(path, nrows=0)

            # Mapping destiné à l'interface.
            mapping = detect_columns(
                header_df,
                verbose=False,
                min_score=min_score
            )

            # Détection scientifique indépendante de l'identifiant.
            # Cela permet de reconnaître un fichier dont la première
            # colonne est directement dg_mexb ou dg_mexr.
            scientific_cols = {}
            for col in header_df.columns:
                norm = str(col).lower()
                norm = norm.replace("-", "_").replace(" ", "_")

                if (
                    "mexb" in norm
                    and any(x in norm for x in
                            ["dg", "delta", "energy", "energ", "score",
                             "bind", "affin"])
                ):
                    scientific_cols["dg_mexb"] = col

                if (
                    "mexr" in norm
                    and any(x in norm for x in
                            ["dg", "delta", "energy", "energ", "score",
                             "bind", "affin"])
                ):
                    scientific_cols["dg_mexr"] = col

            # Compléter avec le mapping intelligent lorsqu'il existe.
            if mapping.get("dg_mexb"):
                scientific_cols["dg_mexb"] = mapping["dg_mexb"]

            if mapping.get("dg_mexr"):
                scientific_cols["dg_mexr"] = mapping["dg_mexr"]
        except Exception as e:
            entry["error"] = str(e)
            results.append(entry)
            continue

        entry["mapping"] = mapping
        entry["rows"] = _count_rows(path)

        # Classification scientifique uniquement.
        # L'identifiant/molecule est facultatif et ne doit jamais
        # empêcher la reconnaissance d'un fichier.
        if scientific_cols.get("dg_mexb") and scientific_cols.get("dg_mexr"):
            entry["modes"] = ["mode1"]
        elif scientific_cols.get("dg_mexb"):
            entry["modes"] = ["mode2"]
        else:
            entry["modes"] = []

        results.append(entry)

    return results
