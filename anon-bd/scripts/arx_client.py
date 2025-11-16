#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, os, sys, subprocess

# --- Manifest helpers ---------------------------------------------------------
def build_manifest(input_path, output_path, k, suppression,
                   attributes, separator=",", encoding="utf-8",
                   has_header=True, search="fast", metric="precision",
                   ldiv=None, tclose=None, version="1"):
    """Devuelve el dict manifest listo para serializar."""
    return {
        "version": str(version),
        "input": {
            "path": input_path,
            "separator": separator,
            "encoding": encoding,
            "has_header": bool(has_header)
        },
        "output": {
            "path": output_path,
            "overwrite": True
        },
        "privacy": {
            "k": int(k),
            "l_diversity": ldiv or [],     # p.ej. [{"column":"salario","l":2,"type":"distinct"}]
            "t_closeness": tclose or [],   # p.ej. [{"column":"importe","t":0.2,"distance":"equal"}]
            "suppression_limit": float(suppression)
        },
        "attributes": attributes,          # lista de dicts: {"name","role",["hierarchy"],["data_type"]}
        "algorithm": {
            "search": search,              # "fast" | "optimal"
            "metric": metric               # "precision" (suficiente para TFG)
        },
        "logging": { "level": "INFO" }
    }

def validate_manifest(m):
    # Comprobaciones mínimas y mensajes claros
    if not os.path.exists(m["input"]["path"]):
        raise SystemExit(f"[ERROR] No existe input: {m['input']['path']}")
    for a in m["attributes"]:
        role = a.get("role")
        if role == "QI":
            h = a.get("hierarchy")
            if not h: raise SystemExit(f"[ERROR] Falta hierarchy para QI '{a.get('name')}'")
            if not os.path.exists(h):
                raise SystemExit(f"[ERROR] No existe jerarquía para '{a.get('name')}': {h}")
    out_dir = os.path.dirname(m["output"]["path"]) or "."
    os.makedirs(out_dir, exist_ok=True)
    if not (0.0 <= float(m["privacy"]["suppression_limit"]) <= 1.0):
        raise SystemExit("[ERROR] suppression_limit debe estar en [0,1]")

# --- CLI ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Crea manifest.json y ejecuta ARX runner (java -jar).")
    ap.add_argument("--input", required=True, help="CSV pseudoanonimizado de entrada")
    ap.add_argument("--out",   required=True, help="CSV anonimizado de salida")
    ap.add_argument("--k",     type=int, default=10)
    ap.add_argument("--suppression", type=float, default=0.02)
    ap.add_argument("--sep",   default=",", help="Separador CSV (por defecto ,)")
    ap.add_argument("--runner", required=True, help="Ruta al arx-runner.jar")
    ap.add_argument("--manifest", default="manifest.json", help="Ruta donde guardar el manifest")
    # Atributos: pasamos un JSON compacto para no complicar flags individuales
    ap.add_argument("--attributes", required=True,
                    help="JSON de atributos. Ej: "
                         "'[{\"name\":\"PERSON_UID\",\"role\":\"Insensitive\"},"
                         "{\"name\":\"edad\",\"role\":\"QI\",\"hierarchy\":\"hierarchies/age_hierarchy.csv\"}]'")
    # Opcionales avanzados
    ap.add_argument("--ldiversity", default="[]",
                    help='JSON de l-diversity. Ej: "[{\\"column\\":\\"salario\\",\\"l\\":2,\\"type\\":\\"distinct\\"}]"')
    ap.add_argument("--tcloseness", default="[]",
                    help='JSON de t-closeness. Ej: "[{\\"column\\":\\"importe\\",\\"t\\":0.2,\\"distance\\":\\"equal\\"}]"')
    ap.add_argument("--search", default="fast", choices=["fast","optimal"])
    ap.add_argument("--metric", default="precision")
    args = ap.parse_args()

    # Parsear JSONs de atributos / l / t
    try:
        attributes = json.loads(args.attributes)
        ldiv = json.loads(args.ldiversity)
        tclose = json.loads(args.tcloseness)
    except json.JSONDecodeError as e:
        raise SystemExit(f"[ERROR] JSON inválido en --attributes/--ldiversity/--tcloseness: {e}")

    manifest = build_manifest(
        input_path=args.input,
        output_path=args.out,
        k=args.k,
        suppression=args.suppression,
        attributes=attributes,
        separator=args.sep,
        ldiv=ldiv,
        tclose=tclose,
        search=args.search,
        metric=args.metric
    )

    validate_manifest(manifest)

    # Guardar manifest
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"✓ manifest escrito en {args.manifest}")

    # Ejecutar runner Java
    cmd = ["java", "-jar", args.runner, args.manifest]
    print("→", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    print(f"✓ Anonimizado generado en {args.out}")

if __name__ == "__main__":
    main()
