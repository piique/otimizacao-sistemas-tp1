import pandas as pd
import pulp
import time

# Leitura dos CSVs
vars_df = pd.read_csv('/work/misc03_variables.csv')
cons_df = pd.read_csv('/work/misc03_constraints.csv')
coefs_df = pd.read_csv('/work/misc03_coefficients.csv')

n = len(vars_df)
m = len(cons_df)

print(f'Variaveis: {n}')
print(f'Restricoes: {m}')
print(f'Coeficientes nao nulos: {len(coefs_df)}')

# Cria dicionario de variaveis no PuLP
var_dict = {}
for _, row in vars_df.iterrows():
    name = row['column']
    lb = row['lower']
    ub = row['upper']
    if ub == float('inf'):
        ub = None
    is_int = bool(row['is_integer'])
    var_dict[name] = pulp.LpVariable(name, lowBound=lb, upBound=ub, cat=pulp.LpBinary if is_int else pulp.LpContinuous)

# Cria o modelo (minimizacao; o MIPLIB e de minimizacao por padrao)
prob = pulp.LpProblem('misc03', pulp.LpMinimize)

# Funcao objetivo
obj_terms = [var_dict[row['column']] * row['obj_coeff'] for _, row in vars_df.iterrows() if row['obj_coeff'] != 0]
prob += pulp.lpSum(obj_terms)

# Agrupa coeficientes por restricao
cons_groups = coefs_df.groupby('constraint')
for _, row in cons_df.iterrows():
    cname = row['constraint']
    ctype = row['type']
    rhs = row['rhs']
    if cname not in cons_groups.groups:
        continue
    cols = cons_groups.get_group(cname)
    expr = pulp.lpSum(var_dict[r['column']] * r['value'] for _, r in cols.iterrows())
    if ctype == 'E':
        prob += expr == rhs, cname
    elif ctype == 'L':
        prob += expr <= rhs, cname
    elif ctype == 'G':
        prob += expr >= rhs, cname

# Resolve a relaxacao linear (sem exigir integralidade)
original_cats = {v.name: v.cat for v in prob.variables()}
for v in prob.variables():
    v.cat = pulp.LpContinuous

print('\n--- RELAXACAO LINEAR ---')
prob.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=300, threads=0))
z_lp = pulp.value(prob.objective)
print(f'Z_LP = {z_lp}')
print(f'Status LP = {pulp.LpStatus[prob.status]}')

# Restaura integralidade e resolve o problema inteiro
for v in prob.variables():
    v.cat = original_cats[v.name]

# Resolve o problema inteiro
print('\n--- PROBLEMA INTEIRO ---')
start = time.time()
prob.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=300, threads=0))
elapsed = time.time() - start
z_ip = pulp.value(prob.objective)
print(f'Z_IP = {z_ip}')
print(f'Status IP = {pulp.LpStatus[prob.status]}')
print(f'Tempo IP = {elapsed:.4f} s')

# GAP
if z_lp is not None and z_ip is not None:
    gap = abs(z_ip - z_lp) / (abs(z_ip) + 1e-12) * 100
    print(f'GAP = {gap:.6f}%')

# Salva log
with open('/work/misc03_solution.txt', 'w') as f:
    f.write(f'Z_LP = {z_lp}\n')
    f.write(f'Z_IP = {z_ip}\n')
    f.write(f'Status IP = {pulp.LpStatus[prob.status]}\n')
    f.write(f'Tempo IP = {elapsed:.4f} s\n')
