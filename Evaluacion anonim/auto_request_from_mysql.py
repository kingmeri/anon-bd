#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, re, json, math, time, os
import mysql.connector
import requests
from dotenv import load_dotenv

# --------- cargar .env ---------
load_dotenv()

def env(key, default=None, cast=None):
    val = os.getenv(key, default)
    if cast and val is not None:
        try:
            return cast(val)
        except Exception:
            return default
    return val

# Defaults desde .env (con fallback)
ENV_HOST = env("DB_HOST", "127.0.0.1")
ENV_PORT = env("DB_PORT", 3306, int)
ENV_USER = env("DB_USER", "gdpr_ro")
ENV_PASS = env("DB_PASS", "ro_pass")
ENV_NAME = env("DB_NAME", "sakila_es")

ENV_OLLAMA_URL = env("OLLAMA_URL", "http://localhost:11434/api/generate")
ENV_MODEL      = env("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")

ENV_TABLE_LIKE = env("TABLE_LIKE", "%")
ENV_SAMPLE_ROWS= env("SAMPLE_ROWS", 5, int)
ENV_BATCH_SIZE = env("BATCH_SIZE", 20, int)
ENV_SLEEP_S    = env("SLEEP_S", 0.3, float)
ENV_OUT_PRED   = env("OUT_PREDICTIONS", "predictions.json")

# ---------- helpers ----------
def map_mysql_type(dt: str, column_type: str) -> str:
    dt = (dt or "").lower()
    ct = (column_type or "").lower()
    if dt in {"varchar","char","text","tinytext","mediumtext","longtext","enum","set"}:
        return "string"
    if dt in {"int","bigint","smallint","mediumint","tinyint"}:
        if dt == "tinyint" and ("(1)" in ct or ct.strip()=="tinyint"):
            return "bool"
        return "int"
    if dt in {"decimal","float","double","real"}:
        return "float"
    if dt in {"date"}:
        return "date"
    if dt in {"datetime","timestamp"}:
        return "datetime"
    if dt in {"json"}:
        return "json"
    if dt in {"time","year","binary","varbinary","blob"}:
        return "other"
    return "other"

_PATTERNS = [
    ("IBAN", re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", re.I)),
    ("DNI", re.compile(r"\b\d{7,8}[A-Z]\b", re.I)),
    ("NIE", re.compile(r"\b[XYZ]\d{7}[A-Z]\b", re.I)),
    ("EMAIL", re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+", re.I)),
    ("TEL", re.compile(r"\+?\d[\d\s\-\(\)]{7,}\d")),
    ("TARJETA", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
]
def mask_value(v):
    s = str(v)
    for label, rx in _PATTERNS:
        if rx.search(s):
            return f"<MASK:{label}>"
    if len(s) > 64:
        return s[:61] + "..."
    return s

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Extrae columnas de MySQL y genera predictions.json llamando a Ollama.")
    ap.add_argument("--host", default=ENV_HOST)
    ap.add_argument("--port", type=int, default=ENV_PORT)
    ap.add_argument("--user", default=ENV_USER)
    ap.add_argument("--password", default=ENV_PASS)
    ap.add_argument("--database", default=ENV_NAME, help="schema de MySQL (table_schema)")

    ap.add_argument("--table_like", default=ENV_TABLE_LIKE, help="patrón LIKE para table_name")
    ap.add_argument("--sample_rows", type=int, default=ENV_SAMPLE_ROWS, help="muestras por columna (máx)")
    ap.add_argument("--batch_size", type=int, default=ENV_BATCH_SIZE, help="nº columnas por petición a LLM")

    ap.add_argument("--model", default=ENV_MODEL)
    ap.add_argument("--ollama_url", default=ENV_OLLAMA_URL)
    ap.add_argument("--out_predictions", default=ENV_OUT_PRED)
    ap.add_argument("--sleep_s", type=float, default=ENV_SLEEP_S, help="pausa entre peticiones")
    args = ap.parse_args()

    print(f"[INFO] Conectando a MySQL {args.host}:{args.port} DB={args.database} con usuario '{args.user}'…")

    # conectar
    conn = mysql.connector.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, database=args.database
    )
    cur = conn.cursor(dictionary=True)

    # 1) columnas (alias para claves en minúscula)
    cur.execute("""
        SELECT
          TABLE_NAME   AS table_name,
          COLUMN_NAME  AS column_name,
          DATA_TYPE    AS data_type,
          COLUMN_TYPE  AS column_type,
          IS_NULLABLE  AS is_nullable
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name LIKE %s
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """, (args.database, args.table_like))
    cols = cur.fetchall()

    # 2) stats + muestras
    cols_info = []
    for c in cols:
        # fallback por si alguna clave viene en MAYÚSCULAS
        t   = c.get("table_name",  c.get("TABLE_NAME"))
        col = c.get("column_name", c.get("COLUMN_NAME"))
        dt  = c.get("data_type",   c.get("DATA_TYPE"))
        ct  = c.get("column_type", c.get("COLUMN_TYPE"))
        nul = c.get("is_nullable", c.get("IS_NULLABLE"))

        # contar filas y nulls
        cur.execute(f"SELECT COUNT(*) AS n, SUM(CASE WHEN `{col}` IS NULL THEN 1 ELSE 0 END) AS n_null FROM `{t}`")
        r = cur.fetchone()
        n_all = r["n"] or 0
        n_null = r["n_null"] or 0

        # count distinct (para demo)
        try:
            cur.execute(f"SELECT COUNT(DISTINCT `{col}`) AS n_dist FROM `{t}`")
            r2 = cur.fetchone(); n_dist = r2["n_dist"] or 0
        except Exception:
            n_dist = None

        # muestras (non-null)
        samples = []
        try:
            cur.execute(f"SELECT `{col}` as v FROM `{t}` WHERE `{col}` IS NOT NULL LIMIT %s", (args.sample_rows,))
            for rr in cur.fetchall():
                samples.append(mask_value(rr["v"]))
        except Exception:
            pass

        llm_type = map_mysql_type(dt, ct)

        cols_info.append({
            "table": t,
            "name": col,
            "mysql_data_type": dt,
            "mysql_column_type": ct,
            "llm_type": llm_type,
            "is_nullable": nul,
            "n_all": n_all,
            "n_null": n_null,
            "n_distinct": n_dist,
            "samples": samples
        })

    cur.close(); conn.close()

    # 3) construir prompts en batches y llamar a Ollama
    all_items = []
    SYSTEM_PROMPT = """Eres experto en GDPR. Clasifica las columnas en:
- identificador_directo
- cuasi_identificador
- atributo_sensible
- no_sensible

Devuelve SOLO JSON con este esquema:
{
  "items": [
    {"name":"string","category":"identificador_directo|cuasi_identificador|atributo_sensible|no_sensible","rationale":"string","confidence":0.0}
  ]
}
"""

    for batch in chunked(cols_info, args.batch_size):
        lines = [SYSTEM_PROMPT, "Columnas:"]
        for c in batch:
            lines.append(f"- {c['name']} ({c['llm_type']})  -- tabla: {c['table']}")
        lines.append("\nEvidencia:")
        for c in batch:
            null_pct = round((c['n_null']/c['n_all']*100), 2) if c['n_all'] else 0
            ev = f"{c['name']}: distinct={c['n_distinct']}, null_pct={null_pct}, muestras={json.dumps(c['samples'], ensure_ascii=False)}"
            lines.append(ev)

        prompt = "\n".join(lines)

        payload = {"model": args.model, "prompt": prompt, "stream": False}
        resp = requests.post(args.ollama_url, json=payload, timeout=180)
        resp.raise_for_status()
        txt = resp.json().get("response", "").strip()

        # intentar parsear el JSON que devuelve el LLM
        items = []
        try:
            j = json.loads(txt)
            items = j.get("items", [])
        except Exception:
            m = re.search(r"\{[\s\S]*\}", txt)
            if m:
                j = json.loads(m.group(0))
                items = j.get("items", [])
            else:
                items = []

        for it in items:
            name = it.get("name","")
            cat  = it.get("category","")
            rat  = it.get("rationale","")
            conf = it.get("confidence", None)
            all_items.append({
                "name": name,
                "category": cat,
                "rationale": rat,
                "confidence": conf
            })

        time.sleep(args.sleep_s)

    # 4) escribir predictions.json
    with open(args.out_predictions, "w", encoding="utf-8") as f:
        json.dump({"items": all_items}, f, ensure_ascii=False, indent=2)

    print(f"[OK] Generado {args.out_predictions} con {len(all_items)} items.")

if __name__ == "__main__":
    main()




# EJEMPLO DE USO

# python3 auto_request_from_mysql.py \
#  --host localhost --port 3306 --user root --password ******** \
# --database mi_schema \
#--table_like '%' \
# --sample_rows 5 \
# --batch_size 20 \
#--model llama3.2:3b-instruct-q4_K_M \
# --out_predictions predictions.json
