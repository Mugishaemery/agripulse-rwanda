"""Train and compare Linear Regression, Random Forest and Gradient Boosting for crop-yield prediction.
Run from the project root:  python ml/models/train_models.py          (needs only numpy + pandas; no scikit-learn / SciPy)
Why numpy-only: some Windows machines block SciPy's compiled files (Application Control). The three algorithms are implemented here directly
(histogram-style regression trees, squared-error boosting, bagged forest, least squares) and were checked against scikit-learn on test data.
Input : data/processed/plots_clean.csv   (made by ml/preprocessing/build_microdata.py; private)
Output: ml/models/model.json    best model exported for the Node server (no individual records inside)
        ml/models/metrics.json  MAE / RMSE / R2 of every model on held-out data + permutation feature importance
Method: target = log(yield kg/ha); features = pre-harvest characteristics only (no harvest, sales, storage or loss variables).
        Hold-out split is by survey SEGMENT (Segment_ID), so plots from one segment never appear in both train and test."""
import json, os, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CSV = os.path.join(ROOT, "data/processed/plots_clean.csv")
CROPS = ["Maize", "Bean", "Sorghum", "Irish potato", "Sweet potato", "Soybean", "Pea", "Wheat", "Groundnuts", "Vegetables", "Paddy rice", "Yams & Taro"]
CAT = ["district", "crop", "season", "erosion_degree", "cropping_system", "fert_rate_band"]
BIN = ["improved_seed", "inorganic_fert", "organic_fert", "pesticide", "anti_erosion", "irrigated", "mechanized", "consolidated_land"]
NUM = "log_area_ha"
LABEL = {"district": "District", "crop": "Crop", "season": "Season", "erosion_degree": "Erosion degree", "cropping_system": "Cropping system", "fert_rate_band": "Inorganic fertilizer rate", "improved_seed": "Improved seed", "inorganic_fert": "Inorganic fertilizer",
         "organic_fert": "Organic fertilizer", "pesticide": "Pesticide/fungicide", "anti_erosion": "Anti-erosion measures", "irrigated": "Irrigation", "mechanized": "Mechanization",
         "consolidated_land": "Land consolidation site", "log_area_ha": "Area under the crop"}

# ---------------------------------------------------------------- data
def prepare(df):
    df = df[df.crop.isin(CROPS)].copy()
    df["mechanized"] = df[["mechanized", "oxen", "tractor"]].max(axis=1)      # any mechanical or animal traction
    df[NUM] = np.log(df.crop_area_ha)
    df["cropping_system"] = df.cropping_system.fillna("Unknown")
    kg = df.fert_kg_ha                                                             # inorganic fertilizer rate band (kg/ha); 0 = none used
    df["fert_rate_band"] = np.select([df.inorganic_fert == 0, kg.isna(), kg <= 50, kg <= 100, kg <= 200], ["None", "Used (amount unknown)", "Up to 50 kg/ha", "51-100 kg/ha", "101-200 kg/ha"], "Over 200 kg/ha")
    n = len(df); df = df.dropna(subset=CAT + BIN + [NUM, "yield_kg_ha"])
    print(f"  rows in scope: {n}; dropped for missing feature values: {n - len(df)}; kept: {len(df)}")
    return df.reset_index(drop=True)

def design(df):
    """Feature matrix: one-hot columns 'district=Musanze', ..., then yes/no columns, then log area (last)."""
    names, cols = [], []
    for c in CAT:
        for v in sorted(df[c].unique()): names.append(f"{c}={v}"); cols.append((df[c] == v).to_numpy(float))
    for b in BIN: names.append(b); cols.append(df[b].to_numpy(float))
    names.append(NUM); cols.append(df[NUM].to_numpy(float))
    return np.column_stack(cols), names

# ---------------------------------------------------------------- trees
class Ctx:
    """Holds the training matrix once: yes/no columns for fast matrix-product split search, and the log-area column binned into <=32 bins."""
    def __init__(self, X, rng):
        self.X, self.rng, self.n, self.p = X, rng, X.shape[0], X.shape[1]
        self.bi = np.arange(self.p - 1); self.ci = self.p - 1
        self.Xb = X[:, self.bi].astype(np.float32)
        q = np.unique(np.quantile(X[:, self.ci], np.linspace(0, 1, 33)[1:-1]))
        self.edges = q; self.codes = np.searchsorted(q, X[:, self.ci], side="left"); self.nb = len(q) + 1

def best_split(c, rows, y, min_leaf, feat_frac):
    yr = y[rows]; n = len(rows); S = yr.sum(); base = S * S / n
    s1 = yr.astype(np.float32) @ c.Xb[rows]; c1 = c.Xb[rows].sum(0)          # sums / counts where the yes/no column is 1
    nR, sR = c1.astype(float), s1.astype(float); nL, sL = n - nR, S - sR
    ok = (nL >= min_leaf) & (nR >= min_leaf)
    with np.errstate(divide="ignore", invalid="ignore"): g_bin = np.where(ok, sL * sL / nL + sR * sR / nR - base, -np.inf)
    cc = c.codes[rows]; bc = np.bincount(cc, minlength=c.nb).cumsum()[:-1].astype(float); bs = np.bincount(cc, weights=yr, minlength=c.nb).cumsum()[:-1]
    ok2 = (bc >= min_leaf) & (n - bc >= min_leaf)
    with np.errstate(divide="ignore", invalid="ignore"): g_num = np.where(ok2, bs * bs / bc + (S - bs) ** 2 / (n - bc) - base, -np.inf)
    if feat_frac < 1.0:                                                       # random forest: only a random share of features may split here
        k = max(1, int(feat_frac * (len(g_bin) + 1))); allowed = np.zeros(len(g_bin) + 1, bool); allowed[c.rng.choice(len(g_bin) + 1, k, replace=False)] = True
        g_bin = np.where(allowed[:-1], g_bin, -np.inf); g_num = np.where(allowed[-1], g_num, -np.inf)
    jb, jn = int(np.argmax(g_bin)), int(np.argmax(g_num)) if len(g_num) else 0
    if max(g_bin[jb], g_num[jn] if len(g_num) else -np.inf) <= 1e-9: return None
    return (int(c.bi[jb]), 0.5) if g_bin[jb] >= (g_num[jn] if len(g_num) else -np.inf) else (c.ci, float(c.edges[jn]))

def grow(c, rows, y, max_depth, min_leaf, feat_frac=1.0):
    T = {"f": [], "t": [], "l": [], "r": [], "v": []}
    def node(rs, d):
        i = len(T["f"]); T["f"].append(-1); T["t"].append(0.0); T["l"].append(-1); T["r"].append(-1); T["v"].append(float(y[rs].mean()))
        if d >= max_depth or len(rs) < 2 * min_leaf: return i
        sp = best_split(c, rs, y, min_leaf, feat_frac)
        if sp is None: return i
        j, t = sp; left = c.X[rs, j] <= t; T["f"][i], T["t"][i] = j, t
        T["l"][i] = node(rs[left], d + 1); T["r"][i] = node(rs[~left], d + 1)
        return i
    node(rows, 0); return {k: np.array(v) for k, v in T.items()}

def tree_predict(T, X):
    node = np.zeros(len(X), int); ar = np.arange(len(X))
    while True:
        f = T["f"][node]; inner = f >= 0
        if not inner.any(): return T["v"][node]
        go = X[ar, np.where(inner, f, 0)] <= T["t"][node]
        node = np.where(inner, np.where(go, T["l"][node], T["r"][node]), node)

# ---------------------------------------------------------------- models
def fit_linear(X, y):
    A = np.column_stack([np.ones(len(X)), X]); w = np.linalg.lstsq(A, y, rcond=None)[0]
    return {"kind": "linear", "intercept": float(w[0]), "coef": w[1:]}

def fit_forest(X, y, seed=42, n_trees=100):
    rng = np.random.default_rng(seed); c = Ctx(X, rng)
    return {"kind": "rf", "init": 0.0, "scale": 1.0 / n_trees, "trees": [grow(c, rng.integers(0, c.n, c.n), y, 14, 15, 0.5) for _ in range(n_trees)]}

def fit_boost(X, y, seed=42, n_trees=300, lr=0.05, depth=4, min_leaf=20, subsample=0.8):
    rng = np.random.default_rng(seed); c = Ctx(X, rng); init = float(y.mean()); pred = np.full(len(y), init); trees = []
    for _ in range(n_trees):
        rows = rng.choice(c.n, int(subsample * c.n), replace=False); T = grow(c, rows, y - pred, depth, min_leaf)
        trees.append(T); pred += lr * tree_predict(T, X)
    return {"kind": "gbm", "init": init, "scale": lr, "trees": trees}

def predict(m, X):
    if m["kind"] == "linear": return m["intercept"] + X @ m["coef"]
    return m["init"] + m["scale"] * sum(tree_predict(T, X) for T in m["trees"])

def metrics(ylog, plog):
    y, p = np.exp(ylog), np.exp(plog); r2 = lambda a, b: 1 - ((a - b) ** 2).sum() / ((a - a.mean()) ** 2).sum()
    return {"mae": round(float(np.abs(y - p).mean()), 1), "rmse": round(float(np.sqrt(((y - p) ** 2).mean())), 1), "mdape": round(float(np.median(np.abs(p - y) / y) * 100), 1), "r2": round(float(r2(y, p)), 3), "r2_log": round(float(r2(ylog, plog)), 3)}

def run(df, label):
    print(f"\n=== {label}"); t0 = time.time()
    df = prepare(df); X, names = design(df); y = np.log(df.yield_kg_ha.to_numpy())
    rng = np.random.default_rng(42); segs = df.Segment_ID.unique(); test_segs = set(rng.choice(segs, int(0.2 * len(segs)), replace=False))
    te = df.Segment_ID.isin(test_segs).to_numpy(); tr = ~te
    print(f"  train {tr.sum()} rows / test {te.sum()} rows (split by survey segment)")
    base = df[tr].groupby(["crop", "season"]).yield_kg_ha.median(); med = df[tr].yield_kg_ha.median()
    bp = np.log(np.array([base.get((a, b), med) for a, b in zip(df.crop[te], df.season[te])]))
    out = {"Baseline (crop x season median)": metrics(y[te], bp)}; fitted = {}
    for name, fn in [("Linear Regression", fit_linear), ("Random Forest", fit_forest), ("Gradient Boosting", fit_boost),
                     ("Gradient Boosting (regularized)", lambda X, y: fit_boost(X, y, n_trees=400, lr=0.03, depth=3, min_leaf=100, subsample=0.7))]:
        fitted[name] = fn(X[tr], y[tr]); out[name] = metrics(y[te], predict(fitted[name], X[te])); print(f"  fitted {name} ({time.time() - t0:.0f}s)")
    for k, v in out.items(): print(f"  {k:34s} MAE {v['mae']:>8} RMSE {v['rmse']:>8} MdAPE {v['mdape']:>5}% R2 {v['r2']:>6} R2(log) {v['r2_log']:>6}")
    return dict(bp=bp, df=df, X=X, y=y, te=te, names=names, metrics=out, fitted=fitted, n_train=int(tr.sum()), n_test=int(te.sum()))

def permutation_importance(m, X, y, names, repeats=5, seed=0):
    rng = np.random.default_rng(seed); r2 = lambda a, b: 1 - ((a - b) ** 2).sum() / ((a - a.mean()) ** 2).sum(); base = r2(y, predict(m, X)); res = []
    for f in CAT + BIN + [NUM]:
        cols = [i for i, n in enumerate(names) if (n.startswith(f + "=") if f in CAT else n == f)]; sc = []
        for _ in range(repeats):
            Xp = X.copy(); Xp[:, cols] = X[rng.permutation(len(X))][:, cols]; sc.append(r2(y, predict(m, Xp)))
        res.append({"feature": f, "label": LABEL[f], "importance": round(float(base - np.mean(sc)), 4)})
    return sorted(res, key=lambda x: -x["importance"])

def export(m, names, resid):
    r5 = lambda a: [round(float(x), 5) for x in a]; base = {"features": names, "log_target": True, "resid_q10": resid[0], "resid_q90": resid[1], "kind": m["kind"]}
    if m["kind"] == "linear": return {**base, "intercept": m["intercept"], "coef": r5(m["coef"])}
    T = [{"f": [int(x) for x in t["f"]], "t": r5(t["t"]), "l": [int(x) for x in t["l"]], "r": [int(x) for x in t["r"]], "v": r5(t["v"])} for t in m["trees"]]
    return {**base, "init": m["init"], "scale": m["scale"], "trees": T}

def main():
    if not os.path.exists(CSV): sys.exit("Run ml/preprocessing/build_microdata.py first.")
    df = pd.read_csv(CSV); print("rows in plots_clean.csv:", len(df))
    P = run(df[df.area_source == "measured"], "PRIMARY: plots with a measured crop area")
    S = run(df, "SENSITIVITY: all plots incl. equal-split crop areas")
    best = max(P["fitted"], key=lambda k: P["metrics"][k]["r2_log"]); print(f"\nBest model (highest log-scale R2 on held-out data; raw-scale RMSE is dominated by a few extreme plots): {best}")
    m = P["fitted"][best]; Xte, yte = P["X"][P["te"]], P["y"][P["te"]]; res = yte - predict(m, Xte)
    resid = [round(float(np.quantile(res, .1)), 4), round(float(np.quantile(res, .9)), 4)]
    fi = permutation_importance(m, Xte, yte, P["names"])
    pb, crops_te, yt = predict(m, Xte), P["df"].crop[P["te"]].to_numpy(), np.exp(yte)
    by_crop = []
    for cr in CROPS:
        k = crops_te == cr
        if k.sum() >= 30: by_crop.append({"crop": cr, "n_test": int(k.sum()), "baseline_mdape": round(float(np.median(np.abs(np.exp(P["bp"][k]) - yt[k]) / yt[k]) * 100), 1),
                                          "model_mdape": round(float(np.median(np.abs(np.exp(pb[k]) - yt[k]) / yt[k]) * 100), 1)})
    by_crop.sort(key=lambda x: -x["n_test"])
    print("\nMedian absolute % error by crop (baseline -> model):")
    for b in by_crop: print(f"  {b['crop']:14s} n={b['n_test']:>5}  {b['baseline_mdape']:>5}% -> {b['model_mdape']:>5}%")
    model = export(m, P["names"], resid)
    model["meta"] = {"best": best, "crops": CROPS, "districts": sorted(P["df"].district.unique().tolist()), "seasons": sorted(P["df"].season.unique().tolist()),
                     "erosion_levels": ["Very low", "Low", "Moderate", "Severe"], "cropping_systems": ["Pure", "Inter-cropping", "Traditional mixed"],
                     "fert_bands": ["None", "Up to 50 kg/ha", "51-100 kg/ha", "101-200 kg/ha", "Over 200 kg/ha", "Used (amount unknown)"], "n_train": P["n_train"]}
    json.dump(model, open(os.path.join(HERE, "model.json"), "w"), separators=(",", ":"))
    mets = {"available": True, "best": best, "scope": "12 annual crops; plots with a measured crop area; split by survey segment", "n_train": P["n_train"], "n_test": P["n_test"],
            "models": [{"name": k, **v} for k, v in P["metrics"].items()], "sensitivity_all_plots": [{"name": k, **v} for k, v in S["metrics"].items()],
            "n_test_sensitivity": S["n_test"], "by_crop": by_crop, "feature_importance": fi, "interval_80pct_log": resid}
    json.dump(mets, open(os.path.join(HERE, "metrics.json"), "w"), indent=1)
    print("\nTop predictive factors (permutation importance, drop in R2 on held-out data):")
    for f in fi[:8]: print(f"  {f['label']:28s} {f['importance']}")
    print("\nWrote ml/models/model.json and ml/models/metrics.json")

if __name__ == "__main__": main()
