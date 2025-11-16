#!/usr/bin/env python3
# Genera jerarquía ARX para códigos postales españoles:
# level0=CP(5), level1=CP(4)x, level2=CP(3)xx, level3=CP(2)xxx, level4=CP(1)xxxx, level5=España

import pandas as pd

# --- Parámetros (edítalos) ---
INPUT_TABLE_PATH   = "cp.csv"   # tu tabla con columna 'cp'
CP_COLUMN_NAME     = "cp"
OUTPUT_HIER_CSV    = "cp_hierarchy.csv"
COUNTRY_NAME       = "España"
# ------------------------------

def trunc(cp: str, keep: int) -> str:
    s = "".join(ch for ch in str(cp) if ch.isdigit())
    s = s.zfill(5)[:5]           # aseguramos 5 dígitos
    return s[:keep] + "x"*(5-keep)

def main():
    df = pd.read_csv(INPUT_TABLE_PATH, dtype=str)
    if CP_COLUMN_NAME not in df.columns:
        raise SystemExit(f"No existe columna '{CP_COLUMN_NAME}' en {INPUT_TABLE_PATH}")
    vals = df[CP_COLUMN_NAME].dropna().astype(str).drop_duplicates()

    rows = []
    for v in vals:
        v5 = "".join(ch for ch in v if ch.isdigit()).zfill(5)[:5]  # level0 exacto (5 dígitos)
        row = {
            "level0": v5,
            "level1": trunc(v5, 4),
            "level2": trunc(v5, 3),
            "level3": trunc(v5, 2),
            "level4": trunc(v5, 1),
            "level5": COUNTRY_NAME,
        }
        rows.append(row)

    pd.DataFrame(rows, columns=["level0","level1","level2","level3","level4","level5"]) \
      .to_csv(OUTPUT_HIER_CSV, index=False)
    print("Jerarquía guardada en:", OUTPUT_HIER_CSV)

if __name__ == "__main__":
    main()
