import json, os, pandas as pd

# ── Paths ────────────────────────────────────────
ANALYSIS_DIR = "data/analysis"
MASTER_CSV   = "data/cleaned/master_UP_crime.csv"
OUT_PATH     = "suraksha_easy_viz.html"

# ── 1. Data Processing ───────────────────────────
df = pd.read_csv(MASTER_CSV)
crime_share = df.groupby('Crime_Type')['Total'].sum().sort_values(ascending=False).to_dict()
df['Regime'] = df['Year'].apply(lambda x: '2014-16 (Regime 1)' if x <= 2016 else '2017-23 (Regime 2)')
regime_data = df.groupby('Regime')['Total'].mean().round(0).to_dict()
safest = df.groupby('District')['Total'].sum().sort_values().head(10).to_dict()

heatmap_df = df.groupby(['Crime_Type', 'Year'])['Total'].sum().unstack().fillna(0)
heatmap_data = {"labels": list(heatmap_df.columns.astype(str)), "datasets": []}
for crime in heatmap_df.index:
    heatmap_data["datasets"].append({"label": crime, "data": list(heatmap_df.loc[crime])})

# ── 2. HTML Structure ──────────────────────────────
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SURAKSHA | Easy Visualizer</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Poppins', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .full {{ grid-column: span 2; }}
        h1 {{ text-align: center; color: #c0392b; }}
    </style>
</head>
<body>
    <h1>📊 UP Crime Visual Insight Gallery</h1>
    <div class="grid">
        <div class="card"><h2>🍰 Crime Type Share</h2><canvas id="shareChart"></canvas></div>
        <div class="card"><h2>⚖️ Regime-wise Average</h2><canvas id="regimeChart"></canvas></div>
        <div class="card full"><h2>🌡️ Crime Intensity Trend (10 Years)</h2><canvas id="heatmapChart"></canvas></div>
        <div class="card full"><h2>🏆 Top 10 Safest Districts</h2><canvas id="safeChart"></canvas></div>
    </div>
    <script>
        const shareD = {json.dumps(crime_share)};
        const regimeD = {json.dumps(regime_data)};
        const heatD = {json.dumps(heatmap_data)};
        const safeD = {json.dumps(safest)};

        new Chart(document.getElementById('shareChart'), {{
            type: 'doughnut', data: {{ labels: Object.keys(shareD).slice(0,8), datasets: [{{ data: Object.values(shareD).slice(0,8), backgroundColor: ['#e74c3c','#3498db','#2ecc71','#f1c40f','#9b59b6','#1abc9c','#e67e22','#34495e'] }}] }}
        }});
        new Chart(document.getElementById('regimeChart'), {{
            type: 'bar', data: {{ labels: Object.keys(regimeD), datasets: [{{ label: 'Avg Cases', data: Object.values(regimeD), backgroundColor: ['#95a5a6','#c0392b'] }}] }}
        }});
        new Chart(document.getElementById('heatmapChart'), {{
            type: 'line', data: heatD, options: {{ plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 10, font: {{ size: 9 }} }} }} }} }}
        }});
        new Chart(document.getElementById('safeChart'), {{
            type: 'bar', data: {{ labels: Object.keys(safeD), datasets: [{{ label: 'Total Cases', data: Object.values(safeD), backgroundColor: '#27ae60' }}] }}
        }});
    </script>
</body>
</html>
"""
with open(OUT_PATH, 'w') as f:
    f.write(html_content)
print(f"✅ Easy Viz Dashboard generated: {OUT_PATH}")