#!/usr/bin/env python3
"""
Genera una jerarquía ARX *leaf-per-value* para una columna NUMÉRICA.

Salida: CSV con columnas level0, level1, ..., levelN, root
- level0 = valor hoja (valor único del CSV, como string)
- level1..levelN = generalizaciones (rangos)
- root = '*'

Uso:
  python3 jerarquias_num_leaf.py \
    --input data/raw/data.csv \
    --column age \
    --out data/hierarchies/age_hierarchy.csv \
    --bins 12 --k 10 --decimal-places 0 --separator ','
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import pandas as pd

# ======= defaults =======
INPUT_FILE_PATH       = "./data/raw/data.csv"
NUM_COLUMN_NAME       = "age"
TARGET_INITIAL_BINS   = 12
MIN_ROWS_PER_BIN_K    = 10
OUTPUT_HIERARCHY_CSV  = "./data/hierarchies/age_hierarchy.csv"
CSV_SEPARATOR         = ','
DECIMAL_PLACES        = 0
# ========================

@dataclass
class Bin:
    lo: float
    hi: float
    idxs: np.ndarray  # índices (en el array filtrado) de filas que caen en el bin

    def size(self) -> int:
        return int(self.idxs.size)

def quantile_edges(values: np.ndarray, qbins: int) -> np.ndarray:
    qs = np.linspace(0.0, 1.0, qbins + 1)
    edges = np.quantile(values, qs, method="linear")
    edges = np.unique(edges)
    if edges.size < 2:
        e0 = float(values.min())
        e1 = e0 + 1e-9
        return np.array([e0, e1], dtype=float)
    return edges.astype(float)

def assign_bins(values: np.ndarray, edges: np.ndarray) -> List[Bin]:
    # 0..len(edges)-2
    bins_idx = np.digitize(values, edges[1:-1], right=True)
    bins: List[Bin] = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        idxs = np.where(bins_idx == i)[0]
        bins.append(Bin(lo, hi, idxs))
    # asegurar que el valor máximo cae en el último bin
    last_hi = edges[-1]
    extra = np.where(values == last_hi)[0]
    if extra.size:
        bins[-1].idxs = np.unique(np.concatenate([bins[-1].idxs, extra]))
    return bins

def merge_until_k(bins: List[Bin], k: int) -> List[Bin]:
    changed = True
    while changed:
        changed = False
        i = 0
        new_bins: List[Bin] = []
        while i < len(bins):
            b = bins[i]
            if b.size() >= k or i == len(bins) - 1:
                new_bins.append(b)
                i += 1
            else:
                j = i + 1
                lo = b.lo
                idxs = b.idxs.copy()
                hi = b.hi
                while j < len(bins) and idxs.size < k:
                    idxs = np.concatenate([idxs, bins[j].idxs])
                    hi = bins[j].hi
                    j += 1
                new_bins.append(Bin(lo, hi, np.unique(idxs)))
                i = j
                changed = True
        bins = new_bins
        # también fusiona por la derecha si el último se queda <k
        if len(bins) > 1 and bins[-1].size() < k:
            prev = bins[-2]
            last = bins[-1]
            merged = Bin(prev.lo, last.hi, np.unique(np.concatenate([prev.idxs, last.idxs])))
            bins = bins[:-2] + [merged]
            changed = True
    return bins

def build_levels(bins: List[Bin]) -> List[List[Tuple[float, float]]]:
    levels: List[List[Tuple[float, float]]] = []
    current = [(b.lo, b.hi) for b in bins]
    while True:
        levels.append(current)
        if len(current) == 1:
            break
        nxt: List[Tuple[float, float]] = []
        i = 0
        while i < len(current):
            lo = current[i][0]
            hi = current[i][1]
            if i + 1 < len(current):
                hi = current[i + 1][1]
                i += 2
            else:
                i += 1
            nxt.append((lo, hi))
        current = nxt
    return levels

def format_range(lo: float, hi: float, dp: int) -> str:
    if dp <= 0:
        return f"[{int(round(lo))},{int(round(hi))})" if lo != hi else f"[{int(round(lo))},{int(round(hi))}]"
    fmt = f"{{:.{dp}f}}"
    a = fmt.format(lo).rstrip('0').rstrip('.')
    b = fmt.format(hi).rstrip('0').rstrip('.')
    return f"[{a},{b})" if lo != hi else f"[{a},{b}]"

def build_unique_leaf_rows(unique_vals: np.ndarray,
                           bins: List[Bin],
                           levels: List[List[Tuple[float, float]]],
                           dp: int) -> pd.DataFrame:
    # preformateo de etiquetas por nivel
    level_labels: List[List[str]] = []
    for rngs in levels:
        labels = [format_range(lo, hi, dp) for (lo, hi) in rngs]
        level_labels.append(labels)

    # función para localizar el bin de un valor v
    def locate_bin(v: float) -> int:
        for bi, (lo, hi) in enumerate([(b.lo, b.hi) for b in bins]):
            if (v >= lo and v < hi) or (bi == len(bins) - 1 and v == hi):
                return bi
        # fallback por si hay redondeos raros
        diffs = [abs((b.lo + b.hi) / 2.0 - v) for b in bins]
        return int(np.argmin(diffs))

    rows: List[List[str]] = []
    for v in unique_vals:
        leaf = str(int(round(v))) if dp <= 0 else str(v)
        bi = locate_bin(float(v))
        path = [leaf]
        # level1..levelN
        for lvl_idx, labels in enumerate(level_labels, start=1):
            idx = bi // (2 ** (lvl_idx - 1))
            path.append(labels[idx])
        path.append('*')
        rows.append(path)

    num_levels = len(level_labels)
    cols = ['level0'] + [f'level{l}' for l in range(1, num_levels + 1)] + ['root']
    # ordenar por leaf numérico si son enteros
    try:
        df = pd.DataFrame(rows, columns=cols)
        df['__leafnum'] = pd.to_numeric(df['level0'], errors='coerce')
        df = df.sort_values(['__leafnum', 'level0']).drop(columns='__leafnum')
        return df
    except Exception:
        return pd.DataFrame(rows, columns=cols)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=INPUT_FILE_PATH)
    ap.add_argument("--column", default=NUM_COLUMN_NAME)
    ap.add_argument("--out", default=OUTPUT_HIERARCHY_CSV)
    ap.add_argument("--bins", type=int, default=TARGET_INITIAL_BINS)
    ap.add_argument("--k", type=int, default=MIN_ROWS_PER_BIN_K)
    ap.add_argument("--separator", default=CSV_SEPARATOR)
    ap.add_argument("--decimal-places", type=int, default=DECIMAL_PLACES)
    args = ap.parse_args()

    df = pd.read_csv(args.input, sep=args.separator)
    if args.column not in df.columns:
        raise SystemExit(f"Columna '{args.column}' no encontrada en {args.input}")

    series = pd.to_numeric(df[args.column], errors='coerce')
    values = series.to_numpy()
    values = values[~np.isnan(values)]
    if values.size == 0:
        raise SystemExit("Sin valores numéricos válidos en la columna (todo NaN).")

    # valores únicos (hojas únicas)
    if args.decimal_places <= 0:
        unique_vals = np.unique(np.round(values).astype(int))
    else:
        unique_vals = np.unique(values)

    edges = quantile_edges(values, max(1, args.bins))
    bins = assign_bins(values, edges)
    bins = merge_until_k(bins, max(1, args.k))
    levels = build_levels(bins)

    leaf_df = build_unique_leaf_rows(unique_vals, bins, levels, dp=max(0, args.decimal_places))
    leaf_df.to_csv(args.out, index=False)
    print(f"Guardado ARX hierarchy leaf-per-value → {args.out}")
    print(f"Filas (valores únicos): {len(leaf_df)} | Columnas: {list(leaf_df.columns)}")

if __name__ == "__main__":
    main()
