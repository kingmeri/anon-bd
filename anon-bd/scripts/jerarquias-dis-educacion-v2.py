#!/usr/bin/env python3
import csv, argparse, sys, unicodedata
from collections import OrderedDict

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = strip_accents(s)
    return " ".join(s.split())

# Palabras clave (ES/EN) para detección
KEYS = {
    "doctorado": [
        "doctorado", "phd", "ph.d", "doctoral", "doctorate", "doctor"
    ],
    "master": [
        "master", "maestria", "msc", "mba", "m. sc", "m.sc", "ms", "mres",
        "posgrado", "postgrado", "post-grado", "post graduate", "postgraduate", "graduate degree (master)"
    ],
    "grado": [
        "grado", "licenciatura", "diplomatura", "bachelor", "bsc", "b.sc", "ba",
        "undergraduate", "college degree", "first cycle"
    ],
    "fp": [
        "fp", "formacion profesional", "ciclo formativo", "vocational", "vet", "technical diploma",
        "tecnico", "tecnica", "tecnico superior"
    ],
    "bachillerato": [
        "bachillerato", "high school", "a-level", "alevel", "secondary (upper)"
    ],
    "secundaria": [
        "secundaria", "eso", "middle school", "secondary", "compulsory secondary"
    ],
    "primaria": [
        "primaria", "primary", "elementary"
    ],
}

# Mapa de categoría -> macro-categoría (nivel superior)
MACRO = {
    "grado": "Universitaria",
    "master": "Universitaria",
    "doctorado": "Universitaria",
    "fp": "Pre-universitaria",
    "bachillerato": "Pre-universitaria",
    "secundaria": "Básica",
    "primaria": "Básica",
    "otros": "Otros"
}

# Orden de prioridad: si un valor matchea varias, gana la más alta
PRIORITY = ["doctorado", "master", "grado", "fp", "bachillerato", "secundaria", "primaria"]

def classify(leaf_raw: str) -> str:
    s = norm(leaf_raw)
    for cat in PRIORITY:
        for kw in KEYS[cat]:
            if kw in s:
                return cat
    return "otros"

def main():
    ap = argparse.ArgumentParser(description="Genera jerarquía ARX para educación (por palabras clave).")
    ap.add_argument("--input", required=True, help="CSV de entrada con la columna de educación")
    ap.add_argument("--col", default="education", help="Nombre de la columna (por defecto 'education')")
    ap.add_argument("--output", required=True, help="CSV de jerarquía de salida")
    ap.add_argument("--root", default="*", help="Etiqueta root (por defecto '*')")
    args = ap.parse_args()

    # Valores únicos, orden estable
    uniq = OrderedDict()
    with open(args.input, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if args.col not in r.fieldnames:
            sys.exit(f"ERROR: la columna '{args.col}' no existe en {args.input}.")
        for row in r:
            v = (row.get(args.col) or "").strip()
            if v:
                uniq.setdefault(v, True)

    rows = []
    for leaf in uniq.keys():
        cat = classify(leaf)
        macro = MACRO.get(cat, "Otros")
        # Formato ARX: level0 (hoja) -> level1 (categoría) -> level2 (macro) -> root
        rows.append([leaf, cat.capitalize(), macro, args.root])

    # Cabecera consistente con 3 niveles + root
    header = ["level0", "level1", "level2", "root"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

if __name__ == "__main__":
    main()
