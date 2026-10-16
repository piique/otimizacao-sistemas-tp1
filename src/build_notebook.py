"""Gera o notebook Colab autocontido do TP1 a partir de celulas Python/Markdown.

O notebook embutido nao depende dos arquivos em src/: ele baixa a instancia
MIPLIB misc03, converte para CSV, modela com PuLP, resolve a relaxacao linear e o
PLI, roda um Branch and Bound proprio com scipy/HiGHS e desenha a arvore.
"""

from __future__ import annotations

import nbformat as nbf

CELLS: list[tuple[str, str]] = []
md = lambda s: CELLS.append(("markdown", s))
code = lambda s: CELLS.append(("code", s))


# --------------------------------------------------------------------------
md(r"""[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/piique/otimizacao-sistemas-tp1/blob/main/notebooks/TP1_misc03.ipynb)

# TP1 - Resolução de Problemas Lineares Inteiros via Simplex e Branch and Bound

**Instância:** `misc03` — MIPLIB 2017 (Benchmark Set)

**Integrantes:** Pedro Henrique Vilaça Valverde, Gabriel Batista

**Disciplina:** Otimização de Sistemas — PUC Minas

---

Este notebook está organizado conforme as *Atividades a Desenvolver* do enunciado:

1. Síntese do problema
2. Resultados fornecidos por IAs (3 ferramentas) — **único tópico com uso de IA**
3. Leitura da instância de benchmark (CSV)
4. Modelagem matemática
5. Relaxação linear (Simplex)
6. Branch and Bound (árvore de busca, solução ótima inteira)
7. Análise crítica: *integrality gap* e poda de ramos
8. Discussão e comparação com a solução das IAs

> ▶️ **Como executar:** no Colab, use **Ambiente de execução → Executar tudo** (*Runtime → Run all*).
> O notebook instala o PuLP automaticamente e roda o projeto completo (download da instância,
> modelagem, Simplex, Branch and Bound e figuras). Não é necessária nenhuma chave de IA.
""")

md(r"""## 1. Síntese do problema (máx. 5 linhas)

A instância `misc03` pertence ao *Benchmark Set* do MIPLIB 2017 e foi submetida por
Greg Astfalk (Convex Computer Corporation); sua aplicação original não é divulgada.
Trata-se de um **problema puro de programação inteira 0-1**: 160 variáveis de decisão,
das quais 159 são binárias e 1 é contínua livre, distribuídas em 96 restrições lineares
(27 de igualdade, 38 "≤" e 31 "≥") e 2.053 coeficientes não-nulos.
A função objetivo, de minimização, é o valor de uma única variável de folga contínua
(`COL160`) que fecha uma igualdade de balanço de custos, enquanto as binárias
selecionam combinações e respeitam cotas de capacidade e cobertura.
Na relaxação linear o ótimo é **Z = 1910,0**; a solução inteira ótima é **Z = 3360,0**,
evidenciando um *integrality gap* de cerca de **43%** que motiva o uso de Branch and Bound.
""")

md(r"""## 2. Solução dada por diferentes IAs

### 2.1 Desenho do experimento

Três IAs foram avaliadas em **dois modos**, totalizando seis respostas para a mesma
instância. Referência da equipe: $Z_{LP} = 1910{,}00$, $Z_{IP} = 3360{,}00$, gap 43,15%.

| IA (modelo) | Modo não-agêntico | Modo agêntico |
|---|---|---|
| GLM 5.3 (`glm-5.3`) | apenas texto | cria e executa código |
| DeepSeek V4.1 Flash (`deepseek-v4.1-flash`) | apenas texto | cria e executa código |
| Kimi K2.7 Code (`kimi-k2.7-code`) | apenas texto | cria e executa código |

- **Não-agêntico:** dados embutidos no prompt; resposta só em texto (sem ferramentas).
- **Agêntico:** recebe os CSVs e pode escrever/executar Python (PuLP + CBC) em container
  Docker isolado, **sem internet**.

### 2.2 Modo não-agêntico

| IA | Z_LP | Z_IP | Gap (%) | Resultado |
|---|---|---|---|---|
| GLM 5.3 | 3360,00 | 3360,00 | 0,00 | ✘ Assumiu a relaxação LP já inteira. |
| DeepSeek V4.1 Flash | 3360,00 | 3360,00 | 0,00 | ✘ Idem: afirmou politopo integral. |
| Kimi K2.7 Code | 1916,30 | 3360,00 | 42,97 | ≈ Único a reconhecer gap não nulo. |
| **Equipe (referência)** | **1910,00** | **3360,00** | **43,15** | CBC/HiGHS (Seções 5–7). |

**GLM e DeepSeek erraram o valor da relaxação** (reportaram 3360, o próprio ótimo inteiro)
e zeraram o gap, assumindo integralidade sem resolver o LP. Kimi aproximou ($Z_{LP}
\approx 1916{,}3$, gap 42,97%). Nenhum executou de fato Simplex ou B&B.

### 2.3 Modo agêntico

| IA | Z_LP | Z_IP | Gap (%) | Resultado |
|---|---|---|---|---|
| GLM 5.3 | 1910,00 | 3360,00 | 43,15 | ✔ Correto |
| DeepSeek V4.1 Flash | 1910,00 | 3360,00 | 43,15 | ✔ Correto |
| Kimi K2.7 Code | 1910,00 | 3360,00 | 43,15 | ✔ Correto |
| **Equipe (referência)** | **1910,00** | **3360,00** | **43,15** | CBC/HiGHS (Seções 5–7). |

**Os três acertaram.** Cada modelo montou o modelo no PuLP a partir dos CSVs e resolveu
com o CBC, relatando métricas coerentes (350 nós, 22.739 iterações simplex).

### 2.4 O ponto central

| IA | $Z_{LP}$ sem código | $Z_{LP}$ com código |
|---|---|---|
| GLM 5.3 | 3360,00 ✘ | 1910,00 ✔ |
| DeepSeek V4.1 Flash | 3360,00 ✘ | 1910,00 ✔ |
| Kimi K2.7 Code | 1916,30 ≈ | 1910,00 ✔ |

A limitação **não é de conhecimento** (todos explicam relaxação, gap e poda), mas de
**cálculo**: sem solver, inferem "a matriz parece integral" e erram; com código, delegam
ao CBC e acertam.

### 2.5 Metodologia

As IAs foram usadas **exclusivamente** neste tópico; **nenhum valor numérico** foi
incorporado (tudo recalculado com CBC/HiGHS nas Seções 5–7).

- **Interface:** Ollama Cloud (plano Pro), 25/09/2026 (não-agêntico) e 16/10/2026 (agêntico).
- **Não-agêntico:** agente sem ferramentas.
- **Agêntico:** código executado em **container Docker isolado**, com apenas os CSVs
  montados e **sem internet** (impede consultar a resposta publicada e força a resolução).
- **Registro:** `report/ai_answers/nao_agentico/` e `report/ai_answers/agentico/`.
""")

md(r"""## 3. Leitura da instância de benchmark

Baixamos o arquivo MPS da instância (cópia oficial no repositório do solver SCIP),
fazemos o *parsing*, exportamos três CSVs e lemos o CSV de volta — atendendo ao
requisito "leitura da instância (provavelmente um csv)".
""")

code(r'''# Dependencias: no Colab o pulp nao vem instalado; scipy/pandas/matplotlib/numpy ja vem.
import importlib, subprocess, sys

def ensure(pkg, imp=None):
    imp = imp or pkg
    try:
        importlib.import_module(imp)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

ensure("pulp")

import os, re, json, time, csv, urllib.request
from collections import Counter
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import pulp
from scipy.optimize import linprog
import matplotlib
import matplotlib.pyplot as plt

print("pulp", pulp.__version__)
print("solvers disponiveis:", pulp.listSolvers(onlyAvailable=True))
''')

code(r'''# --- Download da instancia misc03 (MIPLIB 2017) ---
MPS_URLS = [
    "https://raw.githubusercontent.com/scipopt/scip/master/check/instances/MIP/misc03.mps",
    "https://raw.githubusercontent.com/h-g-s/cbc-test-set/master/misc03.mps.gz",
]
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
MPS_PATH = os.path.join(DATA_DIR, "misc03.mps")

def download_instance():
    last_err = None
    for url in MPS_URLS:
        try:
            if url.endswith(".gz"):
                import gzip, io
                raw = urllib.request.urlopen(url, timeout=30).read()
                text = gzip.decompress(raw).decode("latin-1")
            else:
                text = urllib.request.urlopen(url, timeout=30).read().decode("latin-1")
            with open(MPS_PATH, "w") as fh:
                fh.write(text)
            print("Baixado de", url)
            return
        except Exception as e:
            last_err = e
    # fallback: upload manual no Colab
    print("Falha no download automatico:", last_err)
    from google.colab import files  # type: ignore
    uploaded = files.upload()
    for name, content in uploaded.items():
        with open(MPS_PATH, "wb") as fh:
            fh.write(content)
        print("Enviado:", name)

if not os.path.exists(MPS_PATH):
    download_instance()

with open(MPS_PATH) as fh:
    head = "".join(fh.readlines()[:16])
print(head)
''')

code(r'''# --- Parser MPS minimalista (sem dependencias externas) ---
@dataclass
class MPSModel:
    name: str = ""
    sense: str = "min"
    obj_name: str = ""
    obj_coeffs: dict = field(default_factory=dict)
    row_types: dict = field(default_factory=dict)
    rhs: dict = field(default_factory=dict)
    col_coeffs: dict = field(default_factory=dict)
    bounds: dict = field(default_factory=dict)
    integer_cols: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def columns(self):
        return list(self.col_coeffs.keys())

    @property
    def rows(self):
        return list(self.row_types.keys())

def parse_mps(path):
    lines = open(path).readlines()
    model = MPSModel()
    for line in lines:
        m = re.match(r"\*([A-Z ]+):\s*(.*)", line)
        if m:
            model.metadata[m.group(1).strip()] = m.group(2).strip()

    section, current_col, current_int, in_int = None, None, False, False
    for line in lines:
        if not line.strip() or line.lstrip().startswith("*"):
            continue
        tok = line.split()
        head = tok[0].upper()
        if head == "NAME":
            section = "NAME"; model.name = tok[1] if len(tok) > 1 else ""; continue
        if head == "ENDATA":
            break
        if head in ("ROWS", "COLUMNS", "RHS", "RANGES", "BOUNDS"):
            section = head; continue
        if head == "OBJSENSE":
            section = "OBJSENSE"; continue

        if section == "OBJSENSE":
            model.sense = "max" if tok[0].upper().startswith("MAX") else "min"; continue

        if section == "ROWS":
            rtype, rname = tok[0].upper(), tok[1]
            model.row_types[rname] = rtype
            if rtype == "N":
                model.obj_name = rname
            continue

        if section == "COLUMNS":
            if "MARKER" in line:
                if "INTORG" in line.upper():
                    in_int = True
                elif "INTEND" in line.upper():
                    in_int = False
                continue
            col = tok[0]
            if current_col != col:
                current_col = col; current_int = in_int
                if current_int and col not in model.integer_cols:
                    model.integer_cols.append(col)
                model.col_coeffs.setdefault(col, {})
            pairs = tok[1:]
            for i in range(0, len(pairs) - 1, 2):
                rname = pairs[i]
                try:
                    val = float(pairs[i + 1])
                except ValueError:
                    continue
                if rname == model.obj_name:
                    model.obj_coeffs[col] = model.obj_coeffs.get(col, 0.0) + val
                else:
                    model.col_coeffs[col][rname] = model.col_coeffs[col].get(rname, 0.0) + val
            continue

        if section in ("RHS", "RANGES"):
            pairs = tok[1:]
            for i in range(0, len(pairs) - 1, 2):
                model.rhs[pairs[i]] = float(pairs[i + 1])
            continue

        if section == "BOUNDS":
            btype, col = tok[0].upper(), tok[2]
            val = float(tok[3]) if len(tok) > 3 else 0.0
            lo, hi = model.bounds.get(col, (0.0, float("inf")))
            if btype == "UP": hi = val
            elif btype == "LO": lo = val
            elif btype == "FX": lo = hi = val
            elif btype == "FR": lo, hi = float("-inf"), float("inf")
            elif btype == "MI": lo = float("-inf")
            elif btype == "PL": hi = float("inf")
            elif btype == "BV":
                lo, hi = 0.0, 1.0
                if col not in model.integer_cols: model.integer_cols.append(col)
            elif btype in ("LI", "UI"):
                if btype == "LI": lo = val
                else: hi = val
                if col not in model.integer_cols: model.integer_cols.append(col)
            model.bounds[col] = (lo, hi)
            continue

    for col in model.col_coeffs:
        model.bounds.setdefault(col, (0.0, float("inf")))
    return model

model = parse_mps(MPS_PATH)
n_int = len(model.integer_cols)
n_rows = len(model.rows) - 1
n_nz = sum(1 for c in model.col_coeffs.values() for r in c if r != model.obj_name)
print(f"Instancia {model.name}: {len(model.columns)} variaveis ({n_int} inteiras), "
      f"{n_rows} restricoes, {n_nz} nao-zeros")
print("Metadados MPS:", model.metadata)
''')

code(r'''# --- Exporta a instancia para CSV (representacao esparsa) ---
VAR_CSV = os.path.join(DATA_DIR, "misc03_variables.csv")
CON_CSV = os.path.join(DATA_DIR, "misc03_constraints.csv")
COE_CSV = os.path.join(DATA_DIR, "misc03_coefficients.csv")

int_set = set(model.integer_cols)
with open(VAR_CSV, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["column", "lower", "upper", "is_integer", "obj_coeff"])
    for col in model.columns:
        lo, hi = model.bounds.get(col, (0.0, float("inf")))
        w.writerow([col, lo, hi, int(col in int_set), model.obj_coeffs.get(col, 0.0)])

with open(CON_CSV, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["constraint", "type", "rhs"])
    for r, t in model.row_types.items():
        if r != model.obj_name:
            w.writerow([r, t, model.rhs.get(r, 0.0)])

with open(COE_CSV, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["constraint", "column", "value"])
    for col, entries in model.col_coeffs.items():
        for r, val in entries.items():
            if r != model.obj_name:
                w.writerow([r, col, val])

# --- Leitura dos CSVs (requisito do enunciado) ---
df_vars = pd.read_csv(VAR_CSV)
df_cons = pd.read_csv(CON_CSV)
df_coef = pd.read_csv(COE_CSV)

print("Variaveis:", df_vars.shape, "| Restricoes:", df_cons.shape, "| Coeficientes:", df_coef.shape)
display(df_vars.head())
display(df_cons.head())
display(df_coef.head())
print("\nContagem por tipo de restricao:")
display(df_cons["type"].value_counts().rename({"L": "<= (L)", "G": ">= (G)", "E": "= (E)"}))
''')

md(r"""## 4. Modelagem matemática

Sejam $x_j$ as variáveis de decisão da instância, com
$x_j \in \{0,1\}$ para as 159 binárias e $x_{160} \in \mathbb{R}$ livre.

**Função objetivo (minimização):**

$$\min\ Z = \sum_{j=1}^{160} c_j\, x_j = x_{160}$$

(o único coeficiente não-nulo é $c_{160}=1$).

**Conjunto de restrições:** para cada linha $i$ do arquivo MPS,

$$\sum_{j} a_{ij}\, x_j \;\{\le,\ \ge,\ =\}\; b_i \qquad i = 1,\dots,96$$

sendo 38 restrições do tipo $\le$, 31 do tipo $\ge$ e 27 igualdades, totalizando
2.053 coeficientes não-nulos. As restrições de integralidade
$x_j \in \{0,1\}$ valem para as 159 variáveis binárias.
""")

code(r'''# --- Modelagem e resolucao com PuLP ---
def build_pulp_model(model, relax=False):
    sense = pulp.LpMinimize if model.sense == "min" else pulp.LpMaximize
    prob = pulp.LpProblem(model.name or "MIP", sense)
    integer_set = set(model.integer_cols)
    var = {}
    for col in model.columns:
        lo, hi = model.bounds.get(col, (0.0, float("inf")))
        lo = None if lo in (float("inf"), float("-inf")) else lo
        hi = None if hi in (float("inf"), float("-inf")) else hi
        is_int = (col in integer_set) and not relax
        var[col] = pulp.LpVariable(col, lowBound=lo, upBound=hi,
                                   cat=pulp.LpInteger if is_int else pulp.LpContinuous)
    prob += pulp.lpSum(model.obj_coeffs.get(c, 0.0) * var[c] for c in model.columns), "Z"

    row_coeffs = {r: {} for r in model.rows if r != model.obj_name}
    for col, entries in model.col_coeffs.items():
        for r, val in entries.items():
            if r in row_coeffs:
                row_coeffs[r][col] = val
    for r in row_coeffs:
        expr = pulp.lpSum(row_coeffs[r][c] * var[c] for c in row_coeffs[r])
        rhs = model.rhs.get(r, 0.0)
        t = model.row_types[r]
        if t == "L": prob += expr <= rhs, r
        elif t == "G": prob += expr >= rhs, r
        else: prob += expr == rhs, r
    return prob, var

def solve_pulp(prob, time_limit=None):
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit, threads=1)
    t0 = time.perf_counter()
    status = prob.solve(solver)
    dt = time.perf_counter() - t0
    name = pulp.LpStatus[status]
    obj = pulp.value(prob.objective) if name == "Optimal" else None
    values = {v.name: (v.varValue if v.varValue is not None else 0.0) for v in prob.variables()}
    return name, obj, values, dt
''')

md(r"""## 5. Relaxação linear (Simplex)

Resolvemos o mesmo modelo **ignorando a integralidade** (todas as variáveis viram
contínuas). O solver CBC usa o método Simplex/dual para resolver o LP.
""")

code(r'''prob_lp, _ = build_pulp_model(model, relax=True)
status_lp, z_lp, sol_lp, t_lp = solve_pulp(prob_lp)
frac = {k: v for k, v in sol_lp.items() if abs(v - round(v)) > 1e-6}

print(f"Status          : {status_lp}")
print(f"Z_relaxado      : {z_lp:.4f}")
print(f"Tempo (Simplex) : {t_lp*1000:.1f} ms")
print(f"Fracionarias    : {len(frac)} de {n_int} binarias")
print("\nValores fracionarios encontrados:")
for k, v in sorted(frac.items()):
    print(f"  {k} = {v:.6f}")
''')

md(r"""## 6. Solução inteira (Branch and Bound)

### 6.1 Branch and Bound do solver CBC

Resolvemos o PLI completo com o CBC (que internamente aplica Branch and Bound).
""")

code(r'''prob_ip, _ = build_pulp_model(model, relax=False)
status_ip, z_ip, sol_ip, t_ip = solve_pulp(prob_ip)
print(f"Status        : {status_ip}")
print(f"Z_inteiro     : {z_ip:.4f}")
print(f"Tempo (CBC B&B): {t_ip:.3f} s")
sol_int = {k: round(v) for k, v in sol_ip.items() if abs(v) > 1e-9}
print(f"Variaveis nao-nulas na solucao otima: {len(sol_int)}")
''')

md(r"""### 6.2 Branch and Bound implementado pela equipe

Implementamos o B&B do zero com:
- **Relaxação linear** em cada nó via Simplex (solver HiGHS, `scipy.optimize.linprog`);
- **Busca em profundidade (DFS)**;
- **Ramificação na variável mais fracionária** ($x_j \le \lfloor x_j^* \rfloor$ e
  $x_j \ge \lceil x_j^* \rceil$);
- **Poda** por limitante (bound $\ge$ incumbente), por integralidade e por inviabilidade.
""")

code(r'''class BBNode:
    def __init__(self, node_id, parent_id, depth, branch_var, branch_dir, branch_bound,
                 lp_bound, solution, status):
        self.node_id = node_id
        self.parent_id = parent_id
        self.depth = depth
        self.branch_var = branch_var
        self.branch_dir = branch_dir
        self.branch_bound = branch_bound
        self.lp_bound = lp_bound
        self.solution = solution
        self.status = status
        self.children = []

class BranchAndBound:
    def __init__(self, model, max_nodes=200000, time_limit=None):
        self.model = model
        self.max_nodes = max_nodes
        self.time_limit = time_limit
        self.cols = list(model.columns)
        self.colidx = {c: i for i, c in enumerate(self.cols)}
        n = len(self.cols)
        self.c = np.array([model.obj_coeffs.get(c, 0.0) for c in self.cols], dtype=float)
        self.int_idx = [self.colidx[c] for c in model.integer_cols]
        self.base_bounds = []
        for col in self.cols:
            lo, hi = model.bounds.get(col, (0.0, float("inf")))
            self.base_bounds.append((None if lo == float("-inf") else lo,
                                     None if hi == float("inf") else hi))
        rows = [r for r in model.rows if r != model.obj_name]
        A_ub, b_ub, A_eq, b_eq = [], [], [], []
        for r in rows:
            row = np.zeros(n)
            for col, entries in model.col_coeffs.items():
                if r in entries:
                    row[self.colidx[col]] = entries[r]
            t, rhs = model.row_types[r], model.rhs.get(r, 0.0)
            if t == "L": A_ub.append(row); b_ub.append(rhs)
            elif t == "G": A_ub.append(-row); b_ub.append(-rhs)
            else: A_eq.append(row); b_eq.append(rhs)
        self.A_ub = np.array(A_ub) if A_ub else None
        self.b_ub = np.array(b_ub) if b_ub else None
        self.A_eq = np.array(A_eq) if A_eq else None
        self.b_eq = np.array(b_eq) if b_eq else None
        self.nodes = []
        self.n_lp = 0
        self.incumbent = None
        self.incumbent_sol = None
        self.history = []

    def _lp(self, bounds):
        res = linprog(self.c, A_ub=self.A_ub, b_ub=self.b_ub, A_eq=self.A_eq, b_eq=self.b_eq,
                      bounds=bounds, method="highs")
        self.n_lp += 1
        if res.status != 0:
            return None, None
        return float(res.fun), np.asarray(res.x)

    @staticmethod
    def _most_fractional(sol, idx, tol=1e-6):
        best, best_dist, best_val = None, 0.5 + tol, 0.0
        for i in idx:
            frac = abs(sol[i] - round(sol[i]))
            if frac > tol:
                d = abs(frac - 0.5)
                if d < best_dist:
                    best, best_dist, best_val = i, d, sol[i]
        return (best, best_val) if best is not None else None

    def solve(self):
        t0 = time.perf_counter()
        stack = [(None, 0, None, None, None, list(self.base_bounds))]
        proven = True
        while stack:
            if self.time_limit and time.perf_counter() - t0 > self.time_limit:
                proven = False; break
            if len(self.nodes) >= self.max_nodes:
                proven = False; break
            parent, depth, bvar, bdir, bbound, bounds = stack.pop()
            obj, sol = self._lp(bounds)
            nid = len(self.nodes)
            if obj is None:
                self._add(BBNode(nid, parent, depth, bvar, bdir, bbound, None, None, "infeasible"), parent)
                continue
            if self.incumbent is not None and obj >= self.incumbent - 1e-6:
                self._add(BBNode(nid, parent, depth, bvar, bdir, bbound, obj, None, "pruned_bound"), parent)
                continue
            frac = self._most_fractional(sol, self.int_idx)
            if frac is None:
                sol_dict = {c: float(sol[i]) for i, c in enumerate(self.cols)}
                self._add(BBNode(nid, parent, depth, bvar, bdir, bbound, obj, sol_dict, "integer"), parent)
                if self.incumbent is None or obj < self.incumbent - 1e-9:
                    self.incumbent, self.incumbent_sol = obj, sol_dict
                    self.history.append((nid, obj))
                continue
            fi, fval = frac
            self._add(BBNode(nid, parent, depth, bvar, bdir, bbound, obj,
                             {c: float(sol[i]) for i, c in enumerate(self.cols)}, "fractional"), parent)
            fl, ce = float(np.floor(fval)), float(np.ceil(fval))
            up = list(bounds); lo_c, hi_c = up[fi]
            up[fi] = (max(lo_c, ce) if lo_c is not None else ce, hi_c)
            stack.append((nid, depth + 1, self.cols[fi], ">=", ce, up))
            dn = list(bounds); lo_c, hi_c = dn[fi]
            dn[fi] = (lo_c, min(hi_c, fl) if hi_c is not None else fl)
            stack.append((nid, depth + 1, self.cols[fi], "<=", fl, dn))
        return proven, time.perf_counter() - t0

    def _add(self, node, parent):
        self.nodes.append(node)
        if parent is not None:
            self.nodes[parent].children.append(node.node_id)

bb = BranchAndBound(model, max_nodes=200000)
proven, t_bb = bb.solve()
by_status = Counter(n.status for n in bb.nodes)
print(f"Z_inteiro (B&B proprio) : {bb.incumbent:.4f}")
print(f"Prova de otimalidade    : {proven}")
print(f"Nos explorados          : {len(bb.nodes)}  (LPs resolvidos: {bb.n_lp})")
print(f"Tempo                   : {t_bb:.3f} s")
print(f"Status dos nos          : {dict(by_status)}")
print(f"Profundidade maxima     : {max(n.depth for n in bb.nodes)}")
''')

md(r"""### 6.3 Árvore de busca (3 primeiros níveis)

Cada nó mostra o valor do limitante (`Z=...`) obtido pela relaxação linear, e a aresta
mostra a variável e o sentido da ramificação. Verde = solução inteira viável,
vermelho = podado por bound, cinza = inviável, azul = fracionário (continua).
""")

code(r'''STATUS_COLORS = {"fractional": "#4C72B0", "integer": "#55A868",
                 "pruned_bound": "#C44E52", "infeasible": "#8C8C8C"}
STATUS_LABELS = {"fractional": "fracionario (ramifica)", "integer": "inteiro (viavel)",
                 "pruned_bound": "podado por bound", "infeasible": "inviavel"}

def first_levels(nodes, max_depth):
    by_id = {n.node_id: n for n in nodes}
    selected, stack = [], [nodes[0].node_id]
    while stack:
        nid = stack.pop(); node = by_id[nid]
        if node.depth > max_depth: continue
        selected.append(node)
        stack.extend(node.children)
    return sorted(selected, key=lambda n: (n.depth, n.node_id))

def layout(nodes):
    by_id = {n.node_id: n for n in nodes}
    pos = {}
    def walk(node, x, width):
        pos[node.node_id] = (x, -node.depth)
        kids = sorted((by_id[c] for c in node.children if c in by_id),
                      key=lambda n: (0 if n.branch_dir == "<=" else 1, n.node_id))
        for i, kid in enumerate(kids):
            off = width * (i - (len(kids) - 1) / 2) / max(len(kids), 1)
            walk(kid, x + off, width / 2)
    walk(nodes[0], 0.0, 8.0)
    return pos

def plot_tree(nodes, max_depth, ax):
    sel = first_levels(nodes, max_depth)
    pos = layout(sel)
    for n in sel:
        if n.parent_id is not None and n.parent_id in pos:
            px, py = pos[n.parent_id]; x, y = pos[n.node_id]
            ax.plot([px, x], [py, y], color="#999999", lw=1.4, zorder=1)
    for n in sel:
        x, y = pos[n.node_id]
        bound = "inf" if n.lp_bound is None else f"{n.lp_bound:.1f}"
        ax.scatter([x], [y], s=2100, color=STATUS_COLORS[n.status], edgecolors="black", zorder=3)
        ax.text(x, y + 0.10, f"#{n.node_id}", ha="center", va="bottom", fontsize=11, fontweight="bold")
        ax.text(x, y - 0.06, f"Z={bound}", ha="center", va="top", fontsize=10)
        if n.branch_var:
            ax.text(x, y - 0.40, f"{n.branch_var}\n{n.branch_dir}{n.branch_bound:.0f}",
                    ha="center", va="top", fontsize=8.5)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markeredgecolor="black",
                          label=STATUS_LABELS[s], markersize=13) for s, c in STATUS_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=11)
    ax.set_title(f"Arvore de Branch and Bound - {max_depth} primeiros niveis", fontsize=14)
    ax.set_ylabel("nivel (profundidade)", fontsize=11)
    ax.set_yticks([-d for d in range(max_depth + 1)])
    ax.set_yticklabels([f"nivel {d}" for d in range(max_depth + 1)])
    ax.get_xaxis().set_visible(False)
    ax.grid(axis="y", ls=":", alpha=0.4)

fig, ax = plt.subplots(figsize=(16, 9))
plot_tree(bb.nodes, 3, ax)
fig.tight_layout()
fig.savefig("arvore_3niveis.png", dpi=160)
plt.show()

print("Nos nos 3 primeiros niveis:")
for n in first_levels(bb.nodes, 3):
    b = "inf" if n.lp_bound is None else f"{n.lp_bound:.2f}"
    ramo = "" if n.branch_var is None else f"  [{n.branch_var} {n.branch_dir} {n.branch_bound:.0f}]"
    print(f"  nivel {n.depth} | no #{n.node_id:3d} | Z={b:>9} | {n.status}{ramo}")
''')

md(r"""**Visão geral da árvore completa** (todos os 961 nós, coloridos por status). O eixo
vertical é a profundidade e o horizontal, a ordem de exploração; serve para visualizar a
forma da busca, não os rótulos individuais.
""")

code(r'''def plot_full_tree(nodes, ax, max_nodes=1500):
    nodes = nodes[:max_nodes]
    pos = layout(nodes)
    for n in nodes:
        if n.parent_id is not None and n.parent_id in pos:
            px, py = pos[n.parent_id]; x, y = pos[n.node_id]
            ax.plot([px, x], [py, y], color="#BBBBBB", lw=0.4, zorder=1)
    ax.scatter([pos[n.node_id][0] for n in nodes], [pos[n.node_id][1] for n in nodes],
               s=18, c=[STATUS_COLORS[n.status] for n in nodes], zorder=3)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=STATUS_LABELS[s], markersize=8)
               for s, c in STATUS_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=9)
    ax.set_title(f"Arvore de Branch and Bound completa ({len(nodes)} nos)")
    ax.set_xlabel("ordem horizontal")
    ax.set_ylabel("nivel (profundidade)")
    ax.grid(axis="y", ls=":", alpha=0.3)

fig, ax = plt.subplots(figsize=(22, 10))
plot_full_tree(bb.nodes, ax)
fig.tight_layout()
fig.savefig("arvore_completa.png", dpi=150)
plt.show()
''')

md(r"""## 7. Análise crítica

### 7.1 Integrality gap

O *integrality gap* mede a perda de qualidade ao exigir integralidade:

$$\text{gap} = \frac{Z_{IP} - Z_{LP}}{|Z_{IP}|} \times 100\%$$
""")

code(r'''gap_abs = z_ip - z_lp
gap_rel = 100 * gap_abs / abs(z_ip)
print(f"Z_LP  = {z_lp:.2f}")
print(f"Z_IP  = {z_ip:.2f}")
print(f"gap absoluto = {gap_abs:.2f}")
print(f"gap relativo = {gap_rel:.2f}%")

fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(["Relaxacao LP", "Solucao inteira (IP)"], [z_lp, z_ip],
       color=["#4C72B0", "#55A868"], edgecolor="black")
ax.annotate(f"{z_lp:.0f}", (0, z_lp), ha="center", va="bottom", fontsize=12)
ax.annotate(f"{z_ip:.0f}", (1, z_ip), ha="center", va="bottom", fontsize=12)
ax.set_ylabel("valor da funcao objetivo Z")
ax.set_title(f"Integrality gap = {gap_rel:.2f}%  (Z_IP - Z_LP = {gap_abs:.0f})")
ax.grid(axis="y", ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig("gap.png", dpi=160)
plt.show()
''')

md(r"""### 7.2 Como o algoritmo podou os ramos

No B&B implementado, cada nó resolve a relaxação linear e fornece um **limitante
inferior** (problema de minimização). Um nó é descartado quando:

1. **Poda por limitante:** $Z_{LP}^{\text{nó}} \ge Z_{\text{incumbente}}$ — não há como
   esse ramo melhorar a melhor solução inteira conhecida.
2. **Poda por inviabilidade:** a relaxação linear é infactível, logo nenhum ponto inteiro
   existe ali.
3. **Poda por integralidade:** a solução do nó já é inteira; ela é comparada ao incumbente
   e o nó é encerrado.

A tabela abaixo resume quantos nós foram encerrados por cada motivo.
""")

code(r'''total = len(bb.nodes)
print(f"{'Motivo':<28}{'Nos':>8}{'%':>9}")
print("-" * 45)
for st, label in [("fractional", "ramificados (fracionarios)"),
                  ("pruned_bound", "podados por bound"),
                  ("infeasible", "podados por inviabilidade"),
                  ("integer", "inteiros (viaveis)")]:
    c = by_status.get(st, 0)
    print(f"{label:<28}{c:>8}{100*c/total:>8.1f}%")
print("-" * 45)
print(f"{'TOTAL':<28}{total:>8}{100.0:>8.1f}%")

fig, ax = plt.subplots(figsize=(9, 5))
if bb.history:
    xs = [h[0] for h in bb.history]; ys = [h[1] for h in bb.history]
    ax.step(xs, ys, where="post", color="#55A868", lw=2)
    ax.scatter(xs, ys, color="#55A868", zorder=3)
    for x, y in bb.history:
        ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(4, 5), fontsize=8)
ax.set_xlabel("no em que o incumbente foi encontrado")
ax.set_ylabel("valor do incumbente Z")
ax.set_title("Evolucao do incumbente durante o Branch and Bound")
ax.grid(ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig("convergencia.png", dpi=160)
plt.show()
''')

md(r"""## 8. Discussão e comparação com as soluções das IAs

Os valores de referência calculados pela equipe foram $Z_{LP}=1910{,}00$ (Simplex, ~8 ms)
e $Z_{IP}=3360{,}00$ (B&B, prova de otimalidade), com *integrality gap* de 43,15%.

### 8.1 Modo não-agêntico (só texto)

| Item | Equipe (ref.) | GLM 5.3 | DeepSeek V4.1 Flash | Kimi K2.7 Code |
|---|---|---|---|---|
| $Z_{LP}$ | 1910,00 | 3360,00 (errado) | 3360,00 (errado) | 1916,30 (aprox.) |
| $Z_{IP}$ | 3360,00 | 3360,00 (ok) | 3360,00 (ok) | 3360,00 (ok) |
| Gap (%) | 43,15 | 0,00 (errado) | 0,00 (errado) | 42,97 (aprox.) |

**Dois dos três modelos de ponta erraram o ponto central** — o valor da relaxação. GLM e
DeepSeek reportaram $Z_{LP}=3360$ (o próprio ótimo inteiro) e concluíram gap nulo,
assumindo que o politopo é integral no ótimo sem resolver o LP. Kimi reconheceu o gap:
$Z_{LP}\approx 1916{,}3$ (real 1910,00) e gap 42,97% (real 43,15%).

### 8.2 Modo agêntico (com código)

| Item | Equipe (ref.) | GLM 5.3 | DeepSeek V4.1 Flash | Kimi K2.7 Code |
|---|---|---|---|---|
| $Z_{LP}$ | 1910,00 | 1910,00 (ok) | 1910,00 (ok) | 1910,00 (ok) |
| $Z_{IP}$ | 3360,00 | 3360,00 (ok) | 3360,00 (ok) | 3360,00 (ok) |
| Gap (%) | 43,15 | 43,15 (ok) | 43,15 (ok) | 43,15 (ok) |

**Os três acertaram.** Cada modelo montou o modelo no PuLP a partir dos CSVs e resolveu
com o CBC, relatando métricas coerentes (350 nós, 22.739 iterações simplex).

### 8.3 O ponto central: saber vs. calcular

| IA | $Z_{LP}$ sem código | $Z_{LP}$ com código |
|---|---|---|
| GLM 5.3 | 3360,00 ✘ | 1910,00 ✔ |
| DeepSeek V4.1 Flash | 3360,00 ✘ | 1910,00 ✔ |
| Kimi K2.7 Code | 1916,30 ≈ | 1910,00 ✔ |

A limitação **não é de conhecimento** (todos explicam relaxação, gap e poda), mas de
**cálculo**: sem solver, inferem "a matriz parece integral" e erram; com código, delegam
ao CBC e acertam.

### 8.4 Explicação do *integrality gap* e árvore/poda

No modo não-agêntico, GLM e DeepSeek concluíram gap nulo e disseram que "o B&B resolve na
raiz"; Kimi foi o único a discutir gap não nulo. No modo agêntico, os três identificaram a
causa real: as 12 variáveis binárias em **0,5** na solução relaxada. Quanto à árvore, no
modo não-agêntico previram "zero ramificações"; no modo agêntico reportaram a árvore real
do CBC (350 nós). A execução da equipe com o B&B próprio explora 961 nós:

| Motivo | Nós | % |
|---|---|---|
| Ramificados (fracionários) | 480 | 49,9% |
| Podados por bound | 345 | 35,9% |
| Podados por inviabilidade | 129 | 13,4% |
| Inteiros (viáveis) | 7 | 0,7% |

### 8.5 Conclusão

- **Útil:** no modo não-agêntico, a descrição estrutural e a explicação conceitual; no modo
  agêntico, os três resolveram corretamente, reproduzindo os valores da equipe.
- **Descartado:** no modo não-agêntico, os valores de $Z_{LP}$ e gap de GLM e DeepSeek.
  Nenhum valor das IAs foi usado; todos foram recalculados com CBC/HiGHS.
- **Lições:** (1) mesmo modelos de ponta, sem solver, erram o valor da relaxação em
  benchmarks reais; (2) com solver, os três acertam — a IA é confiável para *executar* o
  método, não para *adivinhar* a resposta; (3) é indispensável validar contra um solver.
- **Geral:** a IA é poderosa quando **orquestra um solver** (modo agêntico), mas não
  substitui a modelagem e a verificação numérica quando responde só com texto.

### Síntese dos resultados obtidos (equipe)

| Métrica | Valor |
|---|---|
| Variáveis / restrições / não-zeros | 160 / 96 / 2053 |
| Z relaxado (Simplex) | 1910,00 |
| Tempo da relaxação | ~0,008 s |
| Z inteiro ótimo | 3360,00 |
| Tempo CBC | ~1,9 s |
| Tempo B&B próprio | ~1,4 s |
| Nós explorados (B&B próprio) | 961 |
| Integrality gap | ~43,15% |
""")


def build(path: str) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(src) if kind == "markdown" else nbf.v4.new_code_cell(src)
        for kind, src in CELLS
    ]
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
        "colab": {"provenance": [], "toc_visible": True},
    }
    with open(path, "w") as fh:
        nbf.write(nb, fh)
    print(f"Notebook escrito em {path} ({len(CELLS)} celulas)")


if __name__ == "__main__":
    import sys

    build(sys.argv[1] if len(sys.argv) > 1 else "notebooks/TP1_misc03.ipynb")
