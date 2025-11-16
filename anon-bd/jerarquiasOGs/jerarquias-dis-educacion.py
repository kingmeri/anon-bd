#!/usr/bin/env python3
# Genera jerarquía ARX para títulos educativos con 4 niveles:
# level0 = título original
# level1 = {grado, máster, doctorado, educación secundaria o bachillerato}
# level2 = {básico, secundario, superior}
# level3 = "Educación"

import re, unicodedata, pandas as pd

# Parámetros
INPUT_TABLE_PATH = "titulos.csv"      # CSV con columna 'titulo'
TITLE_COL        = "titulo"
OUTPUT_HIER_CSV  = "education_hierarchy.csv"
ROOT_NAME        = "Educación"

def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    return s

# Reglas por prioridad (las primeras tienen preferencia)
LEVEL1_RULES = [
    (r"\bdoctorad|\bphd\b",                      "doctorado"),
    (r"\bmaster|\bmaestr",                       "máster"),
    (r"\bfp\b.*grado superior|\bciclo formativo\b.*grado superior|\bgrado superior\b", "grado"),
    (r"\bfp\b.*grado medio|\bciclo formativo\b.*grado medio|\bgrado medio\b",         "educación secundaria o bachillerato"),
    (r"\blicenciatur|\bdiplomatur",              "grado"),  # normalizamos a tu categoría
    (r"\bgrado\b",                               "grado"),
    (r"\bbachiller|\beso\b|secundaria obligatoria", "educación secundaria o bachillerato"),
]

LEVEL2_MAP = {
    "doctorado": "superior",
    "máster": "superior",
    "grado": "superior",
    "educación secundaria o bachillerato": "secundario",
}

def classify_level1(title: str) -> str:
    n = norm(title)
    for pat, label in LEVEL1_RULES:
        if re.search(pat, n):
            return label
    # Fallback conservador: si no se reconoce, lo tratamos como secundario
    return "educación secundaria o bachillerato"

def main():
    df = pd.read_csv(INPUT_TABLE_PATH, dtype=str)
    if TITLE_COL not in df.columns:
        raise SystemExit(f"No existe columna '{TITLE_COL}' en {INPUT_TABLE_PATH}")
    values = df[TITLE_COL].dropna().astype(str).drop_duplicates()

    rows = []
    for t in values:
        lvl1 = classify_level1(t)
        lvl2 = LEVEL2_MAP.get(lvl1, "secundario")  # básico/secundario/superior; por defecto secundario
        rows.append({"level0": t, "level1": lvl1, "level2": lvl2, "level3": ROOT_NAME})

    pd.DataFrame(rows, columns=["level0","level1","level2","level3"]).to_csv(OUTPUT_HIER_CSV, index=False)
    print("Jerarquía guardada en:", OUTPUT_HIER_CSV)

if __name__ == "__main__":
    main()
