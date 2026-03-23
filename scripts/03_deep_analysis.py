"""
SURAKSHA PROJECT - Script 03
Deep Crime Analysis Engine
===========================
Extracts every possible insight from your master dataset.
Answers 12 key questions about UP crime trends.
Saves 10 separate analysis CSVs for visualization.

HOW TO RUN:
  python3 scripts/03_deep_analysis.py

INPUT:  data/cleaned/master_UP_crime.csv
OUTPUT: data/analysis/  (10 CSV files, all insights)
"""

import pandas as pd
import numpy as np
import os, warnings
warnings.filterwarnings('ignore')

# ── CONFIG ───────────────────────────────────────────────
INPUT_FILE  = "data/cleaned/master_UP_crime.csv"
OUTPUT_DIR  = "data/analysis"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEP  = "=" * 70
THIN = "-" * 70

print(f"\n{SEP}")
print("  SURAKSHA — Deep Crime Analysis Engine")
print("  Extracting every insight from your UP crime data")
print(f"{SEP}\n")

# ── Load data ────────────────────────────────────────────
df = pd.read_csv(INPUT_FILE)
df['Year']  = df['Year'].astype(int)
df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0).astype(int)
df['District'] = df['District'].str.strip()

# Remove any stray total rows
df = df[~df['District'].str.lower().str.contains('total|grp|grand', na=False)]

print(f"  Loaded: {len(df):,} rows")
print(f"  Years : {sorted(df['Year'].unique())}")
print(f"  Districts: {df['District'].nunique()}")
print(f"  Crime types: {df['Crime_Type'].nunique()}")

YEARS     = sorted(df['Year'].unique())
FIRST_YR  = YEARS[0]
LAST_YR   = YEARS[-1]
ALL_DIST  = sorted(df['District'].unique())
ALL_TYPES = sorted(df['Crime_Type'].unique())


# ════════════════════════════════════════════════════════
# ANALYSIS 1 — Overall UP Crime Trend (year-wise total)
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [1] OVERALL UP CRIME TREND — Year-wise total")
print(f"{SEP}")

yearly = df.groupby('Year')['Total'].sum().reset_index()
yearly.columns = ['Year', 'Total_Crimes']
yearly['YoY_Change']   = yearly['Total_Crimes'].diff()
yearly['YoY_Change_pct'] = (yearly['Total_Crimes'].pct_change() * 100).round(2)

print(f"\n  {'Year':<6} {'Total Crimes':>14} {'Change':>10} {'Change%':>9}")
print(f"  {THIN[:50]}")
for _, row in yearly.iterrows():
    chg     = f"{int(row['YoY_Change']):+,}" if not pd.isna(row['YoY_Change']) else "  baseline"
    chg_pct = f"{row['YoY_Change_pct']:+.1f}%" if not pd.isna(row['YoY_Change_pct']) else ""
    bar     = "█" * int((row['Total_Crimes'] / yearly['Total_Crimes'].max()) * 30)
    print(f"  {int(row['Year']):<6} {int(row['Total_Crimes']):>14,} {chg:>10} {chg_pct:>9}  {bar}")

base = int(yearly[yearly['Year']==FIRST_YR]['Total_Crimes'].values[0])
last = int(yearly[yearly['Year']==LAST_YR]['Total_Crimes'].values[0])
overall_change = round((last - base) / base * 100, 1)
print(f"\n  Overall change {FIRST_YR}→{LAST_YR}: {overall_change:+.1f}%")
yearly.to_csv(f"{OUTPUT_DIR}/01_yearly_total_crime.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 2 — Each Crime Type Trend Over Years
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [2] CRIME TYPE TRENDS — How each crime changed over years")
print(f"{SEP}")

crime_yearly = df.groupby(['Year','Crime_Type'])['Total'].sum().unstack(fill_value=0)
crime_yearly.index = crime_yearly.index.astype(int)

# Calculate % change for each crime type from first to last year
trends = []
for crime in crime_yearly.columns:
    vals  = crime_yearly[crime]
    old   = int(vals.iloc[0])
    new   = int(vals.iloc[-1])
    peak_yr  = int(vals.idxmax())
    peak_val = int(vals.max())
    pct   = round(((new-old)/old*100) if old > 0 else 0, 1)
    # Trend direction: rising, falling, or volatile
    mid   = int(vals.iloc[len(vals)//2])
    if pct > 10:    direction = "RISING"
    elif pct < -10: direction = "FALLING"
    else:           direction = "STABLE"
    trends.append({
        'Crime_Type': crime, 'Direction': direction,
        f'{FIRST_YR}_count': old, f'{LAST_YR}_count': new,
        'Change_pct': pct,
        'Peak_year': peak_yr, 'Peak_value': peak_val
    })

trend_df = pd.DataFrame(trends).sort_values('Change_pct', ascending=False)

print(f"\n  {'Crime Type':<32} {'Direction':<10} {FIRST_YR:>8} {LAST_YR:>8} {'Change%':>9} {'Peak Year':>10}")
print(f"  {THIN[:70]}")
for _, r in trend_df.iterrows():
    arrow = "▲" if r['Change_pct'] > 0 else "▼" if r['Change_pct'] < 0 else "→"
    print(f"  {r['Crime_Type']:<32} {r['Direction']:<10} "
          f"{r[str(FIRST_YR)+'_count']:>8,} {r[str(LAST_YR)+'_count']:>8,} "
          f"{r['Change_pct']:>+8.1f}%  {arrow}  Peak: {r['Peak_year']}")

trend_df.to_csv(f"{OUTPUT_DIR}/02_crime_type_trends.csv", index=False)

# Full year-by-year matrix
crime_yearly.reset_index(inplace=True)
crime_yearly.rename(columns={'Year': 'Year'}, inplace=True)
crime_yearly.to_csv(f"{OUTPUT_DIR}/02b_crime_type_by_year_matrix.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 3 — District Rankings (Overall + Per Year)
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [3] DISTRICT RANKINGS — All years + year-by-year")
print(f"{SEP}")

# Overall ranking
dist_total = df.groupby('District')['Total'].sum().sort_values(ascending=False).reset_index()
dist_total.columns = ['District', 'Total_All_Years']
dist_total['Rank'] = range(1, len(dist_total)+1)

print(f"\n  TOP 20 DISTRICTS — All years combined")
print(f"  {'Rank':<5} {'District':<30} {'Total':>10}")
print(f"  {THIN[:50]}")
for _, r in dist_total.head(20).iterrows():
    bar = "█" * int((r['Total_All_Years'] / dist_total['Total_All_Years'].max()) * 25)
    print(f"  {int(r['Rank']):<5} {r['District']:<30} {r['Total_All_Years']:>10,}  {bar}")

dist_total.to_csv(f"{OUTPUT_DIR}/03_district_overall_ranking.csv", index=False)

# Year-by-year district ranking
dist_yearly = df.groupby(['Year','District'])['Total'].sum().reset_index()
dist_yearly_pivot = dist_yearly.pivot_table(
    index='District', columns='Year', values='Total', fill_value=0
).reset_index()
dist_yearly_pivot.to_csv(f"{OUTPUT_DIR}/03b_district_crime_by_year.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 4 — Each District's Crime Trend
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [4] DISTRICT CRIME TRENDS — Rising vs Falling districts")
print(f"{SEP}")

dist_trends = []
for dist in ALL_DIST:
    sub = df[df['District']==dist].groupby('Year')['Total'].sum().sort_index()
    if len(sub) < 2:
        continue
    old = int(sub.iloc[0])
    new = int(sub.iloc[-1])
    pct = round(((new-old)/old*100) if old > 0 else 0, 1)
    # Consecutive years rising/falling
    diffs  = sub.diff().dropna()
    rising = int((diffs > 0).sum())
    falling= int((diffs < 0).sum())
    dist_trends.append({
        'District': dist,
        f'{int(sub.index[0])}_total': old,
        f'{int(sub.index[-1])}_total': new,
        'Change_pct': pct,
        'Years_rising': rising,
        'Years_falling': falling,
        'Trend': 'RISING' if pct > 15 else 'FALLING' if pct < -15 else 'STABLE'
    })

dist_trend_df = pd.DataFrame(dist_trends).sort_values('Change_pct', ascending=False)

print(f"\n  MOST RAPIDLY RISING districts:")
for _, r in dist_trend_df[dist_trend_df['Trend']=='RISING'].head(10).iterrows():
    print(f"    ▲ {r['District']:<30} {r['Change_pct']:>+7.1f}%")

print(f"\n  MOST RAPIDLY FALLING districts (improving law & order):")
for _, r in dist_trend_df[dist_trend_df['Trend']=='FALLING'].head(10).iterrows():
    print(f"    ▼ {r['District']:<30} {r['Change_pct']:>+7.1f}%")

dist_trend_df.to_csv(f"{OUTPUT_DIR}/04_district_trends.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 5 — Top 5 Crimes Per District (Signature Crimes)
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [5] TOP 5 CRIMES PER DISTRICT — Signature crimes of each district")
print(f"{SEP}")

district_signatures = []
for dist in sorted(ALL_DIST):
    sub = df[df['District']==dist].groupby('Crime_Type')['Total'].sum().sort_values(ascending=False)
    top5 = sub.head(5)
    total = int(sub.sum())
    for rank, (crime, val) in enumerate(top5.items(), 1):
        district_signatures.append({
            'District': dist,
            'Rank': rank,
            'Crime_Type': crime,
            'Total_Cases': int(val),
            'Pct_of_District_Total': round(val/total*100, 1) if total > 0 else 0
        })

sig_df = pd.DataFrame(district_signatures)
sig_df.to_csv(f"{OUTPUT_DIR}/05_top5_crimes_per_district.csv", index=False)

# Print sample for top 10 districts
top10_dists = dist_total.head(10)['District'].tolist()
print(f"\n  Top 5 crimes for each of UP's 10 most crime-prone districts:")
for dist in top10_dists:
    sub = sig_df[sig_df['District']==dist].head(5)
    crimes_str = " | ".join([f"{r['Crime_Type']} ({r['Total_Cases']:,})" for _,r in sub.iterrows()])
    print(f"\n  {dist}:")
    print(f"    {crimes_str}")


# ════════════════════════════════════════════════════════
# ANALYSIS 6 — Crime Intensity Score Per District Per Year
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [6] CRIME INTENSITY SCORE — Normalized danger level per district")
print(f"{SEP}")

# Normalize each year's crime to 0-100 score
dy = df.groupby(['Year','District'])['Total'].sum().reset_index()
dy['Intensity_Score'] = dy.groupby('Year')['Total'].transform(
    lambda x: ((x - x.min()) / (x.max() - x.min()) * 100).round(1)
)

# Average intensity across all years
avg_intensity = dy.groupby('District')['Intensity_Score'].mean().round(1).sort_values(ascending=False)
intensity_df  = avg_intensity.reset_index()
intensity_df.columns = ['District', 'Avg_Intensity_Score']
intensity_df['Risk_Level'] = pd.cut(
    intensity_df['Avg_Intensity_Score'],
    bins=[0, 25, 50, 75, 100],
    labels=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
)

print(f"\n  CRITICAL risk districts (score 75-100):")
critical = intensity_df[intensity_df['Risk_Level']=='CRITICAL']
for _, r in critical.iterrows():
    bar = "█" * int(r['Avg_Intensity_Score'] / 5)
    print(f"    {r['District']:<30} Score: {r['Avg_Intensity_Score']:>5.1f}  {bar}")

print(f"\n  Risk level summary:")
print(intensity_df['Risk_Level'].value_counts().to_string())

dy.to_csv(f"{OUTPUT_DIR}/06_intensity_scores_by_year.csv", index=False)
intensity_df.to_csv(f"{OUTPUT_DIR}/06b_district_avg_intensity.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 7 — Year-on-Year Change Per District Per Crime
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [7] YEAR-ON-YEAR CHANGE — Each district, each crime type")
print(f"{SEP}")

df_sorted = df.sort_values(['District','Crime_Type','Year'])
df_sorted['Prev_Year_Total'] = df_sorted.groupby(
    ['District','Crime_Type'])['Total'].shift(1)
df_sorted['YoY_Change'] = df_sorted['Total'] - df_sorted['Prev_Year_Total']
df_sorted['YoY_Pct']    = (
    (df_sorted['YoY_Change'] / df_sorted['Prev_Year_Total']) * 100
).round(1)

yoy_df = df_sorted.dropna(subset=['Prev_Year_Total']).copy()
yoy_df['Prev_Year_Total'] = yoy_df['Prev_Year_Total'].astype(int)
yoy_df['YoY_Change']      = yoy_df['YoY_Change'].astype(int)

# Biggest single-year spikes
print(f"\n  TOP 10 BIGGEST SINGLE-YEAR CRIME SPIKES:")
spikes = yoy_df.nlargest(10, 'YoY_Pct')[
    ['District','Crime_Type','Year','Prev_Year_Total','Total','YoY_Pct']
]
for _, r in spikes.iterrows():
    print(f"    {r['District']:<28} {r['Crime_Type']:<25} "
          f"{int(r['Year'])}: {int(r['Prev_Year_Total']):,} → {int(r['Total']):,} "
          f"({r['YoY_Pct']:+.0f}%)")

# Biggest drops (improvements)
print(f"\n  TOP 10 BIGGEST CRIME DROPS (law & order improvement):")
drops = yoy_df.nsmallest(10, 'YoY_Pct')[
    ['District','Crime_Type','Year','Prev_Year_Total','Total','YoY_Pct']
]
for _, r in drops.iterrows():
    print(f"    {r['District']:<28} {r['Crime_Type']:<25} "
          f"{int(r['Year'])}: {int(r['Prev_Year_Total']):,} → {int(r['Total']):,} "
          f"({r['YoY_Pct']:+.0f}%)")

yoy_df[['District','Crime_Type','Year','Total','Prev_Year_Total',
        'YoY_Change','YoY_Pct']].to_csv(f"{OUTPUT_DIR}/07_yoy_changes.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 8 — Law & Order Report Card Per District
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [8] LAW & ORDER REPORT CARD — Final grade per district")
print(f"{SEP}")

report_cards = []
for dist in ALL_DIST:
    sub = df[df['District']==dist].groupby('Year')['Total'].sum().sort_index()
    if len(sub) < 3:
        continue

    total_all_yrs = int(sub.sum())
    recent_yr     = int(sub.iloc[-1])
    oldest_yr     = int(sub.iloc[0])
    overall_trend = round(((recent_yr-oldest_yr)/oldest_yr*100) if oldest_yr > 0 else 0, 1)

    # Last 3 years average vs first 3 years average
    first3_avg = sub.iloc[:3].mean()
    last3_avg  = sub.iloc[-3:].mean()
    recent_trend = round(((last3_avg-first3_avg)/first3_avg*100) if first3_avg > 0 else 0, 1)

    # Rank among all districts
    rank = int(dist_total[dist_total['District']==dist]['Rank'].values[0]) \
           if dist in dist_total['District'].values else 999

    # Grade
    if recent_trend < -20:    grade = "A  (Improving fast)"
    elif recent_trend < -5:   grade = "B  (Improving)"
    elif recent_trend < 5:    grade = "C  (Stable)"
    elif recent_trend < 20:   grade = "D  (Worsening)"
    else:                     grade = "F  (Critical rise)"

    report_cards.append({
        'District': dist,
        'Overall_Rank': rank,
        'Total_All_Years': total_all_yrs,
        'Recent_Trend_pct': recent_trend,
        'Grade': grade,
        'First3yr_avg': round(first3_avg, 0),
        'Last3yr_avg': round(last3_avg, 0),
    })

rc_df = pd.DataFrame(report_cards).sort_values('Overall_Rank')

print(f"\n  {'District':<30} {'Rank':>5} {'Recent Trend':>14} {'Grade'}")
print(f"  {THIN[:70]}")
for _, r in rc_df.head(30).iterrows():
    print(f"  {r['District']:<30} #{int(r['Overall_Rank']):<5} "
          f"{r['Recent_Trend_pct']:>+12.1f}%  {r['Grade']}")

# Grade summary
print(f"\n  Grade distribution across all UP districts:")
for grade_letter in ['A', 'B', 'C', 'D', 'F']:
    count = rc_df['Grade'].str.startswith(grade_letter).sum()
    bar   = "█" * count
    print(f"    Grade {grade_letter}: {count:>3} districts  {bar}")

rc_df.to_csv(f"{OUTPUT_DIR}/08_district_report_cards.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 9 — Crime Concentration (Gini-style)
# Are crimes concentrated in few districts or spread evenly?
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [9] CRIME CONCENTRATION — How concentrated is crime in UP?")
print(f"{SEP}")

for crime in sorted(ALL_TYPES):
    sub = df[df['Crime_Type']==crime].groupby('District')['Total'].sum().sort_values(ascending=False)
    if sub.empty or sub.sum() == 0:
        continue
    total     = sub.sum()
    top5_pct  = round(sub.head(5).sum() / total * 100, 1)
    top10_pct = round(sub.head(10).sum() / total * 100, 1)
    worst_dist = sub.index[0]
    print(f"  {crime:<32}  Top 5 districts = {top5_pct:>5.1f}%  "
          f"Top 10 = {top10_pct:>5.1f}%  Worst: {worst_dist}")

concentration = []
for crime in ALL_TYPES:
    sub = df[df['Crime_Type']==crime].groupby('District')['Total'].sum().sort_values(ascending=False)
    if sub.empty or sub.sum() == 0: continue
    total = sub.sum()
    concentration.append({
        'Crime_Type': crime,
        'Top5_districts_pct':  round(sub.head(5).sum()/total*100, 1),
        'Top10_districts_pct': round(sub.head(10).sum()/total*100, 1),
        'Worst_district':      sub.index[0],
        'Worst_district_pct':  round(sub.iloc[0]/total*100, 1),
    })
pd.DataFrame(concentration).to_csv(f"{OUTPUT_DIR}/09_crime_concentration.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 10 — COVID Impact (2020 vs 2019)
# ════════════════════════════════════════════════════════
if 2019 in YEARS and 2020 in YEARS:
    print(f"\n{SEP}")
    print("  [10] COVID IMPACT — 2019 vs 2020 crime change")
    print(f"{SEP}")

    pre  = df[df['Year']==2019].groupby('Crime_Type')['Total'].sum()
    post = df[df['Year']==2020].groupby('Crime_Type')['Total'].sum()
    covid_df = pd.DataFrame({'Pre_COVID_2019': pre, 'During_COVID_2020': post}).fillna(0)
    covid_df['Change_pct'] = ((covid_df['During_COVID_2020'] - covid_df['Pre_COVID_2019'])
                               / covid_df['Pre_COVID_2019'] * 100).round(1)
    covid_df = covid_df.sort_values('Change_pct')

    print(f"\n  Crimes that DROPPED during COVID lockdown:")
    for crime, r in covid_df[covid_df['Change_pct'] < 0].iterrows():
        print(f"    ▼ {crime:<32} {r['Change_pct']:>+7.1f}%  "
              f"({int(r['Pre_COVID_2019']):,} → {int(r['During_COVID_2020']):,})")

    print(f"\n  Crimes that ROSE during COVID lockdown:")
    for crime, r in covid_df[covid_df['Change_pct'] > 0].iterrows():
        print(f"    ▲ {crime:<32} {r['Change_pct']:>+7.1f}%  "
              f"({int(r['Pre_COVID_2019']):,} → {int(r['During_COVID_2020']):,})")

    covid_df.reset_index().to_csv(f"{OUTPUT_DIR}/10_covid_impact.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 11 — Divisions Summary
# UP has 18 divisions — group districts into divisions
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [11] UP DIVISION-WISE SUMMARY")
print(f"{SEP}")

# UP's 18 administrative divisions
DIVISIONS = {
    'Agra':         ['Agra','Firozabad','Mainpuri','Mathura'],
    'Aligarh':      ['Aligarh','Etah','Hathras','Kasganj'],
    'Ayodhya':      ['Ambedkar Nagar','Amethi','Ayodhya','Barabanki','Sultanpur'],
    'Azamgarh':     ['Azamgarh','Ballia','Mau'],
    'Bareilly':     ['Bareilly','Budaun','Pilibhit','Shahjahanpur'],
    'Basti':        ['Basti','Sant Kabir Nagar','Siddharthnagar'],
    'Chitrakoot':   ['Banda','Chitrakoot','Hamirpur','Mahoba'],
    'Devipatan':    ['Bahraich','Balrampur','Gonda','Shravasti'],
    'Gorakhpur':    ['Deoria','Gorakhpur','Kushinagar','Maharajganj'],
    'Jhansi':       ['Jalaun','Jhansi','Lalitpur'],
    'Kanpur':       ['Auraiya','Etawah','Farrukhabad','Kannauj','Kanpur Dehat','Kanpur Nagar'],
    'Lucknow':      ['Hardoi','Lucknow','Raebareli','Sitapur','Unnao'],
    'Meerut':       ['Baghpat','Bulandshahr','Ghaziabad','Hapur','Meerut','Muzaffarnagar','Shamli'],
    'Mirzapur':     ['Mirzapur','Sonbhadra'],
    'Moradabad':    ['Amroha','Bijnor','Moradabad','Rampur','Sambhal'],
    'Prayagraj':    ['Fatehpur','Kaushambi','Prayagraj','Pratapgarh'],
    'Saharanpur':   ['Saharanpur'],
    'Varanasi':     ['Bhadohi','Chandauli','Ghazipur','Jaunpur','Varanasi'],
}

# Build district → division lookup
dist_to_div = {}
for div, dists in DIVISIONS.items():
    for d in dists:
        dist_to_div[d.lower()] = div

df['Division'] = df['District'].str.lower().map(dist_to_div).fillna('Other')

div_summary = df.groupby(['Division','Year'])['Total'].sum().reset_index()
div_total   = df.groupby('Division')['Total'].sum().sort_values(ascending=False).reset_index()

print(f"\n  Division-wise total crime (all years):")
for _, r in div_total.iterrows():
    bar = "█" * int((r['Total'] / div_total['Total'].max()) * 30)
    print(f"    {r['Division']:<16} {r['Total']:>10,}  {bar}")

div_summary.to_csv(f"{OUTPUT_DIR}/11_division_wise_crime.csv", index=False)
div_total.to_csv(f"{OUTPUT_DIR}/11b_division_totals.csv", index=False)


# ════════════════════════════════════════════════════════
# ANALYSIS 12 — Crime Seasonality (if monthly data exists)
# Using year patterns as proxy
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [12] MOST DANGEROUS YEAR PER DISTRICT")
print(f"{SEP}")

peak_years = []
for dist in ALL_DIST:
    sub = df[df['District']==dist].groupby('Year')['Total'].sum()
    if sub.empty: continue
    peak_yr  = int(sub.idxmax())
    peak_val = int(sub.max())
    min_yr   = int(sub.idxmin())
    min_val  = int(sub.min())
    peak_years.append({
        'District':   dist,
        'Peak_year':  peak_yr,
        'Peak_total': peak_val,
        'Best_year':  min_yr,
        'Best_total': min_val,
        'Worst_Best_ratio': round(peak_val/min_val, 2) if min_val > 0 else 0
    })

peak_df = pd.DataFrame(peak_years).sort_values('Worst_Best_ratio', ascending=False)

print(f"\n  Districts with BIGGEST swing between best and worst year:")
print(f"  {'District':<30} {'Best Year':>10} {'Worst Year':>11} {'Ratio':>7}")
print(f"  {THIN[:60]}")
for _, r in peak_df.head(15).iterrows():
    print(f"  {r['District']:<30} {r['Best_year']:>5} ({r['Best_total']:>7,})  "
          f"{r['Peak_year']:>5} ({r['Peak_total']:>7,})  {r['Worst_Best_ratio']:>6.1f}x")

peak_df.to_csv(f"{OUTPUT_DIR}/12_peak_years_per_district.csv", index=False)


# ════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  ALL ANALYSIS COMPLETE — Files saved in data/analysis/")
print(SEP)
print(f"""
  FILES CREATED:
  ─────────────────────────────────────────────────────
  01_yearly_total_crime.csv          Year-wise UP total + % change
  02_crime_type_trends.csv           Each crime rising/falling since {FIRST_YR}
  02b_crime_type_by_year_matrix.csv  Full year × crime type matrix
  03_district_overall_ranking.csv    All districts ranked by total crime
  03b_district_crime_by_year.csv     District × year crime matrix
  04_district_trends.csv             Each district rising/falling/stable
  05_top5_crimes_per_district.csv    Signature crimes of each district
  06_intensity_scores_by_year.csv    Normalized 0-100 danger score
  06b_district_avg_intensity.csv     Average intensity + risk level
  07_yoy_changes.csv                 Year-on-year change per district/crime
  08_district_report_cards.csv       A-F grade per district
  09_crime_concentration.csv         How concentrated crime is per type
  10_covid_impact.csv                COVID lockdown effect on each crime
  11_division_wise_crime.csv         UP's 18 divisions crime summary
  12_peak_years_per_district.csv     Best and worst year per district

  KEY FINDINGS FROM YOUR DATA:
  ─────────────────────────────────────────────────────
  Use these 12 CSVs to answer ANY question about UP crime.
  Next: Run python3 scripts/04_map_dashboard.py
  to see all of this on an interactive map.
""")