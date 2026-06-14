import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
import copy

sys.path.insert(0, r"C:\credit_tool")

from data.api_client import get_financial_data, get_company_info
from analysis.credit_engine import calculate_ratios, credit_score
from analysis.ml_model import predict_pd, train_model
from analysis.portfolio_model import calculate_portfolio_roe, SEGMENTS, BASEL3_RISK_WEIGHTS

st.set_page_config(page_title="Kredittanalyse", page_icon="📊", layout="wide")

st.sidebar.title("Navigasjon")
side = st.sidebar.radio("Velg side", ["Enkeltselskap", "Portefølje", "ROE-kalkulator"])

if side == "Enkeltselskap":
    st.title("Kredittanalyse – Enkeltselskap")
    org_nr = st.text_input("Organisasjonsnummer", placeholder="989781707")

    if st.button("Analyser") and org_nr:
        with st.spinner("Henter data..."):
            company = get_company_info(org_nr)
            financial = get_financial_data(org_nr)

        if "error" in company:
            st.error(f"Fant ikke selskap med org.nr {org_nr}")
        elif "records" not in financial or not financial["records"]:
            st.error("Ingen finansdata tilgjengelig")
        else:
            navn = company.get("navn", "Ukjent")
            bransje = company.get("naeringskode1", {}).get("beskrivelse", "Ukjent")
            konkurs = company.get("konkurs", False)

            st.header(navn)
            col1, col2, col3 = st.columns(3)
            col1.metric("Org.nr", org_nr)
            col2.metric("Bransje", bransje)
            col3.metric("Konkurs", "⚠️ Ja" if konkurs else "✅ Nei")

            records = financial["records"]
            ratios = calculate_ratios(records)
            siste = ratios[0]
            rule_score = credit_score(siste)
            ml_result = predict_pd(siste)

            st.divider()
            st.subheader("Kredittskår og PD-estimat")

            col1, col2, col3 = st.columns(3)
            score_val = rule_score["score"]
            color = "green" if score_val >= 75 else "orange" if score_val >= 50 else "red"

            with col1:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score_val,
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": color},
                        "steps": [
                            {"range": [0, 25], "color": "#ffcccc"},
                            {"range": [25, 50], "color": "#ffe0b2"},
                            {"range": [50, 75], "color": "#fff9c4"},
                            {"range": [75, 100], "color": "#c8e6c9"},
                        ]
                    },
                    title={"text": rule_score["rating"]}
                ))
                fig.update_layout(height=280, margin=dict(t=50, b=0))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                pd_val = ml_result["pd_percent"]
                pd_color = "green" if pd_val < 1 else "orange" if pd_val < 3 else "red"
                fig2 = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=pd_val,
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 10]},
                        "bar": {"color": pd_color},
                        "steps": [
                            {"range": [0, 1], "color": "#c8e6c9"},
                            {"range": [1, 3], "color": "#fff9c4"},
                            {"range": [3, 10], "color": "#ffcccc"},
                        ]
                    },
                    title={"text": "ML PD-estimat"}
                ))
                fig2.update_layout(height=280, margin=dict(t=50, b=0))
                st.plotly_chart(fig2, use_container_width=True)

            with col3:
                z = ml_result["z_score"]
                z_color = "green" if z > 2.99 else "orange" if z > 1.81 else "red"
                st.metric("Altman Z-score", f"{z}")
                st.markdown(f"**{ml_result['z_rating']}**")
                st.divider()
                st.caption("Risikoindikatorere")
                if rule_score["flags"]:
                    for flag in rule_score["flags"]:
                        st.warning(flag)
                else:
                    st.success("Ingen negative indikatorer")

            st.divider()
            st.subheader("Nøkkeltall – siste år")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Omsetning (NOK)", f"{siste['revenue']:,.0f}")
            col2.metric("EBITDA (NOK)", f"{siste['ebitda']:,.0f}")
            col3.metric("Netto margin", f"{siste['net_margin']}%" if siste['net_margin'] is not None else "N/A")
            col4.metric("Egenkapitalandel", f"{siste['equity_ratio']}%" if siste['equity_ratio'] is not None else "N/A")

            st.divider()
            st.subheader("Feature importance – ML-modell")
            imp = ml_result["feature_importance"]
            fig_imp = px.bar(
                x=list(imp.values()),
                y=list(imp.keys()),
                orientation="h",
                labels={"x": "Viktighet", "y": "Variabel"},
                title="Hvilke variabler driver PD-estimatet"
            )
            fig_imp.update_layout(height=300)
            st.plotly_chart(fig_imp, use_container_width=True)

            st.divider()
            st.subheader("Historisk utvikling")
            df = pd.DataFrame(ratios)
            col1, col2 = st.columns(2)

            with col1:
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(x=df["year"], y=df["revenue"], name="Omsetning"))
                fig3.add_trace(go.Bar(x=df["year"], y=df["ebitda"], name="EBITDA"))
                fig3.update_layout(title="Omsetning og EBITDA", barmode="group", height=350)
                st.plotly_chart(fig3, use_container_width=True)

            with col2:
                fig4 = go.Figure()
                fig4.add_trace(go.Scatter(x=df["year"], y=df["equity_ratio"], name="Egenkapitalandel %", mode="lines+markers"))
                fig4.add_trace(go.Scatter(x=df["year"], y=df["net_margin"], name="Netto margin %", mode="lines+markers"))
                fig4.update_layout(title="Marginer og soliditet", height=350)
                st.plotly_chart(fig4, use_container_width=True)

            st.subheader("Rådata")
            st.dataframe(df, use_container_width=True)

elif side == "Portefølje":
    st.title("Porteføljeovervåking")
    st.info("Last opp en CSV-fil med organisasjonsnumre")
    uploaded = st.file_uploader("Last opp CSV (kolonne: org_nr)", type="csv")

    if uploaded:
        portfolio_df = pd.read_csv(uploaded)
        if "org_nr" not in portfolio_df.columns:
            st.error("CSV-filen må ha en kolonne som heter 'org_nr'")
        else:
            resultater = []
            progress = st.progress(0)
            for i, row in portfolio_df.iterrows():
                org = str(row["org_nr"])
                company = get_company_info(org)
                financial = get_financial_data(org, years=1)
                progress.progress((i + 1) / len(portfolio_df))
                if "records" in financial and financial["records"]:
                    ratios = calculate_ratios(financial["records"])
                    siste = ratios[0]
                    score = credit_score(siste)
                    ml = predict_pd(siste)
                    resultater.append({
                        "Org.nr": org,
                        "Navn": company.get("navn", "Ukjent"),
                        "Bransje": company.get("naeringskode1", {}).get("beskrivelse", "")[:40],
                        "Score": score["score"],
                        "Rating": score["rating"],
                        "PD %": ml["pd_percent"],
                        "Z-score": ml["z_score"],
                        "Egenkapitalandel %": siste["equity_ratio"],
                        "Netto margin %": siste["net_margin"],
                    })

            if resultater:
                result_df = pd.DataFrame(resultater).sort_values("Score")
                col1, col2, col3 = st.columns(3)
                col1.metric("Antall selskaper", len(result_df))
                col2.metric("Gjennomsnittlig score", f"{result_df['Score'].mean():.0f}")
                col3.metric("Høy risiko (C/D)", len(result_df[result_df["Score"] < 50]))

                fig = go.Figure(go.Bar(
                    x=result_df["Navn"],
                    y=result_df["Score"],
                    marker_color=result_df["Score"].apply(
                        lambda x: "green" if x >= 75 else "orange" if x >= 50 else "red"
                    )
                ))
                fig.update_layout(title="Kredittskår per selskap", height=400)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(result_df, use_container_width=True)

elif side == "ROE-kalkulator":
    st.title("ROE-kalkulator – Kredittportefølje")
    st.caption("Basel III risikovekter | NOK 10 mrd portefølje")

    st.subheader("Bankparametere")
    col1, col2, col3 = st.columns(3)
    with col1:
        funding_rate = st.slider("Fundingkostnad (%)", 2.0, 7.0, 4.2, 0.1) / 100
    with col2:
        opex_ratio = st.slider("OpEx (% av NII)", 10, 60, 30, 5) / 100
    with col3:
        capital_ratio = st.slider("Kapitalandel Basel III (%)", 8.0, 15.0, 12.0, 0.5) / 100

    st.divider()
    st.subheader("Segmentparametere")

    segments = copy.deepcopy(SEGMENTS)
    cols = st.columns(4)

    for i, (key, seg) in enumerate(segments.items()):
        with cols[i]:
            st.markdown(f"**{seg['label']}**")
            seg["exposure"] = st.number_input(
                "Eksponering (NOK mrd)",
                min_value=0.5, max_value=5.0,
                value=seg["exposure"] / 1e9, step=0.5,
                key=f"exp_{key}"
            ) * 1e9
            seg["spread"] = st.slider(
                "Spread (%)", 1.0, 6.0,
                float(seg["spread"] * 100), 0.1,
                key=f"spread_{key}"
            ) / 100
            seg["pd"] = st.slider(
                "PD (%)", 0.1, 10.0,
                float(seg["pd"] * 100), 0.1,
                key=f"pd_{key}"
            ) / 100
            seg["lgd"] = st.slider(
                "LGD (%)", 10, 80,
                int(seg["lgd"] * 100), 5,
                key=f"lgd_{key}"
            ) / 100
            st.caption(f"Risikovekt: {int(BASEL3_RISK_WEIGHTS[key]*100)}%")

    st.divider()
    result = calculate_portfolio_roe(segments, funding_rate, opex_ratio, 0.22, capital_ratio)

    st.subheader("Resultat")
    col1, col2, col3, col4 = st.columns(4)
    roe_color = "normal" if result["roe"] >= 10 else "inverse"
    col1.metric("ROE", f"{result['roe']:.1f}%", delta="Mål: 10–15%")
    col2.metric("NII (NOK)", f"{result['total_nii']/1e6:.0f}M")
    col3.metric("EL-avsetning (NOK)", f"{result['total_el']/1e6:.0f}M")
    col4.metric("Netto inntekt (NOK)", f"{result['net_income']/1e6:.0f}M")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NIM", f"{result['nim']:.2f}%")
    col2.metric("Vektet EL", f"{result['weighted_el']:.3f}%")
    col3.metric("Total RWA (NOK)", f"{result['total_rwa']/1e9:.1f} mrd")
    col4.metric("Kapitalkrav (NOK)", f"{result['total_capital']/1e6:.0f}M")

    st.divider()
    st.subheader("P&L-oversikt")
    pnl_data = {
        "Post": ["NII", "EL-avsetning", "Netto etter tap", "OpEx", "EBT", "Skatt", "Netto inntekt"],
        "NOK (millioner)": [
            result["total_nii"] / 1e6,
            -result["total_el"] / 1e6,
            result["net_after_el"] / 1e6,
            -result["opex"] / 1e6,
            result["ebt"] / 1e6,
            -result["tax"] / 1e6,
            result["net_income"] / 1e6,
        ]
    }
    pnl_df = pd.DataFrame(pnl_data)
    fig_pnl = go.Figure(go.Bar(
        x=pnl_df["Post"],
        y=pnl_df["NOK (millioner)"],
        marker_color=["#2196F3", "#F44336", "#4CAF50", "#F44336", "#2196F3", "#F44336", "#4CAF50"]
    ))
    fig_pnl.update_layout(title="P&L-vannfall", height=380)
    st.plotly_chart(fig_pnl, use_container_width=True)

    st.divider()
    st.subheader("Segment-dekomposisjon")
    seg_df = pd.DataFrame(result["segment_results"])

    col1, col2 = st.columns(2)
    with col1:
        fig_seg = go.Figure(go.Bar(
            x=seg_df["segment"],
            y=seg_df["nii"] / 1e6,
            name="NII",
            marker_color="#2196F3"
        ))
        fig_seg.add_trace(go.Bar(
            x=seg_df["segment"],
            y=-seg_df["el"] / 1e6,
            name="EL",
            marker_color="#F44336"
        ))
        fig_seg.update_layout(title="NII vs EL per segment", barmode="group", height=350)
        st.plotly_chart(fig_seg, use_container_width=True)

    with col2:
        fig_rwa = go.Figure(go.Bar(
            x=seg_df["segment"],
            y=seg_df["rwa"] / 1e9,
            marker_color="#FF9800"
        ))
        fig_rwa.update_layout(title="RWA per segment (NOK mrd)", height=350)
        st.plotly_chart(fig_rwa, use_container_width=True)

    st.subheader("Detaljer per segment")
    display_cols = ["segment", "eksponering", "spread", "pd", "lgd", "el_rate", "netto_margin", "risikovekt"]
    seg_display = seg_df[display_cols].copy()
    seg_display["eksponering"] = seg_display["eksponering"].apply(lambda x: f"NOK {x/1e9:.1f} mrd")
    seg_display.columns = ["Segment", "Eksponering", "Spread %", "PD %", "LGD %", "EL %", "Netto margin %", "Risikovekt %"]
    st.dataframe(seg_display, use_container_width=True)
    