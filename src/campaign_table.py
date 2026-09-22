# -*- coding: utf-8 -*-
"""
campaign_table.py

Lecture unique de tous les CSV de docking de VINA Studio.

Quel que soit le format d'entree (cible seule, couple, N recepteurs,
ancien format MexB/MexR, dataset de l'article), la fonction
normalize_docking_csv() renvoie UN tableau "long" :
une ligne par (molecule x recepteur).

Ce module n'importe rien du projet et n'est appele par personne
pour l'instant : l'application n'est pas affectee.

Usage en ligne de commande (lecture seule) :
    python3 src/campaign_table.py fichier1.csv fichier2.csv ...
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


# ----------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------

# Colonnes propres a un couple (molecule, recepteur)
PER_RECEPTOR_COLUMNS = [
    "receptor_id",
    "receptor_label",
    "role",
    "status",
    "best_affinity",
    "best_mode",
    "n_modes",
    "duration_seconds",
    "error",
    "output_pdbqt",
    "log_file",
]

# Colonnes propres a la molecule
MOLECULE_COLUMNS = ["molecule", "cid", "groupe", "ligand_file"]

CANONICAL_COLUMNS = MOLECULE_COLUMNS + PER_RECEPTOR_COLUMNS + ["source_format"]

_MOLECULE_ALIASES = ("molecule", "nom", "name", "ligand_name")
_GROUP_ALIASES = (
    "groupe", "group", "famille", "family", "classe", "class", "category",
)
_RECEPTOR_ALIASES = ("receptor_id", "cible", "target", "receptor")
_AFFINITY_ALIASES = ("best_affinity", "dg", "deltag", "affinity")

# Prefixes de colonnes suffixees par le recepteur (format large)
_AFFINITY_PREFIXES = ("best_affinity", "dg", "deltag")
_FIELD_PREFIXES = (
    "status", "best_mode", "n_modes", "duration_seconds",
    "error", "output_pdbqt", "log_file",
)

# Valeurs qui signifient "pas de famille"
_NO_GROUP = {"", "nan", "none", "null", "sans_groupe", "global"}

# Alias historiques (seulement pour donner un role / un libelle par defaut)
_LEGACY_ROLES = {
    "mexb": "pump",
    "mexr": "repressor",
    "pump": "pump",
    "repressor": "repressor",
}
_LEGACY_LABELS = {"mexb": "MexB", "mexr": "MexR"}

_CID_RE = re.compile(r"cid[\s_\-]*(\d+)", re.IGNORECASE)


# ----------------------------------------------------------------------
# Petits outils
# ----------------------------------------------------------------------

def _slug(name) -> str:
    return re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")


def _first_col(df, aliases):
    """Premiere colonne dont le nom (insensible a la casse) est un alias."""
    lowered = {str(c).strip().lower(): c for c in df.columns}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return None


def _clean_text(series):
    def convert(value):
        if pd.isna(value):
            return ""
        return str(value).strip()

    return series.map(convert)


def _clean_group(series):
    text = _clean_text(series)
    return text.map(lambda v: "" if v.lower() in _NO_GROUP else v)


def _clean_cid_value(value):
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def _extract_cid(name: str) -> str:
    match = _CID_RE.search(name)
    if match:
        return match.group(1)
    if name.isdigit():
        return name
    return ""


def _split_suffixed(column: str):
    """
    'best_affinity_acrb_site2_ecoli' -> ('best_affinity', 'acrb_site2_ecoli')
    Retourne (None, None) si la colonne n'est pas de ce type.
    """
    low = column.strip().lower()
    for prefix in _AFFINITY_PREFIXES + _FIELD_PREFIXES:
        head = prefix + "_"
        if low.startswith(head) and len(low) > len(head):
            return prefix, column.strip()[len(head):]
    return None, None


def _molecule_block(df, mol_col, group_col, cid_col):
    """Colonnes propres a la molecule, une ligne par ligne du CSV."""
    block = pd.DataFrame(index=df.index)
    block["molecule"] = _clean_text(df[mol_col])

    if cid_col is not None:
        cids = df[cid_col].map(_clean_cid_value)
        fallback = block["molecule"].map(_extract_cid)
        block["cid"] = [c if c else f for c, f in zip(cids, fallback)]
    else:
        block["cid"] = block["molecule"].map(_extract_cid)

    if group_col is not None:
        block["groupe"] = _clean_group(df[group_col])
    else:
        block["groupe"] = ""

    if "ligand_file" in df.columns:
        block["ligand_file"] = _clean_text(df["ligand_file"])
    else:
        block["ligand_file"] = ""

    return block


def _role_and_label(rid, original_label, roles, labels):
    role = (roles or {}).get(rid) or _LEGACY_ROLES.get(rid, "")
    label = (labels or {}).get(rid) or _LEGACY_LABELS.get(rid) or original_label
    return role, label


def _fill_fields(part, df, lookup, used):
    """
    Remplit status, erreurs, chemins, mode et duree.
    lookup(champ) renvoie le nom de colonne du CSV pour ce champ (ou None).
    """
    for field in ("status", "error", "output_pdbqt", "log_file"):
        col = lookup(field)
        if col is not None:
            used.add(col)
            part[field] = _clean_text(df[col])
        else:
            part[field] = ""
    for field in ("best_mode", "n_modes", "duration_seconds"):
        col = lookup(field)
        if col is not None:
            used.add(col)
            part[field] = pd.to_numeric(df[col], errors="coerce")
        else:
            part[field] = float("nan")
    # Pas de colonne status : on la deduit de l'affinite.
    if not (part["status"] != "").any():
        part["status"] = part["best_affinity"].map(
            lambda v: "OK" if pd.notna(v) else "MISSING"
        )


# ----------------------------------------------------------------------
# Fonction principale
# ----------------------------------------------------------------------

def normalize_docking_csv(source, target_hint=None, roles=None, labels=None):
    """
    Lit n'importe quel CSV de docking et renvoie le tableau long.

    source      : chemin du CSV ou DataFrame deja lu.
    target_hint : nom de la cible pour un CSV de cible seule (sinon deduit
                  du dossier quand le fichier s'appelle docking_results.csv).
    roles       : {receptor_id: "pump" | "repressor"} facultatif.
    labels      : {receptor_id: "libelle affiche"} facultatif.

    Colonnes du resultat : voir CANONICAL_COLUMNS, puis les colonnes
    propres a la molecule presentes dans le CSV (MW, LogP...).
    """
    path = None
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        path = Path(source)
        df = pd.read_csv(path)

    df.columns = [str(c).strip() for c in df.columns]
    df = df.reset_index(drop=True)

    mol_col = _first_col(df, _MOLECULE_ALIASES)
    if mol_col is None:
        raise ValueError(
            "Colonne de molecule introuvable (attendu : molecule, nom ou name)."
        )
    group_col = _first_col(df, _GROUP_ALIASES)
    cid_col = _first_col(df, ("cid",))
    receptor_col = _first_col(df, _RECEPTOR_ALIASES)
    affinity_col = _first_col(df, _AFFINITY_ALIASES)

    # --- detection du format ------------------------------------------
    suffixed = {}          # {(prefixe, receptor_id): colonne}
    labels_found = {}      # {receptor_id: libelle d'origine}
    for column in df.columns:
        prefix, suffix = _split_suffixed(column)
        if prefix is None:
            continue
        rid = _slug(suffix)
        if not rid:
            continue
        suffixed[(prefix, rid)] = column
        labels_found.setdefault(rid, suffix)

    wide_ids = []
    for (prefix, rid) in suffixed:
        if prefix in _AFFINITY_PREFIXES and rid not in wide_ids:
            wide_ids.append(rid)

    used = {mol_col}
    for col in (group_col, cid_col, "ligand_file"):
        if col is not None:
            used.add(col)

    parts = []

    if receptor_col is not None and affinity_col is not None:
        # ---- format long (deja "une ligne par molecule x cible") ------
        source_format = "long"
        used.update({receptor_col, affinity_col})
        block = _molecule_block(df, mol_col, group_col, cid_col)
        original = _clean_text(df[receptor_col])
        rids = original.map(_slug)

        # Une table deja normalisee garde ses roles et libelles.
        role_col = _first_col(df, ("role",))
        label_col = _first_col(df, ("receptor_label",))
        source_col = _first_col(df, ("source_format",))
        for col in (role_col, label_col, source_col):
            if col is not None:
                used.add(col)
        existing_roles = _clean_text(df[role_col]) if role_col else None
        existing_labels = _clean_text(df[label_col]) if label_col else None

        role_list, label_list = [], []
        for k, (rid, orig) in enumerate(zip(rids, original)):
            role, label = _role_and_label(rid, orig, roles, labels)
            if not (roles and rid in roles) and existing_roles is not None:
                role = existing_roles.iloc[k] or role
            if not (labels and rid in labels) and existing_labels is not None:
                label = existing_labels.iloc[k] or label
            role_list.append(role)
            label_list.append(label)

        part = block.copy()
        part["receptor_id"] = rids
        part["receptor_label"] = label_list
        part["role"] = role_list
        part["best_affinity"] = pd.to_numeric(df[affinity_col], errors="coerce")
        _fill_fields(part, df, lambda f: _first_col(df, (f,)), used)
        parts.append((part, df))

    elif wide_ids:
        # ---- format large (colonnes suffixees par recepteur) -----------
        source_format = "large"
        block = _molecule_block(df, mol_col, group_col, cid_col)
        for rid in wide_ids:
            aff_col = None
            for prefix in _AFFINITY_PREFIXES:
                if (prefix, rid) in suffixed:
                    aff_col = suffixed[(prefix, rid)]
                    break
            role, label = _role_and_label(rid, labels_found.get(rid, rid), roles, labels)

            part = block.copy()
            part["receptor_id"] = rid
            part["receptor_label"] = label
            part["role"] = role
            part["best_affinity"] = pd.to_numeric(df[aff_col], errors="coerce")
            used.add(aff_col)

            _fill_fields(part, df, lambda f, r=rid: suffixed.get((f, r)), used)
            parts.append((part, df))

    elif affinity_col is not None:
        # ---- cible seule (la cible n'est pas dans le fichier) ----------
        source_format = "cible_seule"
        used.add(affinity_col)
        hint = target_hint
        if not hint and path is not None and path.name.lower() == "docking_results.csv":
            hint = path.parent.name
        original = hint or "cible_unique"
        rid = _slug(original) or "cible_unique"
        role, label = _role_and_label(rid, original, roles, labels)

        part = _molecule_block(df, mol_col, group_col, cid_col)
        part["receptor_id"] = rid
        part["receptor_label"] = label
        part["role"] = role
        part["best_affinity"] = pd.to_numeric(df[affinity_col], errors="coerce")
        _fill_fields(part, df, lambda f: _first_col(df, (f,)), used)
        parts.append((part, df))

    else:
        raise ValueError(
            "Format non reconnu : aucune colonne d'affinite "
            "(best_affinity, dg_..., DeltaG_...)."
        )

    # --- colonnes propres a la molecule restantes (MW, LogP...) ----------
    ignored = {"indice_selectivite"}
    extras = [
        c for c in df.columns
        if c not in used and str(c).strip().lower() not in ignored
    ]

    frames = []
    for part, source_df in parts:
        part = part.copy()
        for column in extras:
            part[column] = source_df[column].values
        part["source_format"] = source_format
        frames.append(part)

    table = pd.concat(frames, ignore_index=True)
    ordered = CANONICAL_COLUMNS + [c for c in table.columns if c not in CANONICAL_COLUMNS]
    return table[ordered]


# ----------------------------------------------------------------------
# Forme de la campagne
# ----------------------------------------------------------------------

def campaign_shape(table):
    """Resume ce que contient la campagne (recepteurs, molecules, familles)."""
    receptors = list(dict.fromkeys(table["receptor_id"]))
    labels = {}
    roles = {}
    for rid in receptors:
        rows = table[table["receptor_id"] == rid]
        labels[rid] = rows["receptor_label"].iloc[0]
        roles[rid] = rows["role"].iloc[0]

    families = sorted({g for g in table["groupe"] if g})
    ok = table["status"].astype(str).str.upper() == "OK"

    return {
        "receptors": receptors,
        "labels": labels,
        "roles": roles,
        "n_receptors": len(receptors),
        "n_molecules": int(table["molecule"].nunique()),
        "families": families,
        "n_families": len(families),
        "n_docking_ok": int(ok.sum()),
        "n_docking_echecs": int((~ok).sum()),
    }


def describe_campaign(shape) -> str:
    names = ", ".join(shape["labels"][r] for r in shape["receptors"])
    n_rec = shape["n_receptors"]
    n_mol = shape["n_molecules"]
    n_fam = shape["n_families"]

    rec_txt = f"{n_rec} recepteur{'s' if n_rec > 1 else ''} ({names})"
    mol_txt = f"{n_mol} molecule{'s' if n_mol > 1 else ''}"
    if n_fam == 0:
        fam_txt = "aucune famille"
    else:
        fam_txt = f"{n_fam} famille{'s' if n_fam > 1 else ''}"
    return f"{rec_txt} - {mol_txt} - {fam_txt}"


# ----------------------------------------------------------------------
# Paire de recepteurs -> tableau pret pour les statistiques
# ----------------------------------------------------------------------

def pivot_pair(table, receptor_x, receptor_y, only_ok=True):
    """
    Renvoie un tableau (une ligne par molecule) pour deux recepteurs :
        molecule, cid, groupe, ..., dg_x, dg_y, indice_selectivite
    avec indice_selectivite = dg_y - dg_x (comme l'ancien
    dg_repressor - dg_pump quand x = pompe et y = repressor).

    Les colonnes dg_x / dg_y ont des noms neutres : les libelles
    des recepteurs sont dans .attrs["x_label"] et .attrs["y_label"].
    """
    if receptor_x == receptor_y:
        raise ValueError("Il faut deux recepteurs differents.")

    ids = set(table["receptor_id"])
    for rid in (receptor_x, receptor_y):
        if rid not in ids:
            raise ValueError(f"Recepteur absent de la campagne : {rid}")

    data = table
    if only_ok:
        data = data[data["status"].astype(str).str.upper() == "OK"]
    data = data[data["receptor_id"].isin([receptor_x, receptor_y])]

    wide = data.pivot_table(
        index="molecule",
        columns="receptor_id",
        values="best_affinity",
        aggfunc="first",
    )
    for rid in (receptor_x, receptor_y):
        if rid not in wide.columns:
            wide[rid] = float("nan")

    wide = wide[[receptor_x, receptor_y]].dropna().reset_index()
    wide.columns = ["molecule", "dg_x", "dg_y"]

    molecule_cols = [
        c for c in table.columns
        if c not in PER_RECEPTOR_COLUMNS and c != "source_format"
    ]
    meta = table.drop_duplicates("molecule")[molecule_cols]

    out = meta.merge(wide, on="molecule", how="inner")
    out["indice_selectivite"] = out["dg_y"] - out["dg_x"]

    def label_of(rid):
        return table.loc[table["receptor_id"] == rid, "receptor_label"].iloc[0]

    out.attrs["x_id"] = receptor_x
    out.attrs["y_id"] = receptor_y
    out.attrs["x_label"] = label_of(receptor_x)
    out.attrs["y_label"] = label_of(receptor_y)
    return out


# ----------------------------------------------------------------------
# Ligne de commande : diagnostic en lecture seule
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python3 src/campaign_table.py fichier.csv [autre.csv ...]")
        raise SystemExit(1)

    show = ["molecule", "cid", "groupe", "receptor_id", "role", "status", "best_affinity"]

    for arg in sys.argv[1:]:
        print("=" * 72)
        print(arg)
        try:
            tab = normalize_docking_csv(arg)
        except Exception as exc:
            print("ERREUR :", exc)
            continue

        info = campaign_shape(tab)
        print("Format source :", tab["source_format"].iloc[0])
        print("Campagne      :", describe_campaign(info))
        print("Docking       : %d OK, %d echecs" % (
            info["n_docking_ok"], info["n_docking_echecs"]))
        print(tab[show].head(4).to_string(max_colwidth=30))

        ids = info["receptors"]
        if len(ids) >= 2:
            pair = pivot_pair(tab, ids[0], ids[1])
            print("Paire %s / %s : %d molecules appariees" % (
                pair.attrs["x_label"], pair.attrs["y_label"], len(pair)))
            print(pair[["molecule", "dg_x", "dg_y", "indice_selectivite"]]
                  .head(3).to_string())
