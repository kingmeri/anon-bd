#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, re, json, time, os, sys, subprocess
import mysql.connector
import requests
from dotenv import load_dotenv

from rag_client import RAGClient  # seguimos usando el RAG

# Opcional: si quieres seguir usando el modelo base con Ollama
try:
    from llm_client import call_ollama
except ImportError:
    call_ollama = None

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
        "Clasificación de columnas de una tabla MySQL según GDPR, LOPDGDD y guías AEPD"
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


def call_mlx(prompt: str, model: str, adapter_path: str, max_tokens: int = 1024) -> str:
    """
    Llama a mlx_lm.generate con el modelo base de MLX y el adapter LoRA indicado.
    Devuelve el texto generado (stdout).
    """
    cmd = [
        "mlx_lm.generate",
        "--model", model,
        "--adapter-path", adapter_path,
        "--prompt", prompt,
        "--max-tokens", str(max_tokens),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError(
            f"mlx_lm.generate falló con código {proc.returncode}:\n{proc.stderr}"
        )

    return proc.stdout.strip()


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(
        description="Extrae columnas de MySQL y genera predictions.json llamando a un LLM (Ollama o MLX) por tabla."
    )
    ap.add_argument("--host", default=ENV_HOST)
    ap.add_argument("--port", type=int, default=ENV_PORT)
    ap.add_argument("--user", default=ENV_USER)
    ap.add_argument("--password", default=ENV_PASS)
    ap.add_argument("--database", default=ENV_NAME, help="schema de MySQL (table_schema)")
    ap.add_argument("--table_like", default=ENV_TABLE_LIKE, help="patrón LIKE para table_name")
    ap.add_argument("--sample_rows", type=int, default=ENV_SAMPLE_ROWS, help="muestras por columna (máx)")
    ap.add_argument("--batch_size", type=int, default=ENV_BATCH_SIZE, help="(compat) no se usa para mezclar tablas")
    ap.add_argument("--model", default=ENV_MODEL, help="Nombre del modelo (Ollama o MLX, según modo)")
    ap.add_argument("--ollama_url", default=ENV_OLLAMA_URL)
    ap.add_argument("--out_predictions", default=ENV_OUT_PRED)
    ap.add_argument("--sleep_s", type=float, default=ENV_SLEEP_S, help="pausa entre peticiones")
    ap.add_argument("--use_rag", action="store_true", help="activar RAG para enriquecer el prompt con contexto")

    # NUEVO: modo MLX
    ap.add_argument("--use_mlx", action="store_true",
                    help="usar un modelo MLX local con LoRA (en lugar de Ollama)")
    ap.add_argument("--mlx_adapter_path", default="adapters/oyama_50",
                    help="ruta al adapter LoRA de MLX (por defecto adapters/oyama_50)")

    args = ap.parse_args()
    rag_client = RAGClient() if args.use_rag else None

    print(f"[INFO] Conectando a MySQL {args.host}:{args.port} DB={args.database} con usuario '{args.user}'…")

    # conectar
    conn = mysql.connector.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, database=args.database
    )
    cur = conn.cursor(dictionary=True)

    # 1) columnas
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

    # 3) Prompt por tabla y llamada al LLM

    SYSTEM_PROMPT = """Eres experto en anonimización (GDPR, LOPDGDD y guías de la AEPD).

    Tu tarea es: para CADA columna listada en la sección 'Esquema:', decidir
    EXACTAMENTE UNA categoría entre:
    - identificador_directo
    - cuasi_identificador
    - atributo_sensible
    - no_sensible

    Devuelve SOLO JSON, SIN texto adicional, con este formato EXACTO:

    {
    "items": [
        {
        "category": "identificador_directo|cuasi_identificador|atributo_sensible|no_sensible",
        "rationale": "string breve (máx 1 frase)",
        "confidence": 0.0
        }
    ]
    }

    REGLAS IMPORTANTES:
    - Debe haber UN item por cada columna listada en 'Esquema:', en el MISMO orden.
    Es decir:
    - items[0] = primera columna del Esquema
    - items[1] = segunda columna del Esquema
    - etc.
    - NO incluyas ningún campo 'name' ni otros campos distintos a:
    category, rationale, confidence.
    - NO expliques nada fuera del JSON.
    """



    all_items = []

    for t, info in tables.items():
        lines = [SYSTEM_PROMPT]

        # --- RAG: recuperar contexto y añadirlo al prompt, si está activado ---
        if rag_client is not None:
            query = build_retrieval_query(t, info)

            # si quieres, puedes deducir el dominio_hint según la BD o tabla;
            # aquí te pongo un ejemplo fijo de 'rrhh' para bases de empleo/formación:
            domain_hint = "rrhh"  # o None si no lo sabes

            ctx_chunks = rag_client.retrieve_mixed_context(
                query,
                scope="core",
                domain_hint=domain_hint,
                n_defs=1,
                n_ejemplos=2,   # antes 3
                n_casos_borde=1,
                n_dominios=1,
                n_max_total=6,  # un poco más compacto
            )

            context_block = build_context_block(
                ctx_chunks,
                max_chunks=4,   # antes 5
                max_chars_per_chunk=1000,
            )


            context_block = build_context_block(
                ctx_chunks,
                max_chunks=5,
                max_chars_per_chunk=1200,
            )

            lines.append("Tienes acceso al siguiente CONTEXTO relevante sobre anonimización y clasificación de columnas:")
            lines.append("[CONTEXTO]")
            lines.append(context_block)

        # --- resto de prompt, como antes ---
        lines.append(f"Tabla: {t} (filas ~ {info['row_count']})")
        lines.append("Esquema:")
        for c in info["columns"]:
            marks = []
            if c["is_pk"]: marks.append("PK")
            if c["is_fk"]: marks.append("FK")
            mark = f" [{' ,'.join(marks)}]" if marks else ""
            lines.append(f"- {c['name']} ({c['llm_type']} | {c['mysql_column_type']}){mark}")

        lines.append("\nEvidencia por columna:")
        for c in info["columns"]:
            null_pct = round((c['n_null']/c['n_all']*100), 2) if c['n_all'] else 0
            lines.append(f"{c['name']}: distinct={c['n_distinct']}, null_pct={null_pct}, muestras={json.dumps(c['samples'], ensure_ascii=False)}")

        prompt = "\n".join(lines)

        try:
            print(prompt)
            print("AQUI TERMINA EL PROMPT")

            if args.use_mlx:
                # Usar modelo MLX + LoRA afinado
                txt = call_mlx(
                    prompt,
                    model=args.model,
                    adapter_path=args.mlx_adapter_path,
                    max_tokens=1024,
                ).strip()
            else:
                # Usar modelo base vía Ollama (como antes)
                if call_ollama is None:
                    raise RuntimeError("call_ollama no está disponible y --use_mlx es False")
                txt = call_ollama(
                    prompt,
                    model=args.model,
                    ollama_url=args.ollama_url
                ).strip()

            print("AQUI EMPIEZA LA RESPUESTA")
            print(txt)
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] No puedo conectar con Ollama en {args.ollama_url}. ¿Has ejecutado 'ollama serve' o levantado el contenedor?")
            sys.exit(2)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Tabla {t}: fallo llamando a Ollama: {e}")
            continue
        except Exception as e:
            print(f"[WARN] Tabla {t}: error inesperado llamando al modelo: {e}")
            continue

        # parseo robusto
                # ---------- parseo robusto del JSON ----------
        items = []
        cols_this_table = info["columns"]

        # 1) Intento normal: JSON completo
        try:
            j = json.loads(txt)
            items = j.get("items", [])
        except Exception:
            items = []

        # 2) Si falla o items viene vacío, intentamos rescatar objetos sueltos { ... }
        if not items:
            # Buscamos todos los bloques {...} que contengan al menos "category"
            obj_texts = re.findall(
                r'\{[^{}]*"category"\s*:\s*".*?"[^{}]*\}',
                txt,
                flags=re.S
            )
            parsed = []
            for o in obj_texts:
                try:
                    parsed.append(json.loads(o))
                except Exception:
                    continue
            items = parsed

        # ---------- recolección con lógica robusta ----------
        if not items:
            # No hemos podido parsear nada útil:
            # generamos una fila "dummy" por cada columna para que NINGUNA tabla desaparezca.
            print(f"[WARN] Tabla {t}: no se pudo parsear JSON de la respuesta, se generan predicciones vacías por columna.")
            for c in cols_this_table:
                all_items.append({
                    "table": t,
                    "name": c["name"],
                    "category": "",
                    "rationale": "sin_prediccion_parseo_fallido",
                    "confidence": None,
                })
        else:
            # Tenemos items. Usamos SOLO el orden, emparejando columnas ↔ items por índice.
            n_cols = len(cols_this_table)
            n_items = len(items)
            n_common = min(n_cols, n_items)

            # 1) Emparejar las que encajan en longitud
            for c, it in zip(cols_this_table[:n_common], items[:n_common]):
                all_items.append({
                    "table": t,
                    "name": c["name"],  # siempre el nombre real de la columna
                    "category": it.get("category", ""),
                    "rationale": it.get("rationale", ""),
                    "confidence": it.get("confidence", None),
                })

            # 2) Si hay MÁS columnas que items → rellenamos faltantes
            if n_cols > n_items:
                print(f"[WARN] Tabla {t}: hay {n_cols} columnas pero solo {n_items} items, se rellenan las restantes vacías.")
                for c in cols_this_table[n_items:]:
                    all_items.append({
                        "table": t,
                        "name": c["name"],
                        "category": "",
                        "rationale": "sin_prediccion_por_falta_de_items",
                        "confidence": None,
                    })
            # Si hay MÁS items que columnas, los ignoramos (no tenemos a quién asignarlos)


        time.sleep(args.sleep_s)

    # 4) escribir predictions.json
    with open(args.out_predictions, "w", encoding="utf-8") as f:
        json.dump({"items": all_items}, f, ensure_ascii=False, indent=2)

    print(f"[OK] Generado {args.out_predictions} con {len(all_items)} items.")

if __name__ == "__main__":
    main()
