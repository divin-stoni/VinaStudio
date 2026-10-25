# -*- coding: utf-8 -*-

"""
Pipeline statistique automatique.

Détecte automatiquement :
- analyse par groupes ;
- analyse globale.

Ne contient aucune statistique :
il orchestre uniquement stats_engine.py.
"""

from pathlib import Path
import pandas as pd


from src.stats_engine import (
    detect_analysis_mode,
    prepare_analysis_groups,
    correlations_by_group,
    bootstrap_ci_by_group,
    leave_one_out,
    homogeneity_of_slopes,
    compute_si_and_classification,
    dual_filter,
    top_candidates,
    permutation_test_by_group,
)


def _infer_affinity_columns(df):
    if "dg_mexb" in df.columns and "dg_mexr" in df.columns:
        return "dg_mexb", "dg_mexr"
    if "dg_pump" in df.columns and "dg_repressor" in df.columns:
        return "dg_pump", "dg_repressor"
    candidates = [column for column in df.columns if str(column).startswith("dg_")]
    if len(candidates) >= 2:
        return candidates[0], candidates[1]
    raise ValueError(
        "Le CSV doit contenir deux colonnes d'affinité ΔG pour l'analyse."
    )


def _receptor_labels(csv_path, x_col, y_col):
    """Noms des deux recepteurs : fichier meta de la fusion, sinon defauts."""
    labels = {"x": None, "y": None}
    try:
        import json

        meta_path = Path(csv_path).parent / "scores_fusionnes_meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pump = meta.get("pump") or {}
            repressor = meta.get("repressor") or {}
            # Le fichier meta ne sert que s'il decrit bien ces colonnes.
            if pump.get("column") == x_col and repressor.get("column") == y_col:
                labels["x"] = pump.get("label")
                labels["y"] = repressor.get("label")
    except Exception:
        pass
    defaults = {
        "dg_mexb": "MexB",
        "dg_mexr": "MexR",
        "dg_pump": "Pompe",
        "dg_repressor": "Répresseur",
    }
    labels["x"] = labels["x"] or defaults.get(x_col, str(x_col))
    labels["y"] = labels["y"] or defaults.get(y_col, str(y_col))
    return labels


# patch-references : le seuil de risque n'est plus code en dur. Il vient du choix
# de l'utilisateur (aucun / reference docquee / valeur manuelle), memorise dans
# analysis_settings.json a la racine du projet.
REF_PREFIX = "REF-"
THRESHOLD_ROLE_PREFIXES = ("REF-DEREP__", "REF-SUB__")


def threshold_references_in_csv(csv_path):
    """Molecules de reference pouvant servir de seuil de risque (derepresseur d'abord)."""
    try:
        names = pd.read_csv(csv_path, usecols=["molecule"])["molecule"].astype(str)
    except Exception:
        return []
    out = []
    for m in names:
        if m.startswith(THRESHOLD_ROLE_PREFIXES) and m not in out:
            out.append(m)
    out.sort(key=lambda m: (not m.startswith("REF-DEREP__"), m))
    return out


def reference_display_name(molecule):
    """REF-INH__Berberine -> Berberine."""
    s = str(molecule)
    if s.startswith(REF_PREFIX):
        s = s[len(REF_PREFIX):]
    if "__" in s:
        s = s.split("__", 1)[1]
    s = s.replace("_", " ").strip()
    return s or str(molecule)


def _settings_path():
    try:
        from src import reference_inhibitors as _ri
        return Path(_ri.ROOT) / "analysis_settings.json"
    except Exception:
        return Path.cwd() / "analysis_settings.json"


def load_threshold_config():
    """Choix du seuil : {"mode": "none" | "reference" | "manuel", ...}."""
    import json
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
        cfg = data.get("seuil") or {}
        if cfg.get("mode") in ("none", "reference"):
            return cfg
    except Exception:
        pass
    return {"mode": "none", "valeur": 0.0}


def save_threshold_config(cfg):
    import json
    p = _settings_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    data["seuil"] = cfg
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _split_references(df):
    """Separe les molecules de reference (prefixe REF-) des candidats."""
    if "molecule" not in df.columns:
        return df, pd.DataFrame()
    is_ref = df["molecule"].astype(str).str.startswith(REF_PREFIX)
    if not is_ref.any() or is_ref.all():
        return df, pd.DataFrame()
    return df[~is_ref].copy(), df[is_ref].copy()


def _resolve_threshold(refs_df, y_col):
    """Retourne (seuil, nom_reference, info) selon le choix enregistre."""
    cfg = load_threshold_config()
    mode = cfg.get("mode", "none")
    if mode == "manuel":
        try:
            return float(cfg.get("valeur")), "valeur manuelle", "Seuil manuel"
        except Exception:
            return None, None, "Seuil manuel invalide : aucun seuil applique"
    if mode == "reference":
        wanted = str(cfg.get("reference", ""))
        if refs_df is not None and len(refs_df) and wanted:
            sub = refs_df[refs_df["molecule"].astype(str) == wanted]
            if len(sub) and y_col in sub.columns:
                vals = pd.to_numeric(sub[y_col], errors="coerce").dropna()
                if len(vals):
                    name = reference_display_name(wanted)
                    return float(vals.iloc[0]), name, "Seuil = reference " + name
        return None, None, ("Reference de seuil '%s' absente des donnees : "
                            "aucun seuil applique" % wanted)
    return None, None, "Aucun seuil"


INHIBITOR_PREFIXES = ("REF-INH__", "REF-INH-USER__")


def load_pump_tolerance():
    import json
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
        return float(data.get("tolerance_pompe", 0.2))
    except Exception:
        return 0.2


def save_pump_tolerance(value):
    import json
    p = _settings_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    data["tolerance_pompe"] = float(value)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _pump_inhibitor_filter(cls, refs_df, x_col):
    """Option 1 : un ligand est retenu s'il egale ou depasse AU MOINS UN inhibiteur
    de reference sur la pompe, a la tolerance ppres. Ajoute une colonne Oui/Non par
    inhibiteur a `cls` et retourne (ligands retenus, tolerance)."""
    tol = load_pump_tolerance()
    if refs_df is None or len(refs_df) == 0 or x_col not in refs_df.columns:
        return pd.DataFrame(), tol
    inh = refs_df[refs_df["molecule"].astype(str).map(
        lambda m: m.startswith(INHIBITOR_PREFIXES))]
    if len(inh) == 0:
        return pd.DataFrame(), tol
    any_ok = pd.Series(False, index=cls.index)
    for _, r in inh.iterrows():
        v = pd.to_numeric(r[x_col], errors="coerce")
        if v != v:
            continue
        ok = cls[x_col] <= (float(v) + tol)
        cls["Égal/meilleur : " + reference_display_name(r["molecule"])] = ok.map(
            {True: "Oui", False: "Non"})
        any_ok = any_ok | ok
    cls["Égal/meilleur qu'un inhibiteur"] = any_ok.map({True: "Oui", False: "Non"})
    return cls[any_ok].sort_values(x_col).reset_index(drop=True), tol


def _prepare_references(refs_df, x_col, y_col, seuil, cand_si=None):
    """Tableau des references : SI, percentile parmi les candidats, statut."""
    if refs_df is None or len(refs_df) == 0:
        return pd.DataFrame()
    import numpy as np
    out = refs_df.copy()
    out["nom_reference"] = out["molecule"].map(reference_display_name)
    for c in (x_col, y_col):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out["SI_calc"] = out[y_col] - out[x_col]
    try:
        vals = pd.to_numeric(pd.Series(cand_si), errors="coerce").dropna()
        if len(vals):
            out["percentile_SI"] = out["SI_calc"].map(
                lambda v: float((vals <= v).mean() * 100.0) if v == v else float("nan"))
    except Exception:
        pass
    if seuil is not None:
        out["statut_risque"] = np.where(
            out[y_col] <= seuil, "À risque (dérépression possible)", "Favorable")
    return out


# (ancienne fonction _risk_threshold supprimee : seuil code en dur retire)


def run_statistics_pipeline(csv_path):

    csv_path = Path(csv_path)

    df = pd.read_csv(csv_path)
    df, refs_df = _split_references(df)

    df, mode = prepare_analysis_groups(
        df
    )
    x_col, y_col = _infer_affinity_columns(df)


    result = {
        "file": str(csv_path),
        "mode": mode,
        "data": df,
        "affinity_columns": {"pump": x_col, "repressor": y_col},
    }


    # --------------------------------------------------
    # Analyses communes
    # --------------------------------------------------

    _labels0 = _receptor_labels(csv_path, x_col, y_col)  # patch-seuil
    _seuil, _ref_name, _seuil_info = _resolve_threshold(refs_df, y_col)
    result["classification"] = (
        compute_si_and_classification(
            df, x_col=x_col, y_col=y_col, seuil_risque_absolu=_seuil,
            ref_name=_ref_name
        )
    )

    # patch-libelles : noms des recepteurs (fusion -> meta -> pipeline -> figures)
    result["labels"] = _receptor_labels(csv_path, x_col, y_col)
    result["threshold_info"] = _seuil_info
    result["references"] = _prepare_references(
        refs_df, x_col, y_col, _seuil, result["classification"]["SI_calc"]
    )
    for _frame in (result["classification"], df):
        _frame.attrs["x_label"] = result["labels"]["x"]
        _frame.attrs["y_label"] = result["labels"]["y"]
        _frame.attrs["references"] = (
            result["references"].to_dict("records") if len(result["references"]) else []
        )


    result["pump_inhibitor_filter"], result["pump_tolerance"] = _pump_inhibitor_filter(
        result["classification"], refs_df, x_col
    )

    result["top_candidates"] = (
        top_candidates(
            result["classification"]
        )
    )


    dual_valides, dual_exclus = dual_filter(
        result["classification"]
    )

    result["dual_filter"] = {
        "candidates": dual_valides,
        "excluded_absolute": dual_exclus,
        "threshold_percentile": 50.0,
        "threshold_mexr": _seuil,
    }


    # --------------------------------------------------
    # Analyses dépendantes du mode
    # --------------------------------------------------

    result["correlations"] = (
        correlations_by_group(df, x_col=x_col, y_col=y_col)
    )


    result["bootstrap"] = (
        bootstrap_ci_by_group(df, x_col=x_col, y_col=y_col)
    )

    result["permutation"] = permutation_test_by_group(
        df, x_col=x_col, y_col=y_col
    )


    if mode == "GROUPES":

        result["leave_one_out"] = (
            leave_one_out(df, x_col=x_col, y_col=y_col)
        )

        result["homogeneity"] = (
            homogeneity_of_slopes(df, x_col=x_col, y_col=y_col)
        )


    else:

        result["leave_one_out"] = leave_one_out(df, x_col=x_col, y_col=y_col)  # patch-familles : LOO aussi en mode global
        result["homogeneity"] = None


    return result
