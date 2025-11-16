#!/usr/bin/env python3
import argparse, pandas as pd

def dig5(s: str) -> str:
    t = "".join(ch for ch in str(s) if ch.isdigit())
    return t.zfill(5)[:5]

def trunc(cp: str, keep: int) -> str:
    return cp[:keep] + "x"*(5-keep)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="inp", required=True)
    ap.add_argument("--col", dest="col", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--country", default="España")
    args = ap.parse_args()

    df = pd.read_csv(args.inp, dtype=str)
    if args.col not in df.columns:
        raise SystemExit(f"Columna '{args.col}' no encontrada en {args.inp}")

    vals = df[args.col].dropna().astype(str).drop_duplicates()
    rows = []
    for v in vals:
        v5 = dig5(v)
        rows.append({
            "level0": v5,
            "level1": trunc(v5,4),
            "level2": trunc(v5,3),
            "level3": trunc(v5,2),
            "level4": trunc(v5,1),
            "level5": args.country
        })

    pd.DataFrame(rows, columns=[f"level{i}" for i in range(6)]).to_csv(args.out, index=False)

if __name__ == "__main__":
    main()
