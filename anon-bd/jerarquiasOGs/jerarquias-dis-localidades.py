#!/usr/bin/env python3
import pandas as pd, unicodedata

# --- Parámetros (edítalos) ---
INPUT_TABLE_PATH    = "city.csv"
MUNICIPIO_COL       = "localidad"
REFERENCE_CSV_PATH  = "localidades_referencia.csv"  # columnas: localidad, provincia, ccaa (con , o ;)
OUTPUT_HIER_CSV     = "city_hierarchy.csv"
COUNTRY_NAME        = "España"

norm = lambda s: "".join(c for c in unicodedata.normalize("NFKD", str(s).strip().lower())
                         if not unicodedata.combining(c))

# 1) Referencia -> diccionario normalizado: municipio -> (provincia, ccaa)
ref = pd.read_csv(REFERENCE_CSV_PATH, sep=None, engine="python", dtype=str, encoding="utf-8")
ref.columns = ref.columns.str.strip().str.lower()  # normaliza encabezados mínimos
ref = ref[["localidad","provincia","ccaa"]]
ref["_k"] = ref["localidad"].map(norm)
ref_dict = ref.drop_duplicates("_k").set_index("_k")[["provincia","ccaa"]].to_dict("index")

# 2) Valores distintos de tu tabla (tal cual aparecerán en level0)
vals = pd.read_csv(INPUT_TABLE_PATH, dtype=str, encoding="utf-8")[MUNICIPIO_COL] \
         .dropna().astype(str).drop_duplicates()

# 3) Armar jerarquía ARX
rows = []
for v in vals:
    k = norm(v); hit = ref_dict.get(k, {"provincia":"Desconocido","ccaa":"Desconocido"})
    rows.append({"level0": v, "level1": hit["provincia"], "level2": hit["ccaa"], "level3": COUNTRY_NAME})

pd.DataFrame(rows, columns=["level0","level1","level2","level3"]).to_csv(OUTPUT_HIER_CSV, index=False)
print("Jerarquía guardada en:", OUTPUT_HIER_CSV)
