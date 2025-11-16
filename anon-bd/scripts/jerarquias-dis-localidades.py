#!/usr/bin/env python3
import argparse, unicodedata, re
import pandas as pd

norm = lambda s: re.sub(r"\s+"," ","".join(c for c in unicodedata.normalize("NFKD",str(s).strip().lower()) if not unicodedata.combining(c)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="inp", required=True)           # dataset con columna de municipios
    ap.add_argument("--col", dest="col", required=True)
    ap.add_argument("--ref", dest="ref", required=True)           # CSV referencia municipio→provincia→ccaa
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--country", default="España")
    args = ap.parse_args()

    # referencia (autodetecta separador)
    ref = pd.read_csv(args.ref, sep=None, engine="python", dtype=str, encoding="utf-8")
    ref.columns = [norm(c).replace(" ","_") for c in ref.columns]
    pick = lambda cols,cands: next((c for c in cands if c in cols), None)

    c_m = pick(ref.columns, ["municipio","localidad","poblacion","municipi","ciudad","city"])
    c_p = pick(ref.columns, ["provincia","prov","province"])
    c_c = pick(ref.columns, ["ccaa","comunidad_autonoma","comunidad","ca","region","autonomia"])
    if not (c_m and c_p and c_c):
        raise SystemExit(f"Referencia sin columnas municipio/provincia/ccaa. Columns: {list(ref.columns)}")

    ref["_k"] = ref[c_m].map(norm)
    ref = ref.drop_duplicates("_k")
    mp = ref.set_index("_k")[[c_p, c_c]].to_dict("index")

    df = pd.read_csv(args.inp, dtype=str, encoding="utf-8")
    if args.col not in df.columns:
        raise SystemExit(f"Columna '{args.col}' no encontrada en {args.inp}")

    vals = df[args.col].dropna().astype(str).drop_duplicates()
    rows = []
    for v in vals:
        hit = mp.get(norm(v), {})
        rows.append({
            "level0": v,
            "level1": hit.get(c_p, "Desconocido"),
            "level2": hit.get(c_c, "Desconocido"),
            "level3": args.country
        })

    pd.DataFrame(rows, columns=["level0","level1","level2","level3"]).to_csv(args.out, index=False)

if __name__ == "__main__":
    main()
