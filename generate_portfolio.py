import pandas as pd
import numpy as np
import sys
sys.path.insert(0, r"C:\credit_tool")

np.random.seed(42)

print("Leser enheter_alle.xlsx...")
df = pd.read_excel(
    r"C:\credit_tool\enheter_alle.xlsx",
    usecols=[
        "Organisasjonsnummer",
        "Navn",
        "Næringskode 1.beskrivelse",
        "Antall ansatte",
        "Konkurs",
        "Under avvikling",
        "Registrert i Foretaksregisteret",
        "Siste innsendte årsregnskap",
        "Organisasjonsform.kode",
    ]
)

print(f"Totalt rader: {len(df)}")

df = df[
    (df["Organisasjonsform.kode"] == "AS") &
    (df["Konkurs"] == "NEI") &
    (df["Under avvikling"] == "NEI") &
    (df["Registrert i Foretaksregisteret"] == "JA") &
    (df["Antall ansatte"] >= 5) &
    (df["Siste innsendte årsregnskap"] >= 2021)
].copy()

print(f"Filtrerte selskaper: {len(df)}")

df = df.sample(min(1000, len(df)), random_state=42).reset_index(drop=True)

BRANSJE_PROFILER = {
    "Engroshandel":         {"rev_mean": 80, "rev_std": 40, "margin_mean": 3.5, "pd_base": 0.018},
    "Detaljhandel":         {"rev_mean": 60, "rev_std": 30, "margin_mean": 2.5, "pd_base": 0.022},
    "Bygg og anlegg":       {"rev_mean": 70, "rev_std": 35, "margin_mean": 4.0, "pd_base": 0.020},
    "Transport":            {"rev_mean": 50, "rev_std": 25, "margin_mean": 3.0, "pd_base": 0.025},
    "Industri":             {"rev_mean": 90, "rev_std": 45, "margin_mean": 5.0, "pd_base": 0.015},
    "IT":                   {"rev_mean": 40, "rev_std": 20, "margin_mean": 8.0, "pd_base": 0.010},
    "Eiendom":              {"rev_mean": 30, "rev_std": 15, "margin_mean": 12.0, "pd_base": 0.012},
    "Rådgivning":           {"rev_mean": 25, "rev_std": 12, "margin_mean": 10.0, "pd_base": 0.012},
    "Helse":                {"rev_mean": 35, "rev_std": 18, "margin_mean": 6.0, "pd_base": 0.008},
    "Landbruk":             {"rev_mean": 20, "rev_std": 10, "margin_mean": 4.5, "pd_base": 0.020},
    "Default":              {"rev_mean": 45, "rev_std": 22, "margin_mean": 4.0, "pd_base": 0.018},
}

def get_profil(bransje):
    if pd.isna(bransje):
        return BRANSJE_PROFILER["Default"]
    b = str(bransje).lower()
    if "engros" in b:       return BRANSJE_PROFILER["Engroshandel"]
    if "detalj" in b:       return BRANSJE_PROFILER["Detaljhandel"]
    if "bygg" in b or "anlegg" in b: return BRANSJE_PROFILER["Bygg og anlegg"]
    if "transport" in b or "lager" in b: return BRANSJE_PROFILER["Transport"]
    if "industri" in b or "produksjon" in b: return BRANSJE_PROFILER["Industri"]
    if "ikt" in b or "data" in b or "program" in b: return BRANSJE_PROFILER["IT"]
    if "eiendom" in b:      return BRANSJE_PROFILER["Eiendom"]
    if "rådgiv" in b or "konsulent" in b: return BRANSJE_PROFILER["Rådgivning"]
    if "helse" in b or "lege" in b or "tann" in b: return BRANSJE_PROFILER["Helse"]
    if "jord" in b or "skog" in b or "fisk" in b: return BRANSJE_PROFILER["Landbruk"]
    return BRANSJE_PROFILER["Default"]

n = len(df)
revenues, net_margins, equity_ratios, debt_ratios = [], [], [], []
current_ratios, ebitda_margins, operating_margins, interest_coverages = [], [], [], []

for _, row in df.iterrows():
    p = get_profil(row["Næringskode 1.beskrivelse"])
    ansatte = max(1, row["Antall ansatte"] or 5)
    
    rev = max(1, float(np.random.normal(p["rev_mean"] * ansatte / 20, p["rev_std"])))
    margin = float(np.clip(np.random.normal(p["margin_mean"], 3.0), -15, 25))
    eq = float(np.clip(np.random.normal(38, 15), 5, 85))
    dr = float(np.clip(np.random.normal(0.52, 0.15), 0.10, 0.92))
    cr = float(np.clip(np.random.normal(135, 35), 60, 280))
    ebitda = float(np.clip(np.random.normal(p["margin_mean"] + 3, 3), -5, 30))
    op = float(np.clip(np.random.normal(p["margin_mean"], 3), -10, 20))
    ic = float(np.clip(np.random.normal(4.5, 2.5), 0.3, 15))

    revenues.append(rev)
    net_margins.append(margin)
    equity_ratios.append(eq)
    debt_ratios.append(dr)
    current_ratios.append(cr)
    ebitda_margins.append(ebitda)
    operating_margins.append(op)
    interest_coverages.append(ic)

df["revenue_mnok"] = revenues
df["net_margin"] = net_margins
df["equity_ratio"] = equity_ratios
df["debt_ratio"] = debt_ratios
df["current_ratio"] = current_ratios
df["ebitda_margin"] = ebitda_margins
df["operating_margin"] = operating_margins
df["interest_coverage"] = interest_coverages

from analysis.credit_engine import credit_score
from analysis.ml_model import predict_pd

scores, ratings, pd_estimates, z_scores, z_ratings, flags_list = [], [], [], [], [], []

print("Beregner kredittskår og PD for 1000 selskaper...")
for i, row in df.iterrows():
    ratios = {
        "equity_ratio": row["equity_ratio"],
        "net_margin": row["net_margin"],
        "debt_ratio": row["debt_ratio"],
        "current_ratio": row["current_ratio"],
        "ebitda_margin": row["ebitda_margin"],
        "operating_margin": row["operating_margin"],
        "interest_coverage": row["interest_coverage"],
    }
    score = credit_score(ratios)
    ml = predict_pd(ratios)

    scores.append(score["score"])
    ratings.append(score["rating"])
    pd_estimates.append(ml["pd_percent"])
    z_scores.append(ml["z_score"])
    z_ratings.append(ml["z_rating"])
    flags_list.append("; ".join(score["flags"]))

    if (i + 1) % 100 == 0:
        print(f"  {i+1}/1000 ferdig...")

df["score"] = scores
df["rating"] = ratings
df["pd_percent"] = pd_estimates
df["z_score"] = z_scores
df["z_rating"] = z_ratings
df["risikoindikatorere"] = flags_list

output_cols = [
    "Organisasjonsnummer", "Navn", "Næringskode 1.beskrivelse",
    "Antall ansatte", "revenue_mnok", "net_margin", "equity_ratio",
    "debt_ratio", "current_ratio", "ebitda_margin", "operating_margin",
    "interest_coverage", "score", "rating", "pd_percent",
    "z_score", "z_rating", "risikoindikatorere"
]

output = df[output_cols].copy()
output.columns = [
    "org_nr", "navn", "bransje", "ansatte", "omsetning_mnok",
    "netto_margin", "egenkapital_pct", "gjeldsgrad", "likviditetsgrad",
    "ebitda_margin", "driftsmargin", "rentedekningsgrad",
    "score", "rating", "pd_pct", "z_score", "z_rating", "risikoindikatorere"
]

output.to_csv(r"C:\credit_tool\portfolio_1000.csv", index=False)
print(f"\nFerdig! Lagret {len(output)} selskaper til portfolio_1000.csv")
print(f"\nRatingfordeling:")
print(output["rating"].value_counts())
print(f"\nGjennomsnittlig score: {output['score'].mean():.1f}")
print(f"Gjennomsnittlig PD: {output['pd_pct'].mean():.2f}%")
