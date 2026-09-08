"""
column_matcher.py
Détection automatique et robuste des colonnes du CSV, peu importe leur
orthographe (casse, séparateurs, préfixes type delta_/dG_/ΔG_...).

Version "smart" : scoring pondéré (patterns spécifiques > patterns génériques)
+ repli par similarité de chaîne (difflib, stdlib) pour les cas non prévus,
+ assignation globale gloutonne pour éviter qu'une colonne soit utilisée deux fois.
"""
import re
import unicodedata
import difflib


def _normalize(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text.lower())


COLUMN_PATTERNS = {
    "dg_mexb": [
        (r"(dg|delta|energ|score|bind|affin).*mexb", 1.0),
        (r"mexb.*(dg|delta|energ|score|bind|affin)", 1.0),
        (r"^mexb$", 0.9),
        (r"mexb", 0.6),
    ],
    "dg_mexr": [
        (r"(dg|delta|energ|score|bind|affin).*mexr", 1.0),
        (r"mexr.*(dg|delta|energ|score|bind|affin)", 1.0),
        (r"^mexr$", 0.9),
        (r"mexr", 0.6),
    ],
    "groupe": [
        (r"^(group|famille|family|classe|class)$", 1.0),
        (r"group|famille|family|classe|class|categor", 0.8),
    ],
    "molecule": [
        (r"^(molecule|compose|compound|nom|name|ligand)$", 1.0),
        (r"molecul|compose|compound|^nom|name|ligand", 0.7),
    ],
    "MW": [
        (r"^mw$", 1.0),
        (r"molecularweight|molweight|masse.*mol|poidsmol", 0.9),
        (r"^m$", 0.3),
    ],
    "LogP": [
        (r"^logp$|clogp", 1.0),
        (r"logp", 0.8),
    ],
}

REQUIRED = ["dg_mexb", "dg_mexr"]
FUZZY_THRESHOLD = 0.6

FUZZY_KEYWORDS = {
    "dg_mexb": ["deltagmexb", "energiemexb", "scoremexb", "affinitemexb"],
    "dg_mexr": ["deltagmexr", "energiemexr", "scoremexr", "affinitemexr"],
    "groupe": ["groupe", "famille", "classe", "category"],
    "molecule": ["nommolecule", "composé", "ligand", "compoundname"],
    "MW": ["molecularweight", "massemoleculaire", "poidsmoleculaire"],
    "LogP": ["logp", "clogp", "coefficientpartition"],
}


def _score_column(norm_col, internal_name):
    best = 0.0
    for pattern, weight in COLUMN_PATTERNS.get(internal_name, []):
        if re.search(pattern, norm_col):
            best = max(best, weight)
    if best == 0.0:
        for keyword in FUZZY_KEYWORDS.get(internal_name, []):
            ratio = difflib.SequenceMatcher(None, norm_col, keyword).ratio()
            if ratio >= FUZZY_THRESHOLD:
                best = max(best, ratio * 0.7)
    return best


def detect_columns(df, patterns=COLUMN_PATTERNS, verbose=True, min_score=0.3):
    # La première colonne du fichier brut est toujours considérée
    # comme l'identifiant de la molécule/observation.
    # Son nom original peut être ID, Substance, Compound, Molecule, etc.
    normalized_cols = {col: _normalize(col) for col in df.columns}

    if len(df.columns) > 0:
        first_col = df.columns[0]

        # La première colonne sert normalement d'identifiant.
        # EXCEPTION IMPORTANTE :
        # si la première colonne est elle-même une variable scientifique
        # obligatoire (MexB ou MexR), elle doit rester disponible pour
        # la détection scientifique.
        first_norm = normalized_cols.get(first_col, "")

        first_is_scientific = (
            _score_column(first_norm, "dg_mexb") >= min_score
            or _score_column(first_norm, "dg_mexr") >= min_score
        )

        if first_is_scientific:
            first_col = None
        else:
            # La première colonne est l'identifiant interne "molecule".
            normalized_cols.pop(df.columns[0], None)
    else:
        first_col = None

    candidates = []
    for internal_name in patterns:
        for col, norm_col in normalized_cols.items():
            score = _score_column(norm_col, internal_name)
            if score >= min_score:
                candidates.append((score, internal_name, col))

    candidates.sort(key=lambda x: x[0], reverse=True)

    mapping = {name: None for name in patterns}
    mapping_score = {}
    used_columns = set()
    assigned_fields = set()

    # La première colonne est toujours l'identifiant interne "molecule".
    # Elle n'est donc pas soumise au système de détection par synonymes.
    if first_col is not None and "molecule" in mapping:
        mapping["molecule"] = first_col
        mapping_score["molecule"] = 1.0
        used_columns.add(first_col)
        assigned_fields.add("molecule")

    for score, internal_name, col in candidates:
        if internal_name in assigned_fields or col in used_columns:
            continue
        mapping[internal_name] = col
        mapping_score[internal_name] = score
        used_columns.add(col)
        assigned_fields.add(internal_name)

    if verbose:
        for internal_name in patterns:
            found = mapping[internal_name]
            if found:
                score = mapping_score[internal_name]
                confidence = "haute" if score >= 0.9 else ("moyenne" if score >= 0.6 else "faible")
                print(f"  [column_matcher] {internal_name:12s} -> '{found}' (confiance {confidence}, score={score:.2f})")
            else:
                print(f"  [column_matcher] {internal_name:12s} -> NON TROUVÉE")

    return mapping


def apply_column_mapping(df, mapping=None, verbose=True, min_score=0.3, required=None):
    if mapping is None:
        mapping = detect_columns(df, verbose=verbose, min_score=min_score)

    active_required = required if required is not None else REQUIRED
    missing_required = [k for k in active_required if mapping.get(k) is None]
    if missing_required:
        raise ValueError(
            f"Colonnes obligatoires introuvables dans le CSV : {missing_required}. "
            f"Colonnes disponibles : {list(df.columns)}"
        )

    rename_dict = {v: k for k, v in mapping.items() if v is not None}
    df_renamed = df.rename(columns=rename_dict)

    if verbose:
        print(f"  [column_matcher] Colonnes renommées avec succès : {rename_dict}")

    return df_renamed
