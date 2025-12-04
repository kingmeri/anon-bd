#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, re, json, time, os, sys
import mysql.connector
import requests
from dotenv import load_dotenv

from llm_client import call_ollama  # <<< NUEVO: usamos el cliente LLM compartido
from rag_client import RAGClient 

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
ENV_USER = env("DB_USER", "root")
ENV_PASS = env("DB_PASS", "secret")
ENV_NAME = env("DB_NAME", "formacion_empleo")

ENV_OLLAMA_URL = env("OLLAMA_URL", "http://localhost:11434/api/generate")
ENV_MODEL      = env("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")

ENV_TABLE_LIKE = env("TABLE_LIKE", "%")
ENV_SAMPLE_ROWS= env("SAMPLE_ROWS", 5, int)
ENV_BATCH_SIZE = env("BATCH_SIZE", 20, int)   # ya no se usa para trocear globalmente; lo mantengo por compat
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


def build_retrieval_query(table_name, info):
    """
    Construye una query de texto para el RAG a partir de la tabla y sus columnas.
    """
    col_desc = "; ".join(
        f"{c['name']} ({c['llm_type']}, mysql={c['mysql_column_type']})"
        for c in info["columns"]
    )
    return (
        "Clasificación de columnas de una tabla MySQL según GDPR, LOPDGDD y guías AEPD "
        "en identificador_directo, cuasi_identificador, atributo_sensible y no_sensible. "
        f"Tabla: {table_name}. Columnas: {col_desc}"
    )


def build_context_block(chunks, max_chunks=3, max_chars_per_chunk=1200):
    """
    Convierte los chunks recuperados del RAG en un bloque de texto para el prompt,
    recortando para que no se dispare el tamaño.
    """
    lines = []
    for i, ch in enumerate(chunks[:max_chunks], start=1):
        src = ch.get("metadata", {}).get("source", "desconocido")
        text = ch["text"].strip()
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "..."
        lines.append(f"--- CONTEXTO {i} (source={src}) ---")
        lines.append(text)
        lines.append("")  # línea en blanco
    return "\n".join(lines)



# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Extrae columnas de MySQL y genera predictions.json llamando a Ollama (por tabla).")
    ap.add_argument("--host", default=ENV_HOST)
    ap.add_argument("--port", type=int, default=ENV_PORT)
    ap.add_argument("--user", default=ENV_USER)
    ap.add_argument("--password", default=ENV_PASS)
    ap.add_argument("--database", default=ENV_NAME, help="schema de MySQL (table_schema)")
    ap.add_argument("--table_like", default=ENV_TABLE_LIKE, help="patrón LIKE para table_name")
    ap.add_argument("--sample_rows", type=int, default=ENV_SAMPLE_ROWS, help="muestras por columna (máx)")
    ap.add_argument("--batch_size", type=int, default=ENV_BATCH_SIZE, help="(compat) no se usa para mezclar tablas")
    ap.add_argument("--model", default=ENV_MODEL)
    ap.add_argument("--ollama_url", default=ENV_OLLAMA_URL)
    ap.add_argument("--out_predictions", default=ENV_OUT_PRED)
    ap.add_argument("--sleep_s", type=float, default=ENV_SLEEP_S, help="pausa entre peticiones")
    ap.add_argument("--use_rag", action="store_true", help="activar RAG para enriquecer el prompt con contexto")
    args = ap.parse_args()
    rag_client = RAGClient() if args.use_rag else None


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

    # 1b) PKs y FKs
    cur.execute("""
        SELECT TABLE_NAME, COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA=%s AND CONSTRAINT_NAME='PRIMARY'
    """, (args.database,))
    pk_map = {}
    for r in cur.fetchall():
        pk_map.setdefault(r["TABLE_NAME"], set()).add(r["COLUMN_NAME"])

    cur.execute("""
        SELECT k.TABLE_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE k
        WHERE k.TABLE_SCHEMA=%s AND k.REFERENCED_TABLE_NAME IS NOT NULL
    """, (args.database,))
    fk_map = {}
    for r in cur.fetchall():
        fk_map.setdefault(r["TABLE_NAME"], []).append({
            "column": r["COLUMN_NAME"],
            "ref_table": r["REFERENCED_TABLE_NAME"],
            "ref_column": r["REFERENCED_COLUMN_NAME"],
        })

    # 2) Agrupar por tabla, con stats + muestras
    tables = {}
    for c in cols:
        t   = c.get("table_name",  c.get("TABLE_NAME"))
        col = c.get("column_name", c.get("COLUMN_NAME"))
        dt  = c.get("data_type",   c.get("DATA_TYPE"))
        ct  = c.get("column_type", c.get("COLUMN_TYPE"))
        nul = c.get("is_nullable", c.get("IS_NULLABLE"))

        # contar filas y nulls/distinct para la columna
        cur.execute(f"SELECT COUNT(*) AS n, SUM(CASE WHEN `{col}` IS NULL THEN 1 ELSE 0 END) AS n_null FROM `{t}`")
        r = cur.fetchone() or {}
        n_all = r.get("n", 0) or 0
        n_null = r.get("n_null", 0) or 0

        try:
            cur.execute(f"SELECT COUNT(DISTINCT `{col}`) AS n_dist FROM `{t}`")
            r2 = cur.fetchone() or {}
            n_dist = r2.get("n_dist", 0) or 0
        except Exception:
            n_dist = None

        # muestras (non-null)
        samples = []
        try:
            cur.execute(f"SELECT `{col}` as v FROM `{t}` WHERE `{col}` IS NOT NULL LIMIT %s", (args.sample_rows,))
            samples = [mask_value(rr["v"]) for rr in cur.fetchall()]
        except Exception:
            pass

        llm_type = map_mysql_type(dt, ct)

        tables.setdefault(t, {"row_count": None, "columns": []})
        tables[t]["columns"].append({
            "name": col,
            "mysql_data_type": dt,
            "mysql_column_type": ct,
            "llm_type": llm_type,
            "is_nullable": nul,
            "n_all": n_all,
            "n_null": n_null,
            "n_distinct": n_dist,
            "samples": samples,
            "is_pk": (col in pk_map.get(t, set())),
            "is_fk": any(fk["column"] == col for fk in fk_map.get(t, []))
        })

    # filas por tabla
    for t in tables.keys():
        try:
            cur.execute(f"SELECT COUNT(*) AS n FROM `{t}`")
            tables[t]["row_count"] = (cur.fetchone() or {}).get("n", 0)
        except Exception:
            tables[t]["row_count"] = None

    cur.close(); conn.close()

    # 3) Prompt por tabla y llamada a Ollama

    SYSTEM_PROMPT = """Eres experto en anonimización (GDPR, LOPDGDD y guías de la AEPD).
Clasifica CADA columna en EXACTAMENTE UNA categoría:
- identificador_directo
- cuasi_identificador
- atributo_sensible
- no_sensible

Devuelve SOLO JSON con:
{
  "items": [
    {
      "name":"string",
      "category":"identificador_directo|cuasi_identificador|atributo_sensible|no_sensible",
      "rationale":"string",
      "confidence":0.0
    }
  ]
}

"""

    all_items = []

    for t, info in tables.items():
        lines = [SYSTEM_PROMPT]

        # --- RAG: recuperar contexto y añadirlo al prompt, si está activado ---
        if rag_client is not None:
            query = build_retrieval_query(t, info)
            ctx_chunks = rag_client.retrieve_context(query, k=3)
            context_block = build_context_block(ctx_chunks, max_chunks=3, max_chars_per_chunk=1200)

            lines.append("Tienes acceso al siguiente CONTEXTO relevante sobre anonimización y clasificación de columnas:")
            lines.append("[CONTEXTO]")
            lines.append(context_block)

        # --- resto de prompt, como antes ---
        lines.append(f"Tabla: {t} (filas ~ {info['row_count']})")
        # esquema resumido con marcas
        lines.append("Esquema:")
        for c in info["columns"]:
            marks = []
            if c["is_pk"]: marks.append("PK")
            if c["is_fk"]: marks.append("FK")
            mark = f" [{' ,'.join(marks)}]" if marks else ""
            lines.append(f"- {c['name']} ({c['llm_type']} | {c['mysql_column_type']}){mark}")

        # evidencia por columna
        lines.append("\nEvidencia por columna:")
        for c in info["columns"]:
            null_pct = round((c['n_null']/c['n_all']*100), 2) if c['n_all'] else 0
            lines.append(f"{c['name']}: distinct={c['n_distinct']}, null_pct={null_pct}, muestras={json.dumps(c['samples'], ensure_ascii=False)}")

        prompt = "\n".join(lines)

        try:
            print(prompt)
            print("AQUI TERMINA EL PROMPT")
            txt = call_ollama(prompt, model=args.model, ollama_url=args.ollama_url).strip()
            print("AQUI EMPIEZA LA RESPUESTA")
            print(txt)
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] No puedo conectar con Ollama en {args.ollama_url}. ¿Has ejecutado 'ollama serve' o levantado el contenedor?")
            sys.exit(2)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Tabla {t}: fallo llamando a Ollama: {e}")
            continue
        except Exception as e:
            print(f"[WARN] Tabla {t}: error inesperado llamando a Ollama: {e}")
            continue

        # parseo robusto
        items = []
        try:
            j = json.loads(txt)
            items = j.get("items", [])
        except Exception:
            m = re.search(r"\{[\s\S]*\}", txt)
            if m:
                try:
                    j = json.loads(m.group(0))
                    items = j.get("items", [])
                except Exception:
                    items = []

        # recolectar
        for it in items:
            all_items.append({
                "table": t,
                "name": it.get("name",""),
                "category": it.get("category",""),
                "rationale": it.get("rationale",""),
                "confidence": it.get("confidence", None)
            })

        time.sleep(args.sleep_s)

    # 4) escribir predictions.json
    with open(args.out_predictions, "w", encoding="utf-8") as f:
        json.dump({"items": all_items}, f, ensure_ascii=False, indent=2)

    print(f"[OK] Generado {args.out_predictions} con {len(all_items)} items.")

if __name__ == "__main__":
    main()
