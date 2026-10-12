"""Why do some Production rows fail to match Screening? Prints a short report (no files written).
Run:  python ml/preprocessing/diagnose_join.py"""
import os, numpy as np, pandas as pd
import pyreadstat
RAW = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
def rd(season, key):
    d = os.path.join(RAW, f"Season {season}"); f = next(x for x in sorted(os.listdir(d)) if key in x and x.endswith(".sav"))
    return pyreadstat.read_sav(os.path.join(d, f))[0]
for season in "AB":
    P, S = rd(season, "Production"), rd(season, "Screening")
    S = S.drop(columns=["s2q4"], errors="ignore").rename(columns={"s1q5_2": "s1q6", "s3q1": "s2q4"})
    t3 = ["Segment_ID", "s1q6", "s2q1"]; t4 = t3 + ["s2q4"]
    print(f"\n===== Season {season}: production {len(P)} rows, screening {len(S)} rows")
    print("screening rows with crop code missing:", int(S.s2q4.isna().sum()), "| with farmer id missing:", int(S.s1q6.isna().sum()))
    print("screening land use of rows with crop missing:", S[S.s2q4.isna()].s2q6.value_counts(dropna=False).head(4).to_dict() if "s2q6" in S else "n/a")
    p3 = P[t3].drop_duplicates(); s3 = S[t3].drop_duplicates()
    m3 = p3.merge(s3, on=t3, how="left", indicator=True)
    print(f"production plots (segment+farmer+plot): {len(p3)}; found in screening: {(m3._merge=='both').mean()*100:.1f}%")
    p4 = P[t4].drop_duplicates(); s4 = S.dropna(subset=["s2q4"])[t4].drop_duplicates()
    m4 = p4.merge(s4, on=t4, how="left", indicator=True)
    print(f"production plot-crops: {len(p4)}; found with crop in screening: {(m4._merge=='both').mean()*100:.1f}%")
    both3 = p4.merge(s3, on=t3, how="inner")
    miss = m4[m4._merge == "left_only"].merge(s3, on=t3, how="inner")
    print(f"unmatched plot-crops whose PLOT exists in screening: {len(miss)} of {(m4._merge=='left_only').sum()}")
    ex = miss.head(5)[t4].values.tolist()
    for e in ex:
        sc = S[(S.Segment_ID == e[0]) & (S.s1q6 == e[1]) & (S.s2q1 == e[2])].s2q4.tolist()
        print(f"   production crop {e[3]} on plot {e[:3]} | screening crops on that plot: {sc}")
    segs = set(P.Segment_ID); print("segments in production but not in screening:", len(segs - set(S.Segment_ID)), "of", len(segs))
