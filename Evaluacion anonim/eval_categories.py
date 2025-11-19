#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, csv, unicodedata, re
from collections import Counter

# ---------------- Normalización ----------------
def normalize_text(s: str) -> str:
    if s is None: return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[_\-\.,;/\\|()\[\]{}]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

CATEGORY_CANON = {
    "identificador_directo": "identificador_directo",
    "identificador directo": "identificador_directo",
    "cuasi_identificador": "cuasi_identificador",
    "cuasi identificador": "cuasi_identificador",
    "quasi_identificador": "cuasi_identificador",
    "quasi identificador": "cuasi_identificador",
    "atributo_sensible": "atributo_sensible",
    "atributo sensible": "atributo_sensible",
    "no_sensible": "no_sensible",
    "no sensible": "no_sensible",
}
ALLOWED = ["identificador_directo","cuasi_identificador","atributo_sensible","no_sensible"]

def normalize_category(cat: str) -> str:
    key = normalize_text(cat)
    return CATEGORY_CANON.get(key, key)

# ------------- Carga canon y alias -------------
def load_canonical(csv_path: str):
    canon = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["Entidad"].strip()
            tipo = normalize_text(row["Tipo"])
            if "identificador" in tipo and "directo" in tipo:
                cat = "identificador_directo"
            elif "cuasi" in tipo:
                cat = "cuasi_identificador"
            elif "sensible" in tipo and "no" not in tipo:
                cat = "atributo_sensible"
            elif "no" in tipo and "sensible" in tipo:
                cat = "no_sensible"
            else:
                cat = tipo
            canon[name] = cat
    return canon

def load_aliases(json_path: str):
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)

def build_alias_map(canon_map, aliases_dict):
    alias_to_canon = {}
    for canon in canon_map.keys():
        alias_to_canon[normalize_text(canon)] = canon
    for canon, alias_list in aliases_dict.items():
        for a in alias_list:
            alias_to_canon[normalize_text(a)] = canon
    return alias_to_canon

# ----------- Evaluación SOLO categoría ----------
def evaluate_categories_only(predictions_path, canon_map, alias_map):
    with open(predictions_path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])

    y_true, y_pred = [], []
    rows = []
    unmapped, badcat = [], []

    for it in items:
        raw_name = it.get("name","")
        raw_cat  = it.get("category","")
        raw_risk = it.get("risk","")
        raw_treat= it.get("recommended_treatment","")

        norm = normalize_text(raw_name)
        canon = alias_map.get(norm)
        if canon is None:
            for c in canon_map.keys():
                if normalize_text(c) == norm:
                    canon = c; break
        if canon is None:
            unmapped.append(raw_name)
            continue

        gold = canon_map[canon]
        pred = normalize_category(raw_cat)
        if pred not in ALLOWED:
            badcat.append((raw_name, raw_cat))
            pred = "no_sensible"  # fallback

        y_true.append(gold); y_pred.append(pred)
        rows.append({
            "name_input": raw_name,
            "name_canonical": canon,
            "pred_category": pred,
            "gold_category": gold,
            "risk_info": raw_risk,                   # informativo
            "recommended_treatment_info": raw_treat, # informativo
            "correct": pred == gold
        })

    # Métricas
    total = len(y_true)
    correct = sum(1 for a,b in zip(y_pred,y_true) if a==b)
    accuracy = correct/total if total else 0.0

    labels = ALLOWED
    conf = {a:{b:0 for b in labels} for a in labels}
    prec_num=Counter(); prec_den=Counter(); rec_num=Counter(); rec_den=Counter()

    for t,p in zip(y_true,y_pred):
        conf[t][p]+=1
        if t==p: prec_num[p]+=1; rec_num[t]+=1
        prec_den[p]+=1; rec_den[t]+=1

    per_class={}
    for lab in labels:
        precision = (prec_num[lab]/prec_den[lab]) if prec_den[lab] else 0.0
        recall    = (rec_num[lab]/rec_den[lab]) if rec_den[lab] else 0.0
        f1 = (2*precision*recall/(precision+recall)) if (precision+recall)>0 else 0.0
        per_class[lab] = {"precision": round(precision,4), "recall": round(recall,4),
                          "f1": round(f1,4), "support": rec_den[lab]}

    report = {
        "n_evaluated": total,
        "n_correct": correct,
        "accuracy": round(accuracy,4),
        "per_class": per_class,
        "confusion_matrix": conf,
        "unmapped_columns": unmapped,
        "invalid_categories": badcat,
        "rows": rows
    }
    return report

def print_stdout(report):
    print("=== MÉTRICAS (solo category) ===")
    print(f"Evaluadas: {report['n_evaluated']}  |  Aciertos: {report['n_correct']}  |  Accuracy: {report['accuracy']:.4f}\n")
    print("F1/Prec/Rec por clase:")
    for lab, m in report["per_class"].items():
        print(f"  - {lab:22s}  F1={m['f1']:.4f}  Prec={m['precision']:.4f}  Rec={m['recall']:.4f}  Soporte={m['support']}")
    print("\nMatriz de confusión (true x pred):")
    labs = ["identificador_directo","cuasi_identificador","atributo_sensible","no_sensible"]
    header = ",".join(["true\\pred"] + labs)
    print(header)
    for t in labs:
        row = [t] + [str(report["confusion_matrix"][t][p]) for p in labs]
        print(",".join(row))
    if report["unmapped_columns"]:
        print("\n[WARN] unmapped_columns:", report["unmapped_columns"])
    if report["invalid_categories"]:
        print("\n[WARN] invalid_categories:", report["invalid_categories"])

def export_rows_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name_input","name_canonical","pred_category","gold_category",
                      "risk_info","recommended_treatment_info","correct"]
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(rows)

def export_metrics_csv(report, path):
    # Una fila global + una por clase
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["metric","label","value"])
        wr.writerow(["n_evaluated","all",report["n_evaluated"]])
        wr.writerow(["n_correct","all",report["n_correct"]])
        wr.writerow(["accuracy","all",report["accuracy"]])
        for lab, m in report["per_class"].items():
            wr.writerow(["precision",lab,m["precision"]])
            wr.writerow(["recall",lab,m["recall"]])
            wr.writerow(["f1",lab,m["f1"]])
            wr.writerow(["support",lab,m["support"]])

# -------------------- CLI -----------------------
# ... (todo tu código anterior igual, incluida la función global print_stdout
# con la tabla bonita de la matriz de confusión)

# -------------------- CLI -----------------------
def main():
    ap = argparse.ArgumentParser(description="Evalúa SOLO la categoría. Métricas por stdout y CSV opcionales.")
    ap.add_argument("--canonical_csv", required=True, help="Ruta a canonical_entities.csv")
    ap.add_argument("--aliases_json", required=True, help="Ruta a aliases.json")
    ap.add_argument("--predictions", required=True, help="Ruta a predictions.json (salida LLM)")
    ap.add_argument("--out_rows_csv", default=None, help="CSV con resultados fila a fila")
    ap.add_argument("--out_metrics_csv", default=None, help="CSV con métricas (accuracy/F1/etc.)")
    args = ap.parse_args()

    canon = load_canonical(args.canonical_csv)
    aliases = load_aliases(args.aliases_json)
    alias_map = build_alias_map(canon, aliases)
    report = evaluate_categories_only(args.predictions, canon, alias_map)

    # 1) Imprime SIEMPRE a stdout
    print_stdout(report)

    # 2) CSVs opcionales
    if args.out_rows_csv:
        export_rows_csv(report["rows"], args.out_rows_csv)
        print(f"\n[OK] Resultados fila a fila exportados en: {args.out_rows_csv}")
    if args.out_metrics_csv:
        export_metrics_csv(report, args.out_metrics_csv)
        print(f"[OK] Métricas exportadas en: {args.out_metrics_csv}")

if __name__ == "__main__":
    main()
