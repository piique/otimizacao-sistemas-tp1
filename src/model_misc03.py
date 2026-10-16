"""Modelagem do problema misc03 (MIPLIB 2017) com PuLP.

Le a instancia em formato MPS, monta o modelo de programacao linear inteira
(PLI), resolve a relaxacao linear (Simplex) e a solucao inteira (Branch and
Bound do CBC), e devolve estatisticas para o relatorio.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pulp

from mps_parser import MPSModel, parse_mps


@dataclass
class SolveResult:
    status: str
    objective: float | None
    variables: dict[str, float]
    solve_time: float
    solver_name: str
    is_integer: bool = False


def load_instance(path: str) -> MPSModel:
    return parse_mps(path)


def _pulp_bound(value: float) -> float | None:
    """PuLP representa limite infinito como None (nao como float inf)."""
    return None if value in (float("inf"), float("-inf")) else value


def build_pulp_model(model: MPSModel, relax: bool = False) -> tuple[pulp.LpProblem, dict[str, pulp.LpVariable]]:
    """Monta o LpProblem do PuLP a partir do MPS.

    Se relax=True, todas as variaveis ficam continuas (relaxacao linear).
    Caso contrario, variaveis marcadas como inteiras permanecem inteiras.
    """
    sense = pulp.LpMinimize if model.sense == "min" else pulp.LpMaximize
    prob = pulp.LpProblem(model.name or "MIP", sense)

    integer_set = set(model.integer_cols)
    variables: dict[str, pulp.LpVariable] = {}

    for col in model.columns:
        lo, hi = model.bounds.get(col, (0.0, float("inf")))
        lo = _pulp_bound(lo)
        hi = _pulp_bound(hi)
        is_int = (col in integer_set) and not relax
        if is_int:
            variables[col] = pulp.LpVariable(col, lowBound=lo, upBound=hi, cat=pulp.LpInteger)
        else:
            variables[col] = pulp.LpVariable(col, lowBound=lo, upBound=hi, cat=pulp.LpContinuous)

    obj_terms = [model.obj_coeffs[c] * variables[c] for c in model.columns if c in model.obj_coeffs]
    prob += pulp.lpSum(obj_terms), "Z"

    rhs_by_row: dict[str, float] = {r: model.rhs.get(r, 0.0) for r in model.rows if r != model.obj_name}
    row_coeffs: dict[str, dict[str, float]] = {r: {} for r in rhs_by_row}
    for col, entries in model.col_coeffs.items():
        for r, val in entries.items():
            if r in row_coeffs:
                row_coeffs[r][col] = val

    for r in rhs_by_row:
        rtype = model.row_types[r]
        expr = pulp.lpSum(row_coeffs[r][c] * variables[c] for c in row_coeffs[r])
        rhs = rhs_by_row[r]
        if rtype == "L":
            prob += expr <= rhs, r
        elif rtype == "G":
            prob += expr >= rhs, r
        elif rtype == "E":
            prob += expr == rhs, r

    return prob, variables


def solve(prob: pulp.LpProblem, time_limit: float | None = None, gap_rel: float | None = None,
          msg: bool = False) -> SolveResult:
    solver = pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit, gapRel=gap_rel, threads=1)
    start = time.perf_counter()
    status = prob.solve(solver)
    elapsed = time.perf_counter() - start

    status_str = pulp.LpStatus[status]
    obj = pulp.value(prob.objective) if status_str == "Optimal" or prob.objective is not None else None
    values = {v.name: (v.varValue if v.varValue is not None else 0.0) for v in prob.variables()}
    return SolveResult(status_str, obj, values, elapsed, "CBC", is_integer=False)


def fractional_variables(values: dict[str, float], tol: float = 1e-6) -> dict[str, float]:
    return {k: v for k, v in values.items() if abs(v - round(v)) > tol}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("mps")
    args = ap.parse_args()

    m = load_instance(args.mps)
    print(f"Instancia {m.name}: {len(m.columns)} variaveis, {len(m.rows) - 1} restricoes, "
          f"{len(m.integer_cols)} inteiras")

    prob_lp, _ = build_pulp_model(m, relax=True)
    res_lp = solve(prob_lp)
    print(f"[LP relaxado] Z = {res_lp.objective:.4f}  status={res_lp.status}  "
          f"tempo={res_lp.solve_time:.4f}s")
    frac = fractional_variables(res_lp.variables)
    print(f"  variaveis fracionarias: {len(frac)} / {len(res_lp.variables)}")

    prob_ip, _ = build_pulp_model(m, relax=False)
    res_ip = solve(prob_ip)
    print(f"[IP]          Z = {res_ip.objective:.4f}  status={res_ip.status}  "
          f"tempo={res_ip.solve_time:.4f}s")
