import json, os, pandas as pd

# ── Paths ────────────────────────────────────────
ANALYSIS_DIR = "data/analysis"
OUT_PATH     = "suraksha_deep_intel.html"

# ── Load Analysis Components ─────────────────────
# provides the structure for these CSVs
yearly       = pd.read_csv(f"{ANALYSIS_DIR}/01_yearly_total_crime.csv").to_dict(orient='records')
crime_types  = pd.read_csv(f"{ANALYSIS_DIR}/02_crime_type_trends.csv").to_dict(orient='records')
intensities  = pd.read_csv(f"{ANALYSIS_DIR}/06b_district_avg_intensity.csv").head(20).to_dict(orient='records')
covid_impact = pd.read_csv(f"{ANALYSIS_DIR}/10_covid_impact.csv").to_dict(orient='records')
report_cards = pd.read_csv(f"{ANALYSIS_DIR}/08_district_report_cards.csv").to_dict(orient='records')

# ── HTML Structure ───────────────────────────────
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SURAKSHA Intelligence Panel</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Poppins', sans-serif; background: #0f172a; color: #f1f5f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 40px 0; border-bottom: 1px solid #1e293b; }}
        .header h1 {{ color: #ef4444; font-size: 3rem; margin: 0; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; margin-top: 30px; }}
        .card {{ background: #1e293b; border-radius: 15px; padding: 25px; border: 1px solid #334155; }}
        .full-width {{ grid-column: span 2; }}
        h2 {{ color: #38bdf8; font-size: 1.2rem; margin-top: 0; text-transform: uppercase; }}
        .insight {{ font-size: 0.9rem; color: #94a3b8; margin-top: 10px; border-left: 3px solid #ef4444; padding-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85rem; }}
        th {{ text-align: left; color: #94a3b8; padding: 10px; border-bottom: 1px solid #334155; }}
        td {{ padding: 10px; border-bottom: 1px solid #0f172a; }}
        .badge {{ padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
        .A {{ background: #10b981; color: white; }} .F {{ background: #ef4444; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SURAKSHA 🚔</h1>
            <p>Uttar Pradesh State Crime Deep Intelligence Dashboard</p>
        </div>

        <div class="grid">
            <div class="card full-width">
                <h2>📈 UP Crime Trend: Multi-Regime Perspective (2014-2023)</h2>
                <canvas id="regimeChart" height="100"></canvas>
                <div class="insight">Note: The shaded areas represent different administrative phases. Data shows a significant shift in reporting and control patterns after 2017.</div>
            </div>

            <div class="card">
                <h2>🔥 Top 20 High-Intensity Districts</h2>
                <canvas id="intensityChart"></canvas>
                <div class="insight">Intensity Score (0-100) is a normalized danger level based on all years.</div>
            </div>

            <div class="card">
                <h2>🦠 The COVID-19 Crime Shift (2019 vs 2020)</h2>
                <canvas id="covidChart"></canvas>
                <div class="insight">Street crimes fell during lockdown, but domestic crimes saw a sharp rise.</div>
            </div>

            <div class="card full-width">
                <h2>🏆 Law & Order Report Cards (Recent 3-Year Improvement)</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    <table>
                        <thead>
                            <tr><th>District</th><th>Rank</th><th>Recent Trend</th><th>Grade</th><th>Current Status</th></tr>
                        </thead>
                        <tbody id="report-table"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const yearlyData = {json.dumps(yearly)};
        const intensityData = {json.dumps(intensities)};
        const covidData = {json.dumps(covid_impact)};
        const reportData = {json.dumps(report_cards)};

        // 1. Regime Chart
        new Chart(document.getElementById('regimeChart'), {{
            type: 'line',
            data: {{
                labels: yearlyData.map(d => d.Year),
                datasets: [{{
                    label: 'Total Crimes',
                    data: yearlyData.map(d => d.Total_Crimes),
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    fill: true,
                    tension: 0.4,
                    segment: {{
                        borderColor: ctx => ctx.p0.parsed.x < 3 ? '#fbbf24' : '#ef4444' // Color change at 2017
                    }}
                }}]
            }},
            options: {{ scales: {{ y: {{ grid: {{ color: '#334155' }} }} }} }}
        }});

        // 2. Intensity Chart
        new Chart(document.getElementById('intensityChart'), {{
            type: 'bar',
            data: {{
                labels: intensityData.map(d => d.District),
                datasets: [{{
                    label: 'Score',
                    data: intensityData.map(d => d.Avg_Intensity_Score),
                    backgroundColor: '#38bdf8'
                }}]
            }},
            options: {{ indexAxis: 'y' }}
        }});

        // 3. COVID Chart
        new Chart(document.getElementById('covidChart'), {{
            type: 'bar',
            data: {{
                labels: covidData.map(d => d.Crime_Type).slice(0, 10),
                datasets: [{{
                    label: '% Change during Lockdown',
                    data: covidData.map(d => d.Change_pct).slice(0, 10),
                    backgroundColor: d => d.parsed.y > 0 ? '#ef4444' : '#10b981'
                }}]
            }}
        }});

        // 4. Report Table
        document.getElementById('report-table').innerHTML = reportData.slice(0, 50).map(r => `
            <tr>
                <td>${{r.District}}</td>
                <td>#${{r.Overall_Rank}}</td>
                <td style="color:${{r.Recent_Trend_pct > 0 ? '#ef4444' : '#10b981'}}">${{r.Recent_Trend_pct}}%</td>
                <td><span class="badge ${{r.Grade[0]}}">${{r.Grade[0]}}</span></td>
                <td>${{r.Grade.split('(')[1].replace(')', '')}}</td>
            </tr>
        `).join('');
    </script>
</body>
</html>
"""

with open(OUT_PATH, 'w') as f:
    f.write(html_content)
print(f"✅ Dashboard generated: {{OUT_PATH}}")