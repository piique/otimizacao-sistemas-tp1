"""Visualizacao da arvore de Branch and Bound e figuras do relatorio.

Gera:
  - figures/arvore_3niveis.png  : 3 primeiros niveis de ramificacao com bounds
  - figures/arvore_completa.png : arvore completa (busca DFS), colorida por status
  - figures/convergencia.png    : evolucao do incumbente ao longo dos nos
  - figures/fracionarias.png    : histograma da solucao da relaxacao linear
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from branch_and_bound import BBNode

STATUS_COLORS = {
    "fractional": "#4C72B0",
    "integer": "#55A868",
    "pruned_bound": "#C44E52",
    "infeasible": "#8C8C8C",
}

STATUS_LABELS = {
    "fractional": "fracionario (ramifica)",
    "integer": "inteiro (viavel)",
    "pruned_bound": "podado por bound",
    "infeasible": "inviavel",
}


def _children_map(nodes: list[BBNode]) -> dict[int, list[int]]:
    return {n.node_id: n.children for n in nodes}


def subtree_first_levels(nodes: list[BBNode], max_depth: int) -> list[BBNode]:
    by_id = {n.node_id: n for n in nodes}
    selected: list[BBNode] = []
    stack = [nodes[0].node_id]
    while stack:
        nid = stack.pop()
        node = by_id[nid]
        if node.depth > max_depth:
            continue
        selected.append(node)
        for c in node.children:
            stack.append(c)
    selected.sort(key=lambda n: (n.depth, n.node_id))
    return selected


def _layout_positions(nodes: list[BBNode]) -> dict[int, tuple[float, float]]:
    """Layout binario classico: posicao horizontal pela rota desde a raiz."""
    by_id = {n.node_id: n for n in nodes}
    pos: dict[int, tuple[float, float]] = {}

    def walk(node: BBNode, x: float, width: float) -> None:
        pos[node.node_id] = (x, -node.depth)
        kids = [by_id[c] for c in node.children if c in by_id]
        kids.sort(key=lambda n: (0 if n.branch_dir == "<=" else 1, n.node_id))
        if not kids:
            return
        n_kids = len(kids)
        for i, kid in enumerate(kids):
            offset = width * (i - (n_kids - 1) / 2) / max(n_kids, 1)
            walk(kid, x + offset, width / 2)

    walk(nodes[0], 0.0, 8.0)
    return pos


def plot_first_levels(nodes: list[BBNode], max_depth: int, path: str,
                      title: str | None = None) -> list[BBNode]:
    selected = subtree_first_levels(nodes, max_depth)
    pos = _layout_positions(selected)
    fig, ax = plt.subplots(figsize=(16, 9))

    for node in selected:
        x, y = pos[node.node_id]
        if node.parent_id is not None and node.parent_id in pos:
            px, py = pos[node.parent_id]
            ax.plot([px, x], [py, y], color="#999999", lw=1.4, zorder=1)

    for node in selected:
        x, y = pos[node.node_id]
        color = STATUS_COLORS.get(node.status, "#333333")
        bound = "inf" if node.lp_bound is None else f"{node.lp_bound:.1f}"
        ax.scatter([x], [y], s=2100, color=color, edgecolors="black", zorder=3)
        ax.text(x, y + 0.10, f"#{node.node_id}", ha="center", va="bottom",
                fontsize=11, fontweight="bold", zorder=4)
        ax.text(x, y - 0.06, f"Z={bound}", ha="center", va="top", fontsize=10, zorder=4)
        if node.branch_var is not None:
            ax.text(x, y - 0.40, f"{node.branch_var}\n{node.branch_dir}{node.branch_bound:.0f}",
                    ha="center", va="top", fontsize=8.5, color="#333333", zorder=4)

    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markeredgecolor="black",
                          label=STATUS_LABELS[s], markersize=13)
               for s, c in STATUS_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=11)
    ax.set_title(title or f"Arvore de Branch and Bound - {max_depth} primeiros niveis",
                 fontsize=14)
    ax.set_xlabel("ordem horizontal na arvore", fontsize=11)
    ax.set_ylabel("nivel (profundidade)", fontsize=11)
    ax.set_yticks([-d for d in range(max_depth + 1)])
    ax.set_yticklabels([f"nivel {d}" for d in range(max_depth + 1)], fontsize=10)
    ax.get_xaxis().set_visible(False)
    ax.grid(axis="y", ls=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return selected


def plot_full_tree(nodes: list[BBNode], path: str, max_plot_nodes: int = 1500) -> None:
    if len(nodes) > max_plot_nodes:
        nodes = nodes[:max_plot_nodes]
    by_id = {n.node_id: n for n in nodes}
    pos = _layout_positions(nodes)
    fig, ax = plt.subplots(figsize=(22, 10))
    for node in nodes:
        if node.parent_id is not None and node.parent_id in pos:
            px, py = pos[node.parent_id]
            x, y = pos[node.node_id]
            ax.plot([px, x], [py, y], color="#BBBBBB", lw=0.4, zorder=1)
    xs = [pos[n.node_id][0] for n in nodes]
    ys = [pos[n.node_id][1] for n in nodes]
    colors = [STATUS_COLORS.get(n.status, "#333333") for n in nodes]
    ax.scatter(xs, ys, s=18, c=colors, zorder=3)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=STATUS_LABELS[s], markersize=8)
               for s, c in STATUS_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=9)
    ax.set_title(f"Arvore de Branch and Bound completa ({len(nodes)} nos)")
    ax.set_xlabel("ordem horizontal")
    ax.set_ylabel("nivel (profundidade)")
    ax.grid(axis="y", ls=":", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_convergence(history: list[tuple[int, float]], path: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    if history:
        xs = [h[0] for h in history]
        ys = [h[1] for h in history]
        ax.step(xs, ys, where="post", color="#55A868", lw=2)
        ax.scatter(xs, ys, color="#55A868", zorder=3)
        for x, y in history:
            ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(4, 5), fontsize=8)
    ax.set_xlabel("no em que o incumbente foi encontrado")
    ax.set_ylabel("valor do incumbente Z")
    ax.set_title("Evolucao do incumbente durante o Branch and Bound")
    ax.grid(ls=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_fractional_solution(values: dict[str, float], integer_cols: list[str], path: str,
                             z_lp: float | None = None) -> None:
    int_set = set(integer_cols)
    frac_vals = [v for c, v in values.items() if c in int_set and abs(v - round(v)) > 1e-6]
    int_vals = [v for c, v in values.items() if c in int_set and abs(v - round(v)) <= 1e-6]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].hist(frac_vals, bins=10, range=(0, 1), color="#4C72B0", edgecolor="black")
    axes[0].set_title(f"Solucao da relaxacao linear: {len(frac_vals)} variaveis fracionarias")
    axes[0].set_xlabel("valor da variavel")
    axes[0].set_ylabel("frequencia")
    counts = {0.0: int_vals.count(0.0), 1.0: int_vals.count(1.0)}
    axes[1].bar(["0 (inteiras)", "1 (inteiras)", "fracionarias"],
                [counts[0.0], counts[1.0], len(frac_vals)],
                color=["#8C8C8C", "#55A868", "#4C72B0"], edgecolor="black")
    axes[1].set_title("Classificacao das variaveis binarias" +
                      (f" (Z_LP = {z_lp:.1f})" if z_lp is not None else ""))
    axes[1].set_ylabel("quantidade")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
