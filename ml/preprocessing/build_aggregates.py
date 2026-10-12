"""Build data/processed/aggregates.json from NISR 'SAS 2024 Annual Tables' (published district tables).
Usage: python ml/preprocessing/build_aggregates.py [path/to/SAS_2024_Annual_Tables.xlsx]
Needs: pip install openpyxl.  Every number is read from the NISR workbook; nothing is estimated or invented."""
import json, os, sys, openpyxl
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
XLSX = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/raw/SAS_2024_Annual_Tables.xlsx")
wb = openpyxl.load_workbook(XLSX, data_only=True)
PROV = {}
for p, ds in {"Kigali City": "Nyarugenge Gasabo Kicukiro", "Southern": "Nyanza Gisagara Nyaruguru Huye Nyamagabe Ruhango Muhanga Kamonyi",
              "Western": "Karongi Rutsiro Rubavu Nyabihu Ngororero Rusizi Nyamasheke", "Northern": "Rulindo Gakenke Musanze Burera Gicumbi",
              "Eastern": "Rwamagana Nyagatare Gatsibo Kayonza Kirehe Ngoma Bugesera"}.items():
    for d in ds.split(): PROV[d] = p
CROP = {"maize": "Maize", "sorghum": "Sorghum", "paddy rice": "Paddy rice", "wheat": "Wheat", "cassava": "Cassava", "sweet potato": "Sweet potato",
        "sweet potatoes": "Sweet potato", "irish potato": "Irish potato", "irish potatoes": "Irish potato", "yams & taro": "Yams & Taro",
        "banana": "Banana", "bananas": "Banana", "bean": "Bean", "beans": "Bean", "pea": "Pea", "peas": "Pea", "groundnut": "Groundnuts",
        "groundnuts": "Groundnuts", "soybean": "Soybean", "soya beans": "Soybean", "vegetables": "Vegetables", "fruits": "Fruits"}
num = lambda v: float(v) if isinstance(v, (int, float)) else None

def crop_table(name):
    """{district: {crop: value}} for a district x crop sheet (header row found automatically)."""
    rows = list(wb[name].iter_rows(values_only=True)); hdr = None
    for i, r in enumerate(rows):
        m = {}
        for j, c in enumerate(r):
            k = CROP.get(str(c).strip().lower()) if c else None
            if k and k not in m.values(): m[j] = k
        if len(m) >= 5: hdr = m; break
    if not hdr: raise SystemExit(f"No crop header in {name}")
    out = {}
    for r in rows:
        d = str(r[1]).strip() if len(r) > 1 and r[1] else ""
        if d in PROV: out[d] = {k: num(r[j]) for j, k in hdr.items() if j < len(r)}
    return out

def dist_table(name):
    """{district: [values from column C onward]} for % tables."""
    out = {}
    for r in wb[name].iter_rows(values_only=True):
        d = str(r[1]).strip() if len(r) > 1 and r[1] else ""
        if d in PROV: out[d] = [num(x) for x in r[2:]]
    return out

SEASONS = {"A": dict(cult="Table 10", harv="Table 13", yld="Table 16", prod="Table 21"),
           "B": dict(cult="Table 11", harv="Table 14", yld="Table 17", prod="Table 22"),
           "C": dict(cult="Table 12", harv="Table 15", yld="Table 18", prod="Table 23")}
rows = []
for s, t in SEASONS.items():
    T = {k: crop_table(v) for k, v in t.items()}
    for d in PROV:
        for crop in sorted({c for k in T for c in T[k].get(d, {})}):
            g = lambda k: (T[k].get(d, {}).get(crop) or 0)
            cult, harv, prod, y = g("cult"), g("harv"), g("prod"), g("yld")
            if cult > 0 or harv > 0 or prod > 0:
                rows.append(dict(district=d, province=PROV[d], crop=crop, season=s, cultivated_ha=round(cult, 2), harvested_ha=round(harv, 2),
                                 production_mt=round(prod, 2), yield_kg_ha=round(y, 1) if y else None))

def pick(tbl, i): return {d: v[i] if i < len(v) else None for d, v in dist_table(tbl).items()}
SRC = {"improved_seed_pct": ("Table 30", "Table 31", "Table 32", 0, 0, 0), "organic_fertilizer_pct": ("Table 40", "Table 41", "Table 42", 0, 0, 0),
       "inorganic_fertilizer_pct": ("Table 43", "Table 44", "Table 45", 0, 0, 0), "pesticide_pct": ("Table 55", "Table 56", "Table 57", 0, 0, 0),
       "erosion_protection_pct": ("Table 61", "Table 62", "Table 63", 0, 0, 0), "mechanization_pct": ("Table 61", "Table 62", "Table 63", 3, 3, 1),
       "irrigation_pct": ("Table 61", "Table 62", "Table 63", 6, 6, 2)}
EROS = {"erosion_severe_pct": 0, "erosion_moderate_pct": 1, "erosion_low_pct": 2, "erosion_very_low_pct": 3}
inputs = []
for si, s in enumerate("ABC"):
    cols = {k: pick(v[si], v[3 + si]) for k, v in SRC.items()}
    ero = {k: pick(["Table 73", "Table 74", "Table 75"][si], i) for k, i in EROS.items()}
    for d in PROV:
        rec = {"district": d, "season": s}
        rec.update({k: cols[k].get(d) for k in cols}); rec.update({k: ero[k].get(d) for k in ero}); inputs.append(rec)

# ---- validation against the national summary (Table 0) ----
def nat(s, crop, f): return sum(r[f] for r in rows if r["season"] == s and r["crop"] == crop)
print("CHECK national totals from district rows vs published Table 0:")
for s, crop, pub_area in [("A", "Maize", 249435), ("B", "Maize", 92944), ("A", "Bean", 329001), ("A", "Cassava", 251019)]:
    print(f"  {crop} season {s}: cultivated ha {nat(s, crop, 'cultivated_ha'):,.0f} (published {pub_area:,})")
for s, crop, pub in [("A", "Maize", 507985), ("A", "Cassava", 518044), ("B", "Banana", 1142552)]:
    print(f"  {crop} season {s}: production t {nat(s, crop, 'production_mt'):,.0f} (published {pub:,})")
out = {"source": "NISR Seasonal Agricultural Survey 2024 - Annual Tables (district tables 10-23, 30-32, 40-45, 55-57, 61-63, 73-75)",
       "yield_definition": "yield = production / harvested area (NISR: production in kg divided by crop area in ha); official district yields from Tables 16-18",
       "rows": rows, "inputs": inputs}
os.makedirs(os.path.join(ROOT, "data/processed"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "data/processed/aggregates.json"), "w"), separators=(",", ":"))
print(f"Wrote {len(rows)} district-crop-season rows and {len(inputs)} district-season input rows.")
