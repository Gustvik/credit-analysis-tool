BASEL3_RISK_WEIGHTS = {
    "hard_asset":  0.75,
    "it_utstyr":   1.00,
    "agro":        0.75,
    "medisinsk":   1.00,
}

SEGMENTS = {
    "hard_asset": {
        "label": "Hard asset (maskin/kjøretøy)",
        "exposure": 3_000_000_000,
        "pd": 0.012,
        "lgd": 0.25,
        "spread": 0.025,
    },
    "it_utstyr": {
        "label": "IT-utstyr",
        "exposure": 2_000_000_000,
        "pd": 0.021,
        "lgd": 0.40,
        "spread": 0.030,
    },
    "agro": {
        "label": "Agro",
        "exposure": 2_000_000_000,
        "pd": 0.018,
        "lgd": 0.35,
        "spread": 0.028,
    },
    "medisinsk": {
        "label": "Medisinsk utstyr",
        "exposure": 3_000_000_000,
        "pd": 0.015,
        "lgd": 0.30,
        "spread": 0.027,
    },
}

def calculate_portfolio_roe(
    segments: dict,
    funding_rate: float,
    opex_ratio: float = 0.30,
    tax_rate: float = 0.22,
    capital_ratio: float = 0.12,
) -> dict:
    total_exposure = 0
    total_nii = 0
    total_el = 0
    total_rwa = 0
    segment_results = []

    for key, seg in segments.items():
        exp = seg["exposure"]
        pd = seg["pd"]
        lgd = seg["lgd"]
        spread = seg["spread"]
        rw = BASEL3_RISK_WEIGHTS.get(key, 1.0)

        nii = exp * spread
        el = exp * pd * lgd
        rwa = exp * rw
        capital = rwa * capital_ratio
        net_margin = spread - (pd * lgd)

        segment_results.append({
            "segment": seg["label"],
            "eksponering": exp,
            "spread": spread * 100,
            "pd": pd * 100,
            "lgd": lgd * 100,
            "el": el,
            "el_rate": pd * lgd * 100,
            "nii": nii,
            "rwa": rwa,
            "risikovekt": rw * 100,
            "kapital": capital,
            "netto_margin": net_margin * 100,
        })

        total_exposure += exp
        total_nii += nii
        total_el += el
        total_rwa += rwa

    funding_cost = total_exposure * funding_rate
    gross_income = total_nii
    net_after_el = gross_income - total_el
    opex = gross_income * opex_ratio
    ebt = net_after_el - opex
    tax = max(0, ebt * tax_rate)
    net_income = ebt - tax
    total_capital = total_rwa * capital_ratio
    roe = (net_income / total_capital) * 100 if total_capital > 0 else 0
    nim = (gross_income / total_exposure) * 100
    weighted_el = (total_el / total_exposure) * 100
    weighted_pd = sum(
        s["eksponering"] * s["pd"] / 100
        for s in segment_results
    ) / total_exposure * 100

    return {
        "segment_results": segment_results,
        "total_exposure": total_exposure,
        "total_nii": total_nii,
        "total_el": total_el,
        "total_rwa": total_rwa,
        "total_capital": total_capital,
        "funding_cost": funding_cost,
        "gross_income": gross_income,
        "net_after_el": net_after_el,
        "opex": opex,
        "ebt": ebt,
        "tax": tax,
        "net_income": net_income,
        "roe": roe,
        "nim": nim,
        "weighted_el": weighted_el,
        "weighted_pd": weighted_pd,
    }
