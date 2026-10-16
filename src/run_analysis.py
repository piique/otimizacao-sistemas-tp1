"""Driver de analise completa do TP1 - misc03.

Executa, em sequencia:
  1. Leitura da instancia (MPS + CSV).
  2. Modelagem com PuLP.
  3. Relaxacao linear (Simplex via CBC) -> Z_relax, tempo, fracionarias.
  4. Solucao inteira via CBC (Branch and Bound do solver) -> Z_ip, tempo.
  5. Branch and Bound proprio -> arvore, nos, podas, convergencia.
  6. Metricas de integrality gap.
  7. Figuras.

Salva resultados em results/resumo.json e figuras em figures/.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from branch_and_bound import BranchAndBound
from model_misc03 import build_pulp_model, load_instance, solve
from visualization import (plot_convergence, plot_first_levels, plot_fractional_solution,
                           plot_full_tree)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MPS = os.path.join(ROOT, "data", "misc03.mps")
FIGDIR = os.path.join(ROOT, "figures")
RESDIR = os.path.join(ROOT, "results")


def main() -> None:
    os.makedirs(FIGDIR, exist_ok=True)
    os.makedirs(RESDIR, exist_ok=True)

    model = load_instance(MPS)
    n_int = len(model.integer_cols)
    n_cont = len(model.columns) - n_int
    n_rows = len(model.rows) - 1
    n_nz = sum(1 for c in model.col_coeffs.values() for r in c if r != model.obj_name)

    print("=" * 70)
    print(f"Instancia {model.name}: {len(model.columns)} variaveis "
          f"({n_int} inteiras, {n_cont} continua), {n_rows} restricoes, {n_nz} nao-zeros")
    print("=" * 70)

    # --- 3. Relaxacao linear (Simplex) ---
    prob_lp, _ = build_pulp_model(model, relax=True)
    res_lp = solve(prob_lp)
    frac = {k: v for k, v in res_lp.variables.items() if abs(v - round(v)) > 1e-6}
    print(f"\n[Relaxacao linear | CBC Simplex]")
    print(f"  Z_relax = {res_lp.objective:.4f}   tempo = {res_lp.solve_time * 1000:.1f} ms")
    print(f"  variaveis fracionarias = {len(frac)} / {n_int}")

    # --- 4. Solucao inteira via CBC ---
    prob_ip, _ = build_pulp_model(model, relax=False)
    res_ip = solve(prob_ip)
    print(f"\n[Solucao inteira | CBC Branch and Bound]")
    print(f"  Z_ip = {res_ip.objective:.4f}   tempo = {res_ip.solve_time:.3f} s")

    # --- 5. Branch and Bound proprio ---
    bb = BranchAndBound(model, max_nodes=200000, verbose=False)
    res_bb = bb.solve()
    by_status: dict[str, int] = {}
    for n in res_bb.nodes:
        by_status[n.status] = by_status.get(n.status, 0) + 1
    print(f"\n[Branch and Bound proprio | DFS, ramificacao mais-fracionaria]")
    print(f"  Z_bb = {res_bb.optimal_value:.4f}   prova de otimalidade = {res_bb.proven_optimal}")
    print(f"  nos = {len(res_bb.nodes)}   LPs = {res_bb.n_lp_solves}   tempo = {res_bb.total_time:.3f} s")
    print(f"  status dos nos = {by_status}")
    print(f"  profundidade maxima = {max(n.depth for n in res_bb.nodes)}")

    # --- 6. Integrality gap ---
    assert res_ip.objective is not None and res_lp.objective is not None
    gap_abs = res_ip.objective - res_lp.objective
    gap_rel = 100.0 * gap_abs / abs(res_ip.objective)
    print(f"\n[Integrality gap]")
    print(f"  Z_ip - Z_relax = {gap_abs:.4f}")
    print(f"  gap relativo   = {gap_rel:.2f}%")

    # --- 7. Figuras ---
    plot_first_levels(res_bb.nodes, 3, os.path.join(FIGDIR, "arvore_3niveis.png"))
    plot_full_tree(res_bb.nodes, os.path.join(FIGDIR, "arvore_completa.png"))
    plot_convergence(res_bb.incumbent_history, os.path.join(FIGDIR, "convergencia.png"))
    plot_fractional_solution(res_lp.variables, model.integer_cols,
                             os.path.join(FIGDIR, "fracionarias.png"), z_lp=res_lp.objective)

    root = res_bb.nodes[0]
    level1 = [n for n in res_bb.nodes if n.depth == 1]
    level2 = [n for n in res_bb.nodes if n.depth == 2]
    level3 = [n for n in res_bb.nodes if n.depth == 3]

    resumo = {
        "instancia": {
            "nome": model.name,
            "variaveis": len(model.columns),
            "variaveis_inteiras": n_int,
            "variaveis_continuas": n_cont,
            "restricoes": n_rows,
            "nao_zeros": n_nz,
            "sentinela_mps": model.metadata,
        },
        "relaxacao_linear": {
            "Z_relax": res_lp.objective,
            "tempo_s": res_lp.solve_time,
            "status": res_lp.status,
            "n_fracionarias": len(frac),
            "fracionarias": frac,
        },
        "inteiro_cbc": {
            "Z_ip": res_ip.objective,
            "tempo_s": res_ip.solve_time,
            "status": res_ip.status,
        },
        "branch_and_bound_proprio": {
            "Z_bb": res_bb.optimal_value,
            "proven_optimal": res_bb.proven_optimal,
            "nos": len(res_bb.nodes),
            "lps_resolvidos": res_bb.n_lp_solves,
            "tempo_s": res_bb.total_time,
            "status_nos": by_status,
            "profundidade_maxima": max(n.depth for n in res_bb.nodes),
            "raiz": {"node_id": root.node_id, "lp_bound": root.lp_bound, "status": root.status},
            "nivel_1": [{"node_id": n.node_id, "bound": n.lp_bound, "status": n.status,
                         "var": n.branch_var, "dir": n.branch_dir} for n in level1],
            "nivel_2": [{"node_id": n.node_id, "bound": n.lp_bound, "status": n.status,
                         "var": n.branch_var, "dir": n.branch_dir} for n in level2],
            "nivel_3": [{"node_id": n.node_id, "bound": n.lp_bound, "status": n.status,
                         "var": n.branch_var, "dir": n.branch_dir} for n in level3],
            "historico_incumbente": res_bb.incumbent_history,
            "solucao": {k: v for k, v in (res_bb.optimal_solution or {}).items() if abs(v) > 1e-9},
        },
        "integrality_gap": {
            "absoluto": gap_abs,
            "relativo_pct": gap_rel,
        },
    }

    with open(os.path.join(RESDIR, "resumo.json"), "w") as fh:
        json.dump(resumo, fh, indent=2, ensure_ascii=False)

    print(f"\nResumo salvo em results/resumo.json")
    print(f"Figuras salvas em figures/")


if __name__ == "__main__":
    main()
