"""
regression_model.py
Modèle prédictif ΔG(MexR) ~ ΔG(MexB) [+ MW + LogP], calibré sur le jeu de
référence (139 composés), utilisé en Mode 2 pour prédire ΔG(MexR) à partir
de ΔG(MexB) seul.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import pickle


class MexRPredictor:
    def __init__(self):
        self.model = None
        self.predictors = None
        self.resid_std = None

    def fit(self, df_ref, y_col="dg_mexr", predictors=("dg_mexb",)):
        """Calibre le modèle sur le jeu de données de référence complet."""
        predictors = [p for p in predictors if p in df_ref.columns]
        sub = df_ref.dropna(subset=[y_col, *predictors])
        X = sm.add_constant(sub[predictors])
        self.model = sm.OLS(sub[y_col], X).fit()
        self.predictors = predictors
        self.resid_std = np.std(self.model.resid, ddof=len(predictors) + 1)
        return self

    def predict(self, df_new):
        """Prédit ΔG(MexR) + intervalle de prédiction à 95% pour de
        nouveaux composés ne disposant que de ΔG(MexB) (et MW/LogP si
        disponibles)."""
        if self.model is None:
            raise RuntimeError("Le modèle n'a pas été calibré (appeler fit() d'abord).")
        missing = [p for p in self.predictors if p not in df_new.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes pour la prédiction : {missing}")
        X = sm.add_constant(df_new[self.predictors], has_constant="add")
        pred = self.model.get_prediction(X)
        summary = pred.summary_frame(alpha=0.05)
        out = df_new.copy()
        out["dg_mexr_predit"] = summary["mean"].values
        out["dg_mexr_IC95_bas"] = summary["obs_ci_lower"].values
        out["dg_mexr_IC95_haut"] = summary["obs_ci_upper"].values
        return out

    def summary_text(self):
        if self.model is None:
            return "Modèle non calibré."
        return str(self.model.summary())

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path):
        with open(path, "rb") as f:
            return pickle.load(f)
