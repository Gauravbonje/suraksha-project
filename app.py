import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# --- PAGE CONFIG ---
st.set_page_config(page_title="SURAKSHA | UP Crime Intel", layout="wide")

# Custom CSS for Professional Look
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: white; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv("data/cleaned/master_UP_crime.csv")
    with open("data/maps/up_districts.geojson") as f:
        geojson = json.load(f)
    # Analysis files for easy viz
    yearly = pd.read_csv("data/analysis/01_yearly_total_crime.csv")
    report = pd.read_csv("data/analysis/08_district_report_cards.csv")
    return df, geojson, yearly, report

df, geo, yearly, report = load_data()

# --- SIDEBAR ---
st.sidebar.title("🚔 SURAKSHA Pro")
st.sidebar.markdown("UP State Intelligence Dashboard")
menu = st.sidebar.radio("Navigate", ["Strategic Overview", "District Heatmap", "Regime & COVID Analysis"])

# --- PAGE 1: STRATEGIC OVERVIEW ---
if menu == "Strategic Overview":
    st.title("📊 UP Crime Deep Intelligence")
    
    # Metrics Row
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cases (10Yr)", f"{df['Total'].sum():,}")
    c2.metric("Most Volatile District", report.iloc[0]['District'])
    c3.metric("Data Accuracy", "83% (RF Model)")

    # Big Trend Graph
    st.subheader("📈 State-wide Crime Pulse (2014-2023)")
    fig_trend = px.area(yearly, x='Year', y='Total_Crimes', 
                         color_discrete_sequence=['#ef4444'], template="plotly_dark")
    st.plotly_chart(fig_trend, width='stretch')

# --- PAGE 2: DISTRICT HEATMAP (REAL MAP) ---
elif menu == "District Heatmap":
    st.title("🗺️ Interactive Crime Hotspot Map")
    
    selected_crime = st.selectbox("Filter by Crime Category", df['Crime_Type'].unique())
    
    # Prepare Map Data
    map_df = df[df['Crime_Type'] == selected_crime].groupby('District')['Total'].sum().reset_index()
    
    # Plotly Choropleth - This is the REAL MAP
    fig_map = px.choropleth(
        map_df,
        geojson=geo,
        locations='District',
        featureidkey="properties.Dist_Name", # Check if your GeoJSON uses 'Dist_Name' or 'NAME_2'
        color='Total',
        color_continuous_scale="Reds",
        scope="asia",
        template="plotly_dark",
        labels={'Total': 'Total Cases'}
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
    
    st.plotly_chart(fig_map, width='stretch')
    
    st.subheader("🏆 District Ranking for " + selected_crime)
    st.bar_chart(map_df.set_index('District').sort_values('Total', ascending=False).head(15), width='stretch')

# --- PAGE 3: REGIME & COVID ANALYSIS ---
elif menu == "Regime & COVID Analysis":
    st.title("⚖️ Regime Shift & Lockdown Impact")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Regime 1 vs Regime 2 Average")
        df['Regime'] = df['Year'].apply(lambda x: '2014-16' if x <= 2016 else '2017-23')
        reg_data = df.groupby('Regime')['Total'].mean().reset_index()
        fig_reg = px.bar(reg_data, x='Regime', y='Total', color='Regime', 
                         color_discrete_map={'2014-16':'#94a3b8', '2017-23':'#ef4444'}, template="plotly_dark")
        st.plotly_chart(fig_reg, width='stretch')
        
    with col2:
        st.subheader("COVID Lockdown Shift (2019 vs 2020)")
        covid = pd.read_csv("data/analysis/10_covid_impact.csv")
        fig_cov = px.bar(covid.sort_values('Change_pct'), x='Change_pct', y='Crime_Type', 
                         orientation='h', color='Change_pct', color_continuous_scale="RdYlGn_r", template="plotly_dark")
        st.plotly_chart(fig_cov, width='stretch')