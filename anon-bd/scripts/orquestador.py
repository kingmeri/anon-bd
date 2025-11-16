#!/usr/bin/env python3
import os, json, subprocess, sys, yaml

def ensuredir(d): os.makedirs(d, exist_ok=True)
def run(cmd):
    print("→", " ".join(cmd))
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout)
    if r.returncode != 0: sys.exit(r.returncode)

def main():
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    dataset   = cfg["dataset"]
    out_dir   = cfg.get("output_dir", "hierarchies")
    params    = cfg.get("params", {})
    columns   = cfg.get("columns", {})
    roles     = cfg.get("roles", {})
    ensuredir(out_dir)

    k        = str(params.get("k", 10))
    age_bins = str(params.get("age_bins", "auto"))
    city_ref = params.get("city_reference_csv")

    manifest = {"dataset": dataset, "output_dir": out_dir, "attributes": []}

    for col, typ in columns.items():
        if typ == "age":
            out = os.path.join(out_dir, "age_hierarchy.csv")
            run([sys.executable, "jerarquias-num.py",
                 "--in", dataset, "--col", col, "--k", k, "--bins", age_bins, "--out", out])
            manifest["attributes"].append({"column": col, "type": typ, "hierarchy_csv": out, "role": roles.get(col, "QI")})

        elif typ == "city":
            if not city_ref: sys.exit("Falta params.city_reference_csv en config.yaml")
            out = os.path.join(out_dir, "city_hierarchy.csv")
            run([sys.executable, "jerarquias-dis-localidades.py",
                 "--in", dataset, "--col", col, "--ref", city_ref, "--out", out])
            manifest["attributes"].append({"column": col, "type": typ, "hierarchy_csv": out, "role": roles.get(col, "QI")})

        elif typ == "postal_code":
            out = os.path.join(out_dir, "cp_hierarchy.csv")
            run([sys.executable, "jerarquias-dis-cp.py",
                 "--in", dataset, "--col", col, "--out", out])
            manifest["attributes"].append({"column": col, "type": typ, "hierarchy_csv": out, "role": roles.get(col, "QI")})

        elif typ == "education_title":
            out = os.path.join(out_dir, "education_hierarchy.csv")
            run([sys.executable, "jerarquias-dis-educacion.py",
                 "--in", dataset, "--col", col, "--out", out])
            manifest["attributes"].append({"column": col, "type": typ, "hierarchy_csv": out, "role": roles.get(col, "QI")})

        else:
            print(f"[WARN] Tipo desconocido '{typ}' para '{col}', se ignora.")

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("\n✓ Jerarquías generadas en:", out_dir)
    print("→ Manifest:", os.path.join(out_dir, "manifest.json"))

if __name__ == "__main__":
    main()
