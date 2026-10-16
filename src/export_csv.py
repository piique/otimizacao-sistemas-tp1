"""Converte a instancia MPS para arquivos CSV (representacao esparsa).

Gera tres arquivos em data/:
  - misc03_variables.csv    : coluna, limite inferior, limite superior, inteira?, coef. objetivo
  - misc03_constraints.csv  : restricao, tipo (L/G/E), lado direito (rhs)
  - misc03_coefficients.csv : restricao, coluna, coeficiente  (apenas nao-zeros)

Isso permite "ler a instancia de benchmark" como CSV, conforme o enunciado.
"""

from __future__ import annotations

import csv
import sys

sys.path.insert(0, "src")
from mps_parser import parse_mps

MPS = sys.argv[1] if len(sys.argv) > 1 else "data/misc03.mps"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "data"
STEM = "misc03"


def main() -> None:
    m = parse_mps(MPS)
    int_set = set(m.integer_cols)

    with open(f"{OUTDIR}/{STEM}_variables.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["column", "lower", "upper", "is_integer", "obj_coeff"])
        for col in m.columns:
            lo, hi = m.bounds.get(col, (0.0, float("inf")))
            w.writerow([col, lo, hi, int(col in int_set), m.obj_coeffs.get(col, 0.0)])

    with open(f"{OUTDIR}/{STEM}_constraints.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["constraint", "type", "rhs"])
        for r, t in m.row_types.items():
            if r == m.obj_name:
                continue
            w.writerow([r, t, m.rhs.get(r, 0.0)])

    with open(f"{OUTDIR}/{STEM}_coefficients.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["constraint", "column", "value"])
        for col, entries in m.col_coeffs.items():
            for r, val in entries.items():
                if r == m.obj_name:
                    continue
                w.writerow([r, col, val])

    n_coeff = sum(1 for c in m.col_coeffs.values() for r in c if r != m.obj_name)
    print(f"OK: {len(m.columns)} variaveis, {len(m.rows) - 1} restricoes, "
          f"{n_coeff} coeficientes nao-nulos -> {OUTDIR}/{STEM}_*.csv")


if __name__ == "__main__":
    main()
