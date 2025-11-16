#!/usr/bin/env python3
import argparse, re, unicodedata, pandas as pd

def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+"," ", s)

L1_RULES = [
    (r"\bdoctorad|\bphd\b", "doctorado"),
    (r"\bmaster|\bmaestr",  "máster"),
    (r"\bfp\b.*grado superior|\bciclo formativo\b.*grado superior|\bgrado superior\b", "grado"),
    (r"\bfp\b.*grado medio|\bciclo formativo\b.*grado medio|\bgrado medio\b", "educación secundaria o bachillerato"),
    (r"\blicenciatur|\bdiplomatur", "grado"),
    (r"\bgrado\b", "grado"),
    (r"\bbachiller|\beso\b|secundaria obligatoria", "educación secundaria o bachillerato"),
]
L2 = {"doctorado":"superior","máster":"superior","grado":"superior","educación secundaria o bachillerato":"secundario"}

def classify_level1(title: str) -> str:
    s = norm(title)
    for p,l in L1_RULES:
        if re.search(p, s): return l
    return "educación secundaria o bachillerato"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="inp", required=True)
    ap.add_argument("--col", dest="col", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--root", default="Educación")
    args = ap.parse_args()

    df = pd.read_csv(args.inp, dtype=str)
    if args.col not in df.columns:
        raise SystemExit(f"Columna '{args.col}' no encontrada en {args.inp}")

    vals = df[args.col].dropna().astype(str).drop_duplicates()
    rows = []
    for v in vals:
        l1 = classify_level1(v)
        rows.append({"level0": v, "level1": l1, "level2": L2.get(l1, "secundario"), "level3": args.root})

    pd.DataFrame(rows, columns=["level0","level1","level2","level3"]).to_csv(args.out, index=False)

if __name__ == "__main__":
    main()
