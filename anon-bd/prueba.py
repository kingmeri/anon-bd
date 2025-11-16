 #!/usr/bin/env python3
# Aprender cortes no solapados para una columna numérica (p.ej., Age)
# Estrategia: cuantiles iniciales -> fusionar bins hasta que cada bin tenga >= MIN_ROWS_PER_BIN

import numpy as np
import pandas as pd

# ========= PARÁMETROS (edita aquí) =========
INPUT_FILE_PATH      = "data.csv"   # ruta al CSV de entrada
COLUMN_NAME          = "Age"        # nombre de la columna numérica
TARGET_INITIAL_BINS  = 12           # nº de bins iniciales (cuantiles)
MIN_ROWS_PER_BIN     = 10           # k mínimo por bin
# ==========================================

def compute_quantile_edges(values: np.ndarray, target_bins: int) -> list[float]:
    """Bordes iniciales por cuantiles (equal-frequency), sin duplicados."""
    quantiles = np.linspace(0, 1, num=max(2, target_bins) + 1)
    edges = np.unique(np.quantile(values, quantiles, method="nearest")).astype(float).tolist()
    if len(edges) < 2:  # columna constante
        edges = [float(values.min()), float(values.max())]
    return edges

def count_rows_per_bin(values: np.ndarray, edges: list[float]) -> np.ndarray:
    """Cuenta cuántos valores caen en cada bin [e[i], e[i+1])."""
    bin_index = np.searchsorted(edges, values, side="right") - 1
    bin_index = np.clip(bin_index, 0, len(edges) - 2)
    return np.bincount(bin_index, minlength=len(edges) - 1)

def merge_bin_with_neighbor(edges: list[float], i: int) -> list[float]:
    """Fusiona el bin i con un vecino (derecha si existe, si no izquierda)."""
    if len(edges) <= 2:
        return edges[:]
    new_edges = edges[:]
    # si i no es el último bin, elimina el borde de la derecha; si lo es, elimina el borde de la izquierda
    if i < len(edges) - 2:
        del new_edges[i + 1]
    else:
        del new_edges[i]
    return new_edges

def enforce_min_rows_per_bin(values: np.ndarray, edges: list[float], min_rows: int) -> list[float]:
    """Fusiona bins adyacentes hasta que todos tengan al menos 'min_rows' filas."""
    e = edges[:]
    while True:
        counts = count_rows_per_bin(values, e)
        if len(counts) == 0:
            return e
        small_bins = np.where(counts < min_rows)[0]
        if len(small_bins) == 0:
            return e
        e = merge_bin_with_neighbor(e, int(small_bins[0]))

def main():
    # Cargar datos
    df = pd.read_csv(INPUT_FILE_PATH)
    if COLUMN_NAME not in df.columns:
        raise SystemExit(f"La columna '{COLUMN_NAME}' no existe en {INPUT_FILE_PATH}.")
    values = df[COLUMN_NAME].dropna().astype(float).to_numpy()
    if values.size == 0:
        raise SystemExit("La columna está vacía tras eliminar NaN.")

    # 1) Edges iniciales por cuantiles
    initial_edges = compute_quantile_edges(values, TARGET_INITIAL_BINS)

    # 2) Asegurar mínimo k por bin (fusionando adyacentes)
    final_edges = enforce_min_rows_per_bin(values, initial_edges, MIN_ROWS_PER_BIN)

    # 3) Contar y mostrar resultado
    counts = count_rows_per_bin(values, final_edges)
    print("CORTES FINALES (edges):")
    print(final_edges)
    print("\nBINS (intervalo : nº filas):")
    for i in range(len(final_edges) - 1):
        a, b = final_edges[i], final_edges[i + 1]
        print(f"[{a} – {b}) : {int(counts[i])}")

if __name__ == "__main__":
    main()
