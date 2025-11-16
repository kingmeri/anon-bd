#!/usr/bin/env python3
import argparse, re, unicodedata
import pandas as pd, numpy as np

# --- utils ---
n = lambda s: re.sub(r"\s+"," ","".join(c for c in unicodedata.normalize("NFKD",str(s).strip().lower()) if not unicodedata.combining(c)))
labels = lambda e: [f"[{e[i]}–{e[i+1]})" for i in range(len(e)-1)]
fbin = lambda v,e: int(np.clip(np.searchsorted(e,v,side="right")-1,0,len(e)-2))

def age_hier(series, out_csv, k=10, bins=12):
    x = series.dropna().astype(float).to_numpy()
    if x.size==0:
        pd.DataFrame(columns=["level0"]).to_csv(out_csv, index=False); return
    q = np.linspace(0,1,max(2,bins)+1); e = np.unique(np.quantile(x,q,method="nearest")).astype(float).tolist()
    if len(e)<2: e=[float(x.min()), float(x.max()+1)]
    def cnt(e):
        idx = np.clip(np.searchsorted(e,x,side="right")-1,0,len(e)-2)
        return np.bincount(idx, minlength=len(e)-1)
    while True:
        bad = np.where(cnt(e)<k)[0]
        if len(bad)==0 or len(e)<=2: break
        i = int(bad[0]); del e[i+1 if i < len(e)-2 else i]
    levels=[e[:]]
    cur=e[:]
    while len(cur)>2:
        cur=[cur[0]]+[cur[i+1] for i in range(1,len(cur)-1,2)]
        if cur[-1]!=e[-1]: cur[-1]=e[-1]
        levels.append(cur[:])
    rows=[]
    for i,lab0 in enumerate(labels(levels[0])):
        low=levels[0][i]; row=[lab0]
        for L in levels[1:]:
            row.append(labels(L)[fbin(low,L)])
        rows.append({f"level{j}":row[j] for j in range(len(row))})
    pd.DataFrame(rows).to_csv(out_csv, index=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="inp", required=True)
    ap.add_argument("--col", dest="col", required=True)
    ap.add_argument("--k",   dest="k",  type=int, required=True)
    ap.add_argument("--bins",dest="bins", default="auto")  # "auto" o entero
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.inp, dtype=str)
    if args.col not in df.columns:
        raise SystemExit(f"Columna '{args.col}' no encontrada en {args.inp}")

    # bins: auto -> ~ 2 * floor(n/k), min 8, cap 30
    if str(args.bins).lower()=="auto":
        n_non_null = df[args.col].dropna().shape[0]
        bins = max(8, 2 * (n_non_null // args.k))
        bins = min(30, bins)
    else:
        bins = int(args.bins)

    age_hier(df[args.col], args.out, k=args.k, bins=bins)

if __name__ == "__main__":
    main()
