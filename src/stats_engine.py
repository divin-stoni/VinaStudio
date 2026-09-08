"""
stats_engine.py
Moteur d'analyse statistique reproduisant les analyses de l'article
MexAB-OprM (corrélation ΔG(MexB)-ΔG(MexR), robustesse, régression, SI).
"""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


# Seuil par défaut pour le filtre SI
PERCENTILE_SI_SEUIL_DEFAULT = 75


# ---------------------------------------------------------------------
# Détection automatique du mode d'analyse
# ---------------------------------------------------------------------

def detect_analysis_mode(df, group_col="groupe"):
    """
    Détecte automatiquement le type de référence chargé.

    Retour :
        GROUPES -> présence d'une colonne groupe exploitable
        GLOBAL  -> aucune colonne groupe
    """

    if group_col not in df.columns:
        return "GLOBAL"

    groupes = (
        df[group_col]
        .dropna()
        .astype(str)
        .str.strip()
    )

    groupes = groupes[
        groupes.str.lower().isin(
            ["", "nan", "none", "null"]
        ) == False
    ]

    if len(groupes.unique()) > 0:
        return "GROUPES"

    return "GLOBAL"





# ---------------------------------------------------------------------
# Préparation du mode d'analyse
# ---------------------------------------------------------------------

def prepare_analysis_groups(df, group_col="groupe"):
    """
    Prépare la structure d'analyse.

    GROUPES :
        conserve les familles présentes dans le CSV.

    GLOBAL :
        aucune création de faux groupe.
        retourne uniquement le mode global.
    """

    work = df.copy()

    mode = detect_analysis_mode(work, group_col)

    if mode == "GROUPES":
        work[group_col] = (
            work[group_col]
            .fillna("SANS_GROUPE")
            .astype(str)
            .str.strip()
        )

    return work, mode


# ---------------------------------------------------------------------
# 1. Corrélations Pearson / Spearman par groupe + global
# ---------------------------------------------------------------------
def correlations_by_group(df, x_col="dg_mexb", y_col="dg_mexr",
                          group_col="groupe"):
    """
    Corrélations Pearson / Spearman par groupe + GLOBAL.

    Fonctionne avec :
      - plusieurs groupes ;
      - un seul groupe ;
      - aucune colonne de groupe.

    Si la colonne group_col est absente ou inutilisable, toutes les
    observations sont considérées comme appartenant à un groupe unique
    nommé "SANS_GROUPE".

    Les statistiques sont calculées pour chaque groupe lorsque n >= 3,
    ainsi que pour GLOBAL.
    """
    work, mode = prepare_analysis_groups(df, group_col)

    rows = []

    if mode == "GLOBAL":
        groups = []
    else:
        groups = list(work[group_col].dropna().unique())

    for g in groups + ["GLOBAL"]:
        sub = work if g == "GLOBAL" else work[work[group_col] == g]

        sub = sub.dropna(subset=[x_col, y_col])
        n = len(sub)

        if n < 3:
            continue

        x = sub[x_col].to_numpy(dtype=float)
        y = sub[y_col].to_numpy(dtype=float)

        # Une corrélation n'est pas définie si une variable est constante.
        if np.std(x) == 0 or np.std(y) == 0:
            continue

        r_p, p_p = stats.pearsonr(x, y)
        r_s, p_s = stats.spearmanr(x, y)
        slope, intercept, r_lin, p_lin, se = stats.linregress(x, y)

        rows.append({
            "groupe": g,
            "n": n,
            "r_pearson": r_p,
            "p_pearson": p_p,
            "r_spearman": r_s,
            "p_spearman": p_s,
            "R2": r_lin ** 2,
            "pente": slope,
            "intercept": intercept,
        })

    out = pd.DataFrame(rows)

    if out.empty:
        return out

    # Correction FDR uniquement sur les groupes réels.
    # GLOBAL n'est jamais inclus dans la correction.
    mask = out["groupe"] != "GLOBAL"

    if mask.sum() > 0:
        rej, p_fdr, _, _ = multipletests(
            out.loc[mask, "p_pearson"],
            method="fdr_bh"
        )
        out.loc[mask, "p_pearson_fdr"] = p_fdr

    return out


# ---------------------------------------------------------------------
# 2. Intervalle de confiance bootstrap (percentile) pour r de Pearson
# ---------------------------------------------------------------------
SEED_BOOTSTRAP = 42


def bootstrap_ci_r(x, y, n_boot=5000, ci=95, seed=SEED_BOOTSTRAP):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x), np.asarray(y)
    n = len(x)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        boots[i] = np.corrcoef(x[idx], y[idx])[0, 1]
    lo = np.percentile(boots, (100 - ci) / 2)
    hi = np.percentile(boots, 100 - (100 - ci) / 2)
    return lo, hi, boots


def bootstrap_ci_by_group(df, x_col="dg_mexb", y_col="dg_mexr",
                           group_col="groupe", n_boot=5000, ci=95,
                           seed=SEED_BOOTSTRAP):
    """
    IC bootstrap de Pearson par groupe + GLOBAL.

    Compatible avec zéro, un ou plusieurs groupes.
    Une colonne groupe absente est remplacée par "SANS_GROUPE".
    """
    work = df.copy()

    mode = detect_analysis_mode(work)

    if mode == "GLOBAL":
        work[group_col] = "SANS_GROUPE"

    elif group_col not in work.columns:
        work[group_col] = "SANS_GROUPE"
    else:
        work[group_col] = work[group_col].fillna("SANS_GROUPE").astype(str)
        work.loc[work[group_col].str.strip() == "", group_col] = "SANS_GROUPE"

    rows = []
    groups = list(work[group_col].dropna().unique())

    for g in groups + ["GLOBAL"]:
        sub = work if g == "GLOBAL" else work[work[group_col] == g]
        sub = sub.dropna(subset=[x_col, y_col])

        if len(sub) < 3:
            continue

        x = sub[x_col].to_numpy(dtype=float)
        y = sub[y_col].to_numpy(dtype=float)

        if np.std(x) == 0 or np.std(y) == 0:
            continue

        lo, hi, _ = bootstrap_ci_r(
            x, y,
            n_boot=n_boot,
            ci=ci,
            seed=seed
        )

        rows.append({
            "groupe": g,
            "n": len(sub),
            "IC_low": lo,
            "IC_high": hi
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# 3. Analyse leave-one-out (sensibilité de r à chaque point)
# ---------------------------------------------------------------------
def leave_one_out(df, x_col="dg_mexb", y_col="dg_mexr",
                  group_col="groupe", name_col="molecule"):
    """
    Analyse leave-one-out par groupe + GLOBAL.

    Compatible avec un seul groupe ou plusieurs groupes.
    Si aucune colonne groupe n'existe, toutes les observations sont
    placées dans "SANS_GROUPE".
    """
    work = df.copy()

    mode = detect_analysis_mode(work)

    if mode == "GLOBAL":
        work[group_col] = "SANS_GROUPE"

    elif group_col not in work.columns:
        work[group_col] = "SANS_GROUPE"
    else:
        work[group_col] = work[group_col].fillna("SANS_GROUPE").astype(str)
        work.loc[work[group_col].str.strip() == "", group_col] = "SANS_GROUPE"

    results = []
    groups = list(work[group_col].dropna().unique())

    for g in groups + ["GLOBAL"]:
        sub = work if g == "GLOBAL" else work[work[group_col] == g]
        sub = sub.dropna(subset=[x_col, y_col]).reset_index(drop=True)

        if len(sub) < 4:
            continue

        x = sub[x_col].to_numpy(dtype=float)
        y = sub[y_col].to_numpy(dtype=float)

        if np.std(x) == 0 or np.std(y) == 0:
            continue

        r_full = np.corrcoef(x, y)[0, 1]

        deltas = []

        for i in range(len(sub)):
            rest = sub.drop(index=i)

            xr = rest[x_col].to_numpy(dtype=float)
            yr = rest[y_col].to_numpy(dtype=float)

            if len(rest) < 3 or np.std(xr) == 0 or np.std(yr) == 0:
                deltas.append(np.nan)
                continue

            r_loo = np.corrcoef(xr, yr)[0, 1]
            deltas.append(r_full - r_loo)

        deltas = np.asarray(deltas, dtype=float)

        if np.all(np.isnan(deltas)):
            continue

        i_max = np.nanargmax(np.abs(deltas))

        results.append({
            "groupe": g,
            "n": len(sub),
            "r_complet": r_full,
            "delta_r_max": deltas[i_max],
            "composé_le_plus_influent": (
                sub.loc[i_max, name_col]
                if name_col in sub.columns
                else i_max
            ),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------
# 4. Corrélation partielle (contrôlant MW, LogP) + régression multiple
# ---------------------------------------------------------------------
def partial_correlation(df, x_col="dg_mexb", y_col="dg_mexr", covariates=("MW", "LogP")):
    covariates = [c for c in covariates if c in df.columns]
    sub = df.dropna(subset=[x_col, y_col, *covariates])
    if not covariates:
        return None, sub
    # résidus de x et y après régression sur les covariables
    Xc = sm.add_constant(sub[covariates])
    res_x = sm.OLS(sub[x_col], Xc).fit().resid
    res_y = sm.OLS(sub[y_col], Xc).fit().resid
    r_partial, p_partial = stats.pearsonr(res_x, res_y)
    r_brut, p_brut = stats.pearsonr(sub[x_col], sub[y_col])
    return {"r_partiel": r_partial, "p_partiel": p_partial,
            "r_brut": r_brut, "p_brut": p_brut, "n": len(sub),
            "covariables": covariates}, sub


def multiple_regression(df, y_col="dg_mexr", predictors=("dg_mexb", "MW", "LogP")):
    predictors = [p for p in predictors if p in df.columns]
    sub = df.dropna(subset=[y_col, *predictors])
    X = sm.add_constant(sub[predictors])
    model = sm.OLS(sub[y_col], X).fit()
    coef_table = pd.DataFrame({
        "coef": model.params, "std_err": model.bse,
        "t": model.tvalues, "p": model.pvalues,
    })
    return model, coef_table


# ---------------------------------------------------------------------
# 5. Homogénéité des pentes entre familles (ANCOVA, interaction)
# ---------------------------------------------------------------------
def homogeneity_of_slopes(
    df,
    x_col="dg_mexb",
    y_col="dg_mexr",
    group_col="groupe"
):
    """
    Test d'homogénéité des pentes entre groupes.

    Activé uniquement si plusieurs vrais groupes existent.
    """

    import pandas as pd

    if group_col not in df.columns:
        return pd.DataFrame({
            "status": ["NON_APPLICABLE"],
            "raison": ["Colonne groupe absente"]
        })

    groups = (
        df[group_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    groups = [
        g for g in groups.unique()
        if g and g.upper() not in [
            "SANS_GROUPE",
            "GLOBAL"
        ]
    ]

    if len(groups) < 2:
        return pd.DataFrame({
            "status": ["NON_APPLICABLE"],
            "raison": ["Pas assez de groupes"]
        })

    work = df.copy()

    work[group_col] = (
        work[group_col]
        .astype(str)
        .str.strip()
    )

    model = smf.ols(
        f"{y_col} ~ {x_col} * C({group_col})",
        data=work
    ).fit()

    return sm.stats.anova_lm(
        model,
        typ=2
    )



def compute_si_and_classification(df, x_col="dg_mexb", y_col="dg_mexr",
                                   seuil_risque_absolu=-8.289, ref_name="pyocyanine"):
    out = df.copy()

    # ------------------------------------------------------------
    # SECURITE : les colonnes dupliquees peuvent transformer
    # out[x_col] ou out[y_col] en DataFrame au lieu d'une Series.
    # On les coalesce proprement avant le calcul du SI.
    # ------------------------------------------------------------
    for column in (x_col, y_col):
        positions = [
            i
            for i, name in enumerate(out.columns)
            if name == column
        ]

        if len(positions) > 1:
            merged = out.iloc[:, positions[0]].copy()

            for position in positions[1:]:
                merged = merged.combine_first(
                    out.iloc[:, position]
                )

            out = out.drop(
                columns=[column]
            )

            out[column] = merged

    if x_col not in out.columns:
        raise ValueError(
            f"Colonne scientifique absente : {x_col}"
        )

    if y_col not in out.columns:
        raise ValueError(
            f"Colonne scientifique absente : {y_col}"
        )

    out[x_col] = pd.to_numeric(
        out[x_col],
        errors="coerce",
    )

    out[y_col] = pd.to_numeric(
        out[y_col],
        errors="coerce",
    )

    out["SI_calc"] = (
        out[y_col] - out[x_col]
    )
    out["percentile_SI"] = out["SI_calc"].rank(pct=True) * 100
    # Convention : plus ΔG(MexR) est négatif, plus la liaison est forte -> plus le risque
    # de dérépression est élevé. Un composé est "à risque" si ΔG(MexR) <= seuil
    # (donc au moins aussi négatif que le seuil), "Favorable" si ΔG(MexR) > seuil.
    out["statut_risque"] = np.where(
        out[y_col] <= seuil_risque_absolu, "À risque (dérépression possible)", "Favorable"
    )
    out.attrs["seuil_risque_absolu"] = seuil_risque_absolu
    out.attrs["ref_name"] = ref_name
    return out


PERCENTILE_SI_SEUIL_DEFAULT = 50.0



def dual_filter(df_classified, percentile_col="percentile_SI", status_col="statut_risque",
                 percentile_seuil=PERCENTILE_SI_SEUIL_DEFAULT):
    """
    Filtre à double critère : ne considère que les composés à indice de sélectivité
    relatif favorable (percentile_SI > percentile_seuil), puis les sépare selon le
    critère de risque absolu :
      - valides         : percentile > seuil ET statut "Favorable" (sous le seuil absolu)
      - exclus_absolu    : percentile > seuil MAIS "À risque" (au-dessus du seuil absolu),
                            donc de bons candidats relatifs à exclure malgré tout.
    Retourne (valides, exclus_absolu).
    """
    relatif_favorable = df_classified[df_classified[percentile_col] > percentile_seuil]
    valides = relatif_favorable[relatif_favorable[status_col] == "Favorable"].sort_values(
        "SI_calc", ascending=False).reset_index(drop=True)
    exclus_absolu = relatif_favorable[relatif_favorable[status_col] == "À risque (dérépression possible)"].sort_values(
        "SI_calc", ascending=False).reset_index(drop=True)
    return valides, exclus_absolu


def top_candidates(df_classified, n=10, si_col="SI_calc", status_col="statut_risque"):
    favorables = df_classified[df_classified[status_col] == "Favorable"]
    return favorables.sort_values(si_col, ascending=False).head(n)
