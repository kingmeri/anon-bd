#!/usr/bin/env python3
# Genera cortes NO solapados para Age (cuantiles + fusión hasta >= k por bin)
# y exporta la jerarquía multinivel en formato compatible con ARX.

import numpy as np
import pandas as pd

# ========= PARÁMETROS (edita aquí) =========
INPUT_FILE_PATH       = "age.csv"            # CSV de entrada con columna Age
AGE_COLUMN_NAME       = "Age"                 # nombre de la columna numérica
TARGET_INITIAL_BINS   = 12                    # nº de bins iniciales (cuantiles)
MIN_ROWS_PER_BIN_K    = 10                    # k mínimo por bin
OUTPUT_HIERARCHY_CSV  = "age_hierarchy.csv"   # CSV de jerarquía para ARX
# ==========================================

# ---------- Utilidades de binning ----------
def compute_quantile_edges(values: np.ndarray, target_bins: int) -> list[float]:
    """Bordes iniciales por cuantiles (equal-frequency), sin duplicados."""
    quantiles = np.linspace(0, 1, num=max(2, target_bins) + 1)
    # method="nearest" para valores enteros típicos de edades
    edges = np.unique(np.quantile(values, quantiles, method="nearest")).astype(float).tolist()
    if len(edges) < 2:
        vmin = float(values.min()); vmax = float(values.max())
        edges = [vmin, vmax if vmax > vmin else vmin + 1.0]
    return edges

def count_rows_per_bin(values: np.ndarray, edges: list[float]) -> np.ndarray:
    """Cuenta filas por bin [e[i], e[i+1])."""
    bin_index = np.searchsorted(edges, values, side="right") - 1
    bin_index = np.clip(bin_index, 0, len(edges) - 2)
    return np.bincount(bin_index, minlength=len(edges) - 1)

def merge_bin_with_neighbor(edges: list[float], i: int) -> list[float]:
    """Fusiona el bin i con un vecino (derecha si existe, si no izquierda)."""
    if len(edges) <= 2:
        return edges[:]
    merged = edges[:]
    if i < len(edges) - 2:
        # une i con su vecino derecho => elimina el borde derecho de i
        del merged[i + 1]
    else:
        # i es el último bin => une con el izquierdo => elimina el borde izquierdo de i
        del merged[i]
    return merged

def enforce_min_rows_per_bin(values: np.ndarray, edges: list[float], min_rows: int) -> list[float]:
    """Fusiona bins adyacentes hasta que todos tengan al menos 'min_rows' filas."""
    e = edges[:]
    while True:
        counts = count_rows_per_bin(values, e)
        if len(counts) == 0:
            return e
        small = np.where(counts < min_rows)[0]
        if len(small) == 0:
            return e
        e = merge_bin_with_neighbor(e, int(small[0]))

def build_hierarchy_levels(all_edges_fine: list[float]) -> list[list[float]]:
    """Crea niveles fusionando bins adyacentes hasta llegar a un único bin (raíz)."""
    levels = [all_edges_fine[:]]
    current = all_edges_fine[:]
    while len(current) > 2:  # mientras haya >= 2 bins
        new_edges = [current[0]]
        i = 1
        while i < len(current) - 1:
            new_edges.append(current[i + 1])  # fusiona en pares
            i += 2
        if new_edges[-1] != current[-1]:
            new_edges[-1] = current[-1]
        current = new_edges
        levels.append(current[:])
    return levels  # [nivel_fino, nivel_medio, ..., nivel_raiz]

def interval_labels_from_edges(edges: list[float]) -> list[str]:
    """Convierte edges en etiquetas '[a–b)' para cada bin."""
    labels = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        labels.append(f"[{a}–{b})")
    return labels

def find_bin_index_for_value(value: float, edges: list[float]) -> int:
    """Devuelve el índice del bin en 'edges' tal que value ∈ [e[j], e[j+1])."""
    j = np.searchsorted(edges, value, side="right") - 1
    return int(np.clip(j, 0, len(edges) - 2))

# ---------- Export a jerarquía ARX ----------
def write_arx_hierarchy_csv(levels_edges: list[list[float]], out_path: str):
    """
    Escribe un CSV de jerarquía compatible con ARX:
    - Filas: cada bin del nivel fino (level0).
    - Columnas: level0 (fino), level1 (más general), ..., levelN (raíz).
    """
    fine_edges = levels_edges[0]
    fine_labels = interval_labels_from_edges(fine_edges)

    # Prepara etiquetas por nivel
    level_labels = []
    for e in levels_edges:
        level_labels.append(interval_labels_from_edges(e))

    # Para cada bin fino, construimos su "camino" hacia arriba:
    rows = []
    for i, fine_label in enumerate(fine_labels):
        # tomamos el límite inferior del bin fino como referencia para localizarlo en niveles superiores
        lower_bound = fine_edges[i]
        row = [fine_label]  # empieza por level0
        for lvl in range(1, len(levels_edges)):
            parent_edges = levels_edges[lvl]
            parent_labels = interval_labels_from_edges(parent_edges)
            parent_bin = find_bin_index_for_value(lower_bound, parent_edges)
            row.append(parent_labels[parent_bin])
        rows.append(row)

    # Construir DataFrame y guardar CSV
    col_names = [f"level{idx}" for idx in range(len(levels_edges))]
    pd.DataFrame(rows, columns=col_names).to_csv(out_path, index=False)

# ---------------------- MAIN ----------------------
def main():
    # 1) Cargar datos
    df = pd.read_csv(INPUT_FILE_PATH)
    if AGE_COLUMN_NAME not in df.columns:
        raise SystemExit(f"La columna '{AGE_COLUMN_NAME}' no existe en {INPUT_FILE_PATH}.")
    values = df[AGE_COLUMN_NAME].dropna().astype(float).to_numpy()
    if values.size == 0:
        raise SystemExit("La columna está vacía tras eliminar NaN.")

    # 2) Edges iniciales por cuantiles
    initial_edges = compute_quantile_edges(values, TARGET_INITIAL_BINS)

    # 3) Asegurar k mínimo por bin (fusionando adyacentes)
    final_edges = enforce_min_rows_per_bin(values, initial_edges, MIN_ROWS_PER_BIN_K)

    # 4) Mostrar resultado básico en consola
    counts = count_rows_per_bin(values, final_edges)
    print("CORTES FINALES (edges):")
    print(final_edges)
    print("\nBINS (intervalo : nº filas):")
    for i in range(len(final_edges) - 1):
        a, b = final_edges[i], final_edges[i + 1]
        print(f"[{a} – {b}) : {int(counts[i])}")

    # 5) Construir jerarquía multinivel y exportar a ARX
    levels_edges = build_hierarchy_levels(final_edges)
    write_arx_hierarchy_csv(levels_edges, OUTPUT_HIERARCHY_CSV)
    print(f"\nJerarquía ARX guardada en: {OUTPUT_HIERARCHY_CSV}")
    print("Columnas: level0 (fino) -> ... -> último nivel (raíz)")

if __name__ == "__main__":
    main()
