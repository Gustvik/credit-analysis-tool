import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os

MODEL_PATH = r"C:\credit_tool\analysis\pd_model.pkl"
SCALER_PATH = r"C:\credit_tool\analysis\scaler.pkl"

def generate_training_data(n: int = 2000) -> pd.DataFrame:
    np.random.seed(42)

    equity_ratio = np.random.normal(35, 15, n).clip(2, 90)
    net_margin = np.random.normal(4, 6, n).clip(-20, 25)
    debt_ratio = np.random.normal(0.55, 0.18, n).clip(0.05, 0.98)
    current_ratio = np.random.normal(140, 40, n).clip(50, 300)
    ebitda_margin = np.random.normal(8, 5, n).clip(-10, 35)
    operating_margin = np.random.normal(3, 5, n).clip(-15, 25)
    revenue_growth = np.random.normal(3, 12, n).clip(-40, 50)
    interest_coverage = np.random.normal(4, 3, n).clip(0.1, 20)

    # Altman Z-score (forenklet versjon)
    working_capital_ratio = (current_ratio / 100 - 1) * 0.3
    retained_earnings_ratio = equity_ratio / 100 * 0.5
    ebit_ratio = operating_margin / 100
    equity_debt_ratio = (equity_ratio / (100 - equity_ratio + 1))
    z_score = (
        1.2 * working_capital_ratio +
        1.4 * retained_earnings_ratio +
        3.3 * ebit_ratio +
        0.6 * equity_debt_ratio +
        0.999 * 0.05
    )

    # Mislighold basert på realistiske terskler
    default_prob = (
        0.15 * (debt_ratio > 0.80).astype(float) +
        0.20 * (net_margin < 0).astype(float) +
        0.15 * (equity_ratio < 10).astype(float) +
        0.15 * (current_ratio < 100).astype(float) +
        0.10 * (interest_coverage < 1.5).astype(float) +
        0.10 * (ebitda_margin < 2).astype(float) +
        0.05 * (z_score < 1.8).astype(float) +
        np.random.uniform(0, 0.15, n)
    )
    default = (default_prob > 0.35).astype(int)

    return pd.DataFrame({
        "equity_ratio": equity_ratio,
        "net_margin": net_margin,
        "debt_ratio": debt_ratio,
        "current_ratio": current_ratio,
        "ebitda_margin": ebitda_margin,
        "operating_margin": operating_margin,
        "revenue_growth": revenue_growth,
        "interest_coverage": interest_coverage,
        "z_score": z_score,
        "default": default,
    })

FEATURES = [
    "equity_ratio", "net_margin", "debt_ratio",
    "current_ratio", "ebitda_margin", "operating_margin",
    "interest_coverage", "z_score"
]

def train_model():
    df = generate_training_data(2000)
    X = df[FEATURES]
    y = df["default"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=20,
        random_state=42,
        class_weight="balanced"
    )
    model.fit(X_scaled, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    return model, scaler

def load_or_train():
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
    else:
        model, scaler = train_model()
    return model, scaler

def predict_pd(ratios: dict) -> dict:
    model, scaler = load_or_train()

    equity_ratio = ratios.get("equity_ratio") or 30
    net_margin = ratios.get("net_margin") or 2
    debt_ratio = ratios.get("debt_ratio") or 0.5
    current_ratio = ratios.get("current_ratio") or 130
    ebitda_margin = ratios.get("ebitda_margin") or 5
    operating_margin = ratios.get("operating_margin") or 3
    interest_coverage = ratios.get("interest_coverage") or 3

    wc_ratio = (current_ratio / 100 - 1) * 0.3
    re_ratio = equity_ratio / 100 * 0.5
    ebit_ratio = operating_margin / 100
    eq_debt = equity_ratio / (100 - equity_ratio + 1)
    z_score = (
        1.2 * wc_ratio +
        1.4 * re_ratio +
        3.3 * ebit_ratio +
        0.6 * eq_debt +
        0.999 * 0.05
    )

    features = np.array([[
        equity_ratio, net_margin, debt_ratio,
        current_ratio, ebitda_margin, operating_margin,
        interest_coverage, z_score
    ]])

    features_scaled = scaler.transform(features)
    pd_estimate = model.predict_proba(features_scaled)[0][1]
    importances = dict(zip(FEATURES, model.feature_importances_))

    if z_score > 2.99:
        z_rating = "Sikker sone (Z > 2.99)"
    elif z_score > 1.81:
        z_rating = "Grå sone (1.81–2.99)"
    else:
        z_rating = "Faresone (Z < 1.81)"

    return {
        "pd_estimate": pd_estimate,
        "pd_percent": round(pd_estimate * 100, 2),
        "z_score": round(z_score, 2),
        "z_rating": z_rating,
        "feature_importance": importances,
    }
