"""
SURAKSHA PROJECT - Complete Pipeline v3
========================================
Loads ALL NCRB files (2016-2023) + Kaggle CSV
Extracts UP districts only
Trains crime prediction model
Predicts next year hotspots

HOW TO RUN:
  cd ~/Desktop/suraksha-project
  source venv/bin/activate
  python3 scripts/suraksha_complete.py

FOLDER STRUCTURE:
  suraksha-project/
  ├── data/
  │   ├── ncrb/
  │   │   ├── 2016/   all 10 xlsx files
  │   │   ├── 2018/   all 10 xlsx files
  │   │   ├── 2019/   all 10 xlsx files
  │   │   ├── 2020/   all 10 xlsx files
  │   │   ├── 2021/   all 10 xlsx files
  │   │   ├── 2022/   all 10 xlsx files
  │   │   └── 2023/   all 10 xlsx files
  │   └── kaggle/
  │       └── india_district_crime_2014_2023_30k.csv
  └── scripts/
      └── suraksha_complete.py
"""

import pandas as pd
import numpy as np
import os, glob, re, json, warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

# ════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════
NCRB_ROOT  = "data/ncrb"
KAGGLE_DIR = "data/kaggle"
OUTPUT_DIR = "data/cleaned"
MODEL_DIR  = "data/model"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR,  exist_ok=True)

SEP  = "=" * 65
THIN = "-" * 65

# ── ROWS TO ALWAYS SKIP ──────────────────────────────────
# These appear in NCRB files but are NOT real districts
SKIP_NAMES = {
    'total district(s)', 'total districts', 'total',
    'grand total', 'state total', 'district total',
    'grp', 'nan', 'none', ''
}

# ── FILE TYPE RULES ──────────────────────────────────────
# total_col = -1  means use last column (works for all files
#                 EXCEPT Missing Persons which uses col 20)
FILE_RULES = {
    "ipc":         {"crime_type": "IPC Crimes",              "total_col": -1},
    "sll":         {"crime_type": "SLL Crimes",              "total_col": -1},
    "women":       {"crime_type": "Crimes Against Women",    "total_col": -1},
    "children":    {"crime_type": "Crimes Against Children", "total_col": -1},
    "scs":         {"crime_type": "Crimes Against SCs",      "total_col": -1},
    "sts":         {"crime_type": "Crimes Against STs",      "total_col": -1},
    "ipcjuvenile": {"crime_type": "Juvenile IPC",            "total_col": -1},
    "slljuvenile": {"crime_type": "Juvenile SLL",            "total_col": -1},
    "cyber":       {"crime_type": "Cyber Crimes",            "total_col": -1},
    "missing":     {"crime_type": "Missing Persons",         "total_col": 20},
}

# ════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════

def detect_file_type(filename):
    """Detect crime category from filename"""
    # Remove all non-letters and lowercase
    f = re.sub(r'[^a-z]', '', filename.lower())
    # Check juvenile FIRST — some files spell it "Jeveniles" (NCRB typo)
    is_juv = 'juvenile' in f or 'jeveni' in f
    if is_juv and 'ipc' in f:  return 'ipcjuvenile'
    if is_juv and 'sll' in f:  return 'slljuvenile'
    if 'ipc' in f:             return 'ipc'
    if 'sll' in f:             return 'sll'
    if 'women' in f:           return 'women'
    if 'woman' in f:           return 'women'
    if 'children' in f:        return 'children'
    if 'child' in f:           return 'children'
    if 'scs' in f:             return 'scs'
    if 'sts' in f:             return 'sts'
    if 'cyber' in f:           return 'cyber'
    if 'missing' in f:         return 'missing'
    return None

def extract_year(filepath):
    """Extract 20XX from filename or folder path"""
    m = re.search(r'(20[12]\d)', filepath)
    return int(m.group(1)) if m else None

def is_UP_state_row(cell):
    """
    Check if a cell is the Uttar Pradesh state header row.

    NCRB uses different formats across years:
      2023: "State: Uttar Pradesh"   (no space before colon)
      2021: "State: Uttar Pradesh"
      2020: "State: Uttar Pradesh"
      2019: "State : Uttar Pradesh"  (space before colon)
      2018: "State : Uttar Pradesh"  (space before colon)
      2016: "State: Uttar Pradesh"

    We handle ALL variants here.
    """
    v = str(cell).strip().lower()
    # Remove all spaces around colon for comparison
    v_clean = v.replace(' : ', ':').replace(' :', ':')
    return (
        v_clean == 'state:uttar pradesh' or
        v == 'uttar pradesh' or
        v == 'state: uttar pradesh' or
        v == 'state : uttar pradesh'
    )

def load_UP_from_file(filepath, file_type, year):
    """
    Load one NCRB Excel file.
    Find the Uttar Pradesh section.
    Return only UP district rows with their total crime count.
    """
    rule = FILE_RULES.get(file_type)
    if not rule:
        return None

    try:
        xl  = pd.ExcelFile(filepath)
        raw = pd.read_excel(
            filepath,
            sheet_name=xl.sheet_names[0],
            header=None,
            dtype=str
        )

        # ── Step 1: Find UP state header row ─────────────
        # Check column 0 primarily (all years use col 0 for state name)
        up_start = None
        for i, row in raw.iterrows():
            if is_UP_state_row(row.iloc[0]):
                up_start = i
                break
            # Backup: check col 1
            if is_UP_state_row(row.iloc[1]):
                up_start = i
                break

        if up_start is None:
            # Last resort: scan for 'uttar' anywhere in first 3 cols
            for i, row in raw.iterrows():
                for c in range(min(3, len(row))):
                    if 'uttar pradesh' in str(row.iloc[c]).lower():
                        up_start = i
                        break
                if up_start is not None:
                    break

        if up_start is None:
            return None

        # ── Step 2: Get total column index ───────────────
        total_col = rule['total_col']
        if total_col == -1:
            total_col = len(raw.columns) - 1

        # ── Step 3: Collect district rows ────────────────
        # District rows have a number in col 0 (S.No = 1, 2, 3...)
        # Stop when we hit the next state header
        records = []
        for i in range(up_start + 1, min(up_start + 110, len(raw))):
            col0 = str(raw.iloc[i, 0]).strip()
            col1 = str(raw.iloc[i, 1]).strip()

            # Stop at next state
            if 'state' in col0.lower() and (
                ':' in col0 or 'pradesh' in col0.lower() or
                'bengal' in col0.lower() or 'uttarakhand' in col0.lower()
            ):
                break

            # District name is always in column 1
            dist = col1.strip()

            # Skip non-district rows
            if dist.lower() in SKIP_NAMES:
                continue
            if 'total' in dist.lower():
                continue

            # S.No in col 0 must be a plain number like 1, 2, 3
            sno_clean = col0.replace('.','').strip()
            if not re.match(r'^\d+$', sno_clean):
                continue

            # Get total value
            total_val = pd.to_numeric(raw.iloc[i, total_col], errors='coerce')
            if pd.isna(total_val) or total_val < 0:
                continue

            records.append({
                'District':   dist,
                'Year':       year,
                'Crime_Type': rule['crime_type'],
                'Total':      int(total_val),
                'Source':     'NCRB'
            })

        return pd.DataFrame(records) if records else None

    except Exception as e:
        print(f"    ERROR in {os.path.basename(filepath)}: {e}")
        return None


# ════════════════════════════════════════════════════════
# PART 1 — LOAD ALL NCRB EXCEL FILES
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  PART 1 — Loading NCRB District Excel Files")
print(f"{SEP}\n")

all_xlsx = sorted(set(
    glob.glob(f"{NCRB_ROOT}/**/*.xlsx", recursive=True) +
    glob.glob(f"{NCRB_ROOT}/**/*.xls",  recursive=True)
))

if not all_xlsx:
    print(f"ERROR: No Excel files found in '{NCRB_ROOT}/'")
    print("Put your NCRB files inside year subfolders:")
    print("  data/ncrb/2023/   data/ncrb/2022/   etc.")
    exit(1)

print(f"Found {len(all_xlsx)} Excel files\n")

ncrb_frames = []
ok_count    = 0
fail_count  = 0

for fp in all_xlsx:
    fname = os.path.basename(fp)
    year  = extract_year(fp)
    ftype = detect_file_type(fname)

    if not year:
        print(f"  SKIP  (no year in name): {fname}")
        fail_count += 1
        continue
    if not ftype:
        print(f"  SKIP  (unknown type):    {fname}")
        fail_count += 1
        continue

    df = load_UP_from_file(fp, ftype, year)

    if df is not None and len(df) > 0:
        ncrb_frames.append(df)
        ok_count += 1
        label = FILE_RULES[ftype]['crime_type']
        print(f"  OK    {year}  {label:<30}  {len(df)} districts")
    else:
        print(f"  FAIL  {year}  {fname}")
        fail_count += 1

print(f"\n{THIN}")
print(f"  Loaded: {ok_count} files    Failed: {fail_count} files")

if ncrb_frames:
    ncrb_master = pd.concat(ncrb_frames, ignore_index=True)
    # Final safety: remove any total rows that slipped through
    ncrb_master = ncrb_master[
        ~ncrb_master['District'].str.lower().str.contains(
            r'total|grp|grand', regex=True, na=False
        )
    ]
    ncrb_master.to_csv(f"{OUTPUT_DIR}/ncrb_UP_all_years.csv", index=False)
    print(f"  NCRB rows   : {len(ncrb_master):,}")
    print(f"  Years       : {sorted(ncrb_master['Year'].unique())}")
    print(f"  Districts   : {ncrb_master['District'].nunique()}")
    print(f"  Crime types : {ncrb_master['Crime_Type'].nunique()}")
else:
    print("  WARNING: No NCRB data loaded — check folder structure")
    ncrb_master = pd.DataFrame(
        columns=['District','Year','Crime_Type','Total','Source'])


# ════════════════════════════════════════════════════════
# PART 2 — LOAD KAGGLE CSV
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  PART 2 — Loading Kaggle Dataset")
print(f"{SEP}\n")

csv_files = glob.glob(f"{KAGGLE_DIR}/*.csv")

if not csv_files:
    print(f"  WARNING: No CSV in '{KAGGLE_DIR}/' — skipping Kaggle data")
    kaggle_master = pd.DataFrame(
        columns=['District','Year','Crime_Type','Total','Source'])
else:
    raw_kg = pd.read_csv(csv_files[0])
    print(f"  File    : {os.path.basename(csv_files[0])}")
    print(f"  Columns : {list(raw_kg.columns)}")

    up_kg = raw_kg[raw_kg['State'] == 'Uttar Pradesh'].copy()
    up_kg = up_kg.rename(columns={'Cases_Reported': 'Total'})
    up_kg = up_kg[['District','Year','Crime_Type','Total']].copy()
    up_kg['Source'] = 'Kaggle'

    kaggle_master = up_kg
    kaggle_master.to_csv(f"{OUTPUT_DIR}/kaggle_UP.csv", index=False)

    print(f"  UP rows   : {len(kaggle_master):,}")
    print(f"  Years     : {sorted(kaggle_master['Year'].unique())}")
    print(f"  Districts : {kaggle_master['District'].nunique()}")
    print(f"  Types     : {list(kaggle_master['Crime_Type'].unique())}")


# ════════════════════════════════════════════════════════
# PART 3 — MERGE BOTH DATASETS
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  PART 3 — Merging NCRB + Kaggle")
print(f"{SEP}\n")

all_data = pd.concat([ncrb_master, kaggle_master], ignore_index=True)

# Clean up
all_data = all_data.dropna(subset=['District','Year','Crime_Type','Total'])
all_data['Total']    = pd.to_numeric(all_data['Total'], errors='coerce').fillna(0).astype(int)
all_data['Year']     = all_data['Year'].astype(int)
all_data['District'] = all_data['District'].str.strip()

# Remove total/grp rows one more time just to be safe
all_data = all_data[
    ~all_data['District'].str.lower().str.contains(
        r'total|grp|grand', regex=True, na=False
    )
]

all_data = all_data.sort_values(
    ['District','Crime_Type','Year']
).reset_index(drop=True)

# Save master file
master_path = f"{OUTPUT_DIR}/master_UP_crime.csv"
all_data.to_csv(master_path, index=False)

print(f"  Total rows  : {len(all_data):,}")
print(f"  Districts   : {all_data['District'].nunique()}")
print(f"  Years       : {sorted(all_data['Year'].unique())}")
print(f"  Crime types : {all_data['Crime_Type'].nunique()}")
print(f"  Sources     : {list(all_data['Source'].unique())}")
print(f"  Saved to    : {master_path}")


# ════════════════════════════════════════════════════════
# PART 4 — DATA ANALYSIS
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  PART 4 — Data Analysis (key insights)")
print(f"{SEP}")

df = all_data.copy()

# ── Q1: Top districts ────────────────────────────────────
print("\n  [1] TOP 10 CRIME-PRONE DISTRICTS — all years combined")
print(THIN)
top = df.groupby('District')['Total'].sum().sort_values(ascending=False).head(10)
for i,(d,v) in enumerate(top.items(), 1):
    bar = "█" * int((v / top.iloc[0]) * 28)
    print(f"  {i:>2}. {d:<30} {v:>10,}  {bar}")

# ── Q2: Year-wise total ───────────────────────────────────
print("\n  [2] YEAR-WISE TOTAL CRIME IN UP")
print(THIN)
yr = df.groupby('Year')['Total'].sum().sort_index()
mx = yr.max()
for year, val in yr.items():
    bar = "█" * max(1, int((val / mx) * 35))
    print(f"  {int(year)}  {val:>10,}  {bar}")

# ── Q3: Crime trends ─────────────────────────────────────
years_list = sorted(df['Year'].unique())
if len(years_list) >= 2:
    fy, ly = years_list[0], years_list[-1]
    print(f"\n  [3] CRIME TRENDS  {fy} → {ly}")
    print(THIN)
    pt = df.groupby(['Year','Crime_Type'])['Total'].sum().unstack(fill_value=0)
    rows = []
    for crime in pt.columns:
        if fy in pt.index and ly in pt.index:
            old = int(pt.loc[fy, crime])
            new = int(pt.loc[ly, crime])
            pct = round(((new-old)/old*100) if old > 0 else 0, 1)
            rows.append((crime, pct, old, new))
    for crime, pct, old, new in sorted(rows, key=lambda x: -x[1]):
        arrow = "▲" if pct >= 0 else "▼"
        print(f"  {arrow} {crime:<32} {pct:>+7.1f}%"
              f"   ({fy}: {old:,} → {ly}: {new:,})")

# ── Q4: Worst district per type ──────────────────────────
print("\n  [4] WORST DISTRICT PER CRIME TYPE")
print(THIN)
for crime in sorted(df['Crime_Type'].unique()):
    sub   = df[df['Crime_Type'] == crime]
    worst = sub.groupby('District')['Total'].sum()
    if worst.empty: continue
    d, v  = worst.idxmax(), int(worst.max())
    print(f"  {crime:<32}  →  {d}  ({v:,})")


# ════════════════════════════════════════════════════════
# PART 5 — TRAIN PREDICTION MODEL
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  PART 5 — Training Crime Prediction Model")
print(f"{SEP}\n")

df_model = df.copy().sort_values(['District','Crime_Type','Year'])

# Label encode
le_dist  = LabelEncoder()
le_crime = LabelEncoder()
df_model['District_enc']   = le_dist.fit_transform(df_model['District'])
df_model['Crime_Type_enc'] = le_crime.fit_transform(df_model['Crime_Type'])
df_model['Year_norm']      = df_model['Year'] - df_model['Year'].min()

# Lag features — previous years' crime count
# These are the most powerful predictors
df_model['Lag1'] = df_model.groupby(
    ['District','Crime_Type'])['Total'].shift(1)
df_model['Lag2'] = df_model.groupby(
    ['District','Crime_Type'])['Total'].shift(2)
df_model['RollMean3'] = df_model.groupby(
    ['District','Crime_Type'])['Total'].transform(
    lambda x: x.shift(1).rolling(3, min_periods=1).mean()
)

# Drop rows where Lag1 is missing (first year of each group)
df_model = df_model.dropna(subset=['Lag1']).copy()
# Fill remaining NaN with Lag1 value
df_model['Lag2']      = df_model['Lag2'].fillna(df_model['Lag1'])
df_model['RollMean3'] = df_model['RollMean3'].fillna(df_model['Lag1'])

print(f"  Training rows : {len(df_model):,}")

FEATURES = [
    'District_enc', 'Crime_Type_enc', 'Year_norm',
    'Lag1', 'Lag2', 'RollMean3'
]
TARGET = 'Total'

X = df_model[FEATURES]
y = df_model[TARGET]

# Train/test split — test on last 2 years, train on everything before
max_year  = int(df_model['Year'].max())
min_year  = int(df_model['Year'].min())
train_idx = df_model['Year'] < (max_year - 1)
X_train, y_train = X[train_idx],  y[train_idx]
X_test,  y_test  = X[~train_idx], y[~train_idx]
print(f"  Train: {len(X_train):,} rows  |  Test: {len(X_test):,} rows\n")

# Train 3 models and compare
MODELS = {
    'Gradient Boosting': GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.05,
        max_depth=5, random_state=42
    ),
    'Random Forest': RandomForestRegressor(
        n_estimators=200, max_depth=10,
        random_state=42, n_jobs=-1
    ),
    'Linear Regression': LinearRegression()
}

print(f"  {'Model':<22}  {'MAE':>8}  {'RMSE':>8}  {'R2':>8}")
print(f"  {THIN[:55]}")

best_model  = None
best_name   = None
best_rmse   = float('inf')
all_results = {}

for name, model in MODELS.items():
    model.fit(X_train, y_train)
    preds = np.maximum(model.predict(X_test), 0)
    mae   = mean_absolute_error(y_test, preds)
    rmse  = np.sqrt(mean_squared_error(y_test, preds))
    r2    = r2_score(y_test, preds)
    all_results[name] = {
        'MAE': round(mae,2), 'RMSE': round(rmse,2), 'R2': round(r2,4)
    }
    tag = "  ← BEST" if rmse < best_rmse else ""
    print(f"  {name:<22}  {mae:>8.1f}  {rmse:>8.1f}  {r2:>8.4f}{tag}")
    if rmse < best_rmse:
        best_rmse  = rmse
        best_name  = name
        best_model = model

print(f"\n  Best model : {best_name}")
print(f"  RMSE       : {best_rmse:.1f}  (avg error per prediction in cases)")
print(f"  R²         : {all_results[best_name]['R2']}  (1.0 = perfect)")

# Feature importance
if hasattr(best_model, 'feature_importances_'):
    print(f"\n  What drives predictions:")
    imp = sorted(
        zip(FEATURES, best_model.feature_importances_),
        key=lambda x: -x[1]
    )
    for feat, score in imp:
        bar = "█" * int(score * 50)
        print(f"    {feat:<16}  {score:.3f}  {bar}")


# ════════════════════════════════════════════════════════
# PART 6 — PREDICT NEXT YEAR
# ════════════════════════════════════════════════════════
next_year = max_year + 1
print(f"\n{SEP}")
print(f"  PART 6 — Predicting {next_year} Crime Hotspots")
print(f"{SEP}\n")

# Build pivot: district × crime → last 2 years of actuals
recent = df_model[df_model['Year'] >= max_year - 1].copy()
pivot  = recent.pivot_table(
    index=['District','Crime_Type'],
    columns='Year',
    values='Total',
    aggfunc='sum'
)

predictions = []

for district in sorted(df_model['District'].unique()):
    for crime in sorted(df_model['Crime_Type'].unique()):

        # Lag1 = most recent year actual (required)
        try:
            lag1 = pivot.loc[(district, crime), max_year]
            if pd.isna(lag1):
                continue
            lag1 = float(lag1)
        except (KeyError, TypeError):
            continue

        # Lag2 = year before (use lag1 if missing)
        try:
            lag2 = pivot.loc[(district, crime), max_year - 1]
            lag2 = float(lag2) if not pd.isna(lag2) else lag1
        except (KeyError, TypeError):
            lag2 = lag1

        # Rolling mean from last 3 years of history
        hist = df_model[
            (df_model['District']   == district) &
            (df_model['Crime_Type'] == crime)
        ].sort_values('Year')['Total'].tail(3)
        roll = float(hist.mean()) if len(hist) > 0 else lag1

        # Encode labels — skip if unseen label
        try:
            d_enc = int(le_dist.transform([district])[0])
            c_enc = int(le_crime.transform([crime])[0])
        except ValueError:
            continue

        row = pd.DataFrame([[
            d_enc, c_enc,
            next_year - min_year,
            lag1, lag2, roll
        ]], columns=FEATURES)

        pred    = max(0, int(round(float(best_model.predict(row)[0]))))
        chg_pct = round(((pred - lag1) / lag1 * 100) if lag1 > 0 else 0, 1)

        predictions.append({
            'District':                district,
            'Crime_Type':              crime,
            f'Actual_{max_year}':      int(lag1),
            f'Predicted_{next_year}':  pred,
            'Change_cases':            pred - int(lag1),
            'Change_pct':              chg_pct
        })

pred_df = pd.DataFrame(predictions)
print(f"  Predictions made: {len(pred_df):,}\n")

# ── Results ──────────────────────────────────────────────
print(f"  TOP 10 DISTRICTS — Highest predicted crime {next_year}")
print(THIN)
top_p = pred_df.groupby('District')[f'Predicted_{next_year}'].sum() \
               .sort_values(ascending=False)
for i,(d,v) in enumerate(top_p.head(10).items(), 1):
    bar = "█" * int((v / top_p.iloc[0]) * 28)
    print(f"  {i:>2}. {d:<30}  {v:>7,}  {bar}")

print(f"\n  CRIME TYPE TRENDS — {next_year} predictions")
print(THIN)
ct = pred_df.groupby('Crime_Type').agg(
    Total_Pred=(f'Predicted_{next_year}', 'sum'),
    Avg_Change=('Change_pct', 'mean')
).sort_values('Avg_Change', ascending=False)
for crime, row in ct.iterrows():
    arrow = "▲" if row['Avg_Change'] > 0 else "▼"
    print(f"  {arrow} {crime:<32} {row['Avg_Change']:>+6.1f}%"
          f"   total: {int(row['Total_Pred']):,}")

# ── Save outputs ─────────────────────────────────────────
pred_path = f"{OUTPUT_DIR}/predictions_{next_year}.csv"
pred_df.to_csv(pred_path, index=False)

meta = {
    'best_model':     best_name,
    'RMSE':           round(best_rmse, 2),
    'R2':             all_results[best_name]['R2'],
    'MAE':            all_results[best_name]['MAE'],
    'train_rows':     int(len(X_train)),
    'test_rows':      int(len(X_test)),
    'districts':      int(df_model['District'].nunique()),
    'crime_types':    list(df_model['Crime_Type'].unique()),
    'years_trained':  sorted([int(y) for y in df_model['Year'].unique()]),
    'prediction_year':int(next_year),
    'all_models':     all_results
}
with open(f"{MODEL_DIR}/metrics.json", "w") as f:
    json.dump(meta, f, indent=2)


# ════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  ALL DONE")
print(SEP)
ncrb_d  = ncrb_master['District'].nunique()   if len(ncrb_master)   > 0 else 0
kag_d   = kaggle_master['District'].nunique() if len(kaggle_master) > 0 else 0
print(f"""
  DATA
    NCRB districts   : {ncrb_d}  (all years combined)
    Kaggle districts : {kag_d}
    Total rows       : {len(all_data):,}
    Years covered    : {sorted(all_data['Year'].unique())}
    Crime types      : {all_data['Crime_Type'].nunique()}

  MODEL
    Best model : {best_name}
    RMSE       : {best_rmse:.1f}  cases avg error
    R²         : {all_results[best_name]['R2']}
    MAE        : {all_results[best_name]['MAE']}

  FILES SAVED
    data/cleaned/ncrb_UP_all_years.csv
    data/cleaned/kaggle_UP.csv
    data/cleaned/master_UP_crime.csv
    data/cleaned/predictions_{next_year}.csv
    data/model/metrics.json

  YOUR RESUME LINE
    Trained {best_name} on NCRB + Kaggle UP Police crime data
    ({all_data['District'].nunique()} districts | {all_data['Crime_Type'].nunique()} crime types | {len(sorted(all_data['Year'].unique()))} years)
    RMSE = {best_rmse:.0f} | R² = {all_results[best_name]['R2']}
    Predicts next-year district-level crime hotspots for UP Police

  NEXT STEP
    Run: python3 scripts/03_map_dashboard.py
    Opens interactive UP crime hotspot map in your browser
""")