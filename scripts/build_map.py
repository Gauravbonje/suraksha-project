import json, math, os, re, csv

# ── Configuration ────────────────────────────────
GEO_PATH    = "data/maps/up_districts.geojson"
CRIME_PATH  = "data/cleaned/master_UP_crime.csv"
OUT_PATH    = "suraksha_realmap.html"

# ── 1. Load GeoJSON ──────────────────────────────
with open(GEO_PATH) as f:
    geo = json.load(f)

print(f"✅ Loaded {len(geo['features'])} districts from GeoJSON")

# ── 2. Build crime data from master CSV ──────────
master = []
with open(CRIME_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        master.append(row)

print(f"✅ Loaded {len(master)} crime rows")

# Analytics Containers
dist_total = {}
dist_yearly = {}
crime_yearly = {}
crime_per_dist = {}
top5 = {}
grades = {}

# Process Rows
for row in master:
    d = row['District'].strip()
    try:
        yr = int(row['Year'])
        ct = row['Crime_Type'].strip()
        tot = int(float(row['Total']))
    except (ValueError, TypeError, KeyError):
        continue

    # District totals
    dist_total[d] = dist_total.get(d, 0) + tot
    
    # Yearly trend per district
    if d not in dist_yearly: dist_yearly[d] = {}
    dist_yearly[d][yr] = dist_yearly[d].get(yr, 0) + tot

    # FIX: Correctly increment yearly crime type totals (No more Dict error)
    if ct not in crime_yearly: crime_yearly[ct] = {}
    crime_yearly[ct][yr] = crime_yearly[ct].get(yr, 0) + tot

    # Breakup for Top 5
    if d not in crime_per_dist: crime_per_dist[d] = {}
    crime_per_dist[d][ct] = crime_per_dist[d].get(ct, 0) + tot

# Calculate Top 5 crimes per district
for d, crimes in crime_per_dist.items():
    sorted_crimes = sorted(crimes.items(), key=lambda x: -x[1])[:5]
    top5[d] = [{"crime": c, "total": v} for c, v in sorted_crimes]

# Calculate Grades (A to F based on 3-year trend)
for d, yearly in dist_yearly.items():
    yrs = sorted(yearly.keys())
    if len(yrs) < 3: continue
    vals = [yearly[y] for y in yrs]
    first3 = sum(vals[:3]) / 3
    last3  = sum(vals[-3:]) / 3
    pct    = round(((last3 - first3) / first3 * 100) if first3 > 0 else 0, 1)
    
    if pct < -20:   grade = 'A'
    elif pct < -5:  grade = 'B'
    elif pct < 5:   grade = 'C'
    elif pct < 20:  grade = 'D'
    else:           grade = 'F'
    grades[d] = {"grade": grade, "trend_pct": pct}

latest_year = max(yr for yearly in dist_yearly.values() for yr in yearly.keys())

# ── 3. Project GeoJSON → SVG paths & Centroids ───
def get_coords(geometry):
    if geometry['type'] == 'Polygon': return geometry['coordinates'][0]
    elif geometry['type'] == 'MultiPolygon':
        coords = []
        for poly in geometry['coordinates']: coords.extend(poly[0])
        return coords
    return []

all_coords = []
for feat in geo['features']: all_coords.extend(get_coords(feat['geometry']))
lons, lats = [c[0] for c in all_coords], [c[1] for c in all_coords]
min_lon, max_lon, min_lat, max_lat = min(lons), max(lons), min(lats), max(lats)

VW, VH, PAD = 860, 580, 20
scale = min((VW - 2*PAD) / (max_lon - min_lon), (VH - 2*PAD) / (max_lat - min_lat))

def project(lon, lat):
    x = PAD + (lon - min_lon) * scale + ((VW - 2*PAD) - (max_lon - min_lon) * scale) / 2
    y = PAD + (max_lat - lat) * scale + ((VH - 2*PAD) - (max_lat - min_lat) * scale) / 2
    return round(x, 2), round(y, 2)

def make_path(geometry):
    rings = geometry['coordinates'] if geometry['type'] == 'Polygon' else [p[0] for p in geometry['coordinates']]
    return " ".join(["M" + " L".join(f"{project(c[0],c[1])[0]},{project(c[0],c[1])[1]}" for c in r) + "Z" for r in rings])

# Map matching logic
mapped_paths = {}
NAME_MAP = {'Allahabad': 'Prayagraj', 'Faizabad': 'Ayodhya', 'Kheri': 'Khiri', 'Lakhimpur Kheri': 'Khiri', 'Sant Ravidas Nagar': 'Bhadohi'}

for feat in geo['features']:
    props = feat['properties']
    raw_name = props.get('Dist_Name') or props.get('NAME_2') or "Unknown"
    crime_name = NAME_MAP.get(raw_name, raw_name)
    path = make_path(feat['geometry'])
    
    # Calculate Centroid for Label
    c_pts = get_coords(feat['geometry'])
    if not c_pts: continue
    px = [project(c[0], c[1])[0] for c in c_pts]
    py = [project(c[0], c[1])[1] for c in c_pts]
    centroid = [sum(px)/len(px), sum(py)/len(py)]

    mapped_paths[raw_name] = {"path": path, "mapped": crime_name, "centroid": centroid}

# Colors
COLORS = ["#e74c3c","#3498db","#2ecc71","#f39c12","#9b59b6","#1abc9c","#e67e22","#27ae60","#2980b9"]
district_colors = {n: COLORS[i % len(COLORS)] for i, n in enumerate(sorted(mapped_paths.keys()))}

# ── 4. HTML Generation (Detailed Dashboard) ──────
crime_data_json = json.dumps({
    "dist_total": dist_total, "dist_yearly": {d: {str(y): v for y, v in yrs.items()} for d, yrs in dist_yearly.items()},
    "top5": top5, "grades": grades, "latest_year": latest_year
})

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SURAKSHA - UP Crime Map</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Roboto', sans-serif; display: grid; grid-template-columns: 1fr 380px; height: 100vh; margin: 0; background: #f4f4f2; overflow:hidden; }}
        
        /* Map Panel */
        #map-container {{ position: relative; background: #fff; border-right: 1px solid #ddd; display: flex; flex-direction: column; }}
        #map-header {{ padding: 10px 20px; border-bottom: 1px solid #eee; display:flex; justify-content:space-between; align-items:center;}}
        #up-svg {{ flex: 1; width: 100%; height: 100%; }}
        path.dist {{ stroke: #fff; stroke-width: 0.5; cursor: pointer; transition: 0.2s; }}
        path.dist:hover {{ filter: brightness(0.8); stroke: #000; stroke-width: 1.5; }}
        .dist-label {{ font-size: 8px; fill: #fff; font-weight: bold; pointer-events: none; text-anchor: middle; paint-order: stroke; stroke: rgba(0,0,0,0.5); stroke-width: 1px;}}

        /* Info Panel */
        #info-panel {{ padding: 0; overflow-y: auto; background: #f9f9f9; display: flex; flex-direction: column; }}
        #placeholder {{ padding: 40px; text-align: center; color: #777; margin-top: auto; margin-bottom: auto;}}
        #details {{ display: none; padding: 20px; }}
        
        .card {{ background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}}
        h2 {{ margin-top: 0; color: #1a2a3a; font-size: 22px; }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;}}
        .stat-box {{ background: #f0f3f6; padding: 10px; border-radius: 4px; text-align: center; }}
        .stat-val {{ font-size: 20px; font-weight: bold; color: #c0392b; }}
        .stat-lbl {{ font-size: 11px; color: #777; text-transform: uppercase; }}
        
        .grade-badge {{ float: right; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 18px; }}
        .gA {{ background: #d4edda; color: #155724; }} .gB {{ background: #c3e6cb; color: #155724; }}
        .gC {{ background: #fff3cd; color: #856404; }} .gD {{ background: #ffeeba; color: #856404; }} .gF {{ background: #f8d7da; color: #721c24; }}
        
        select {{ padding: 5px; border-radius: 4px; border: 1px solid #ccc; }}
    </style>
</head>
<body>
    <div id="map-container">
        <div id="map-header">
            <h1 style="margin:0; font-size:18px;">SURAKSHA: UP Crime Intelligence</h1>
            <div style="font-size:12px;">Shade by: 
                <select id="shade-mode" onchange="applyShading()">
                    <option value="total">Total Crime</option>
                    <option value="women">Against Women</option>
                    <option value="cyber">Cyber Crime</option>
                </select>
            </div>
        </div>
        <svg id="up-svg" viewBox="0 0 860 580"></svg>
    </div>
    
    <div id="info-panel">
        <div id="placeholder">
            <div style="font-size:50px;">📍</div>
            <h3>Select a district on the map</h3>
            <p>Click any region to see detailed crime analytics, trends, and rankings.</p>
        </div>
        <div id="details">
            <span id="d-grade" class="grade-badge">C</span>
            <h2 id="d-name">District</h2>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val" id="d-total">0</div><div class="stat-lbl">Total Cases</div></div>
                <div class="stat-box"><div class="stat-val" id="d-trend">0%</div><div class="stat-lbl">5Yr Trend</div></div>
            </div>
            
            <div class="card">
                <h4 style="margin-top:0;">Yearly Trend</h4>
                <canvas id="trendChart" width="340" height="180"></canvas>
            </div>
            
            <div id="top-crimes" class="card"></div>
        </div>
    </div>

    <script>
        const data = {crime_data_json};
        const paths = {json.dumps(mapped_paths)};
        const colors = {json.dumps(district_colors)};
        let myChart = null;

        const svg = document.getElementById('up-svg');
        
        // --- ADDING MAP DISTRICTS & LABELS ---
        Object.entries(paths).forEach(([name, info]) => {{
            // 1. Add Shape (Path)
            const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
            p.setAttribute("d", info.path);
            p.setAttribute("class", "dist");
            p.setAttribute("id", "path-" + info.mapped);
            p.setAttribute("fill", colors[name]);
            p.onclick = () => showDistrict(name, info.mapped);
            svg.appendChild(p);
            
            // 2. Add Label (Text) at Centroid
            const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
            t.setAttribute("x", info.centroid[0]);
            t.setAttribute("y", info.centroid[1]);
            t.setAttribute("class", "dist-label");
            // Shorten name if too long (e.g., Lakhimpur Kheri -> Khiri)
            t.textContent = info.mapped.length > 10 ? info.mapped.substring(0,8)+".." : info.mapped;
            svg.appendChild(t);
        }});

        function applyShading() {{
            const mode = document.getElementById('shade-mode').value;
            // Shading logic based on mode... (Simplified for now, keeps base colors)
            alert("Shading feature placeholder. Implementation depends on Crime_Type names in CSV.");
        }}

        function showDistrict(geoName, crimeName) {{
            document.getElementById('placeholder').style.display = 'none';
            document.getElementById('details').style.display = 'block';
            document.getElementById('d-name').innerText = crimeName;
            
            // Stats & Grade
            const total = data.dist_total[crimeName] || 0;
            const gradeInfo = data.grades[crimeName] || {{grade: 'N/A', trend_pct: 0}};
            document.getElementById('d-total').innerText = total.toLocaleString('en-IN');
            document.getElementById('d-trend').innerText = (gradeInfo.trend_pct > 0 ? "+" : "") + gradeInfo.trend_pct + "%";
            document.getElementById('d-grade').innerText = gradeInfo.grade;
            document.getElementById('d-grade').className = 'grade-badge g' + gradeInfo.grade;

            // Chart
            const yearly = data.dist_yearly[crimeName] || {{}};
            const labels = Object.keys(yearly).sort();
            const values = labels.map(l => yearly[l]);

            if(myChart) myChart.destroy();
            myChart = new Chart(document.getElementById('trendChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{ label: 'Crime Rate', data: values, borderColor: '#c0392b', backgroundColor: 'rgba(192,57,43,0.1)', fill: true, tension: 0.3 }}]
                }},
                options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
            }});

            // Top Crimes List
            const tc = data.top5[crimeName] || [];
            document.getElementById('top-crimes').innerHTML = '<h4 style="margin-top:0;">Top 5 Crime Types</h4>' + 
                tc.map(c => `<div style="font-size:13px; margin-top:6px; display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding-bottom:3px;">
                                <span>${{c.crime}}</span> <strong>${{c.total.toLocaleString('en-IN')}}</strong>
                             </div>`).join('');
        }}
    </script>
</body>
</html>
"""

with open(OUT_PATH, 'w') as f:
    f.write(html_template)

print(f"\n🚀 SUCCESS! Detailed Map with Labels saved as: {OUT_PATH}")
print(f"Open in browser: open {OUT_PATH}")