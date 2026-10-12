"""Build the plot-level modelling dataset from NISR SAS 2024 microdata (.sav).
Run from the project root (PowerShell):   python ml/preprocessing/build_microdata.py
Reads  : data/raw/Season A|B|C/*.sav     (private - never commit, never publish)
Writes : data/processed/plots_clean.csv   (one row per crop on a plot with a valid yield; private)
         data/processed/cleaning_log.txt  (every cleaning step with counts + validation vs published NISR yields)
         data/processed/crop_codes.csv    (crop code -> label -> app crop group, for review)
Design (from the data dictionary): Production = one row per farmer x plot x crop, with harvest and input answers.
Screening = one row per plot x crop with crop_area (ha). Yield = harvest (kg) / crop area (ha), as defined in the SAS report.
Harvest, sales, storage and loss variables are NEVER copied into the feature columns (data-leakage rule)."""
import json, os, re, sys
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW, OUT = os.path.join(ROOT, "data/raw"), os.path.join(ROOT, "data/processed")
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s)

# ---------- crop grouping (keyword rules on the SPSS value labels; reviewed via crop_codes.csv) ----------
RULES = [("Maize", ["maize"]), ("Sorghum", ["sorghum"]), ("Paddy rice", ["rice"]), ("Wheat", ["wheat"]), ("Cassava", ["cassava"]),
         ("Sweet potato", ["sweet potato"]), ("Irish potato", ["irish"]), ("Yams & Taro", ["yam", "taro", "colocas"]),
         ("Banana", ["banana"]), ("Soybean", ["soy", "soya"]), ("Groundnuts", ["groundnut", "peanut"]), ("Bean", ["bean"]), ("Pea", [" pea", "peas"]),
         ("Vegetables", ["cabbage", "tomato", "carrot", "onion", "eggplant", "pepper", "amaranth", "spinach", "cucumber", "pumpkin", "beet", "cauliflower",
                         "leek", "celery", "lettuce", "vegetable", "brocolli", "broccoli", "garlic"]),
         ("Fruits", ["avocado", "mango", "orange", "pineapple", "passion", "papaya", "apple", "fruit", "lemon", "guava", "water melon", "strawberry", "mandoline"])]
def crop_group(label):
    l = " " + str(label).lower()
    if "fodder" in l or "lemongrass" in l: return "Other"      # fodder crops and lemongrass are not the food crops of the same name
    if "tree tomato" in l: return "Fruits"                      # tree tomato is a fruit, not a vegetable
    for g, keys in RULES:
        if any(k in l for k in keys): return g
    return "Other"

def yes(s):  # SAS coding: 1 = Yes, 2 = No
    return s.map({1.0: 1.0, 2.0: 0.0})

def clean_name(v):  # "Nyarugenge" or "11 Nyarugenge" -> "Nyarugenge"
    if pd.isna(v): return np.nan
    return re.sub(r"^[\d\s\-\.:]+", "", str(v)).strip().title()

def load(path):
    import pyreadstat
    df, meta = pyreadstat.read_sav(path)
    return df, meta.variable_value_labels

def read_season(season):
    d = os.path.join(RAW, f"Season {season}")
    pick = lambda key: next(os.path.join(d, f) for f in sorted(os.listdir(d)) if key in f and f.lower().endswith(".sav"))
    (P, vlP), (S, _), (FT, _) = load(pick("Production")), load(pick("Screening")), load(pick("fertilizer"))
    return P, vlP, S, FT

def build_season(P, vl, S, season, FT=None):
    n0 = len(P); log(f"\n=== Season {season}: production rows {n0}, screening rows {len(S)}")
    P = P.copy(); S = S.copy()
    for c in ["s1q1","s1q2","s1q3","s1q7","s2q7","s2q9","s2q11","s2q21","s2q22","s3q1","s3q3","s3q7","s3q9","s3q16","s3q17","s3q18","s3q19","s4q1","s4q2","s4q3",
              "s4q6","s4q8","s4q9","s4q10_1","s4q11_1","s4q14","s4q15","s2q2","plot_weight"]:
        if c not in P.columns: P[c] = np.nan; log(f"WARNING: production column {c} missing in season {season}")
    for c in ["Plot_size_ha", "s2q13", "s3q2_1"]:
        if c not in S.columns: S[c] = np.nan; log(f"WARNING: screening column {c} missing in season {season}")
    # --- keys: Production (Segment_ID, s1q6 farmer, s2q1 plot, s2q4 crop) <-> Screening (Segment_ID, s1q5_2, s2q1, s3q1)
    S = S.drop(columns=["s2q4"], errors="ignore")      # Screening already has its own s2q4 (grid list text): drop it before renaming s3q1
    S = S.rename(columns={"s1q5_2": "s1q6", "s3q1": "s2q4"})
    key = ["Segment_ID", "s1q6", "s2q1", "s2q4"]
    calc = S.Plot_size_ha * S.s3q2_1 / 100          # crop area implied by plot size x crop proportion
    if "crop_area" in S.columns:
        r = (S.crop_area / calc).replace([np.inf, -np.inf], np.nan).dropna()
        log(f"check: crop_area / (plot size x crop share) median ratio = {r.median():.3f} (1.0 means the formula matches)")
    else:
        S["crop_area"] = calc; log("crop_area column absent in this season: computed as Plot_size_ha x crop proportion / 100")
    S = S.dropna(subset=["crop_area"] + key)
    dupS = S.duplicated(key, keep=False).sum(); log(f"screening rows sharing a join key (kept first): {dupS}")
    S = S.drop_duplicates(key)
    dupP = P.duplicated(key, keep=False).sum(); log(f"production rows sharing a join key (kept first): {dupP}")
    P = P.drop_duplicates(key)
    scols = key + ["crop_area", "Plot_size_ha", "s2q13", "s3q2_1"]
    M = P.merge(S[scols], on=key, how="left", validate="one_to_one")
    log(f"matched to screening (crop_area available): {M.crop_area.notna().sum()} of {len(M)} ({M.crop_area.notna().mean()*100:.1f}%)")
    # --- crop area fallback: where Screening has no crop_area for this crop (mostly Season B), split the plot area equally among the crops on the plot
    M["plot_ha_prod"] = M.s2q2 / 10000
    M["area_equal"] = M.plot_ha_prod / M.groupby(["Segment_ID", "s1q6", "s2q1"])["s2q4"].transform("size")
    meas = M[M.crop_area.notna() & (M.crop_area > 0)]
    r = (meas.area_equal / meas.crop_area).replace([np.inf, -np.inf], np.nan).dropna()
    log(f"fallback quality on rows WITH measured area: median(equal-split / measured) = {r.median():.2f}; within a factor of 2: {((r > .5) & (r < 2)).mean()*100:.0f}%")
    M["area_source"] = np.where(M.crop_area.notna(), "measured", "equal_split")
    M["crop_area_final"] = M.crop_area.fillna(M.area_equal)
    log(f"rows using equal-split area: {(M.area_source == 'equal_split').sum()} of {len(M)}")
    # --- inorganic fertilizer rate (kg/ha) from the fertilizer table: quantity used on the plot / plot area. kg or g only; implausible (>1000 kg/ha) -> unknown
    M["fert_kg_ha"] = np.nan
    if FT is not None:
        fk = ["Segment_ID", "s1q6", "s2q1"]; FT = FT.drop_duplicates(fk).copy()
        for c in ["s3q11", "s3q12"]:
            if c not in FT.columns: FT[c] = np.nan
        FT["fert_kg"] = FT["s3q12"].where(FT["s3q11"] == 1.0, FT["s3q12"] / 1000.0).where(FT["s3q11"].isin([1.0, 2.0]))
        M = M.merge(FT[fk + ["fert_kg"]], on=fk, how="left"); kgha = M["fert_kg"] / M["plot_ha_prod"]
        M["fert_kg_ha"] = kgha.where((kgha > 0) & (kgha <= 1000))
    # --- harvest: s2q21 = total harvest this season (kg); NaN = not yet harvested (expected period 'other season')
    M["harvest_kg"] = M["s2q21"]
    log(f"rows with no harvest value (not yet harvested): {M.harvest_kg.isna().sum()}")
    # --- features known before harvest only
    F = pd.DataFrame({"season": season, "Segment_ID": M.Segment_ID, "plot_weight": M.plot_weight})
    F["province"] = M.s1q1.map(vl.get("s1q1", {})).map(clean_name)
    F["district"] = M.s1q2.map(vl.get("s1q2", {})).map(clean_name)
    F["stratum"] = M.s1q3.map(vl.get("s1q3", {}))
    F["farmer_type"] = M.s1q7.map(vl.get("s1q7", {}))
    F["crop_code"] = M.s2q4
    F["crop_label"] = M.s2q4.map(vl.get("s2q4", {}))
    F["crop"] = F.crop_label.map(crop_group)
    F["plot_area_ha"] = M.Plot_size_ha.fillna(M.plot_ha_prod); F["crop_area_ha"] = M.crop_area_final; F["area_source"] = M.area_source; F["crop_share_pct"] = M.s3q2_1
    F["cropping_system"] = M.s2q13.map({1.0: "Pure", 2.0: "Inter-cropping", 3.0: "Traditional mixed"})
    F["sowing_period_code"] = M.s2q7
    F["improved_seed"] = M.s2q11.map({1.0: 0.0, 2.0: 1.0, 3.0: 1.0})
    # plot-level answers are blank when the farm-level gate question was "No" (counts match exactly in the data) -> 0
    gate = lambda plot, g: yes(M[plot]).where(M[g] != 2.0, 0.0)
    F["organic_fert"] = gate("s3q3", "s3q1"); F["inorganic_fert"] = gate("s3q9", "s3q7")
    F["micronutrient"] = gate("s3q17", "s3q16"); F["pesticide"] = gate("s3q19", "s3q18")
    F["anti_erosion"] = gate("s4q3", "s4q2"); F["mechanized"] = gate("s4q9", "s4q8"); F["irrigated"] = gate("s4q15", "s4q14")
    F["oxen"] = yes(M.s4q10_1).fillna(0.0); F["tractor"] = yes(M.s4q11_1).fillna(0.0)
    F["consolidated_land"] = yes(M.s4q6)
    F["erosion_degree"] = M.s4q1.map({1.0: "Severe", 2.0: "Moderate", 3.0: "Low", 4.0: "Very low"})
    F["fert_kg_ha"] = M.fert_kg_ha.where(F.inorganic_fert != 0, 0.0)             # 0 where no inorganic fertilizer was used
    used = F.inorganic_fert == 1
    log(f"inorganic fertilizer plots: {int(used.sum())}; with a usable kg/ha value: {int((used & F.fert_kg_ha.notna()).sum())}; median kg/ha where known: {F.fert_kg_ha[used].median():.0f}")
    F["harvest_kg"] = M.harvest_kg                      # target numerator ONLY - never a feature
    F["harvest_alt_s2q22"] = M.s2q22                    # kept to test which harvest variable matches NISR totals
    return F

def clean(F):
    n = len(F); log(f"\nCLEANING all seasons: {n} rows")
    F = F[F.harvest_kg.notna() & (F.harvest_kg > 0)]; log(f"  keep harvest > 0:            {len(F)}")
    F = F[F.crop_area_ha.notna() & (F.crop_area_ha > 0)]; log(f"  keep crop area > 0:          {len(F)}")
    F = F.assign(yield_kg_ha=F.harvest_kg / F.crop_area_ha)
    ly = np.log(F.yield_kg_ha)  # outliers: robust rule within crop x season on log yield (median +/- 4 MAD); logged, not silent
    g = ly.groupby([F.crop, F.season])
    med, mad = g.transform("median"), (ly - g.transform("median")).abs().groupby([F.crop, F.season]).transform("median")
    ok = (ly - med).abs() <= 4 * 1.4826 * mad.replace(0, np.nan).fillna(ly.std())
    log(f"  drop yield outliers (4 MAD on log yield within crop x season): {(~ok).sum()}")
    F = F[ok]; log(f"  final modelling rows:        {len(F)}")
    return F

def validate(F, published):
    log("\nVALIDATION: survey-weighted yield (kg/ha). 'measured' = rows with a real crop area; 'all' = measured + equal-split rows")
    log("crop | season | measured | all | published | rows measured/all")
    for (crop, s), d in F[F.crop != "Other"].groupby(["crop", "season"]):
        wy = lambda x: (x.plot_weight * x.harvest_kg).sum() / (x.plot_weight * x.crop_area_ha).sum() if len(x) else float("nan")
        m = d[d.area_source == "measured"]; pub = published.get((crop, s))
        log(f"{crop} | {s} | {wy(m):,.0f} | {wy(d):,.0f} | {pub if pub else 'n/a'} | {len(m)}/{len(d)}")

def main():
    os.makedirs(OUT, exist_ok=True); frames, codes = [], {}
    for s in "ABC":
        P, vl, S, FT = read_season(s); F = build_season(P, vl, S, s, FT); frames.append(F)
        for c, l in F[["crop_code", "crop_label"]].drop_duplicates().itertuples(index=False): codes[(c, l)] = crop_group(l)
    F = clean(pd.concat(frames, ignore_index=True))
    agg = json.load(open(os.path.join(OUT, "aggregates.json")))["rows"]
    df = pd.DataFrame(agg).groupby(["crop", "season"])[["production_mt", "harvested_ha"]].sum()
    pub = {k: round(r.production_mt * 1000 / r.harvested_ha) for k, r in df.iterrows() if r.harvested_ha > 0}
    validate(F, pub)
    F.drop(columns=["harvest_alt_s2q22"]).to_csv(os.path.join(OUT, "plots_clean.csv"), index=False)
    pd.DataFrame([(c, l, g) for (c, l), g in sorted(codes.items(), key=lambda x: str(x[0]))], columns=["code", "label", "group"]).to_csv(os.path.join(OUT, "crop_codes.csv"), index=False)
    open(os.path.join(OUT, "cleaning_log.txt"), "w", encoding="utf-8").write("\n".join(LOG))
    log("\nWrote plots_clean.csv, crop_codes.csv, cleaning_log.txt in data/processed/")

if __name__ == "__main__": main()
