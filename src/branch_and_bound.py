"""Branch and Bound proprio para o problema misc03 (0-1 puro).

Implementacao didatica com solucao exata da relaxacao linear em cada no via
Simplex (solver HiGHS, atraves de scipy.optimize.linprog). Registra a arvore de
busca completa para permitir desenhar os primeiros niveis e analisar as podas.

Estrategias:
  - Busca em profundidade (DFS) com ramificacao na variavel mais fracionaria.
  - Poda por limitante (bound): se o limitante do no >= incumbente (minimizacao),
    o no e podado.
  - Poda por integralidade: solucao inteira vira novo incumbente.
  - Poda por inviabilidade: LP infactivel.
  - Incumbente inicial opcional (ex.: arredondamento da relaxacao linear).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog

from mps_parser import MPSModel, parse_mps


@dataclass
class BBNode:
    node_id: int
    parent_id: int | None
    depth: int
    branch_var: str | None
    branch_dir: str | None          # "<=" ou ">="
    branch_bound: float | None
    lp_bound: float | None          # valor da relaxacao linear no no
    solution: dict[str, float] | None
    status: str                     # "fractional" | "integer" | "pruned_bound" | "infeasible"
    children: list[int] = field(default_factory=list)


@dataclass
class BBResult:
    optimal_value: float | None
    optimal_solution: dict[str, float] | None
    nodes: list[BBNode]
    n_lp_solves: int
    total_time: float
    incumbent_history: list[tuple[int, float]]
    proven_optimal: bool


def _most_fractional(sol: np.ndarray, integer_idx: list[int], tol: float = 1e-6) -> tuple[int, float] | None:
    best_idx: int | None = None
    best_val = 0.0
    best_dist = 0.5 + tol
    for i in integer_idx:
        val = sol[i]
        frac = abs(val - round(val))
        if frac > tol:
            dist = abs(frac - 0.5)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_val = val
    if best_idx is None:
        return None
    return best_idx, best_val


class BranchAndBound:
    def __init__(self, model: MPSModel, max_nodes: int = 100000, time_limit: float | None = None,
                 verbose: bool = False, initial_incumbent: dict[str, float] | None = None):
        self.model = model
        self.max_nodes = max_nodes
        self.time_limit = time_limit
        self.verbose = verbose

        self.cols = list(model.columns)
        self.colidx = {c: i for i, c in enumerate(self.cols)}
        n = len(self.cols)

        self.c = np.array([model.obj_coeffs.get(col, 0.0) for col in self.cols], dtype=float)
        self._integer_idx = [self.colidx[c] for c in model.integer_cols]

        self.base_bounds: list[tuple[float | None, float | None]] = []
        for col in self.cols:
            lo, hi = model.bounds.get(col, (0.0, float("inf")))
            lo = None if lo == float("-inf") else lo
            hi = None if hi == float("inf") else hi
            self.base_bounds.append((lo, hi))

        rows = [r for r in model.rows if r != model.obj_name]
        a_ub, b_ub, a_eq, b_eq = [], [], [], []
        for r in rows:
            row = np.zeros(n)
            for col, entries in model.col_coeffs.items():
                if r in entries:
                    row[self.colidx[col]] = entries[r]
            t = model.row_types[r]
            rhs = model.rhs.get(r, 0.0)
            if t == "L":
                a_ub.append(row); b_ub.append(rhs)
            elif t == "G":
                a_ub.append(-row); b_ub.append(-rhs)
            else:
                a_eq.append(row); b_eq.append(rhs)
        self.A_ub = np.array(a_ub) if a_ub else None
        self.b_ub = np.array(b_ub) if b_ub else None
        self.A_eq = np.array(a_eq) if a_eq else None
        self.b_eq = np.array(b_eq) if b_eq else None

        self.nodes: list[BBNode] = []
        self.n_lp_solves = 0
        self.incumbent: float | None = None
        self.incumbent_sol: dict[str, float] | None = None
        self.incumbent_history: list[tuple[int, float]] = []

        if initial_incumbent is not None:
            self.incumbent = float(sum(self.c[self.colidx[c]] * v for c, v in initial_incumbent.items()))
            self.incumbent_sol = dict(initial_incumbent)

    def _solve_lp(self, bounds: list[tuple[float | None, float | None]]):
        res = linprog(self.c, A_ub=self.A_ub, b_ub=self.b_ub, A_eq=self.A_eq, b_eq=self.b_eq,
                      bounds=bounds, method="highs")
        self.n_lp_solves += 1
        if res.status != 0:
            return None, None
        return float(res.fun), np.asarray(res.x, dtype=float)

    def solve(self) -> BBResult:
        start = time.perf_counter()
        root_bounds = list(self.base_bounds)
        stack: list[tuple[int | None, int, str | None, str | None, float | None,
                        list[tuple[float | None, float | None]]]] = [
            (None, 0, None, None, None, root_bounds)
        ]

        proven_optimal = True
        while stack:
            if self.time_limit is not None and (time.perf_counter() - start) > self.time_limit:
                proven_optimal = False
                break
            if len(self.nodes) >= self.max_nodes:
                proven_optimal = False
                break

            parent_id, depth, bvar, bdir, bbound, bounds = stack.pop()
            obj, sol = self._solve_lp(bounds)
            node_id = len(self.nodes)

            if obj is None:
                self._add_node(BBNode(node_id, parent_id, depth, bvar, bdir, bbound,
                                      None, None, "infeasible"), parent_id)
                continue

            if self.incumbent is not None and obj >= self.incumbent - 1e-6:
                self._add_node(BBNode(node_id, parent_id, depth, bvar, bdir, bbound,
                                      obj, None, "pruned_bound"), parent_id)
                continue

            frac = _most_fractional(sol, self._integer_idx)
            if frac is None:
                self._add_node(BBNode(node_id, parent_id, depth, bvar, bdir, bbound,
                                      obj, self._sol_dict(sol), "integer"), parent_id)
                if self.incumbent is None or obj < self.incumbent - 1e-9:
                    self.incumbent = obj
                    self.incumbent_sol = self._sol_dict(sol)
                    self.incumbent_history.append((node_id, obj))
                    if self.verbose:
                        print(f"  no {node_id}: novo incumbente Z = {obj:.2f}")
                continue

            fi, fval = frac
            self._add_node(BBNode(node_id, parent_id, depth, bvar, bdir, bbound,
                                  obj, self._sol_dict(sol), "fractional"), parent_id)

            floor_val = float(np.floor(fval))
            ceil_val = float(np.ceil(fval))

            # ramo x >= ceil(fval): eleva o limite inferior.
            # Empilhado primeiro para que o DFS explore antes o ramo x <= floor.
            hi_child = list(bounds)
            lo_c, hi_c = hi_child[fi]
            hi_child[fi] = (max(lo_c, ceil_val) if lo_c is not None else ceil_val, hi_c)
            stack.append((node_id, depth + 1, self.cols[fi], ">=", ceil_val, hi_child))

            # ramo x <= floor(fval): reduz o limite superior.
            lo_child = list(bounds)
            lo_c, hi_c = lo_child[fi]
            lo_child[fi] = (lo_c, min(hi_c, floor_val) if hi_c is not None else floor_val)
            stack.append((node_id, depth + 1, self.cols[fi], "<=", floor_val, lo_child))

        total = time.perf_counter() - start
        return BBResult(self.incumbent, self.incumbent_sol, self.nodes,
                        self.n_lp_solves, total, self.incumbent_history, proven_optimal)

    def _add_node(self, node: BBNode, parent_id: int | None) -> None:
        self.nodes.append(node)
        if parent_id is not None:
            self.nodes[parent_id].children.append(node.node_id)

    def _sol_dict(self, sol: np.ndarray) -> dict[str, float]:
        return {col: float(sol[i]) for i, col in enumerate(self.cols)}


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, "src")

    ap = argparse.ArgumentParser()
    ap.add_argument("mps")
    ap.add_argument("--max-nodes", type=int, default=100000)
    ap.add_argument("--time-limit", type=float, default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    m = parse_mps(args.mps)
    bb = BranchAndBound(m, max_nodes=args.max_nodes, time_limit=args.time_limit, verbose=args.verbose)
    res = bb.solve()
    print(f"Otimo inteiro = {res.optimal_value}")
    print(f"Prova de otimalidade = {res.proven_optimal}")
    print(f"Nos explorados = {len(res.nodes)}  |  LPs resolvidos = {res.n_lp_solves}")
    print(f"Tempo total = {res.total_time:.3f}s")
    by_status: dict[str, int] = {}
    for n in res.nodes:
        by_status[n.status] = by_status.get(n.status, 0) + 1
    print("Status dos nos:", by_status)
    print("Profundidade maxima:", max(n.depth for n in res.nodes))
