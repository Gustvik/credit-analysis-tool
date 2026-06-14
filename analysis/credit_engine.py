def calculate_ratios(records: list) -> list:
    results = []

    for r in records:
        revenue = r.get("plNetSales", 0) or 0
        ebitda = r.get("kpiEbitda", 0) or 0
        ebit = r.get("plEbit", 0) or 0
        net_income = r.get("plNetProfitLoss", 0) or 0
        total_assets = r.get("bsTotalEquityAndLiabilities", 0) or 0
        equity = r.get("bsTotalEquity", 0) or 0
        long_term_debt = r.get("bsTotalLongTermDebts", 0) or 0
        short_term_debt = r.get("bsTotalCurrentLiabilities", 0) or 0
        total_debt = long_term_debt + short_term_debt
        year = r.get("toDate", "ukjent")[:4]

        debt_ratio = round(total_debt / total_assets, 2) if total_assets else None
        equity_ratio = r.get("kpiEquityRatioPercent")
        net_margin = round(net_income / revenue * 100, 1) if revenue else None
        ebitda_margin = round(ebitda / revenue * 100, 1) if revenue else None
        operating_margin = r.get("kpiOperatingMarginPercent")
        current_ratio = r.get("kpiCurrentRatioPercent")

        results.append({
            "year": year,
            "revenue": revenue,
            "ebitda": ebitda,
            "ebit": ebit,
            "net_income": net_income,
            "total_assets": total_assets,
            "total_debt": total_debt,
            "equity": equity,
            "debt_ratio": debt_ratio,
            "equity_ratio": equity_ratio,
            "net_margin": net_margin,
            "ebitda_margin": ebitda_margin,
            "operating_margin": operating_margin,
            "current_ratio": current_ratio,
        })

    return results


def credit_score(ratios: dict) -> dict:
    score = 100
    flags = []

    if ratios.get("debt_ratio") is not None:
        if ratios["debt_ratio"] > 0.80:
            score -= 30
            flags.append("Meget høy gjeldsgrad (>80%)")
        elif ratios["debt_ratio"] > 0.65:
            score -= 15
            flags.append("Høy gjeldsgrad (>65%)")

    if ratios.get("equity_ratio") is not None:
        if ratios["equity_ratio"] < 10:
            score -= 20
            flags.append("Meget lav egenkapitalandel (<10%)")
        elif ratios["equity_ratio"] < 20:
            score -= 10
            flags.append("Lav egenkapitalandel (<20%)")

    if ratios.get("net_margin") is not None:
        if ratios["net_margin"] < 0:
            score -= 20
            flags.append("Negativt nettoresultat")
        elif ratios["net_margin"] < 3:
            score -= 10
            flags.append("Lav netto margin (<3%)")

    if ratios.get("operating_margin") is not None:
        if ratios["operating_margin"] < 0:
            score -= 20
            flags.append("Negativt driftsresultat")
        elif ratios["operating_margin"] < 2:
            score -= 10
            flags.append("Svak driftsmargin (<2%)")

    if ratios.get("current_ratio") is not None:
        if ratios["current_ratio"] < 100:
            score -= 15
            flags.append("Likviditetsgrad under 1.0")
        elif ratios["current_ratio"] < 120:
            score -= 5
            flags.append("Svak likviditetsgrad (<1.2)")

    score = max(0, score)

    if score >= 75:
        rating = "A – Lav risiko"
    elif score >= 50:
        rating = "B – Moderat risiko"
    elif score >= 25:
        rating = "C – Høy risiko"
    else:
        rating = "D – Meget høy risiko"

    return {"score": score, "rating": rating, "flags": flags}
