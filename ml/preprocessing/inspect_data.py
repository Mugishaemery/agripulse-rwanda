"""Inspect NISR SAS microdata files and write a compact plain-text report.
Usage (PowerShell, project root):
  python ml/preprocessing/inspect_data.py (Get-ChildItem data\\raw -Recurse -Filter *.sav).FullName
Supports .sav (SPSS), .dta (Stata), .csv, .xlsx. Install once:  pip install pandas pyreadstat openpyxl
Output: data/processed/inspect_report.txt  (upload this file back to Claude). Prints only what is in the data - nothing invented."""
import sys, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

def load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".sav", ".dta"):
        import pyreadstat
        df, meta = (pyreadstat.read_sav if ext == ".sav" else pyreadstat.read_dta)(path)
        return df, meta.column_names_to_labels, meta.variable_value_labels
    if ext == ".csv": return pd.read_csv(path, low_memory=False), {}, {}
    if ext in (".xlsx", ".xls"): return pd.read_excel(path), {}, {}
    raise SystemExit(f"Unsupported file type: {path}")

out = []
for path in sys.argv[1:]:
    df, labels, vl = load(path)
    out += [f"\n===== {os.path.relpath(path)} : {df.shape[0]} rows x {df.shape[1]} cols ====="]
    for c in df.columns:
        s = df[c]; miss = s.isna().mean() * 100; lab = (labels.get(c) or "")[:80]
        head = f"{c} | {s.dtype} | {lab} | missing {miss:.0f}% | unique {s.nunique()}"
        if s.nunique() <= 20:
            vc = s.value_counts(dropna=False).head(20); m = vl.get(c, {})
            body = "; ".join(f"{k}{'=' + str(m[k])[:30] if k in m else ''}:{v}" for k, v in vc.items())
            out.append(f"{head}\n    values: {body}")
        elif pd.api.types.is_numeric_dtype(s):
            q = s.quantile([0, .5, .99, 1]).round(2).tolist()
            out.append(f"{head}\n    min/median/p99/max: {q}")
        else:
            out.append(f"{head}\n    examples: {list(s.dropna().astype(str).unique()[:4])}")
os.makedirs(os.path.join(HERE, "../../data/processed"), exist_ok=True)
rep = os.path.abspath(os.path.join(HERE, "../../data/processed/inspect_report.txt"))
open(rep, "w", encoding="utf-8").write("\n".join(out)); print("Report written:", rep, f"({len(out)} lines)")
