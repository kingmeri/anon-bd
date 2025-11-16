#!/usr/bin/env python3
import csv, argparse, sys, re
from collections import OrderedDict

def normalize_cp(cp: str, digits: int, pad_char: str = "0"):
    s = re.sub(r"\D", "", str(cp))  # solo dígitos
    if not s:
        return None
    if len(s) < digits:
        s = s.zfill(digits)
    elif len(s) > digits:
        s = s[:digits]
    return s

def generalize_chain(cp: str):
    # level0 = exacto; luego vamos truncando y rellenando con '*'
    # 5 dígitos -> 4* -> 3** -> 2*** -> 1**** -> root=*
    levels = [cp]
    for keep in (4, 3, 2, 1):
        levels.append(cp[:keep] + "*"*(len(cp)-keep))
    return levels

def main():
    ap = argparse.ArgumentParser(description="Genera jerarquía ARX (una fila por CP).")
    ap.add_argument("--input", required=True, help="CSV con columna de CP")
    ap.add_argument("--col", default="cp", help="Nombre de la columna (por defecto 'cp')")
    ap.add_argument("--output", required=True, help="CSV de jerarquía de salida")
    ap.add_argument("--digits", type=int, default=5, help="Longitud objetivo de CP (por defecto 5)")
    ap.add_argument("--root", default="*", help="Etiqueta de raíz (por defecto '*')")
    args = ap.parse_args()

    # Lee y deduplica
    uniq = OrderedDict()
    with open(args.input, newline='', encoding="utf-8") as f:
        r = csv.DictReader(f)
        if args.col not in r.fieldnames:
            sys.exit(f"ERROR: la columna '{args.col}' no existe en {args.input}.")
        for row in r:
            raw = row.get(args.col, "")
            cp = normalize_cp(raw, args.digits)
            if cp:
                uniq[cp] = True

    # Construye filas
    rows = []
    for cp in uniq.keys():
        chain = generalize_chain(cp)
        rows.append(chain + [args.root])

    # Cabecera level0..level5,root (si digits=5 habrá 6 niveles incluyendo 1****)
    header = [f"level{i}" for i in range(len(rows[0]) - 1)] + ["root"] if rows else ["level0","root"]

    with open(args.output, "w", newline='', encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

if __name__ == "__main__":
    main()
