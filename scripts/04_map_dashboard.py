"""
SURAKSHA PROJECT - Script 04
Interactive Crime Hotspot Dashboard
=====================================
Run: streamlit run scripts/04_map_dashboard.py
Opens in browser at: http://localhost:8501
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json, os, warnings
warnings.filterwarnings('ignore')

# ── PAGE CONFIG ─────────────────────────────────────────
st.set_page_config(
    page_title="SURAKSHA — UP Crime Intelligence",
    page_icon="🚔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2rem; font-weight: 700; color: #1a1a2e;
        text-align: center; padding: 1rem 0 0.2rem 0;
    }
    .sub-header {
        font-size: 1rem; color: #666; text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8f9fa; border-radius: 10px;
        padding: 1rem; text-align: center;
        border-left: 4px solid #e74c3c;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #e74c3c; }
    .metric-label { font-size: 0.8rem; color: #666; margin-top: 0.2rem; }
    .insight-box {
        background: #fff3cd; border-radius: 8px;
        padding: 0.8rem 1rem; margin: 0.5rem 0;
        border-left: 4px solid #ffc107;
    }
    div[data-testid="stSidebar"] { background: #1a1a2e; }
    div[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ── LOAD DATA ────────────────────────────────────────────
@st.cache_data
def load_all_data():
    base = "data"
    master     = pd.read_csv(f"{base}/cleaned/master_UP_crime.csv")
    yearly     = pd.read_csv(f"{base}/analysis/01_yearly_total_crime.csv")
    crime_trend= pd.read_csv(f"{base}/analysis/02_crime_type_trends.csv")
    dist_rank  = pd.read_csv(f"{base}/analysis/03_district_overall_ranking.csv")
    dist_yr    = pd.read_csv(f"{base}/analysis/03b_district_crime_by_year.csv")
    dist_trend = pd.read_csv(f"{base}/analysis/04_district_trends.csv")
    top5       = pd.read_csv(f"{base}/analysis/05_top5_crimes_per_district.csv")
    intensity  = pd.read_csv(f"{base}/analysis/06b_district_avg_intensity.csv")
    yoy        = pd.read_csv(f"{base}/analysis/07_yoy_changes.csv")
    report     = pd.read_csv(f"{base}/analysis/08_district_report_cards.csv")
    covid      = pd.read_csv(f"{base}/analysis/10_covid_impact.csv")
    pred_path  = f"{base}/cleaned/predictions_2024.csv"
    preds      = pd.read_csv(pred_path) if os.path.exists(pred_path) else pd.DataFrame()

    master['Year']  = master['Year'].astype(int)
    master['Total'] = pd.to_numeric(master['Total'], errors='coerce').fillna(0).astype(int)
    master = master[~master['District'].str.lower().str.contains('total|grp|grand', na=False)]

    return dict(
        master=master, yearly=yearly, crime_trend=crime_trend,
        dist_rank=dist_rank, dist_yr=dist_yr, dist_trend=dist_trend,
        top5=top5, intensity=intensity, yoy=yoy, report=report,
        covid=covid, preds=preds
    )

data = load_all_data()
master = data['master']
ALL_DISTRICTS  = sorted(master['District'].unique())
ALL_CRIMES     = sorted(master['Crime_Type'].unique())
ALL_YEARS      = sorted(master['Year'].unique())

# ════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚔 SURAKSHA")
    st.markdown("**UP Crime Intelligence System**")
    st.markdown("---")

    page = st.radio("Navigate", [
        "📊 Overview Dashboard",
        "🗺️ District Deep Dive",
        "📈 Crime Trends",
        "🏆 District Rankings",
        "🔮 2024 Predictions",
        "🦠 COVID Impact"
    ])

    st.markdown("---")
    st.markdown("**Data Sources**")
    st.markdown("NCRB 2016–2023")
    st.markdown("Kaggle UP Dataset")
    st.markdown(f"**{len(master):,} data points**")
    st.markdown(f"**{master['District'].nunique()} districts**")
    st.markdown(f"**{master['Crime_Type'].nunique()} crime types**")
    st.markdown(f"**{len(ALL_YEARS)} years**")


# ════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW DASHBOARD
# ════════════════════════════════════════════════════════
if page == "📊 Overview Dashboard":
    st.markdown('<div class="main-header">🚔 SURAKSHA — UP Crime Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Uttar Pradesh District Crime Analysis | 2014–2023 | NCRB Official Data</div>', unsafe_allow_html=True)

    # ── Top metrics ──────────────────────────────────────
    total_crimes = int(master['Total'].sum())
    worst_dist   = data['dist_rank'].iloc[0]['District']
    worst_val    = int(data['dist_rank'].iloc[0]['Total_All_Years'])
    most_common  = master.groupby('Crime_Type')['Total'].sum().idxmax()
    recent_yr    = int(master['Year'].max())
    recent_total = int(master[master['Year']==recent_yr]['Total'].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cases (All Years)", f"{total_crimes:,}", "2014–2023")
    c2.metric("Most Crime-Prone District", worst_dist, f"{worst_val:,} cases")
    c3.metric("Most Common Crime", most_common)
    c4.metric(f"Total Cases in {recent_yr}", f"{recent_total:,}")

    st.markdown("---")

    # ── Year-wise total crime chart ───────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Year-wise Total Crime in UP")
        yr_df = data['yearly'].copy()
        yr_df['Year'] = yr_df['Year'].astype(int)
        fig = px.bar(yr_df, x='Year', y='Total_Crimes',
                     color='Total_Crimes',
                     color_continuous_scale='Reds',
                     text='Total_Crimes',
                     title="Total Crime Cases per Year")
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(showlegend=False, height=400,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🔢 Crime Type Distribution (Latest Year)")
        latest = master[master['Year']==recent_yr]
        ct_latest = latest.groupby('Crime_Type')['Total'].sum().sort_values(ascending=True).tail(10)
        fig2 = px.bar(ct_latest.reset_index(), x='Total', y='Crime_Type',
                      orientation='h',
                      color='Total', color_continuous_scale='Oranges',
                      title=f"Top 10 Crime Types in {recent_yr}")
        fig2.update_layout(showlegend=False, height=400,
                           coloraxis_showscale=False, yaxis_title="")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Top 15 districts bar chart ────────────────────────
    st.subheader("🏙️ Top 15 Most Crime-Prone Districts (All Years)")
    top15 = data['dist_rank'].head(15)
    fig3  = px.bar(top15, x='District', y='Total_All_Years',
                   color='Total_All_Years', color_continuous_scale='Reds',
                   text='Total_All_Years')
    fig3.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig3.update_layout(height=400, coloraxis_showscale=False,
                       xaxis_tickangle=-30)
    st.plotly_chart(fig3, use_container_width=True)

    # ── Key insights ──────────────────────────────────────
    st.subheader("💡 Key Insights from the Data")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="insight-box">🔺 <b>Cybercrime rose 59%</b> from 2014 to 2023 — fastest growing serious crime in UP</div>', unsafe_allow_html=True)
        st.markdown('<div class="insight-box">🔺 <b>Meerut Division</b> has the highest total crime among all UP divisions</div>', unsafe_allow_html=True)
        st.markdown('<div class="insight-box">🔺 <b>Rape rose 20.5%</b> during COVID lockdown (2020) — domestic crime increased</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="insight-box">🔻 <b>Murder fell 24%</b> from 2014 to 2023 — genuine law and order improvement</div>', unsafe_allow_html=True)
        st.markdown('<div class="insight-box">🔻 <b>Robbery fell 14%</b> and Dowry Deaths fell 19% over the decade</div>', unsafe_allow_html=True)
        st.markdown('<div class="insight-box">✅ <b>Lucknow, Kanpur, Varanasi</b> show Grade A improvement in recent years</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# PAGE 2 — DISTRICT DEEP DIVE
# ════════════════════════════════════════════════════════
elif page == "🗺️ District Deep Dive":
    st.title("🗺️ District Deep Dive")
    st.markdown("Select any UP district to see its complete crime profile")

    selected = st.selectbox("Choose a District", ALL_DISTRICTS, index=ALL_DISTRICTS.index('Lucknow') if 'Lucknow' in ALL_DISTRICTS else 0)

    dist_data = master[master['District'] == selected]

    if dist_data.empty:
        st.warning(f"No data found for {selected}")
    else:
        # ── Report card ──────────────────────────────────
        rc = data['report'][data['report']['District'] == selected]
        if not rc.empty:
            rc = rc.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Overall UP Rank", f"#{int(rc['Overall_Rank'])}")
            col2.metric("Total Cases (All Years)", f"{int(rc['Total_All_Years']):,}")
            col3.metric("Recent Trend", f"{rc['Recent_Trend_pct']:+.1f}%")
            col4.metric("Grade", rc['Grade'].split()[0],
                        rc['Grade'].split('(')[1].rstrip(')') if '(' in rc['Grade'] else "")

        st.markdown("---")
        col1, col2 = st.columns(2)

        # ── Year-wise total for this district ────────────
        with col1:
            st.subheader(f"📅 Year-wise Crime Trend — {selected}")
            yr_dist = dist_data.groupby('Year')['Total'].sum().reset_index()
            yr_dist['Year'] = yr_dist['Year'].astype(int)
            fig = px.line(yr_dist, x='Year', y='Total',
                          markers=True, line_shape='spline',
                          color_discrete_sequence=['#e74c3c'])
            fig.update_traces(line_width=3, marker_size=8)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        # ── Crime type breakdown ──────────────────────────
        with col2:
            st.subheader(f"🔢 Crime Type Breakdown — {selected}")
            ct_dist = dist_data.groupby('Crime_Type')['Total'].sum().sort_values(ascending=True).tail(10)
            fig2 = px.bar(ct_dist.reset_index(), x='Total', y='Crime_Type',
                          orientation='h', color='Total',
                          color_continuous_scale='Reds')
            fig2.update_layout(height=350, coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig2, use_container_width=True)

        # ── Heatmap: crime type × year ────────────────────
        st.subheader(f"🌡️ Crime Heatmap — {selected} (Crime Type × Year)")
        heat_data = dist_data.pivot_table(
            index='Crime_Type', columns='Year', values='Total', aggfunc='sum', fill_value=0
        )
        fig3 = px.imshow(heat_data, color_continuous_scale='YlOrRd',
                         aspect='auto', text_auto=True)
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)

        # ── Top 5 signature crimes ────────────────────────
        st.subheader(f"🔍 Signature Crimes of {selected}")
        top5_d = data['top5'][data['top5']['District'] == selected].head(5)
        if not top5_d.empty:
            cols = st.columns(5)
            for i, (_, row) in enumerate(top5_d.iterrows()):
                with cols[i]:
                    st.metric(
                        f"#{int(row['Rank'])} Crime",
                        row['Crime_Type'],
                        f"{int(row['Total_Cases']):,} cases"
                    )

        # ── YoY changes ───────────────────────────────────
        st.subheader(f"📊 Year-on-Year Changes — {selected}")
        yoy_d = data['yoy'][data['yoy']['District'] == selected].copy()
        if not yoy_d.empty:
            yoy_d['Year'] = yoy_d['Year'].astype(int)
            fig4 = px.bar(yoy_d, x='Year', y='YoY_Pct',
                          color='Crime_Type', barmode='group',
                          title="% Change per Year per Crime Type")
            fig4.update_layout(height=400)
            st.plotly_chart(fig4, use_container_width=True)


# ════════════════════════════════════════════════════════
# PAGE 3 — CRIME TRENDS
# ════════════════════════════════════════════════════════
elif page == "📈 Crime Trends":
    st.title("📈 Crime Trends Analysis")

    tab1, tab2, tab3 = st.tabs(["By Crime Type", "Multi-District Compare", "Crime vs Year Heatmap"])

    with tab1:
        selected_crime = st.selectbox("Select Crime Type", ALL_CRIMES)
        crime_data = master[master['Crime_Type'] == selected_crime]

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📅 UP-wide Trend — {selected_crime}")
            yr_crime = crime_data.groupby('Year')['Total'].sum().reset_index()
            yr_crime['Year'] = yr_crime['Year'].astype(int)
            fig = px.area(yr_crime, x='Year', y='Total',
                          color_discrete_sequence=['#e74c3c'],
                          title=f"Total {selected_crime} in UP per Year")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader(f"🏙️ Top 15 Districts — {selected_crime}")
            top_d = crime_data.groupby('District')['Total'].sum().sort_values(ascending=False).head(15)
            fig2  = px.bar(top_d.reset_index(), x='Total', y='District',
                           orientation='h', color='Total',
                           color_continuous_scale='Reds')
            fig2.update_layout(height=350, coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig2, use_container_width=True)

        # District trend lines for selected crime
        st.subheader(f"📊 District-wise Trend — {selected_crime} (Top 10 districts)")
        top10_dists = crime_data.groupby('District')['Total'].sum().nlargest(10).index.tolist()
        sub = crime_data[crime_data['District'].isin(top10_dists)]
        sub_pivot = sub.groupby(['Year','District'])['Total'].sum().reset_index()
        sub_pivot['Year'] = sub_pivot['Year'].astype(int)
        fig3 = px.line(sub_pivot, x='Year', y='Total', color='District',
                       markers=True, line_shape='spline')
        fig3.update_layout(height=450)
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Compare Multiple Districts")
        compare_dists = st.multiselect(
            "Select districts to compare (max 6)",
            ALL_DISTRICTS,
            default=['Lucknow','Ghaziabad','Prayagraj'] if all(d in ALL_DISTRICTS for d in ['Lucknow','Ghaziabad','Prayagraj']) else ALL_DISTRICTS[:3]
        )
        compare_crime = st.selectbox("Crime Type to Compare", ALL_CRIMES, key='cmp')

        if compare_dists:
            cmp_data = master[(master['District'].isin(compare_dists)) &
                              (master['Crime_Type'] == compare_crime)]
            cmp_yr   = cmp_data.groupby(['Year','District'])['Total'].sum().reset_index()
            cmp_yr['Year'] = cmp_yr['Year'].astype(int)
            fig = px.line(cmp_yr, x='Year', y='Total', color='District',
                          markers=True, line_shape='spline',
                          title=f"{compare_crime} — Multi-District Comparison")
            fig.update_traces(line_width=2.5, marker_size=7)
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("All Crimes × All Years Heatmap (UP Total)")
        pivot_all = master.groupby(['Crime_Type','Year'])['Total'].sum().unstack(fill_value=0)
        pivot_all.columns = pivot_all.columns.astype(int)
        fig = px.imshow(pivot_all, color_continuous_scale='YlOrRd',
                        aspect='auto', text_auto=True,
                        title="Crime Type vs Year — Total Cases in UP")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════
# PAGE 4 — DISTRICT RANKINGS
# ════════════════════════════════════════════════════════
elif page == "🏆 District Rankings":
    st.title("🏆 District Rankings & Report Cards")

    tab1, tab2, tab3 = st.tabs(["Overall Rankings", "Report Cards (A-F)", "Intensity Scores"])

    with tab1:
        st.subheader("District Rankings — All Years Combined")
        rank_df = data['dist_rank'].copy()
        rank_df['Total_All_Years'] = rank_df['Total_All_Years'].astype(int)

        top_n = st.slider("Show top N districts", 10, len(rank_df), 25)
        fig = px.bar(rank_df.head(top_n), x='District', y='Total_All_Years',
                     color='Total_All_Years', color_continuous_scale='Reds',
                     text='Total_All_Years')
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, coloraxis_showscale=False, xaxis_tickangle=-40)
        st.plotly_chart(fig, use_container_width=True)

        # Show full table
        st.dataframe(rank_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Law & Order Report Cards")
        st.markdown("Grade based on recent 3-year trend vs first 3 years")

        rc_df = data['report'].copy()

        grade_filter = st.multiselect(
            "Filter by Grade",
            ['A', 'B', 'C', 'D', 'F'],
            default=['A', 'B', 'C', 'D', 'F']
        )
        filtered_rc = rc_df[rc_df['Grade'].str.startswith(tuple(grade_filter))]

        # Color map
        grade_colors = {'A': '#27ae60', 'B': '#2ecc71', 'C': '#f39c12', 'D': '#e67e22', 'F': '#e74c3c'}
        filtered_rc['Grade_Letter'] = filtered_rc['Grade'].str[0]
        filtered_rc['Color'] = filtered_rc['Grade_Letter'].map(grade_colors)

        fig = px.scatter(
            filtered_rc,
            x='Overall_Rank', y='Recent_Trend_pct',
            color='Grade_Letter',
            hover_name='District',
            hover_data={'Overall_Rank': True, 'Recent_Trend_pct': ':.1f'},
            color_discrete_map=grade_colors,
            title="District Report Cards — Rank vs Recent Trend %",
            labels={'Recent_Trend_pct': 'Recent Crime Trend %', 'Overall_Rank': 'Overall Crime Rank'}
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            filtered_rc[['District','Overall_Rank','Total_All_Years','Recent_Trend_pct','Grade']],
            use_container_width=True, hide_index=True
        )

    with tab3:
        st.subheader("Crime Intensity Scores (0-100 Normalized)")
        int_df = data['intensity'].copy()
        int_df['Avg_Intensity_Score'] = int_df['Avg_Intensity_Score'].astype(float)
        int_df['Risk_Level'] = int_df['Risk_Level'].astype(str)

        color_map = {'LOW': '#27ae60', 'MEDIUM': '#f39c12', 'HIGH': '#e67e22', 'CRITICAL': '#e74c3c'}
        fig = px.bar(
            int_df.sort_values('Avg_Intensity_Score', ascending=False).head(40),
            x='District', y='Avg_Intensity_Score',
            color='Risk_Level', color_discrete_map=color_map,
            title="Top 40 Districts by Crime Intensity Score"
        )
        fig.update_layout(height=500, xaxis_tickangle=-40)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════
# PAGE 5 — 2024 PREDICTIONS
# ════════════════════════════════════════════════════════
elif page == "🔮 2024 Predictions":
    st.title("🔮 2024 Crime Hotspot Predictions")
    st.markdown("Predictions from Random Forest model trained on 2014–2023 data")

    if data['preds'].empty:
        st.warning("Predictions file not found. Run suraksha_complete.py first.")
    else:
        pred_df = data['preds'].copy()
        actual_col = [c for c in pred_df.columns if 'Actual' in c][0]
        pred_col   = [c for c in pred_df.columns if 'Predicted' in c][0]
        pred_year  = pred_col.split('_')[1]

        pred_df[actual_col] = pd.to_numeric(pred_df[actual_col], errors='coerce').fillna(0).astype(int)
        pred_df[pred_col]   = pd.to_numeric(pred_df[pred_col],   errors='coerce').fillna(0).astype(int)

        tab1, tab2 = st.tabs(["By District", "By Crime Type"])

        with tab1:
            st.subheader(f"Top Districts — Predicted Crime {pred_year}")
            top_pred = pred_df.groupby('District')[pred_col].sum().sort_values(ascending=False).head(20)
            fig = px.bar(top_pred.reset_index(), x='District', y=pred_col,
                         color=pred_col, color_continuous_scale='Reds',
                         text=pred_col,
                         title=f"Top 20 Districts — Predicted Total Crime {pred_year}")
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=500, coloraxis_showscale=False, xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

            # Actual vs predicted comparison
            st.subheader("Actual vs Predicted Comparison")
            compare = pred_df.groupby('District').agg(
                Actual=(actual_col, 'sum'),
                Predicted=(pred_col, 'sum')
            ).reset_index().sort_values('Predicted', ascending=False).head(15)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name='Actual', x=compare['District'],
                                  y=compare['Actual'], marker_color='#3498db'))
            fig2.add_trace(go.Bar(name='Predicted', x=compare['District'],
                                  y=compare['Predicted'], marker_color='#e74c3c'))
            fig2.update_layout(barmode='group', height=450, xaxis_tickangle=-35)
            st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            st.subheader(f"Crime Type Predictions — {pred_year}")
            ct_pred = pred_df.groupby('Crime_Type').agg(
                Actual=(actual_col, 'sum'),
                Predicted=(pred_col, 'sum'),
                Avg_Change=('Change_pct', 'mean')
            ).reset_index().sort_values('Avg_Change', ascending=False)

            fig = px.bar(ct_pred, x='Crime_Type', y='Avg_Change',
                         color='Avg_Change',
                         color_continuous_scale='RdYlGn_r',
                         title=f"Predicted % Change by Crime Type ({pred_year})")
            fig.add_hline(y=0, line_dash="dash", line_color="black")
            fig.update_layout(height=450, xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(ct_pred.round(1), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════
# PAGE 6 — COVID IMPACT
# ════════════════════════════════════════════════════════
elif page == "🦠 COVID Impact":
    st.title("🦠 COVID-19 Impact on Crime (2019 vs 2020)")
    st.markdown("How did the lockdown change crime patterns in Uttar Pradesh?")

    covid_df = data['covid'].copy()
    if covid_df.empty:
        st.warning("COVID impact data not found.")
    else:
        covid_df.columns = [c.strip() for c in covid_df.columns]
        if 'Crime_Type' not in covid_df.columns and 'index' in covid_df.columns:
            covid_df = covid_df.rename(columns={'index': 'Crime_Type'})

        pre_col  = [c for c in covid_df.columns if '2019' in str(c)][0]
        post_col = [c for c in covid_df.columns if '2020' in str(c)][0]

        covid_df[pre_col]  = pd.to_numeric(covid_df[pre_col],  errors='coerce').fillna(0)
        covid_df[post_col] = pd.to_numeric(covid_df[post_col], errors='coerce').fillna(0)
        covid_df['Change_pct'] = pd.to_numeric(covid_df['Change_pct'], errors='coerce').fillna(0)
        covid_df = covid_df.sort_values('Change_pct')

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Crimes that DROPPED during lockdown")
            dropped = covid_df[covid_df['Change_pct'] < 0]
            for _, r in dropped.iterrows():
                st.metric(str(r['Crime_Type']), f"{r['Change_pct']:.1f}%",
                          f"{int(r[pre_col]):,} → {int(r[post_col]):,}")

        with col2:
            st.subheader("Crimes that ROSE during lockdown")
            rose = covid_df[covid_df['Change_pct'] > 0].sort_values('Change_pct', ascending=False)
            for _, r in rose.iterrows():
                st.metric(str(r['Crime_Type']), f"+{r['Change_pct']:.1f}%",
                          f"{int(r[pre_col]):,} → {int(r[post_col]):,}")

        st.markdown("---")
        fig = px.bar(covid_df.sort_values('Change_pct'),
                     x='Change_pct', y='Crime_Type',
                     orientation='h',
                     color='Change_pct',
                     color_continuous_scale='RdYlGn',
                     title="COVID Impact: % Change in Crime (2019→2020)",
                     labels={'Change_pct': '% Change', 'Crime_Type': ''})
        fig.add_vline(x=0, line_dash="solid", line_color="black", line_width=1)
        fig.update_layout(height=500, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

        st.info("**Key insight:** Street crimes (robbery, kidnapping, theft) fell during lockdown. But domestic crimes (rape, dowry deaths, burglary) ROSE — people were trapped at home.")