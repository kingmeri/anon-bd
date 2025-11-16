#!/usr/bin/env python3
import csv, argparse, os

def norm(s):
    return (s or "").strip().lower()

def sniff_reader(fh, sample_size=4096, fallback_delimiter=","):
    sample = fh.read(sample_size)
    fh.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",",";","|","\t"])
    except Exception:
        class SimpleDialect(csv.excel):
            delimiter = fallback_delimiter
        dialect = SimpleDialect()
    return dialect

def read_unique_values(csv_path, col):
    seen = {}
    out  = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        dialect = sniff_reader(f)
        r = csv.DictReader(f, dialect=dialect)
        if col not in r.fieldnames:
            raise ValueError(f"La columna '{col}' no existe en {csv_path}. Columnas: {r.fieldnames}")
        for row in r:
            v = (row[col] or "").strip()
            if v and v not in seen:
                seen[v] = True
                out.append(v)
    return out

def read_dictionary(dict_csv):
    """
    Acepta cabeceras:
      - municipio / localidad  (cualquiera de las dos)
      - provincia
      - ccaa
    Delimitador detectado automáticamente (',' o ';', etc).
    Devuelve dict: key=municipio(lower), value=(provincia, ccaa) con nombres originales.
    """
    with open(dict_csv, "r", encoding="utf-8-sig", newline="") as f:
        dialect = sniff_reader(f)
        r = csv.DictReader(f, dialect=dialect)

        # Columnas esperadas (case-insensitive). Permitimos 'localidad' como alias de 'municipio'.
        cols_lower = { (c or "").strip().lower(): c for c in r.fieldnames if c }
        municipio_col = cols_lower.get("municipio") or cols_lower.get("localidad")
        provincia_col = cols_lower.get("provincia")
        ccaa_col      = cols_lower.get("ccaa")

        if not (municipio_col and provincia_col and ccaa_col):
            raise ValueError(
                "El diccionario debe tener columnas municipio/localidad, provincia y ccaa.\n"
                f"Encontradas: {r.fieldnames}\n"
                "Ejemplos válidos de cabecera: "
                "['municipio;provincia;ccaa'], ['localidad;provincia;ccaa;país'], ['municipio,provincia,ccaa']"
            )

        d = {}
        for row in r:
            mun  = (row[municipio_col] or "").strip()
            prov = (row[provincia_col] or "").strip()
            ccaa = (row[ccaa_col] or "").strip()
            if not mun:
                continue
            d[norm(mun)] = (prov, ccaa)
    return d

def write_hierarchy(values, dictionary, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    missing = []
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        # niveles: municipio -> provincia -> ccaa -> root
        w.writerow(["level0","level1","level2","root"])
        for mun in values:
            key = norm(mun)
            if key not in dictionary:
                missing.append(mun)
                continue
            prov, ccaa = dictionary[key]
            w.writerow([mun, prov, ccaa, "*"])
    if missing:
        raise RuntimeError(
            "Faltan mapeos en el diccionario para los siguientes municipios/localidades:\n  - " +
            "\n  - ".join(missing)
        )

def main():
    ap = argparse.ArgumentParser(
        description="Genera jerarquía ARX para localidades (municipio/localidad → provincia → ccaa), siempre deduplicada."
    )
    ap.add_argument("--input",      required=True, help="CSV de datos")
    ap.add_argument("--col",        required=True, help="Nombre de la columna de municipio/localidad en el CSV de datos")
    ap.add_argument("--dictionary", required=True, help="CSV diccionario con columnas municipio/localidad,provincia,ccaa (delimitador auto)")
    ap.add_argument("--output",     required=True, help="Ruta del CSV de jerarquía")
    args = ap.parse_args()

    uniques = read_unique_values(args.input, args.col)
    uniques.sort()
    dictionary = read_dictionary(args.dictionary)
    write_hierarchy(uniques, dictionary, args.output)
    print(f"OK: jerarquía localidades → {args.output} ({len(uniques)} hojas únicas)")

if __name__ == "__main__":
    main()
