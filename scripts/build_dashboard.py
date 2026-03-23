import json, os, csv, pandas as pd

# ── Configuration ────────────────────────────────
GEO_PATH         = "data/maps/up_districts.geojson"
MASTER_CSV       = "data/cleaned/master_UP_crime.csv"
PREDICTION_CSV   = "data/cleaned/predictions_2024.csv"
ANALYSIS_DIR     = "data/analysis"
OUT_PATH         = "suraksha_pro_dashboard.html"

# ── 1. Load Data ─────────────────────────────────
# Load Master & Predictions
df = pd.read_csv(MASTER_CSV)
pred_df = pd.read_csv(PREDICTION_CSV) if os.path.exists(PREDICTION_CSV) else pd.DataFrame()

# Load Analysis results (from Script 03)
yearly_trend = pd.read_csv(f"{ANALYSIS_DIR}/01_yearly_total_crime.csv").to_dict(orient='records')
dist_rank = pd.read_csv(f"{ANALYSIS_DIR}/03_district_overall_ranking.csv").head(15).to_dict(orient='records')
crime_trends = pd.read_csv(f"{ANALYSIS_DIR}/02_crime_type_trends.csv").to_dict(orient='records')

# Prep Data for HTML
# District Profile Data
dist_yearly = df.groupby(['District', 'Year'])['Total'].sum().unstack().fillna(0).to_dict(orient='index')
dist_total = df.groupby('District')['Total'].sum().to_dict()
top5 = {}
for d in df['District'].unique():
    t5 = df[df['District']==d].groupby('Crime_Type')['Total'].sum().sort_values(ascending=False).head(5)
    top5[d] = [{"crime": k, "total": int(v)} for k, v in t5.items()]

# ── 2. Process Map (GeoJSON) ─────────────────────
with open(GEO_PATH) as f:
    geo = json.load(f)

def get_coords(geometry):
    if geometry['type'] == 'Polygon': return geometry['coordinates'][0]
    elif geometry['type'] == 'MultiPolygon':
        coords = []
        for poly in geometry['coordinates']: coords.extend(poly[0])
        return coords
    return []

# Bounding box for scaling
all_coords = []
for feat in geo['features']: all_coords.extend(get_coords(feat['geometry']))
lons, lats = [c[0] for c in all_coords], [c[1] for c in all_coords]
min_lon, max_lon, min_lat, max_lat = min(lons), max(lons), min(lats), max(lats)

VW, VH, PAD = 850, 550, 20
scale = min((VW - 2*PAD) / (max_lon - min_lon), (VH - 2*PAD) / (max_lat - min_lat))

def project(lon, lat):
    x = PAD + (lon - min_lon) * scale + ((VW - 2*PAD) - (max_lon - min_lon) * scale) / 2
    y = PAD + (max_lat - lat) * scale + ((VH - 2*PAD) - (max_lat - min_lat) * scale) / 2
    return round(x, 2), round(y, 2)

mapped_paths = {}
NAME_MAP = {'Allahabad': 'Prayagraj', 'Faizabad': 'Ayodhya', 'Kheri': 'Khiri', 'Lakhimpur Kheri': 'Khiri'}

for feat in geo['features']:
    props = feat['properties']
    raw_name = props.get('Dist_Name') or props.get('NAME_2') or "Unknown"
    crime_name = NAME_MAP.get(raw_name, raw_name)
    
    # SVG Path
    rings = feat['geometry']['coordinates'] if feat['geometry']['type'] == 'Polygon' else [p[0] for p in feat['geometry']['coordinates']]
    path_data = " ".join(["M" + " L".join(f"{project(c[0],c[1])[0]},{project(c[0],c[1])[1]}" for c in r) + "Z" for r in rings])
    
    # Centroid for Label
    c_pts = get_coords(feat['geometry'])
    px = [project(c[0], c[1])[0] for c in c_pts]
    py = [project(c[0], c[1])[1] for c in c_pts]
    centroid = [sum(px)/len(px), sum(py)/len(py)]

    mapped_paths[raw_name] = {"path": path_data, "mapped": crime_name, "centroid": centroid}

# ── 3. Final Assembly ────────────────────────────
json_data = json.dumps({
    "yearly": yearly_trend,
    "ranking": dist_rank,
    "crime_trends": crime_trends,
    "predictions": pred_df.head(20).to_dict(orient='records') if not pred_df.empty else [],
    "dist_data": {
        "yearly": {d: {str(y): int(v) for y, v in yrs.items()} for d, yrs in dist_yearly.items()},
        "total": {k: int(v) for k, v in dist_total.items()},
        "top5": top5
    },
    "paths": mapped_paths
})

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SURAKSHA — UP Crime Intel Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --primary: #c0392b; --bg: #f8f9fa; --sidebar: #1a1a2e; --card: #ffffff; }}
        body {{ font-family: 'Inter', sans-serif; margin: 0; display: flex; height: 100vh; background: var(--bg); overflow: hidden; }}
        
        /* Sidebar Navigation */
        #nav {{ width: 240px; background: var(--sidebar); color: white; padding: 20px; display: flex; flex-direction: column; }}
        .nav-item {{ padding: 12px 15px; margin: 5px 0; border-radius: 6px; cursor: pointer; transition: 0.3s; color: #a0a0b0; }}
        .nav-item:hover, .nav-item.active {{ background: rgba(255,255,255,0.1); color: white; }}
        .nav-item i {{ margin-right: 10px; }}
        
        /* Main Content */
        #main {{ flex: 1; overflow-y: auto; padding: 25px; position: relative; }}
        .page {{ display: none; }}
        .page.active {{ display: block; }}
        
        /* Dashboard Elements */
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        h1 {{ font-size: 24px; color: #1a1a2e; margin-bottom: 20px; }}
        h3 {{ margin-top: 0; font-size: 16px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        
        /* Map Styles */
        #map-panel {{ display: grid; grid-template-columns: 1fr 380px; gap: 20px; height: 80vh; }}
        .svg-wrap {{ background: white; border-radius: 12px; position: relative; overflow: hidden; border: 1px solid #eee; }}
        path.dist {{ stroke: #fff; stroke-width: 0.4; transition: 0.2s; cursor: pointer; }}
        path.dist:hover {{ fill: var(--primary) !important; opacity: 0.8; }}
        .dist-label {{ font-size: 7px; fill: #333; pointer-events: none; text-anchor: middle; font-weight: 600; opacity: 0.7; }}
        
        /* Details Panel */
        #details-card {{ display: none; }}
        .stat-badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; background: #eee; font-size: 12px; }}
    </style>
</head>
<body>
    <div id="nav">
        <h2 style="color:var(--primary); margin-bottom:30px;">🚔 SURAKSHA</h2>
        <div class="nav-item active" onclick="showPage('overview')">📊 Overview Analysis</div>
        <div class="nav-item" onclick="showPage('map')">🗺️ Interactive Map</div>
        <div class="nav-item" onclick="showPage('predictions')">🔮 AI Predictions 2024</div>
        <div style="margin-top:auto; font-size:11px; color:#667;">NCRB Data Intel v3.0</div>
    </div>

    <div id="main">
        <div id="overview" class="page active">
            <h1>UP Crime Deep Analysis</h1>
            <div class="grid">
                <div class="card">
                    <h3>UP Yearly Trend (Total Cases)</h3>
                    <canvas id="yearlyChart"></canvas>
                </div>
                <div class="card">
                    <h3>Top 15 Crime-Prone Districts</h3>
                    <canvas id="rankChart"></canvas>
                </div>
                <div class="card" style="grid-column: span 2;">
                    <h3>Crime Type Direction (Rising vs Falling)</h3>
                    <div id="trend-list" style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:13px;"></div>
                </div>
            </div>
        </div>

        <div id="map" class="page">
            <h1>UP District Crime Hotspots</h1>
            <div id="map-panel">
                <div class="svg-wrap">
                    <svg id="up-svg" viewBox="0 0 850 550" width="100%" height="100%"></svg>
                </div>
                <div id="details-side">
                    <div id="map-hint" class="card">
                        <h3>District Profile</h3>
                        <p>Click a district on the map to see its trend and signature crimes.</p>
                    </div>
                    <div id="details-card" class="card">
                        <h2 id="d-name" style="margin-bottom:5px;">District</h2>
                        <span id="d-total" class="stat-badge">Total: 0</span>
                        <hr style="border:0; border-top:1px solid #eee; margin:15px 0;">
                        <canvas id="distTrendChart" height="200"></canvas>
                        <div id="d-top5" style="margin-top:15px; font-size:13px;"></div>
                    </div>
                </div>
            </div>
        </div>

        <div id="predictions" class="page">
            <h1>🔮 AI Predictions for 2024</h1>
            <div class="card">
                <p>Based on Random Forest model (R²=0.83). Predicted hotspots for next year.</p>
                <table style="width:100%; border-collapse: collapse; font-size:14px;">
                    <thead style="background:#f0f0f0;">
                        <tr><th style="padding:10px; text-align:left;">District</th><th style="text-align:left;">Crime Type</th><th>Predicted</th><th>Trend</th></tr>
                    </thead>
                    <tbody id="pred-table"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const D = {json_data};
        let activeChart = null;

        function showPage(id) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.currentTarget.classList.add('active');
            if(id === 'overview') loadOverviewCharts();
        }}

        function loadOverviewCharts() {{
            // Yearly Chart
            new Chart(document.getElementById('yearlyChart'), {{
                type: 'line',
                data: {{
                    labels: D.yearly.map(r => r.Year),
                    datasets: [{{ label: 'Total Crimes', data: D.yearly.map(r => r.Total_Crimes), borderColor: '#c0392b', tension: 0.3, fill: true, backgroundColor: 'rgba(192,57,43,0.1)' }}]
                }}
            }});
            // Rank Chart
            new Chart(document.getElementById('rankChart'), {{
                type: 'bar',
                data: {{
                    labels: D.ranking.map(r => r.District),
                    datasets: [{{ label: 'Total Cases', data: D.ranking.map(r => r.Total_All_Years), backgroundColor: '#1a1a2e' }}]
                }},
                options: {{ indexAxis: 'y' }}
            }});
            // Trend List
            const list = document.getElementById('trend-list');
            list.innerHTML = D.crime_trends.map(t => `
                <div style="padding:8px; border-bottom:1px solid #eee;">
                    <b>${{t.Crime_Type}}</b>: 
                    <span style="color:${{t.Change_pct > 0 ? 'red' : 'green'}}">
                        ${{t.Change_pct > 0 ? '▲' : '▼'}} ${{Math.abs(t.Change_pct)}}%
                    </span>
                </div>
            `).join('');
        }}

        // Initialize Map
        const svg = document.getElementById('up-svg');
        Object.entries(D.paths).forEach(([rawName, info]) => {{
            const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
            p.setAttribute("d", info.path);
            p.setAttribute("class", "dist");
            p.setAttribute("fill", "#e0e0e0");
            p.onclick = () => selectDistrict(info.mapped);
            svg.appendChild(p);
            
            const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
            t.setAttribute("x", info.centroid[0]);
            t.setAttribute("y", info.centroid[1]);
            t.setAttribute("class", "dist-label");
            t.textContent = info.mapped.length > 9 ? info.mapped.substring(0,7)+'..' : info.mapped;
            svg.appendChild(t);
        }});

        function selectDistrict(name) {{
            document.getElementById('map-hint').style.display = 'none';
            document.getElementById('details-card').style.display = 'block';
            document.getElementById('d-name').innerText = name;
            document.getElementById('d-total').innerText = "Total: " + (D.dist_data.total[name] || 0).toLocaleString();
            
            const yearly = D.dist_data.yearly[name] || {{}};
            if(activeChart) activeChart.destroy();
            activeChart = new Chart(document.getElementById('distTrendChart'), {{
                type: 'line',
                data: {{
                    labels: Object.keys(yearly).sort(),
                    datasets: [{{ label: 'Trend', data: Object.values(yearly), borderColor: '#c0392b' }}]
                }}
            }});

            const t5 = D.dist_data.top5[name] || [];
            document.getElementById('d-top5').innerHTML = "<b>Top 5 Crimes:</b><br>" + 
                t5.map(c => `<div style="display:flex; justify-content:space-between; margin-top:5px;"><span>${{c.crime}}</span><span>${{c.total}}</span></div>`).join('');
        }}

        // Predictions Table
        document.getElementById('pred-table').innerHTML = D.predictions.map(p => `
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:10px;">${{p.District}}</td>
                <td>${{p.Crime_Type}}</td>
                <td style="font-weight:bold;">${{p.Predicted_2024}}</td>
                <td style="color:${{p.Change_pct > 0 ? 'red' : 'green'}}">${{p.Change_pct > 0 ? '▲' : '▼'}} ${{p.Change_pct}}%</td>
            </tr>
        `).join('');

        loadOverviewCharts();
    </script>
</body>
</html>
"""

with open(OUT_PATH, 'w') as f:
    f.write(html_content)

print(f"\n🚀 DONE! Full Pro Dashboard generated: {OUT_PATH}")
print(f"Open in browser: open {OUT_PATH}")